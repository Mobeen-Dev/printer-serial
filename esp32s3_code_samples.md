# ESP32-S3 Embedded Development Guide
## RGB LED Control, Serial Communication & Task Status Indication

---

## Table of Contents
1. [RGB LED Control Best Practices](#rgb-led-control)
2. [Serial Communication Patterns](#serial-communication)
3. [Task-Based Status Indication](#task-status-indication)
4. [Complete Working Examples](#complete-examples)

---

## RGB LED Control Best Practices {#rgb-led-control}

### 1. Basic WS2812 LED Setup (FastLED)

```cpp
#include <FastLED.h>

// ======== LED Configuration ========
#define LED_PIN     48          // ESP32-S3 DevKitC-1 onboard WS2812
#define NUM_LEDS    1
#define CHIPSET     WS2812
#define COLOR_ORDER GRB
#define BRIGHTNESS  128

CRGB leds[NUM_LEDS];

void setup() {
  FastLED.addLeds<CHIPSET, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  leds[0] = CRGB::Black;
  FastLED.show();
}
```

**Key Points:**
- Pin 48 is the standard WS2812 pin for ESP32-S3 DevKitC-1
- Always call `FastLED.show()` after updating LED colors
- GRB is the typical color order for WS2812B LEDs
- Brightness range: 0-255 (128 = 50%)

---

### 2. Smooth Color Transitions

#### Method A: Linear Interpolation
```cpp
// Smooth transition between two colors
void transitionColor(CRGB startColor, CRGB endColor, uint16_t duration_ms) {
  uint16_t steps = duration_ms / 20;  // 20ms per step = 50fps
  
  for (uint16_t i = 0; i <= steps; i++) {
    float ratio = (float)i / steps;
    
    uint8_t r = startColor.r + (endColor.r - startColor.r) * ratio;
    uint8_t g = startColor.g + (endColor.g - startColor.g) * ratio;
    uint8_t b = startColor.b + (endColor.b - startColor.b) * ratio;
    
    leds[0] = CRGB(r, g, b);
    FastLED.show();
    delay(20);
  }
}

// Usage
void loop() {
  transitionColor(CRGB::Red, CRGB::Blue, 1000);    // 1 second transition
  transitionColor(CRGB::Blue, CRGB::Green, 1000);
  transitionColor(CRGB::Green, CRGB::Red, 1000);
}
```

#### Method B: Non-Blocking Transitions (Better for Multitasking)
```cpp
class ColorTransition {
private:
  CRGB startColor, endColor, currentColor;
  unsigned long startTime, duration;
  bool active;

public:
  ColorTransition() : active(false) {}
  
  void start(CRGB start, CRGB end, unsigned long dur_ms) {
    startColor = start;
    endColor = end;
    duration = dur_ms;
    startTime = millis();
    active = true;
  }
  
  bool update(CRGB &output) {
    if (!active) return false;
    
    unsigned long elapsed = millis() - startTime;
    if (elapsed >= duration) {
      output = endColor;
      active = false;
      return false;
    }
    
    float ratio = (float)elapsed / duration;
    output.r = startColor.r + (endColor.r - startColor.r) * ratio;
    output.g = startColor.g + (endColor.g - startColor.g) * ratio;
    output.b = startColor.b + (endColor.b - startColor.b) * ratio;
    
    return true;
  }
  
  bool isActive() { return active; }
};

// Usage
ColorTransition transition;

void loop() {
  if (!transition.isActive()) {
    transition.start(CRGB::Red, CRGB::Blue, 2000);
  }
  
  CRGB color;
  if (transition.update(color)) {
    leds[0] = color;
    FastLED.show();
  }
  
  // Other non-blocking code can run here
  delay(10);
}
```

---

### 3. Status Indication Color Patterns

```cpp
// Status LED colors
enum TaskStatus {
  TASK_IDLE,
  TASK_STARTING,
  TASK_PROCESSING,
  TASK_SUCCESS,
  TASK_FAILURE
};

CRGB getStatusColor(TaskStatus status) {
  switch (status) {
    case TASK_IDLE:       return CRGB::Black;
    case TASK_STARTING:   return CRGB(0, 191, 255);    // Light Blue
    case TASK_PROCESSING: return CRGB(255, 255, 0);    // Yellow
    case TASK_SUCCESS:    return CRGB::Green;
    case TASK_FAILURE:    return CRGB::Red;
    default:              return CRGB::Black;
  }
}

void setStatusLED(TaskStatus status, bool transition = true) {
  CRGB targetColor = getStatusColor(status);
  
  if (transition) {
    transitionColor(leds[0], targetColor, 300);  // 300ms transition
  } else {
    leds[0] = targetColor;
    FastLED.show();
  }
}
```

---

### 4. Breathing Effect for Processing State

```cpp
void breathingEffect(CRGB baseColor, uint16_t duration_ms) {
  static unsigned long lastUpdate = 0;
  static uint8_t brightness = 0;
  static int8_t direction = 1;
  
  if (millis() - lastUpdate < 10) return;
  lastUpdate = millis();
  
  brightness += direction * 2;
  
  if (brightness >= 255 || brightness <= 0) {
    direction = -direction;
  }
  
  CRGB dimmedColor = baseColor;
  dimmedColor.nscale8(brightness);
  leds[0] = dimmedColor;
  FastLED.show();
}

// Usage in loop
void loop() {
  breathingEffect(CRGB(0, 191, 255), 2000);  // Light blue breathing
}
```

---

## Serial Communication Patterns {#serial-communication}

### 1. Multi-UART Configuration for ESP32-S3

```cpp
#include <HardwareSerial.h>

// Define multiple serial ports
HardwareSerial Serial1(1);  // UART1
HardwareSerial Serial2(2);  // UART2

// Pin assignments (can be any GPIO)
#define UART1_TX_PIN  17
#define UART1_RX_PIN  18
#define UART2_TX_PIN  21
#define UART2_RX_PIN  22

void setup() {
  // Serial0 (USB) for debugging
  Serial.begin(115200);
  
  // UART1 configuration
  Serial1.begin(9600, SERIAL_8N1, UART1_RX_PIN, UART1_TX_PIN);
  
  // UART2 configuration
  Serial2.begin(115200, SERIAL_8N1, UART2_RX_PIN, UART2_TX_PIN);
  
  Serial.println("Multi-UART initialized");
}
```

**ESP32-S3 Default UART Pins:**
- UART0: TX=43, RX=44 (USB)
- UART1: TX=17, RX=18 (default, can be reassigned)
- UART2: No default (must be assigned)

---

### 2. Non-Blocking Serial Data Reading

```cpp
// Buffer for incoming serial data
#define BUFFER_SIZE 256
char serialBuffer[BUFFER_SIZE];
uint8_t bufferIndex = 0;

bool readSerialData(HardwareSerial &serial, String &output) {
  while (serial.available() > 0) {
    char inChar = serial.read();
    
    // Check for newline (command terminator)
    if (inChar == '\n' || inChar == '\r') {
      if (bufferIndex > 0) {
        serialBuffer[bufferIndex] = '\0';
        output = String(serialBuffer);
        bufferIndex = 0;
        return true;
      }
    } 
    // Add to buffer if space available
    else if (bufferIndex < BUFFER_SIZE - 1) {
      serialBuffer[bufferIndex++] = inChar;
    }
    // Buffer overflow - reset
    else {
      Serial.println("Buffer overflow!");
      bufferIndex = 0;
    }
  }
  return false;
}

// Usage
void loop() {
  String command;
  if (readSerialData(Serial1, command)) {
    Serial.print("Received: ");
    Serial.println(command);
    
    // Process command
    processCommand(command);
  }
}
```

---

### 3. Protocol-Based Communication

```cpp
// Simple packet structure
struct DataPacket {
  uint8_t header;       // 0xAA
  uint8_t command;      // Command ID
  uint8_t dataLength;   // Length of data
  uint8_t data[32];     // Payload
  uint8_t checksum;     // Simple XOR checksum
};

// Send structured data
void sendPacket(HardwareSerial &serial, uint8_t cmd, uint8_t *data, uint8_t len) {
  DataPacket packet;
  packet.header = 0xAA;
  packet.command = cmd;
  packet.dataLength = len;
  
  // Copy data
  memcpy(packet.data, data, len);
  
  // Calculate checksum
  packet.checksum = 0xAA ^ cmd ^ len;
  for (uint8_t i = 0; i < len; i++) {
    packet.checksum ^= data[i];
  }
  
  // Send packet
  serial.write(packet.header);
  serial.write(packet.command);
  serial.write(packet.dataLength);
  serial.write(packet.data, len);
  serial.write(packet.checksum);
}

// Receive and validate packet
bool receivePacket(HardwareSerial &serial, DataPacket &packet) {
  if (serial.available() < 4) return false;
  
  // Read header
  if (serial.read() != 0xAA) return false;
  
  packet.header = 0xAA;
  packet.command = serial.read();
  packet.dataLength = serial.read();
  
  // Validate length
  if (packet.dataLength > 32) return false;
  
  // Wait for complete packet
  unsigned long timeout = millis() + 1000;
  while (serial.available() < packet.dataLength + 1) {
    if (millis() > timeout) return false;
    delay(1);
  }
  
  // Read data and checksum
  serial.readBytes(packet.data, packet.dataLength);
  packet.checksum = serial.read();
  
  // Verify checksum
  uint8_t calc_checksum = 0xAA ^ packet.command ^ packet.dataLength;
  for (uint8_t i = 0; i < packet.dataLength; i++) {
    calc_checksum ^= packet.data[i];
  }
  
  return (calc_checksum == packet.checksum);
}
```

---

## Task-Based Status Indication {#task-status-indication}

### 1. FreeRTOS Task Structure

```cpp
#include <Arduino.h>
#include <FastLED.h>

// Task handles
TaskHandle_t taskHandleLED = NULL;
TaskHandle_t taskHandleComm = NULL;
TaskHandle_t taskHandleProcess = NULL;

// Shared status variable (protected by mutex)
SemaphoreHandle_t statusMutex;
TaskStatus currentStatus = TASK_IDLE;

// LED update task
void taskLEDControl(void *parameter) {
  while (1) {
    TaskStatus status;
    
    // Get current status (thread-safe)
    xSemaphoreTake(statusMutex, portMAX_DELAY);
    status = currentStatus;
    xSemaphoreGive(statusMutex);
    
    // Update LED based on status
    setStatusLED(status);
    
    vTaskDelay(pdMS_TO_TICKS(50));  // 50ms update rate
  }
}

// Set status (thread-safe)
void setStatus(TaskStatus newStatus) {
  xSemaphoreTake(statusMutex, portMAX_DELAY);
  currentStatus = newStatus;
  xSemaphoreGive(statusMutex);
}

void setup() {
  // Initialize LED
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  
  // Create mutex
  statusMutex = xSemaphoreCreateMutex();
  
  // Create LED control task (high priority for responsiveness)
  xTaskCreatePinnedToCore(
    taskLEDControl,      // Function
    "LED Control",       // Name
    2048,                // Stack size
    NULL,                // Parameters
    2,                   // Priority (0-24, higher is more important)
    &taskHandleLED,      // Handle
    1                    // Core (0 or 1)
  );
  
  Serial.println("Tasks created");
}
```

---

### 2. Communication Task with Status Updates

```cpp
void taskSerialComm(void *parameter) {
  String command;
  
  while (1) {
    if (readSerialData(Serial1, command)) {
      // Indicate we're processing
      setStatus(TASK_PROCESSING);
      
      // Process command
      bool success = processCommand(command);
      
      // Update status based on result
      if (success) {
        setStatus(TASK_SUCCESS);
        vTaskDelay(pdMS_TO_TICKS(1000));  // Show success for 1 second
      } else {
        setStatus(TASK_FAILURE);
        vTaskDelay(pdMS_TO_TICKS(2000));  // Show failure for 2 seconds
      }
      
      // Return to idle
      setStatus(TASK_IDLE);
    }
    
    vTaskDelay(pdMS_TO_TICKS(10));  // Check every 10ms
  }
}

bool processCommand(String cmd) {
  cmd.trim();
  
  if (cmd == "START") {
    Serial1.println("OK: Started");
    return true;
  }
  else if (cmd == "STOP") {
    Serial1.println("OK: Stopped");
    return true;
  }
  else if (cmd.startsWith("SET:")) {
    String value = cmd.substring(4);
    Serial1.println("OK: Set to " + value);
    return true;
  }
  else {
    Serial1.println("ERROR: Unknown command");
    return false;
  }
}
```

---

### 3. Queue-Based Task Communication

```cpp
// Queue for passing data between tasks
QueueHandle_t dataQueue;

struct TaskData {
  uint8_t command;
  uint8_t data[16];
  uint8_t length;
};

// Producer task (Serial receiver)
void taskSerialReceiver(void *parameter) {
  while (1) {
    DataPacket packet;
    if (receivePacket(Serial1, packet)) {
      TaskData taskData;
      taskData.command = packet.command;
      taskData.length = packet.dataLength;
      memcpy(taskData.data, packet.data, packet.dataLength);
      
      // Send to queue (wait max 100ms)
      if (xQueueSend(dataQueue, &taskData, pdMS_TO_TICKS(100)) == pdTRUE) {
        setStatus(TASK_STARTING);
      }
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// Consumer task (Data processor)
void taskDataProcessor(void *parameter) {
  TaskData taskData;
  
  while (1) {
    // Wait for data (blocking)
    if (xQueueReceive(dataQueue, &taskData, portMAX_DELAY) == pdTRUE) {
      setStatus(TASK_PROCESSING);
      
      // Process data
      bool success = processData(taskData);
      
      // Update status
      setStatus(success ? TASK_SUCCESS : TASK_FAILURE);
      vTaskDelay(pdMS_TO_TICKS(1000));
      
      setStatus(TASK_IDLE);
    }
  }
}

void setup() {
  // Create queue (10 items max)
  dataQueue = xQueueCreate(10, sizeof(TaskData));
  
  // Create tasks...
}
```

---

## Complete Working Examples {#complete-examples}

### Example 1: Serial Command Processor with LED Status

```cpp
#include <FastLED.h>
#include <HardwareSerial.h>

// ======== Configuration ========
#define LED_PIN     48
#define NUM_LEDS    1
#define BRIGHTNESS  128

#define UART1_TX    17
#define UART1_RX    18

// ======== Globals ========
CRGB leds[NUM_LEDS];
HardwareSerial Serial1(1);

// Color transition
class ColorFader {
  CRGB start, end, current;
  unsigned long startTime, duration;
  bool active;

public:
  ColorFader() : active(false) {}
  
  void begin(CRGB s, CRGB e, unsigned long dur) {
    start = s;
    end = e;
    startTime = millis();
    duration = dur;
    active = true;
  }
  
  bool update() {
    if (!active) return false;
    
    unsigned long elapsed = millis() - startTime;
    if (elapsed >= duration) {
      current = end;
      active = false;
      leds[0] = current;
      FastLED.show();
      return false;
    }
    
    float ratio = (float)elapsed / duration;
    current.r = start.r + (end.r - start.r) * ratio;
    current.g = start.g + (end.g - start.g) * ratio;
    current.b = start.b + (end.b - start.b) * ratio;
    
    leds[0] = current;
    FastLED.show();
    return true;
  }
};

ColorFader fader;

// ======== Status Functions ========
void setLED(CRGB color) {
  fader.begin(leds[0], color, 300);
}

void indicateProcessing() {
  setLED(CRGB(0, 191, 255));  // Light Blue
}

void indicateSuccess() {
  setLED(CRGB::Green);
}

void indicateFailure() {
  setLED(CRGB::Red);
}

void indicateIdle() {
  setLED(CRGB::Black);
}

// ======== Command Processing ========
char cmdBuffer[64];
uint8_t cmdIndex = 0;

bool readCommand(String &output) {
  while (Serial1.available()) {
    char c = Serial1.read();
    
    if (c == '\n' || c == '\r') {
      if (cmdIndex > 0) {
        cmdBuffer[cmdIndex] = '\0';
        output = String(cmdBuffer);
        cmdIndex = 0;
        return true;
      }
    } else if (cmdIndex < 63) {
      cmdBuffer[cmdIndex++] = c;
    }
  }
  return false;
}

void processCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  
  indicateProcessing();
  delay(500);  // Simulate processing
  
  if (cmd == "PING") {
    Serial1.println("PONG");
    indicateSuccess();
  }
  else if (cmd == "STATUS") {
    Serial1.println("OK: System running");
    indicateSuccess();
  }
  else if (cmd.startsWith("ECHO ")) {
    Serial1.println(cmd.substring(5));
    indicateSuccess();
  }
  else {
    Serial1.println("ERROR: Unknown command");
    indicateFailure();
  }
  
  delay(1000);
  indicateIdle();
}

// ======== Setup ========
void setup() {
  Serial.begin(115200);
  Serial1.begin(9600, SERIAL_8N1, UART1_RX, UART1_TX);
  
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  
  indicateIdle();
  
  Serial.println("ESP32-S3 Command Processor Ready");
  Serial1.println("Ready");
}

// ======== Loop ========
void loop() {
  // Update LED transitions
  fader.update();
  
  // Check for commands
  String command;
  if (readCommand(command)) {
    Serial.println("CMD: " + command);
    processCommand(command);
  }
  
  delay(10);
}
```

---

### Example 2: FreeRTOS Multi-Task System

```cpp
#include <FastLED.h>
#include <HardwareSerial.h>

// ======== Configuration ========
#define LED_PIN     48
#define NUM_LEDS    1
#define BRIGHTNESS  128

// ======== Globals ========
CRGB leds[NUM_LEDS];
HardwareSerial Serial1(1);

enum Status { IDLE, STARTING, PROCESSING, SUCCESS, FAILURE };
volatile Status systemStatus = IDLE;
SemaphoreHandle_t statusMutex;

// ======== LED Task ========
void taskLED(void *param) {
  ColorFader fader;
  Status lastStatus = IDLE;
  
  while (1) {
    // Get current status
    xSemaphoreTake(statusMutex, portMAX_DELAY);
    Status current = systemStatus;
    xSemaphoreGive(statusMutex);
    
    // Update LED if status changed
    if (current != lastStatus) {
      CRGB targetColor;
      switch (current) {
        case IDLE:       targetColor = CRGB::Black; break;
        case STARTING:   targetColor = CRGB(0, 191, 255); break;
        case PROCESSING: targetColor = CRGB(255, 255, 0); break;
        case SUCCESS:    targetColor = CRGB::Green; break;
        case FAILURE:    targetColor = CRGB::Red; break;
      }
      fader.begin(leds[0], targetColor, 300);
      lastStatus = current;
    }
    
    // Update fader
    fader.update();
    
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

// ======== Communication Task ========
void taskComm(void *param) {
  char buffer[64];
  uint8_t index = 0;
  
  while (1) {
    if (Serial1.available()) {
      char c = Serial1.read();
      
      if (c == '\n') {
        buffer[index] = '\0';
        
        // Update status
        xSemaphoreTake(statusMutex, portMAX_DELAY);
        systemStatus = PROCESSING;
        xSemaphoreGive(statusMutex);
        
        vTaskDelay(pdMS_TO_TICKS(500));  // Simulate work
        
        // Process command
        bool success = (strcmp(buffer, "TEST") == 0);
        
        // Update result
        xSemaphoreTake(statusMutex, portMAX_DELAY);
        systemStatus = success ? SUCCESS : FAILURE;
        xSemaphoreGive(statusMutex);
        
        vTaskDelay(pdMS_TO_TICKS(1500));
        
        // Back to idle
        xSemaphoreTake(statusMutex, portMAX_DELAY);
        systemStatus = IDLE;
        xSemaphoreGive(statusMutex);
        
        index = 0;
      } else if (index < 63) {
        buffer[index++] = c;
      }
    }
    
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// ======== Setup ========
void setup() {
  Serial.begin(115200);
  Serial1.begin(9600, SERIAL_8N1, 18, 17);
  
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  
  statusMutex = xSemaphoreCreateMutex();
  
  xTaskCreatePinnedToCore(taskLED, "LED", 2048, NULL, 2, NULL, 1);
  xTaskCreatePinnedToCore(taskComm, "Comm", 4096, NULL, 1, NULL, 0);
  
  Serial.println("FreeRTOS System Ready");
}

void loop() {
  vTaskDelay(portMAX_DELAY);  // Idle - tasks handle everything
}
```

---

## Best Practices Summary

### RGB LED Control
- ✅ Always call `FastLED.show()` after updating colors
- ✅ Use non-blocking transitions for multitasking
- ✅ Keep brightness ≤ 128 to reduce power consumption
- ✅ Use `nscale8()` for dimming effects
- ❌ Avoid blocking delays in `loop()` if using tasks

### Serial Communication
- ✅ Always define custom pins for UART1/UART2
- ✅ Use buffering for incoming data
- ✅ Implement timeouts for packet reception
- ✅ Add checksums for data integrity
- ❌ Don't use `Serial.parseInt()` in time-critical code (blocking)

### FreeRTOS Tasks
- ✅ Use mutexes for shared variables
- ✅ Use queues for inter-task data transfer
- ✅ Pin time-critical tasks to specific cores
- ✅ Set appropriate task priorities (LED > Comm > Processing)
- ✅ Use `vTaskDelay()` instead of `delay()` in tasks
- ❌ Never use blocking operations in high-priority tasks

### Memory Management
- ✅ Monitor stack usage with `uxTaskGetStackHighWaterMark()`
- ✅ Allocate sufficient stack (2048-4096 bytes per task)
- ✅ Free dynamically allocated memory promptly
- ❌ Avoid large buffers on the stack

