/*
 * ESP32-S3 Thermal Printer - Advanced Example
 * FreeRTOS Task-Based Implementation with Serial Command Control
 * 
 * This example demonstrates:
 *  - FreeRTOS task separation (LED, Communication, Printing)
 *  - Serial command interface
 *  - Thread-safe status updates
 *  - Queue-based print job management
 */

#include <FastLED.h>
#include <HardwareSerial.h>
#include "ThermalPrinter.h"
#include "BitmapCanvas.h"
#include "GraphGenerator.h"

// ======== LED Configuration ========
#define LED_PIN     48
#define NUM_LEDS    1
#define BRIGHTNESS  128

CRGB leds[NUM_LEDS];

// ======== Serial Configuration ========
#define PRINTER_TX  17
#define PRINTER_RX  18
#define PRINTER_BAUD 19200

HardwareSerial PrinterSerial(1);

// ======== Status Enumeration ========
enum SystemStatus {
  STATUS_IDLE,
  STATUS_STARTING,
  STATUS_PROCESSING,
  STATUS_SUCCESS,
  STATUS_FAILURE
};

// ======== Global State ========
volatile SystemStatus currentStatus = STATUS_IDLE;
SemaphoreHandle_t statusMutex;
QueueHandle_t printQueue;

// Print job structure
struct PrintJob {
  uint8_t pattern;      // 1 or 2
  uint16_t numPoints;   // Data points
  char description[32]; // Job description
};

// ======== LED Task ========
void taskLED(void* param) {
  SystemStatus lastStatus = STATUS_IDLE;
  
  while (1) {
    // Get current status
    xSemaphoreTake(statusMutex, portMAX_DELAY);
    SystemStatus status = currentStatus;
    xSemaphoreGive(statusMutex);
    
    // Update LED if status changed
    if (status != lastStatus) {
      switch (status) {
        case STATUS_IDLE:
          leds[0] = CRGB::Black;
          break;
        case STATUS_STARTING:
          leds[0] = CRGB(0, 191, 255);  // Light Blue
          break;
        case STATUS_PROCESSING:
          leds[0] = CRGB(255, 255, 0);  // Yellow
          break;
        case STATUS_SUCCESS:
          leds[0] = CRGB::Green;
          break;
        case STATUS_FAILURE:
          leds[0] = CRGB::Red;
          break;
      }
      FastLED.show();
      lastStatus = status;
    }
    
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

// ======== Set Status (Thread-Safe) ========
void setStatus(SystemStatus newStatus) {
  xSemaphoreTake(statusMutex, portMAX_DELAY);
  currentStatus = newStatus;
  xSemaphoreGive(statusMutex);
}

// ======== Serial Command Task ========
void taskSerialCommand(void* param) {
  char buffer[64];
  uint8_t index = 0;
  
  Serial.println("\nCommands:");
  Serial.println("  P1 = Print Pattern 1 (Quadratic)");
  Serial.println("  P2 = Print Pattern 2 (Linear)");
  Serial.println("  S  = Status query");
  
  while (1) {
    if (Serial.available()) {
      char c = Serial.read();
      
      if (c == '\n' || c == '\r') {
        if (index > 0) {
          buffer[index] = '\0';
          
          // Parse command
          if (strcmp(buffer, "P1") == 0 || strcmp(buffer, "p1") == 0) {
            PrintJob job;
            job.pattern = 1;
            job.numPoints = 4800;
            strcpy(job.description, "Quadratic Curve");
            
            if (xQueueSend(printQueue, &job, pdMS_TO_TICKS(100)) == pdTRUE) {
              Serial.println("✓ Print job queued (Pattern 1)");
            } else {
              Serial.println("✗ Queue full!");
            }
          }
          else if (strcmp(buffer, "P2") == 0 || strcmp(buffer, "p2") == 0) {
            PrintJob job;
            job.pattern = 2;
            job.numPoints = 4800;
            strcpy(job.description, "Linear Curve");
            
            if (xQueueSend(printQueue, &job, pdMS_TO_TICKS(100)) == pdTRUE) {
              Serial.println("✓ Print job queued (Pattern 2)");
            } else {
              Serial.println("✗ Queue full!");
            }
          }
          else if (strcmp(buffer, "S") == 0 || strcmp(buffer, "s") == 0) {
            xSemaphoreTake(statusMutex, portMAX_DELAY);
            SystemStatus status = currentStatus;
            xSemaphoreGive(statusMutex);
            
            const char* statusStr[] = {"IDLE", "STARTING", "PROCESSING", "SUCCESS", "FAILURE"};
            Serial.printf("Status: %s\n", statusStr[status]);
          }
          else {
            Serial.println("✗ Unknown command");
          }
          
          index = 0;
        }
      }
      else if (index < 63) {
        buffer[index++] = c;
      }
    }
    
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// ======== Print Job Task ========
void taskPrintJob(void* param) {
  ThermalPrinter* printer = new ThermalPrinter(PrinterSerial);
  
  // Initialize printer
  if (!printer->begin()) {
    Serial.println("✗ Printer initialization failed!");
    setStatus(STATUS_FAILURE);
    vTaskDelete(NULL);
    return;
  }
  
  printer->setDensity(10, 2);
  printer->setLineHeight(24);
  
  while (1) {
    PrintJob job;
    
    // Wait for print job
    if (xQueueReceive(printQueue, &job, portMAX_DELAY) == pdTRUE) {
      Serial.printf("\n▶ Starting print job: %s\n", job.description);
      setStatus(STATUS_STARTING);
      vTaskDelay(pdMS_TO_TICKS(500));
      
      setStatus(STATUS_PROCESSING);
      
      // Create canvas
      uint16_t totalHeight = 1200 + 70 + 10;
      BitmapCanvas* canvas = new BitmapCanvas(512, totalHeight);
      
      if (!canvas || !canvas->isValid()) {
        Serial.println("✗ Canvas allocation failed!");
        setStatus(STATUS_FAILURE);
        vTaskDelay(pdMS_TO_TICKS(2000));
        setStatus(STATUS_IDLE);
        continue;
      }
      
      canvas->clear();
      
      // Create graph
      GraphGenerator generator(canvas, 512, 1200, 30, 70, 30, 2, 200, 25, 80, 60);
      
      generator.drawYAxisLabels();
      generator.drawGrid(true);
      generator.drawXAxisLabels();
      
      float* curveData = generator.generateBuildUpCurve(job.numPoints, job.pattern);
      
      if (!curveData) {
        Serial.println("✗ Curve generation failed!");
        delete canvas;
        setStatus(STATUS_FAILURE);
        vTaskDelay(pdMS_TO_TICKS(2000));
        setStatus(STATUS_IDLE);
        continue;
      }
      
      generator.drawCurve(curveData, job.numPoints, 1);
      free(curveData);
      
      generator.drawBottomLabel();
      
      // Print
      printer->setAlign(ALIGN_CENTER);
      printer->setFontSize(2, 2);
      printer->println(job.description);
      printer->feed(8);
      
      if (!printer->printBitmap(canvas->getWidth(), canvas->getHeight(), canvas->getData())) {
        Serial.println("✗ Printing failed!");
        delete canvas;
        setStatus(STATUS_FAILURE);
        vTaskDelay(pdMS_TO_TICKS(2000));
        setStatus(STATUS_IDLE);
        continue;
      }
      
      printer->feed(2);
      printer->setFontSize(2, 2);
      printer->println("PRESSURE");
      printer->feed(3);
      
      delete canvas;
      
      Serial.println("✓ Print job completed!");
      setStatus(STATUS_SUCCESS);
      vTaskDelay(pdMS_TO_TICKS(2000));
      setStatus(STATUS_IDLE);
    }
  }
}

// ======== Setup ========
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========================================");
  Serial.println("ESP32-S3 Thermal Printer");
  Serial.println("FreeRTOS Task-Based Control");
  Serial.println("========================================\n");
  
  // Initialize LED
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  leds[0] = CRGB::Black;
  FastLED.show();
  
  // Initialize printer serial
  PrinterSerial.begin(PRINTER_BAUD, SERIAL_8N1, PRINTER_RX, PRINTER_TX);
  delay(500);
  
  // Create synchronization objects
  statusMutex = xSemaphoreCreateMutex();
  printQueue = xQueueCreate(5, sizeof(PrintJob));
  
  // Create tasks
  xTaskCreatePinnedToCore(taskLED, "LED", 2048, NULL, 2, NULL, 1);
  xTaskCreatePinnedToCore(taskSerialCommand, "SerialCmd", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(taskPrintJob, "PrintJob", 8192, NULL, 1, NULL, 0);
  
  Serial.println("✓ System initialized");
  Serial.println("✓ Tasks created\n");
}

// ======== Loop ========
void loop() {
  // Tasks handle everything
  vTaskDelay(portMAX_DELAY);
}
