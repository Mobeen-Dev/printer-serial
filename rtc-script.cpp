#include <Wire.h>
#include <RTClib.h>

RTC_DS3231 rtc;
bool rtcAvailable = false;

void setup() {
  Serial.begin(115200);

  // Set your I2C pins here
  Wire.begin(8, 9);   // SDA=8, SCL=9 (example for ESP32-S3)
  // Wire.begin(21, 22); // Common ESP32 pins

  rtcAvailable = rtc.begin();

  if (rtcAvailable) {
    Serial.println("RTC found");
  } else {
    Serial.println("RTC NOT found, using default time");
  }
}

void loop() {
  if (rtcAvailable) {
    DateTime now = rtc.now();

    Serial.printf("RTC: %04d/%02d/%02d %02d:%02d:%02d\n",
                  now.year(),
                  now.month(),
                  now.day(),
                  now.hour(),
                  now.minute(),
                  now.second());
  } else {
    // Default date/time
    Serial.println("2026/01/01 00:00:00");
  }

  delay(1000);
}