/* TokenKey RT - HS96L03W2C03 (SSD1315, SSD1306-compatible) 128x64 OLED on LPI2C1 @ 0x3C. */
#ifndef TK_OLED_H
#define TK_OLED_H

#include <stdbool.h>
#include <stdint.h>

#define OLED_W 128
#define OLED_H 64

/* Display orientation (PM enclosure decision, #30): the OLED is mounted rotated 180 degrees to
 * the user, so the default is ON. Done purely in the SSD1315 init sequence (segment remap +
 * COM scan direction); the framebuffer is never flipped.
 *   OLED_ROTATE_180 = 1: 0xA1 (segment remap, column 127 -> SEG0) + 0xC8 (COM scan COM63 -> COM0)
 *   OLED_ROTATE_180 = 0: 0xA0 (column 0 -> SEG0, reset value)      + 0xC0 (COM scan COM0 -> COM63, reset value)
 * Override with CMake -DOLED_ROTATE_180=OFF (or -DOLED_ROTATE_180=0). */
#ifndef OLED_ROTATE_180
#define OLED_ROTATE_180 1
#endif

bool oled_init(void);                 /* LPI2C1 400 kHz + controller init; false = no ACK */
bool oled_present(void);
void oled_clear(void);
void oled_pixel(int x, int y, bool on);
void oled_fill_rect(int x, int y, int w, int h, bool on);
/* 5x7 font in a 6x8 cell; scale 1 or 2. Returns x after the text. inv = black on white. */
int oled_text(int x, int y, const char *s, int scale, bool inv);
bool oled_flush(void);                /* writes dirty pages only */
const uint8_t *oled_framebuffer(void);

#endif
