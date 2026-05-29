/*
 * ESP32-S3 Thermal Printer - Build-up Curve Generator
 * Epson TM-T88III Compatible (ESC/POS)
 * 
 * Hardware:
 *  - ESP32-S3 DevKitC-1
 *  - WS2812 RGB LED on pin 48
 *  - Thermal printer on UART1 (TX=17, RX=18)
 *  
 * Features:
 *  - ESC/POS command support
 *  - Bitmap graphics generation
 *  - Build-up curve patterns
 *  - LED status indication:
 *      • Light Blue = Processing
 *      • Green = Success
 *      • Red = Failure
 */

#include <FastLED.h>
#include <HardwareSerial.h>

#include "ThermalPrinter.h"
#include "BitmapCanvas.h"
#include "GraphGenerator.h"

#include "DataSource.h"
#include "HardcodedDataSource.h"

// ======== LED Configuration ========
#define LED_PIN     48           // on-board WS2812 data line
#define NUM_LEDS    1
#define BRIGHTNESS  128

CRGB leds[NUM_LEDS];

// ======== Serial Configuration ========
#define PRINTER_TX  17
#define PRINTER_RX  18
#define PRINTER_BAUD 19200

HardwareSerial PrinterSerial(1);

// ======== Graph Parameters ========
#define GRAPH_WIDTH  512
#define GRAPH_HEIGHT 750
#define GRID_X_SPACING 75
#define GRID_Y_SPACING 60
#define GRID_DASHED true

#define X_MAX 30
#define X_STEP 3
#define Y_MAX 200
#define Y_STEP 25

#define LEFT_MARGIN 30
#define TOP_MARGIN 70
#define BOTTOM_MARGIN 40

// ======== Global Objects ========
ThermalPrinter* printer = nullptr;

// DATA SOURCE — swap HardcodedDataSource for UARTDataSource when IC is ready
DataSource* dataSource = new HardcodedDataSource();

// ======== LED Status Functions ========
void setLEDColor(CRGB color) {
  leds[0] = color;
  FastLED.show();
}

void indicateProcessing() {
  setLEDColor(CRGB(0, 191, 255));  // Light Blue
}

void indicateSuccess() {
  setLEDColor(CRGB::Green);
}

void indicateFailure() {
  setLEDColor(CRGB::Red);
}

void indicateIdle() {
  setLEDColor(CRGB::Black);
}

// ======== Setup ========
void setup() {
  // Initialize Serial for debugging
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n========================================");
  Serial.println("ESP32-S3 Thermal Printer");
  Serial.println("Build-up Curve Generator");
  Serial.println("========================================");
  
  // Initialize LED
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  indicateIdle();
  Serial.println("✓ LED initialized");
  
  // Initialize printer serial
  PrinterSerial.begin(PRINTER_BAUD, SERIAL_8N1, PRINTER_RX, PRINTER_TX);
  delay(500);
  Serial.println("✓ Serial port opened");
  
  // Print configuration
  Serial.println("\nConfiguration:");
  Serial.printf("  Canvas: %dx%d pixels\n", GRAPH_WIDTH, GRAPH_HEIGHT + TOP_MARGIN + BOTTOM_MARGIN);
  const uint32_t canvasBytes = (GRAPH_WIDTH / 8) * (GRAPH_HEIGHT + TOP_MARGIN + BOTTOM_MARGIN);
  Serial.printf("  Canvas bytes: %lu\n", (unsigned long)canvasBytes);
  Serial.printf("  Graph area: %dx%d pixels\n", GRID_Y_SPACING * (Y_MAX / Y_STEP), GRAPH_HEIGHT - TOP_MARGIN);
  Serial.printf("  X-axis: 0 to %ds (step %ds)\n", X_MAX, X_STEP);
  Serial.printf("  Y-axis: 0 to %dK (step %dK)\n", Y_MAX, Y_STEP);
  Serial.println("  Pattern: Quadratic rise (0→200K in ≤26s → Drop)");
  Serial.println("\n========================================\n");
  
  delay(2000);
  
  // Create printer instance
  printer = new ThermalPrinter(PrinterSerial);
  
  // Run the print job
  printGraph();
}

// ======== Main Print Function ========
void printGraph() {
  indicateProcessing();
  Serial.println("[1/5] Initializing printer...");
  
  if (!printer->begin()) {
    Serial.println("  ✗ Printer initialization failed!");
    indicateFailure();
    return;
  }
  Serial.println("  ✓ Printer ready");
  
  // Configure printer
  Serial.println("\n[2/5] Configuring printer...");
  printer->setDensity(10, 2);
  printer->setLineHeight(24);
  Serial.println("  ✓ Configuration applied");
  
  // Generate graph
  Serial.println("\n[3/5] Generating graph...");
  
  uint16_t totalHeight = GRAPH_HEIGHT + TOP_MARGIN + BOTTOM_MARGIN;
  BitmapCanvas* canvas = new BitmapCanvas(GRAPH_WIDTH, totalHeight);
  
  if (!canvas) {
    Serial.println("  ✗ Failed to create canvas!");
    indicateFailure();
    return;
  }
  
  canvas->clear();
  Serial.println("  ✓ Canvas created");
  
  // Create graph generator
  GraphGenerator generator(canvas, GRAPH_WIDTH, GRAPH_HEIGHT, 
                          LEFT_MARGIN, TOP_MARGIN,
                          X_MAX, X_STEP, Y_MAX, Y_STEP,
                          GRID_X_SPACING, GRID_Y_SPACING);
  
  Serial.println("\n[4/5] Drawing graph components...");
  
  // Draw Y-axis labels (Pressure)
  Serial.println("  → Drawing Y-axis labels...");
  generator.drawYAxisLabels();
  
  // Draw grid
  Serial.println("  → Drawing grid...");
  generator.drawGrid(GRID_DASHED);
  
  // Draw X-axis labels (Time)
  Serial.println("  → Drawing X-axis labels...");
  generator.drawXAxisLabels();
  
  // Generate and draw curve
  // Pattern system reference (previously generated formula-based curves here):
  //  - Pattern 1: Quadratic build-up (smooth acceleration)
  //  - Pattern 2: Linear with noise (steady rise)
  // Now replaced by DataSource HAL so acquisition can be swapped (hardcoded ↔ UART IC)

  Serial.println("  → Fetching curve data from DataSource...");

  if (!dataSource->initialize()) {
    Serial.println("  ✗ DataSource initialize() failed!");
    delete canvas;
    indicateFailure();
    return;
  }

  if (!dataSource->fetchData()) {
    Serial.println("  ✗ DataSource fetchData() failed!");
    delete canvas;
    indicateFailure();
    return;
  }

  const int16_t* curveData = dataSource->getData();
  const uint16_t dataLen = dataSource->getDataLength();

  if (!curveData) {
    Serial.println("  ✗ DataSource returned null data!");
    delete canvas;
    indicateFailure();
    return;
  }

  Serial.println("  → Drawing curve...");
  generator.drawCurve(curveData, dataLen);
  // No free() needed — PROGMEM data, not heap allocated
  
  Serial.println("  ✓ Graph generation complete");
  
  // Print to thermal printer
  Serial.println("\n[5/5] Printing to device...");
  // Reset text mode before header to avoid stray characters
  printer->setDefault();
  printer->setLineHeight(24);
  printer->setAlign(ALIGN_CENTER);
  // Font (1,2): width=normal, height=doubled — fits 22-char title on one line
  printer->println("Standard Failure Graph");
  printer->feed(1);
  printer->setFontSize(1, 1);
  // Y-axis unit label — printed centered before graph bitmap
  printer->println("Load (kN)");
  printer->feed(1);
  
  Serial.printf("  → Sending bitmap (%dx%d)...\n", canvas->getWidth(), canvas->getHeight());
  
  if (!printer->printBitmap(canvas->getWidth(), canvas->getHeight(), canvas->getData())) {
    Serial.println("  ✗ Bitmap transmission failed!");
    delete canvas;
    indicateFailure();
    return;
  }
  
  Serial.println("  ✓ Bitmap sent");
  
  delete canvas;
  
  Serial.println("\n========================================");
  Serial.println("✓✓✓ PRINTING COMPLETED! ✓✓✓");
  Serial.println("========================================");
  
  indicateSuccess();
  delay(3000);
  indicateIdle();
}

// ======== Loop ========
void loop() {
  // Check for serial commands to trigger another print
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'p' || cmd == 'P') {
      Serial.println("\n\nStarting new print job...\n");
      printGraph();
    }
  }
  
  delay(1000);
}
