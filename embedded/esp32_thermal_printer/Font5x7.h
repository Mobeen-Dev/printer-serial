/*
 * Font5x7.h
 * 5x7 pixel font for thermal printer text rendering
 * Supports digits 0-9 and letter K
 */

#ifndef FONT_5X7_H
#define FONT_5X7_H

#include <Arduino.h>

// Font data: Each character is 7 rows × 5 columns
// Bit 7 is leftmost pixel, bits 6-2 unused, bits 1-0 for last two columns

static const uint8_t font5x7_data[][7] PROGMEM = {
  // '0' (index 0)
  {
    0b01110000,
    0b10001000,
    0b10001000,
    0b10001000,
    0b10001000,
    0b10001000,
    0b01110000
  },
  // '1' (index 1)
  {
    0b00100000,
    0b01100000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b01110000
  },
  // '2' (index 2)
  {
    0b01110000,
    0b10001000,
    0b00001000,
    0b00010000,
    0b00100000,
    0b01000000,
    0b11111000
  },
  // '3' (index 3)
  {
    0b01110000,
    0b10001000,
    0b00001000,
    0b00110000,
    0b00001000,
    0b10001000,
    0b01110000
  },
  // '4' (index 4)
  {
    0b00010000,
    0b00110000,
    0b01010000,
    0b10010000,
    0b11111000,
    0b00010000,
    0b00010000
  },
  // '5' (index 5)
  {
    0b11111000,
    0b10000000,
    0b11110000,
    0b00001000,
    0b00001000,
    0b10001000,
    0b01110000
  },
  // '6' (index 6)
  {
    0b01110000,
    0b10000000,
    0b10000000,
    0b11110000,
    0b10001000,
    0b10001000,
    0b01110000
  },
  // '7' (index 7)
  {
    0b11111000,
    0b00001000,
    0b00010000,
    0b00100000,
    0b01000000,
    0b01000000,
    0b01000000
  },
  // '8' (index 8)
  {
    0b01110000,
    0b10001000,
    0b10001000,
    0b01110000,
    0b10001000,
    0b10001000,
    0b01110000
  },
  // '9' (index 9)
  {
    0b01110000,
    0b10001000,
    0b10001000,
    0b01111000,
    0b00001000,
    0b00001000,
    0b01110000
  },
  // 'K' (index 10)
  {
    0b10001000,
    0b10010000,
    0b10100000,
    0b11000000,
    0b10100000,
    0b10010000,
    0b10001000
  },
  // 'T' (index 11)
  {
    0b11111000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b00100000
  },
  // 'I' (index 12)
  {
    0b01110000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b00100000,
    0b01110000
  },
  // 'M' (index 13)
  {
    0b10001000,
    0b11011000,
    0b10101000,
    0b10101000,
    0b10001000,
    0b10001000,
    0b10001000
  },
  // 'E' (index 14)
  {
    0b11111000,
    0b10000000,
    0b10000000,
    0b11110000,
    0b10000000,
    0b10000000,
    0b11111000
  },
  // 'P' (index 15)
  {
    0b11110000,
    0b10001000,
    0b10001000,
    0b11110000,
    0b10000000,
    0b10000000,
    0b10000000
  },
  // 'R' (index 16)
  {
    0b11110000,
    0b10001000,
    0b10001000,
    0b11110000,
    0b10100000,
    0b10010000,
    0b10001000
  },
  // 'S' (index 17)
  {
    0b01111000,
    0b10000000,
    0b10000000,
    0b01110000,
    0b00001000,
    0b00001000,
    0b11110000
  },
  // 'U' (index 18)
  {
    0b10001000,
    0b10001000,
    0b10001000,
    0b10001000,
    0b10001000,
    0b10001000,
    0b01110000
  }
};

// Character index mapping
inline int8_t getCharIndex(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  
  switch (c) {
    case 'K': case 'k': return 10;
    case 'T': case 't': return 11;
    case 'I': case 'i': return 12;
    case 'M': case 'm': return 13;
    case 'E': case 'e': return 14;
    case 'P': case 'p': return 15;
    case 'R': case 'r': return 16;
    case 'S': case 's': return 17;
    case 'U': case 'u': return 18;
    default: return -1;
  }
}

// Get font character data
inline const uint8_t* getFont5x7Char(char c) {
  int8_t idx = getCharIndex(c);
  if (idx < 0) return nullptr;
  return font5x7_data[idx];
}

#endif // FONT_5X7_H
