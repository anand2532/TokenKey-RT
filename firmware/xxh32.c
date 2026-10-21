/* TokenKey RT - streaming xxHash32. */
#include "xxh32.h"

#include <string.h>

#define P1 0x9E3779B1u
#define P2 0x85EBCA77u
#define P3 0xC2B2AE3Du
#define P4 0x27D4EB2Fu
#define P5 0x165667B1u

static uint32_t rotl(uint32_t x, int r) { return (x << r) | (x >> (32 - r)); }
static uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static uint32_t round32(uint32_t acc, uint32_t in) { return rotl(acc + in * P2, 13) * P1; }

void tk_xxh32_reset(tk_xxh32_t *s, uint32_t seed)
{
    memset(s, 0, sizeof *s);
    s->v[0] = seed + P1 + P2;
    s->v[1] = seed + P2;
    s->v[2] = seed;
    s->v[3] = seed - P1;
}

void tk_xxh32_update(tk_xxh32_t *s, const void *data, size_t len)
{
    const uint8_t *p = data;
    s->total_len += (uint32_t)len;
    if (s->total_len >= 16u) {
        s->large = 1;
    }
    if (s->memsize + len < 16u) {
        memcpy(s->mem + s->memsize, p, len);
        s->memsize += (uint32_t)len;
        return;
    }
    if (s->memsize) {
        size_t fill = 16u - s->memsize;
        memcpy(s->mem + s->memsize, p, fill);
        for (int i = 0; i < 4; i++) {
            s->v[i] = round32(s->v[i], rd32(s->mem + 4 * i));
        }
        p += fill;
        len -= fill;
        s->memsize = 0;
    }
    while (len >= 16u) {
        for (int i = 0; i < 4; i++) {
            s->v[i] = round32(s->v[i], rd32(p + 4 * i));
        }
        p += 16;
        len -= 16;
    }
    if (len) {
        memcpy(s->mem, p, len);
        s->memsize = (uint32_t)len;
    }
}

uint32_t tk_xxh32_digest(const tk_xxh32_t *s)
{
    uint32_t h;
    if (s->large) {
        h = rotl(s->v[0], 1) + rotl(s->v[1], 7) + rotl(s->v[2], 12) + rotl(s->v[3], 18);
    } else {
        h = s->v[2] + P5; /* v[2] == seed */
    }
    h += s->total_len;
    const uint8_t *p = s->mem;
    uint32_t n = s->memsize;
    while (n >= 4u) {
        h = rotl(h + rd32(p) * P3, 17) * P4;
        p += 4;
        n -= 4;
    }
    while (n--) {
        h = rotl(h + (*p++) * P5, 11) * P1;
    }
    h ^= h >> 15;
    h *= P2;
    h ^= h >> 13;
    h *= P3;
    h ^= h >> 16;
    return h;
}

uint32_t tk_xxh32(const void *data, size_t len, uint32_t seed)
{
    tk_xxh32_t s;
    tk_xxh32_reset(&s, seed);
    tk_xxh32_update(&s, data, len);
    return tk_xxh32_digest(&s);
}
