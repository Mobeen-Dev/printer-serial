/*
 * PICDataSource.h
 * DataSource backed by PIC → ESP32 UART packet protocol.
 * The uart_rx_task (in esp32_thermal_printer.cpp) posts validated
 * payloads into pic_data_queue; this class drains that queue on
 * fetchData() and exposes the samples via the DataSource interface.
 *
 * Packet format (from PIC):
 *   [AA BB CC DD]       4 bytes  — sync preamble
 *   [len_hi len_lo]     2 bytes  — big-endian payload byte count
 *   [... payload ...]   N bytes  — uint16_t samples, big-endian, max 1600 B (800 samples)
 *   [crc]               1 byte   — CRC-8 poly 0x07 over payload only
 */

#ifndef PIC_DATA_SOURCE_H
#define PIC_DATA_SOURCE_H

#include <cstdint>
#include <cstring>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "DataSource.h"

// Maximum samples the PIC will ever send (800 × uint16_t = 1600 bytes payload)
#define PIC_MAX_SAMPLES     800
#define PIC_MAX_PAYLOAD     (PIC_MAX_SAMPLES * 2)   // bytes

// Queue item: raw payload bytes + actual sample count
typedef struct {
    uint8_t  bytes[PIC_MAX_PAYLOAD];
    uint16_t num_samples;
} pic_packet_t;

// Single-slot queue — only the latest packet matters
extern QueueHandle_t pic_data_queue;

class PICDataSource : public DataSource
{
    static constexpr const char *TAG = "PICDataSource";

    int16_t      _samples[PIC_MAX_SAMPLES];
    pic_packet_t _rxPacket;
    uint16_t     _length;
    bool         _hasFetched;

public:
    PICDataSource() : _length(0), _hasFetched(false)
    {
        memset(_samples, 0, sizeof(_samples));
        memset(&_rxPacket, 0, sizeof(_rxPacket));
    }

    bool initialize() override { return true; }

    // Blocks until a validated packet arrives from the PIC FSM.
    // Converts big-endian uint16_t pairs → int16_t samples.
    bool fetchData() override
    {
        ESP_LOGI(TAG, "Waiting for PIC packet...");

        // Block indefinitely — printGraph() won't proceed until data arrives
        if (xQueueReceive(pic_data_queue, &_rxPacket, portMAX_DELAY) != pdTRUE)
        {
            ESP_LOGE(TAG, "Queue receive failed");
            return false;
        }

        _length = _rxPacket.num_samples;
        if (_length > PIC_MAX_SAMPLES) _length = PIC_MAX_SAMPLES;

        for (uint16_t i = 0; i < _length; i++)
        {
            // Big-endian deserialisation
            uint16_t raw = ((uint16_t)_rxPacket.bytes[i * 2] << 8)
                         |  (uint16_t)_rxPacket.bytes[i * 2 + 1];
            _samples[i] = (int16_t)raw;
        }

        _hasFetched = true;
        ESP_LOGI(TAG, "Packet ready: %u samples", _length);
        return true;
    }

    const int16_t *getData() const override
    {
        if (!_hasFetched) {
            ESP_LOGW(TAG, "getData() before fetchData()!");
            return nullptr;
        }
        return _samples;
    }

    uint16_t getDataLength() const override { return _length; }
};

#endif // PIC_DATA_SOURCE_H