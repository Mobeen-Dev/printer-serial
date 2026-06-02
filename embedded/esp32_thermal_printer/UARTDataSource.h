/*
 * UARTDataSource.h
 * Stub DataSource for future UART-based IC acquisition
 */

#ifndef UART_DATA_SOURCE_H
#define UART_DATA_SOURCE_H

#include <Arduino.h>
#include <HardwareSerial.h>

#include "DataSource.h"

#define UART_DATASOURCE_ENABLED 0

class UARTDataSource : public DataSource
{
private:
  int16_t *_buffer;
  HardwareSerial &_serial;
  uint32_t _baud;
  uint16_t _length;
  bool _hasFetched;

public:
  UARTDataSource(HardwareSerial &serial, uint32_t baudRate, uint16_t dataLength)
      : _buffer(nullptr), _serial(serial), _baud(baudRate), _length(dataLength), _hasFetched(false)
  {
    _buffer = (int16_t *)malloc(_length * sizeof(int16_t));
    if (!_buffer)
    {
      Serial.println("  ✗ UARTDataSource buffer allocation failed!");
    }
  }

  ~UARTDataSource() override
  {
    if (_buffer)
    {
      free(_buffer);
      _buffer = nullptr;
    }
  }

  bool initialize() override
  {
#if UART_DATASOURCE_ENABLED
    // TODO: Initialize UART, configure baud rate, handshake with IC
    // Future: PrinterSerial or a dedicated Serial port at configured baud
    return false; // Not implemented
#else
    // TODO: Initialize UART, configure baud rate, handshake with IC
    // Future: PrinterSerial or a dedicated Serial port at configured baud
    Serial.println("  ✗ UARTDataSource disabled (UART_DATASOURCE_ENABLED=0)");
    return false; // Not implemented
#endif
  }

  bool fetchData() override
  {
#if UART_DATASOURCE_ENABLED
    // TODO: Read 2400 int16_t values over UART from external IC
    // Protocol TBD — blocking read with timeout recommended
    // Future: populate _buffer with received values
    _hasFetched = false;
    return false; // Not implemented
#else
    // TODO: Read 2400 int16_t values over UART from external IC
    // Protocol TBD — blocking read with timeout recommended
    // Future: populate _buffer with received values
    Serial.println("  ✗ UARTDataSource fetchData() not implemented");
    _hasFetched = false;
    return false; // Not implemented
#endif
  }

  const int16_t *getData() const override
  {
    if (!_hasFetched)
    {
      Serial.println("  ⚠ getData() called before fetchData()!");
      return nullptr;
    }
    return _buffer;
  }

  uint16_t getDataLength() const override
  {
    return _length;
  }
};

#endif // UART_DATA_SOURCE_H
