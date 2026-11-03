/*
 * UARTDataSource.h
 * Stub DataSource for future UART-based IC acquisition
 *
 * Migration note:
 *  - HardwareSerial& replaced with uart_port_t (driver must be installed
 *    by the caller, same convention as ThermalPrinter).
 *  - malloc() replaced with heap_caps_malloc(MALLOC_CAP_8BIT).
 */

#ifndef UART_DATA_SOURCE_H
#define UART_DATA_SOURCE_H

#include <cstdint>
#include "driver/uart.h"
#include "esp_heap_caps.h"
#include "esp_log.h"

#include "DataSource.h"

#define UART_DATASOURCE_ENABLED 0

class UARTDataSource : public DataSource
{
private:
  static constexpr const char *TAG = "UARTDataSource";

  int16_t *_buffer;
  uart_port_t _uart_port;
  uint32_t _baud;
  uint16_t _length;
  bool _hasFetched;

public:
  UARTDataSource(uart_port_t port, uint32_t baudRate, uint16_t dataLength)
      : _buffer(nullptr), _uart_port(port), _baud(baudRate), _length(dataLength), _hasFetched(false)
  {
    _buffer = (int16_t *)heap_caps_malloc(_length * sizeof(int16_t), MALLOC_CAP_8BIT);
    if (!_buffer)
    {
      ESP_LOGE(TAG, "  ✗ UARTDataSource buffer allocation failed!");
    }
  }

  ~UARTDataSource() override
  {
    if (_buffer)
    {
      heap_caps_free(_buffer);
      _buffer = nullptr;
    }
  }

  bool initialize() override
  {
#if UART_DATASOURCE_ENABLED
    // TODO: uart_param_config() + uart_set_pin() + uart_driver_install()
    // on _uart_port at _baud, then handshake with the external IC.
    return false; // Not implemented
#else
    // TODO: uart_param_config() + uart_set_pin() + uart_driver_install()
    // on _uart_port at _baud, then handshake with the external IC.
    ESP_LOGW(TAG, "  ✗ UARTDataSource disabled (UART_DATASOURCE_ENABLED=0)");
    return false; // Not implemented
#endif
  }

  bool fetchData() override
  {
#if UART_DATASOURCE_ENABLED
    // TODO: uart_read_bytes() to read 2400 int16_t values from the IC.
    // Protocol TBD — blocking read with timeout recommended.
    _hasFetched = false;
    return false; // Not implemented
#else
    // TODO: uart_read_bytes() to read 2400 int16_t values from the IC.
    // Protocol TBD — blocking read with timeout recommended.
    ESP_LOGW(TAG, "  ✗ UARTDataSource fetchData() not implemented");
    _hasFetched = false;
    return false; // Not implemented
#endif
  }

  const int16_t *getData() const override
  {
    if (!_hasFetched)
    {
      ESP_LOGW(TAG, "  ⚠ getData() called before fetchData()!");
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
