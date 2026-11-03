/*
 * DataSource.h
 * Hardware Abstraction Layer (HAL) for curve data sourcing
 *
 * Purpose:
 *  - Provide a drop-in interface for swapping data sources (hardcoded, UART IC, etc.)
 *  - Keep graph + printer logic completely independent from acquisition method
 *
 * Migration note: this interface was already pure C++ (no Arduino API usage),
 * so it is unchanged from the Arduino version other than the <Arduino.h> include.
 */

#ifndef DATA_SOURCE_H
#define DATA_SOURCE_H

#include <cstdint>

class DataSource
{
public:
  virtual bool initialize() = 0;
  virtual bool fetchData() = 0; // Populates internal buffer
  virtual const int16_t *getData() const = 0;
  virtual uint16_t getDataLength() const = 0;
  virtual ~DataSource() {}
};

#endif // DATA_SOURCE_H
