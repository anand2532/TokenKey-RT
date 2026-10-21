/* TokenKey RT - streaming xxHash32 (XXH32, seed configurable). Pure C, no allocation.
 * Reference algorithm: Yann Collet, xxHash specification (XXH32). Test vectors in test_engine.c. */
#ifndef TK_XXH32_H
#define TK_XXH32_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t total_len;
    uint32_t v[4];
    uint8_t mem[16];
    uint32_t memsize;
    uint8_t large; /* total_len >= 16 at some point */
} tk_xxh32_t;

void tk_xxh32_reset(tk_xxh32_t *s, uint32_t seed);
void tk_xxh32_update(tk_xxh32_t *s, const void *data, size_t len);
uint32_t tk_xxh32_digest(const tk_xxh32_t *s);
uint32_t tk_xxh32(const void *data, size_t len, uint32_t seed);

#endif
