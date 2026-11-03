/*
 * esp32_thermal_printer.cpp
 * ESP32-S3 Thermal Printer — Build-up Curve Generator
 * Native ESP-IDF entry point (migrated from esp32_thermal_printer.ino)
 *
 * Migration notes:
 *  - FastLED replaced with the espressif/led_strip managed component
 *    (RMT-backed). setLEDColor() -> led_strip_set_pixel()+refresh().
 *  - USB debug Serial.print -> ESP_LOG macros.
 *  - Arduino loop()'s 'p'/'P' keystroke listener -> a dedicated FreeRTOS
 *    task reading UART0 (the USB-to-serial console), non-blocking with a
 *    timeout so it always yields to the watchdog.
 *  - PrinterSerial (HardwareSerial on UART1) -> native uart_driver_install
 *    on UART_NUM_1, passed into ThermalPrinter via uart_port_t.
 */

#include <cstdio>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "led_strip.h"

#include "ThermalPrinter.h"
#include "BitmapCanvas.h"
#include "GraphGenerator.h"
#include "DataSource.h"
#include "HardcodedDataSource.h"
#include "PICDataSource.h"

static const char *TAG = "ThermalPrinterApp";

// ---------------------------------------------------------------------
// Configuration (mirrors the original sketch's #defines)
// ---------------------------------------------------------------------

// Status LED (onboard WS2812 on most ESP32-S3 dev boards)
#define LED_GPIO_PIN GPIO_NUM_48
#define LED_NUM_PIXELS 1
#define LED_BRIGHTNESS 64 // 0-255

// Printer UART (TM-T88III link)
#define PRINTER_UART_PORT UART_NUM_1
#define PRINTER_TX_PIN GPIO_NUM_17
#define PRINTER_RX_PIN GPIO_NUM_18
#define PRINTER_BAUD 19200

// PIC data-acquisition UART (UART2)
// GPIO 19 (RX) and 20 (TX for ACK back-channel)
#define PIC_UART_PORT UART_NUM_2
#define PIC_RX_PIN GPIO_NUM_19
#define PIC_TX_PIN GPIO_NUM_20
#define PIC_BAUD 115200

// PIC protocol constants
#define PIC_SYNC_0 0xAAU
#define PIC_SYNC_1 0xBBU
#define PIC_SYNC_2 0xCCU
#define PIC_SYNC_3 0xDDU
// #define PIC_MAX_PAYLOAD 1600U // 800 samples × 2 bytes
#define ACK_BYTE 0x06U
#define NACK_BYTE 0x15U
#define PAYLOAD_TIMEOUT_MS 800
#define CRC_TIMEOUT_MS 200

// USB/debug console UART (used for the 'p'/'P' manual-trigger listener)
#define CONSOLE_UART_PORT UART_NUM_0
#define CONSOLE_BAUD 115200

// Graph geometry
#define GRAPH_WIDTH 512 // 496   // must be multiple of 8 (bitmap byte packing)
#define GRAPH_HEIGHT 750
#define LEFT_MARGIN 30
#define TOP_MARGIN 70
#define CANVAS_WIDTH (GRAPH_WIDTH + LEFT_MARGIN + 16)
#define CANVAS_HEIGHT (GRAPH_HEIGHT + TOP_MARGIN + 40)

#define X_MAX 30 // time axis max (seconds)
#define X_STEP 3
#define Y_MAX 2000 // pressure/load axis max
#define Y_STEP 250

#define GRID_X_SPACING 75 // px between horizontal (time) grid lines
#define GRID_Y_SPACING 60 // px between vertical (pressure) grid lines

// ---------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------

static led_strip_handle_t s_led_strip = nullptr;
static ThermalPrinter *printer = nullptr;
static DataSource *dataSource = nullptr;
QueueHandle_t pic_data_queue = nullptr; // defined here, extern'd in PICDataSource.h

// ---------------------------------------------------------------------
// LED status indicators
// ---------------------------------------------------------------------

static void setLEDColor(uint8_t r, uint8_t g, uint8_t b)
{
  if (!s_led_strip)
    return;
  led_strip_set_pixel(s_led_strip, 0, r, g, b);
  led_strip_refresh(s_led_strip);
}

static void indicateProcessing() { setLEDColor(0, 0, LED_BRIGHTNESS); } // blue
static void indicateSuccess() { setLEDColor(0, LED_BRIGHTNESS, 0); }    // green
static void indicateFailure() { setLEDColor(LED_BRIGHTNESS, 0, 0); }    // red
static void indicateIdle() { setLEDColor(0, 0, 0); }                    // off

// ---------------------------------------------------------------------
// Core print workflow
// ---------------------------------------------------------------------

// ── CRC-8 poly 0x07 — must match PIC firmware byte-for-byte ──────────────
static uint8_t crc8_compute(const uint8_t *data, uint16_t len)
{
  uint8_t crc = 0x00U;
  while (len--)
  {
    crc ^= *data++;
    for (uint8_t bit = 0; bit < 8U; bit++)
      crc = (crc & 0x80U) ? (uint8_t)((crc << 1U) ^ 0x07U)
                          : (uint8_t)(crc << 1U);
  }
  return crc;
}

static void pic_send_response(uint8_t byte)
{
  uart_write_bytes(PIC_UART_PORT, (const char *)&byte, 1);
}

// ── PIC receiver FSM task ─────────────────────────────────────────────────
typedef enum
{
  HUNT,
  LENGTH,
  PAYLOAD,
  CRC_CHECK
} pic_rx_state_t;

static void pic_rx_task(void *pvParameters)
{
  static uint8_t payload_buf[PIC_MAX_PAYLOAD];

  pic_rx_state_t state = HUNT;
  uint8_t sync_win[4] = {0, 0, 0, 0};
  uint8_t len_buf[2];
  uint8_t len_count = 0;
  uint16_t declared_len = 0;
  uint16_t payload_idx = 0;
  uint8_t b;

  ESP_LOGI(TAG, "PIC RX task started, hunting for sync...");

  while (true)
  {
    switch (state)
    {
    case HUNT:
    {
      int n = uart_read_bytes(PIC_UART_PORT, &b, 1, pdMS_TO_TICKS(100));
      if (n <= 0)
        break;
      sync_win[0] = sync_win[1];
      sync_win[1] = sync_win[2];
      sync_win[2] = sync_win[3];
      sync_win[3] = b;
      if (sync_win[0] == PIC_SYNC_0 && sync_win[1] == PIC_SYNC_1 &&
          sync_win[2] == PIC_SYNC_2 && sync_win[3] == PIC_SYNC_3)
      {
        ESP_LOGD(TAG, "PIC sync locked");
        len_count = 0;
        state = LENGTH;
      }
      break;
    }

    case LENGTH:
    {
      int n = uart_read_bytes(PIC_UART_PORT, &b, 1, pdMS_TO_TICKS(100));
      if (n <= 0)
        break;
      len_buf[len_count++] = b;
      if (len_count == 2)
      {
        declared_len = ((uint16_t)len_buf[0] << 8) | len_buf[1];
        if (declared_len == 0 || declared_len > PIC_MAX_PAYLOAD)
        {
          ESP_LOGW(TAG, "Bad length 0x%04X — re-hunting", declared_len);
          memset(sync_win, 0, 4);
          state = HUNT;
        }
        else
        {
          payload_idx = 0;
          state = PAYLOAD;
        }
      }
      break;
    }

    case PAYLOAD:
    {
      uint16_t remaining = declared_len - payload_idx;
      int got = uart_read_bytes(PIC_UART_PORT,
                                payload_buf + payload_idx,
                                remaining,
                                pdMS_TO_TICKS(PAYLOAD_TIMEOUT_MS));
      if (got < 0)
      {
        ESP_LOGE(TAG, "UART error in PAYLOAD — re-hunting");
        memset(sync_win, 0, 4);
        state = HUNT;
        break;
      }
      if (got == 0)
      {
        ESP_LOGW(TAG, "Payload timeout at %u/%u — re-hunting",
                 payload_idx, declared_len);
        memset(sync_win, 0, 4);
        state = HUNT;
        break;
      }
      payload_idx += (uint16_t)got;
      if (payload_idx >= declared_len)
        state = CRC_CHECK;
      break;
    }

    case CRC_CHECK:
    {
      int n = uart_read_bytes(PIC_UART_PORT, &b, 1,
                              pdMS_TO_TICKS(CRC_TIMEOUT_MS));
      if (n <= 0)
      {
        ESP_LOGW(TAG, "CRC byte timeout — re-hunting");
        memset(sync_win, 0, 4);
        state = HUNT;
        break;
      }
      uint8_t calc = crc8_compute(payload_buf, declared_len);
      if (b == calc)
      {
        ESP_LOGI(TAG, "CRC OK — %u bytes = %u samples",
                 declared_len, declared_len / 2);
        pic_send_response(ACK_BYTE);

        pic_packet_t pkt;
        pkt.num_samples = declared_len / 2;
        memcpy(pkt.bytes, payload_buf, declared_len);

        // Overwrite any stale unread packet — printer must use latest data
        xQueueOverwrite(pic_data_queue, &pkt);
      }
      else
      {
        ESP_LOGW(TAG, "CRC FAIL rx=0x%02X calc=0x%02X — NACK", b, calc);
        pic_send_response(NACK_BYTE);
      }
      memset(sync_win, 0, 4);
      state = HUNT;
      break;
    }
    } // switch
  } // while
}

static void printGraph()
{
  ESP_LOGI(TAG, "=== printGraph() start ===");
  indicateProcessing();

  if (!printer->begin())
  {
    ESP_LOGE(TAG, "  ✗ Printer init failed!");
    indicateFailure();
    return;
  }
  printer->setLineHeight(24);

  // 1. Allocate canvas
  BitmapCanvas canvas(CANVAS_WIDTH, CANVAS_HEIGHT);
  if (!canvas.isValid())
  {
    ESP_LOGE(TAG, "  ✗ Canvas allocation failed, aborting print.");
    indicateFailure();
    return;
  }
  canvas.clear();

  // 2. Build graph layout + draw axes/grid/curve
  GraphGenerator graph(&canvas, GRAPH_WIDTH, GRAPH_HEIGHT,
                       LEFT_MARGIN, TOP_MARGIN,
                       X_MAX, X_STEP,
                       Y_MAX, Y_STEP,
                       GRID_X_SPACING, GRID_Y_SPACING);

  graph.drawGrid(true);
  graph.drawYAxisLabels();
  graph.drawXAxisLabels();

  if (!dataSource->fetchData())
  {
    ESP_LOGE(TAG, "  ✗ fetchData() failed, aborting print.");
    indicateFailure();
    return;
  }
  graph.drawCurve(dataSource->getData(), dataSource->getDataLength(), 1);

  // 3. Header zones: title, date/time, sample number.
  //    NOTE: date/time and sample number are still hardcoded placeholders
  //    pending RTC/NTP integration — ported as-is from the Arduino version.
  printer->setAlign(ALIGN_CENTER);
  printer->setFontSize(1, 2);
  printer->println("Standard Failure Graph");
  printer->setFontSize(1, 1);
  printer->println("------------------------------");
  printer->println("");

  printer->setAlign(ALIGN_LEFT);
  printer->println("Date/Time : 2026-06-20 11:47"); // TODO: RTC/NTP
  printer->println("");
  printer->println("Sample No.: "); // TODO: incrementing counter
  printer->println("");
  printer->println("");
  printer->setAlign(ALIGN_CENTER);
  printer->println("Load (kN)");
  printer->println("");

  // 4. Send bitmap
  if (!printer->printBitmap(canvas.getWidth(), canvas.getHeight(), canvas.getData()))
  {
    ESP_LOGE(TAG, "  ✗ printBitmap() failed!");
    indicateFailure();
    return;
  }

  printer->feed(5);
  printer->feed(1);
  printer->cut();

  ESP_LOGI(TAG, "=== printGraph() complete ===");
  indicateSuccess();
  vTaskDelay(pdMS_TO_TICKS(500));
  indicateIdle();
}

// ---------------------------------------------------------------------
// Console listener task (replaces Arduino loop()'s Serial.read() poll)
// ---------------------------------------------------------------------

static void console_listener_task(void *pvParameters)
{
  uint8_t data[1];
  while (true)
  {
    // 20ms timeout keeps this non-blocking enough to never starve the IDLE
    // task / watchdog, while still being responsive to keypresses.
    int len = uart_read_bytes(CONSOLE_UART_PORT, data, 1, pdMS_TO_TICKS(20));
    if (len > 0 && (data[0] == 'p' || data[0] == 'P'))
    {
      ESP_LOGI(TAG, "Manual trigger received, reprinting graph...");
      printGraph();
    }
    vTaskDelay(pdMS_TO_TICKS(50)); // yield, feed watchdog
  }
}

// ---------------------------------------------------------------------
// Driver init helpers
// ---------------------------------------------------------------------

static void init_pic_uart()
{
  uart_config_t cfg = {};
  cfg.baud_rate = PIC_BAUD;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.source_clk = UART_SCLK_DEFAULT;

  ESP_ERROR_CHECK(uart_driver_install(PIC_UART_PORT, 4096, 4096, 0, nullptr, 0));
  ESP_ERROR_CHECK(uart_param_config(PIC_UART_PORT, &cfg));
  ESP_ERROR_CHECK(uart_set_pin(PIC_UART_PORT, PIC_TX_PIN, PIC_RX_PIN,
                               UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
  ESP_LOGI(TAG, "PIC UART: port=%d rx=%d tx=%d baud=%d",
           PIC_UART_PORT, PIC_RX_PIN, PIC_TX_PIN, PIC_BAUD);
}

static void init_led_strip()
{
  led_strip_config_t strip_config = {};
  strip_config.strip_gpio_num = LED_GPIO_PIN;
  strip_config.max_leds = LED_NUM_PIXELS;
  strip_config.led_model = LED_MODEL_WS2812;
  strip_config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB;
  strip_config.flags.invert_out = false;

  led_strip_rmt_config_t rmt_config = {};
  rmt_config.clk_src = RMT_CLK_SRC_DEFAULT;
  rmt_config.resolution_hz = 10 * 1000 * 1000; // 10MHz
  rmt_config.flags.with_dma = false;

  esp_err_t err = led_strip_new_rmt_device(&strip_config, &rmt_config, &s_led_strip);
  if (err != ESP_OK)
  {
    ESP_LOGE(TAG, "  ✗ led_strip init failed: %s", esp_err_to_name(err));
    s_led_strip = nullptr;
    return;
  }
  led_strip_clear(s_led_strip);
}

static void init_console_uart()
{
  uart_config_t cfg = {};
  cfg.baud_rate = CONSOLE_BAUD;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.source_clk = UART_SCLK_DEFAULT;

  // UART0 is typically already wired to the USB-serial bridge / boot pins,
  // so we skip uart_set_pin() here and accept the default IO mux pins.
  ESP_ERROR_CHECK(uart_driver_install(CONSOLE_UART_PORT, 256, 0, 0, nullptr, 0));
  ESP_ERROR_CHECK(uart_param_config(CONSOLE_UART_PORT, &cfg));
}

static void init_printer_uart()
{
  uart_config_t cfg = {};
  cfg.baud_rate = PRINTER_BAUD;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.source_clk = UART_SCLK_DEFAULT;

  ESP_ERROR_CHECK(uart_driver_install(PRINTER_UART_PORT, 1024, 1024, 0, nullptr, 0));
  ESP_ERROR_CHECK(uart_param_config(PRINTER_UART_PORT, &cfg));
  ESP_ERROR_CHECK(uart_set_pin(PRINTER_UART_PORT, PRINTER_TX_PIN, PRINTER_RX_PIN,
                               UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
}

// ---------------------------------------------------------------------
// app_main
// ---------------------------------------------------------------------

extern "C" void app_main1(void)
{
  ESP_LOGI(TAG, "ESP32-S3 Thermal Printer (native ESP-IDF) starting...");

  init_pic_uart();
  init_console_uart();
  init_printer_uart();
  init_led_strip();

  ESP_LOGI(TAG, "Printer UART: port=%d tx=%d rx=%d baud=%d",
           PRINTER_UART_PORT, PRINTER_TX_PIN, PRINTER_RX_PIN, PRINTER_BAUD);

  // printer = new ThermalPrinter(PRINTER_UART_PORT);
  // dataSource = new HardcodedDataSource();
  // dataSource->initialize();

  // // Initial print at boot, matching the original setup()'s behavior.
  // printGraph();

  pic_data_queue = xQueueCreate(1, sizeof(pic_packet_t));
  configASSERT(pic_data_queue);

  printer = new ThermalPrinter(PRINTER_UART_PORT);
  dataSource = new PICDataSource();
  dataSource->initialize();

  // Launch PIC FSM — runs continuously, posts packets to pic_data_queue
  xTaskCreatePinnedToCore(pic_rx_task, "pic_rx", 8192, nullptr, 5, nullptr, 1);

  // Main loop: block on queue inside fetchData(), print when data arrives
  while (true)
  {
    printGraph(); // fetchData() inside here blocks until PIC sends a packet
  }

  // Background task: listens for 'p'/'P' on the console UART to re-trigger
  // a print without resetting the board.
  xTaskCreate(console_listener_task, "console_task", 4096, nullptr, 10, nullptr);
}
