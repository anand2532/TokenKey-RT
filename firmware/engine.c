/* TokenKey RT - context engine v1.0 (see engine.h, docs/engine.md, handoff SPEC.md). */
#include "engine.h"

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

enum { ST_NONE = 0, ST_CODE, ST_DIFF, ST_LOG, ST_PROSE };
enum { SF_DUP = 1u << 0, SF_BLANK = 1u << 1, SF_PROT = 1u << 2 };

/* ---- dupset (PoC DupSet) ------------------------------------------------------------------ */
void tk_dupset_reset(tk_dupset_t *d) { memset(d, 0, sizeof *d); }

static bool used_get(const tk_dupset_t *d, uint32_t i) { return (d->used[i >> 3] >> (i & 7u)) & 1u; }

bool tk_dupset_check_insert(tk_dupset_t *d, uint32_t h, int *slot)
{
    uint32_t i = h & (TK_DUPSET_SLOTS - 1u);
    *slot = -1;
    while (used_get(d, i)) {
        if (d->hash[i] == h) {
            return true;
        }
        i = (i + 1u) & (TK_DUPSET_SLOTS - 1u);
    }
    if (d->count >= TK_DUPSET_CAP) {
        d->set_full++;
        return false;
    }
    d->hash[i] = h;
    d->used[i >> 3] |= (uint8_t)(1u << (i & 7u));
    d->count++;
    *slot = (int)i;
    return false;
}

/* ---- UTF-8 character classes (Python str semantics, approximated outside ASCII) ------------ */
static uint32_t cp_at(const uint8_t *b, uint32_t n, uint32_t i, uint32_t *len)
{
    uint8_t c = b[i];
    uint32_t need = c < 0x80 ? 0 : (c & 0xE0) == 0xC0 ? 1 : (c & 0xF0) == 0xE0 ? 2 : (c & 0xF8) == 0xF0 ? 3 : 0;
    if (c >= 0x80 && need == 0) {
        *len = 1;
        return 0xFFFD;
    }
    if (i + need >= n) {
        *len = 1;
        return 0xFFFD;
    }
    uint32_t cp = need == 0 ? c : need == 1 ? (c & 0x1Fu) : need == 2 ? (c & 0x0Fu) : (c & 0x07u);
    for (uint32_t k = 1; k <= need; k++) {
        cp = (cp << 6) | (b[i + k] & 0x3Fu);
    }
    *len = need + 1u;
    return cp;
}

static bool cp_space(uint32_t c)
{
    return (c >= 0x09 && c <= 0x0D) || (c >= 0x1C && c <= 0x20) || c == 0x85 || c == 0xA0 || c == 0x1680 ||
           (c >= 0x2000 && c <= 0x200A) || c == 0x2028 || c == 0x2029 || c == 0x202F || c == 0x205F || c == 0x3000;
}

static bool cp_word(uint32_t c)
{
    if (c < 0x80) {
        return (c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '_';
    }
    if (cp_space(c) || c == 0xFFFD) {
        return false;
    }
    if (c >= 0xA1 && c <= 0xBF) {
        return c == 0xAA || c == 0xB2 || c == 0xB3 || c == 0xB5 || c == 0xB9 || c == 0xBA || (c >= 0xBC && c <= 0xBE);
    }
    if (c == 0xD7 || c == 0xF7 || (c >= 0x2000 && c <= 0x206F) || (c >= 0x20A0 && c <= 0x20CF) ||
        (c >= 0x2190 && c <= 0x23FF) || (c >= 0x2500 && c <= 0x27BF) || (c >= 0x2900 && c <= 0x2BFF) ||
        (c >= 0x3000 && c <= 0x303F) || (c >= 0xD800 && c <= 0xF8FF) || (c >= 0xFE30 && c <= 0xFE4F) ||
        (c >= 0xFF00 && c <= 0xFF0F) || c >= 0x1F000) {
        return false;
    }
    return true;
}

static bool space_at(const uint8_t *b, uint32_t n, uint32_t i, uint32_t *len) { return cp_space(cp_at(b, n, i, len)); }

static uint32_t lstrip(const uint8_t *b, uint32_t n)
{
    uint32_t i = 0, l;
    while (i < n && space_at(b, n, i, &l)) {
        i += l;
    }
    return i;
}

static bool blank(const uint8_t *b, uint32_t n) { return lstrip(b, n) == n; }

static bool pre(const uint8_t *b, uint32_t n, const char *s)
{
    size_t k = strlen(s);
    return n >= k && memcmp(b, s, k) == 0;
}

static bool dig(uint8_t c) { return c >= '0' && c <= '9'; }

/* fence string of a line: 0 none, '`' or '~' */
static uint8_t fence_of(const uint8_t *b, uint32_t n)
{
    uint32_t i = lstrip(b, n);
    if (pre(b + i, n - i, "```")) {
        return '`';
    }
    if (pre(b + i, n - i, "~~~")) {
        return '~';
    }
    return 0;
}

/* PoC _LOG_RE with re.match (anchored at line start), case-sensitive. */
bool tk_engine_log_line(const uint8_t *b, uint32_t n)
{
    uint32_t l;
    if (pre(b, n, "Traceback (most recent call last)")) {
        return true;
    }
    /* \s*File ".*", line \d+ */
    uint32_t i = lstrip(b, n);
    if (pre(b + i, n - i, "File \"")) {
        for (uint32_t j = i + 6; j + 8 < n; j++) {
            if (b[j] == '\n') {
                break;
            }
            if (memcmp(b + j, "\", line ", 8) == 0 && dig(b[j + 8])) {
                return true;
            }
        }
    }
    /* E\s{2,} */
    if (n >= 1 && b[0] == 'E') {
        uint32_t k = 1, c = 0;
        while (k < n && c < 2 && space_at(b, n, k, &l)) {
            k += l;
            c++;
        }
        if (c >= 2) {
            return true;
        }
    }
    /* \w*(Error|Exception): */
    for (uint32_t k = 0; k < n;) {
        if (pre(b + k, n - k, "Error:") || pre(b + k, n - k, "Exception:")) {
            return true;
        }
        if (!cp_word(cp_at(b, n, k, &l))) {
            break;
        }
        k += l;
    }
    /* .*\b(FAILED|FAIL|WARN(ING)?|ERROR|CRITICAL|panic|fatal)\b */
    {
        static const char *const tok[] = {"FAILED", "FAIL", "WARNING", "WARN", "ERROR", "CRITICAL", "panic", "fatal"};
        bool prev_word = false;
        for (uint32_t k = 0; k < n && b[k] != '\n';) {
            if (!prev_word) {
                for (unsigned t = 0; t < sizeof tok / sizeof tok[0]; t++) {
                    size_t tl = strlen(tok[t]);
                    if (pre(b + k, n - k, tok[t])) {
                        uint32_t e = k + (uint32_t)tl, l2;
                        if (e >= n || !cp_word(cp_at(b, n, e, &l2))) {
                            return true;
                        }
                    }
                }
            }
            prev_word = cp_word(cp_at(b, n, k, &l));
            k += l;
        }
    }
    /* \d{4}-\d\d-\d\d[ T]\d\d:\d\d */
    if (n >= 16 && dig(b[0]) && dig(b[1]) && dig(b[2]) && dig(b[3]) && b[4] == '-' && dig(b[5]) && dig(b[6]) &&
        b[7] == '-' && dig(b[8]) && dig(b[9]) && (b[10] == ' ' || b[10] == 'T') && dig(b[11]) && dig(b[12]) &&
        b[13] == ':' && dig(b[14]) && dig(b[15])) {
        return true;
    }
    /* \[\s*\d+\.\d+\] */
    if (n >= 1 && b[0] == '[') {
        uint32_t k = 1;
        while (k < n && space_at(b, n, k, &l)) {
            k += l;
        }
        uint32_t d0 = k;
        while (k < n && dig(b[k])) {
            k++;
        }
        if (k > d0 && k < n && b[k] == '.') {
            uint32_t d1 = ++k;
            while (k < n && dig(b[k])) {
                k++;
            }
            if (k > d1 && k < n && b[k] == ']') {
                return true;
            }
        }
    }
    /* \s+at .+\(.+:\d+\) */
    if (i > 0 && pre(b + i, n - i, "at ")) {
        uint32_t p = i + 3, q = p + 1;
        while (q < n && b[q] != '\n' && b[q] != '(') {
            q++;
        }
        if (q < n && b[q] == '(' && q >= p + 1) {
            for (uint32_t r = q + 2; r < n && b[r] != '\n'; r++) {
                if (b[r] == ':') {
                    uint32_t s = r + 1;
                    while (s < n && dig(b[s])) {
                        s++;
                    }
                    if (s > r + 1 && s < n && b[s] == ')') {
                        return true;
                    }
                }
            }
        }
    }
    return false;
}

static bool diff_body(const uint8_t *b, uint32_t n)
{
    static const char *const p[] = {" ", "+", "-", "@@", "index ", "diff ", "\\", "new file", "deleted file",
                                    "similarity", "rename ", "old mode", "new mode", "Binary "};
    if (blank(b, n)) {
        return true;
    }
    for (unsigned k = 0; k < sizeof p / sizeof p[0]; k++) {
        if (pre(b, n, p[k])) {
            return true;
        }
    }
    return false;
}

/* maximal \S run at i */
static uint32_t nonspace_run(const uint8_t *b, uint32_t n, uint32_t i)
{
    uint32_t k = i, l;
    while (k < n && !space_at(b, n, k, &l)) {
        k += l;
    }
    return k - i;
}

/* file id (PoC _diff_file_id): returns length, *s start; 0 = None */
static uint32_t diff_file_id(const uint8_t *b, uint32_t n, uint32_t *s)
{
    if (pre(b, n, "diff --git a/")) {
        uint32_t a = 13, r1 = nonspace_run(b, n, a);
        uint32_t k = a + r1;
        if (r1 && pre(b + k, n - k, " b/")) {
            uint32_t r2 = nonspace_run(b, n, k + 3);
            if (r2) {
                *s = k + 3;
                return r2;
            }
        }
    }
    if (pre(b, n, "+++ ")) {
        if (pre(b + 4, n - 4, "b/")) {
            uint32_t r = nonspace_run(b, n, 6);
            if (r) {
                *s = 6;
                return r;
            }
        }
        uint32_t r = nonspace_run(b, n, 4);
        if (r) {
            *s = 4;
            return r;
        }
    }
    return 0;
}

/* ---- scanner -------------------------------------------------------------------------------- */
typedef struct {
    const uint8_t *b;
    uint32_t n, off;
} line_t;

static void seg_start(tk_engine_t *e, const line_t *L, uint8_t type, uint8_t st)
{
    e->seg_start = L->off;
    e->seg_type = type;
    e->st = st;
    e->chunk_lines = 0;
    e->cur_ref = -1;
    e->seg_blank = true;
    tk_xxh32_reset(&e->h, 0);
}

static void seg_add(tk_engine_t *e, const line_t *L)
{
    tk_xxh32_update(&e->h, L->b, L->n);
    e->chunk_lines++;
    if (!blank(L->b, L->n)) {
        e->seg_blank = false;
    }
}

static void seg_end(tk_engine_t *e, uint32_t end)
{
    e->st = ST_NONE;
    if (e->overflow) {
        return;
    }
    if (end == e->seg_start) {
        return;
    }
    if (e->nseg >= TK_ENGINE_MAX_SEGS) {
        e->overflow = OVF_SEGMENTS; /* checked per segment (SPEC 5.2 #7) */
        return;
    }
    tk_seg_t *s = &e->seg[e->nseg];
    memset(s, 0, sizeof *s);
    s->off = e->seg_start;
    s->len = end - e->seg_start;
    s->hash = tk_xxh32_digest(&e->h);
    s->msg = (uint16_t)e->msg;
    s->type = e->seg_type;
    s->flags = e->seg_blank ? SF_BLANK : 0u;
    s->ref = (uint8_t)(e->cur_ref + 1);
    if (e->cur_ref >= 0) {
        e->ref[e->cur_ref].seg = (uint16_t)e->nseg;
    }
    for (uint32_t k = 0; k < e->nprot; k++) {
        if (e->prot[k].off < s->off + s->len && s->off < e->prot[k].off + e->prot[k].len) {
            s->flags |= SF_PROT;
        }
    }
    e->seg_count[s->type]++;
    e->nseg++;
}

static void add_ref(tk_engine_t *e, const uint8_t *fid, uint32_t fl)
{
    if (e->overflow) {
        return;
    }
    uint32_t a = 0;
    for (uint32_t k = 0; k < fl; k++) {
        if (fid[k] == '/') {
            a = k + 1;
        }
    }
    if (e->nref >= TK_MAX_DIFF_REFS) {
        e->overflow = OVF_DIFF_REFS;
        return;
    }
    if (fl - a > TK_BASENAME_CAP) {
        e->overflow = OVF_BASENAME;
        return;
    }
    tk_diffref_t *r = &e->ref[e->nref];
    memset(r, 0, sizeof *r);
    r->blen = (uint16_t)(fl - a);
    r->empty = (r->blen == 0);
    memcpy(r->base, fid + a, r->blen);
    /* KMP failure function */
    for (uint32_t q = 1, k = 0; q < r->blen; q++) {
        while (k && r->base[q] != r->base[k]) {
            k = r->fail[k - 1];
        }
        if (r->base[q] == r->base[k]) {
            k++;
        }
        r->fail[q] = (uint8_t)k;
    }
    e->cur_ref = (int)e->nref++;
}

static bool uni_start(const line_t *L, const line_t *N)
{
    return pre(L->b, L->n, "--- ") && N && pre(N->b, N->n, "+++ ");
}

/* one line, with one line of lookahead N (NULL at message end) */
static void process(tk_engine_t *e, const line_t *L, const line_t *N)
{
    for (;;) {
        switch (e->st) {
        case ST_CODE:
            seg_add(e, L);
            {
                uint32_t i = lstrip(L->b, L->n);
                if (pre(L->b + i, L->n - i, e->fence[0] == '`' ? "```" : "~~~")) {
                    seg_end(e, L->off + L->n);
                }
            }
            return;
        case ST_DIFF:
            if (pre(L->b, L->n, "diff --git ")) {
                break;
            }
            if (diff_body(L->b, L->n)) {
                if (uni_start(L, N) && e->chunk_lines > 2) {
                    break;
                }
                seg_add(e, L);
                return;
            }
            break;
        case ST_LOG:
            if (!blank(L->b, L->n) && (tk_engine_log_line(L->b, L->n) || (L->n && (L->b[0] == ' ' || L->b[0] == '\t'))) &&
                !fence_of(L->b, L->n)) {
                seg_add(e, L);
                return;
            }
            break;
        case ST_PROSE:
            if (e->chunk_lines >= TK_PROSE_MAX_LINES || fence_of(L->b, L->n) || pre(L->b, L->n, "diff --git ") ||
                uni_start(L, N) || tk_engine_log_line(L->b, L->n)) {
                break;
            }
            seg_add(e, L);
            if (blank(L->b, L->n)) {
                seg_end(e, L->off + L->n);
            }
            return;
        default: { /* ST_NONE: classify */
            uint8_t f = fence_of(L->b, L->n);
            if (f) {
                seg_start(e, L, SEG_CODE, ST_CODE);
                e->fence[0] = f;
                seg_add(e, L);
                return;
            }
            bool git = pre(L->b, L->n, "diff --git ");
            if (git || uni_start(L, N)) {
                seg_start(e, L, SEG_DIFF, ST_DIFF);
                uint32_t s = 0, fl = git ? diff_file_id(L->b, L->n, &s) : diff_file_id(N->b, N->n, &s);
                if (fl) {
                    add_ref(e, (git ? L->b : N->b) + s, fl);
                }
                seg_add(e, L);
                return;
            }
            if (tk_engine_log_line(L->b, L->n)) {
                seg_start(e, L, SEG_LOG, ST_LOG);
                seg_add(e, L);
                return;
            }
            seg_start(e, L, SEG_PROSE, ST_PROSE);
            seg_add(e, L);
            if (blank(L->b, L->n)) {
                seg_end(e, L->off + L->n);
            }
            return;
        }
        }
        /* current segment ends before L; classify L afresh */
        seg_end(e, L->off);
    }
}

static void msg_done(tk_engine_t *e);
static void line_done(tk_engine_t *e);

/* close every message that ends at the current position (also empty ones) */
static void advance_msgs(tk_engine_t *e)
{
    while (e->msg < e->nmsg && e->pos == e->msg_end) {
        if (e->pending_cr) {
            e->pending_cr = false;
            line_done(e);
        }
        msg_done(e);
        e->msg++;
        if (e->msg < e->nmsg) {
            e->msg_end += e->msgs[e->msg].len;
        }
    }
}

void tk_engine_begin(tk_engine_t *e, const tk_msg_t *msgs, uint32_t nmsg, uint32_t total, const tk_range_t *prot,
                     uint32_t nprot, const proto_policy_t *pol, uint32_t token_budget)
{
    memset(e, 0, offsetof(tk_engine_t, seg)); /* tables are filled as used */
    e->nseg = 0;
    e->nref = 0;
    e->msgs = msgs;
    e->nmsg = nmsg;
    e->total = total;
    e->prot = prot;
    e->nprot = nprot;
    e->pol = *pol;
    e->token_budget = token_budget;
    e->cur = 0;
    e->msg = 0;
    e->msg_end = nmsg ? msgs[0].len : 0;
    advance_msgs(e);
}

/* the line being built is complete */
static void line_done(tk_engine_t *e)
{
    uint8_t bi = (uint8_t)(1u - e->cur);
    if (e->have_cur) {
        line_t L = {e->line[e->cur], e->llen[e->cur], e->loff[e->cur]};
        line_t N = {e->line[bi], e->llen[bi], e->loff[bi]};
        process(e, &L, &N);
    }
    e->cur = bi;
    e->have_cur = true;
    e->llen[1u - e->cur] = 0;
    e->building = false;
}

static void msg_done(tk_engine_t *e)
{
    if (e->building) {
        line_done(e);
    }
    if (e->have_cur) {
        line_t L = {e->line[e->cur], e->llen[e->cur], e->loff[e->cur]};
        process(e, &L, NULL);
        e->have_cur = false;
    }
    if (e->st != ST_NONE) {
        seg_end(e, e->pos);
    }
    e->pending_cr = false;
}

static void put_byte(tk_engine_t *e, uint8_t c)
{
    uint8_t bi = (uint8_t)(1u - e->cur);
    if (e->pending_cr) {
        e->pending_cr = false;
        if (c != '\n') {
            line_done(e); /* "\r" ended the line; c starts a new one */
            bi = (uint8_t)(1u - e->cur);
        }
    }
    if (!e->building) {
        e->building = true;
        e->llen[bi] = 0;
        e->loff[bi] = e->pos;
    }
    if (e->llen[bi] >= TK_LINE_CAP) {
        if (!e->overflow) {
            e->overflow = OVF_LINE;
        }
        e->llen[bi] = 0; /* keep tracking positions only */
    }
    uint8_t *b = e->line[bi];
    uint32_t n = e->llen[bi];
    b[n++] = c;
    e->llen[bi] = n;
    e->pos++;
    bool end = c == '\n' || c == 0x0B || c == 0x0C || c == 0x1C ||
               c == 0x1D || c == 0x1E || (c == 0x85 && n >= 2 && b[n - 2] == 0xC2) ||
               ((c == 0xA8 || c == 0xA9) && n >= 3 && b[n - 2] == 0x80 && b[n - 3] == 0xE2);
    if (c == '\r') {
        e->pending_cr = true;
        end = false;
    }
    if (end) {
        line_done(e);
    }
}

void tk_engine_feed(tk_engine_t *e, const uint8_t *d, uint32_t n)
{
    for (uint32_t i = 0; i < n; i++) {
        if (e->msg >= e->nmsg || e->pos >= e->total) {
            return;
        }
        put_byte(e, d[i]);
        advance_msgs(e);
    }
}

/* ---- decisions ---------------------------------------------------------------------------- */
static const tk_engine_t *s_cmp;

static int64_t density(const tk_seg_t *s)
{
    int64_t num = (int64_t)s->score * 1024;
    int64_t den = s->len ? s->len : 1;
    int64_t q = num / den;
    if ((num % den) != 0 && ((num < 0) != (den < 0))) {
        q--; /* Python floor division */
    }
    return q;
}

static int cmp_seg(const void *a, const void *b)
{
    const tk_seg_t *x = &s_cmp->seg[*(const uint16_t *)a], *y = &s_cmp->seg[*(const uint16_t *)b];
    int64_t dx = density(x), dy = density(y);
    if (dx != dy) {
        return dx > dy ? -1 : 1;
    }
    return x->off < y->off ? -1 : x->off > y->off ? 1 : 0;
}

static bool seg_exempt(const tk_engine_t *e, const tk_seg_t *s) { return (e->msgs[s->msg].flags & MSGF_EXEMPT) != 0; }
static bool seg_newest(const tk_engine_t *e, const tk_seg_t *s)
{
    return (e->msgs[s->msg].flags & MSGF_NEWEST) != 0 && !e->pol.newest_dedup;
}

/* candidates for the greedy pass; returns count, *sum = their tokens, *budget */
static uint32_t candidates(tk_engine_t *e, uint64_t *sum, uint64_t *budget, bool *diff_ref)
{
    uint32_t nc = 0;
    uint64_t base = 0;
    *sum = 0;
    *diff_ref = false;
    const bool v01 = e->pol.rules == POLICY_RULES_V01;
    for (uint32_t i = 0; i < e->nseg; i++) {
        tk_seg_t *s = &e->seg[i];
        if (v01) {
            if (s->flags & SF_PROT) { /* host-declared protected spans hold under every rule set */
                s->act = SEG_ACT_KEEP;
                continue;
            }
            s->act = SEG_ACT_DROP_BUDGET;
        } else {
            if (!seg_exempt(e, s)) {
                base += s->len / 4u;
            }
            if ((s->flags & SF_PROT) || seg_newest(e, s)) {
                s->act = SEG_ACT_KEEP;
                continue;
            }
            if (e->pol.dedup && (s->flags & SF_DUP) && !(s->flags & SF_BLANK)) {
                s->act = SEG_ACT_DROP_DUP;
                continue;
            }
            if (seg_exempt(e, s)) {
                s->act = SEG_ACT_KEEP;
                continue;
            }
            s->act = SEG_ACT_DROP_BUDGET;
        }
        e->order[nc++] = (uint16_t)i;
        *sum += s->len / 4u;
        if (s->ref) {
            *diff_ref = true;
        }
    }
    if (v01) {
        base = e->total / 4u; /* D: budget from total_bytes // 4 */
    }
    *budget = e->token_budget ? e->token_budget : (base * e->pol.keep_pct) / 100u;
    return nc;
}

static void decide(tk_engine_t *e, bool with_refs)
{
    uint64_t sum, budget;
    bool dr;
    uint32_t nc = candidates(e, &sum, &budget, &dr);
    for (uint32_t k = 0; k < nc; k++) {
        tk_seg_t *s = &e->seg[e->order[k]];
        int32_t sc = (int32_t)e->pol.type_weight[s->type] + (int32_t)(e->total ? ((uint64_t)s->off * 100u) / e->total : 0u);
        if (with_refs && s->ref) {
            const tk_diffref_t *r = &e->ref[s->ref - 1];
            uint32_t all = r->empty ? e->total + 1u : r->n_all, own = r->empty ? s->len + 1u : r->n_own;
            uint32_t hits = all > own ? all - own : 0u;
            sc += (int32_t)((hits < 10u ? hits : 10u) * 10u);
        }
        if (s->flags & SF_DUP) {
            sc -= 1000;
        }
        s->score = (int16_t)sc;
    }
    s_cmp = e;
    qsort(e->order, nc, sizeof e->order[0], cmp_seg);
    uint64_t used = 0;
    for (uint32_t k = 0; k < nc; k++) {
        tk_seg_t *s = &e->seg[e->order[k]];
        uint32_t t = s->len / 4u;
        if (used + t <= budget) {
            s->act = SEG_ACT_KEEP;
            used += t;
        } else {
            s->act = (s->flags & SF_DUP) ? SEG_ACT_DROP_DUP : SEG_ACT_DROP_BUDGET;
        }
    }
    e->kept_bytes = 0;
    e->tok_out = 0;
    for (uint32_t i = 0; i < e->nseg; i++) {
        if (e->seg[i].act == SEG_ACT_KEEP) {
            e->kept_bytes += e->seg[i].len;
            e->tok_out += e->seg[i].len / 4u;
        }
    }
    e->phase = 2;
}

uint8_t tk_engine_finish(tk_engine_t *e, tk_dupset_t *dup)
{
    e->tok_in = e->total / 4u;
    if (e->pos != e->total || e->overflow) {
        if (!e->overflow) {
            e->overflow = OVF_SEGMENTS;
        }
        return ENG_OVERFLOW; /* PoC CtxOverflow: host forwards unreduced; dupset untouched */
    }
    e->set_full0 = dup->set_full;
    e->nundo = 0;
    for (uint32_t i = 0; i < e->nseg; i++) {
        tk_seg_t *s = &e->seg[i];
        if (!e->pol.dedup) {
            continue;
        }
        int slot;
        if (tk_dupset_check_insert(dup, s->hash, &slot)) {
            s->flags |= SF_DUP;
            e->dup_hits++;
        } else if (slot >= 0) {
            e->undo[e->nundo++] = (uint16_t)slot;
        }
    }
    e->set_full = dup->set_full - e->set_full0;
    uint64_t sum, budget;
    bool dr;
    candidates(e, &sum, &budget, &dr);
    if (dr && sum > budget) {
        e->phase = 1; /* ranking can depend on the diff reference counts: need pass 2 */
        e->p2_pos = 0;
        e->p2_seg = 0;
        return ENG_NEED_PASS2;
    }
    decide(e, false); /* all candidates fit, or no diff refs among them: refs cannot matter */
    return ENG_DONE;
}

void tk_engine_rollback(tk_engine_t *e, tk_dupset_t *dup)
{
    for (uint32_t k = 0; k < e->nundo; k++) {
        uint32_t i = e->undo[k];
        dup->used[i >> 3] &= (uint8_t) ~(1u << (i & 7u));
        dup->count--;
    }
    /* linear probing: removing entries can break probe chains of entries inserted later in
     * the same job only, and those are removed too; earlier entries never probe past them. */
    e->nundo = 0;
    dup->set_full = e->set_full0;
}

static void kmp_step(const tk_diffref_t *r, uint16_t *st, uint32_t *cnt, uint8_t c)
{
    uint32_t k = *st;
    while (k && r->base[k] != c) {
        k = r->fail[k - 1];
    }
    if (r->base[k] == c) {
        k++;
    }
    if (k == r->blen) {
        (*cnt)++;
        k = 0; /* non-overlapping, as bytes.count() */
    }
    *st = (uint16_t)k;
}

void tk_engine_feed2(tk_engine_t *e, const uint8_t *d, uint32_t n)
{
    if (e->phase != 1) {
        return;
    }
    for (uint32_t i = 0; i < n && e->p2_pos < e->total; i++, e->p2_pos++) {
        uint8_t c = d[i];
        for (uint32_t k = 0; k < e->nref; k++) {
            tk_diffref_t *r = &e->ref[k];
            if (r->empty) {
                continue;
            }
            kmp_step(r, &r->st_all, &r->n_all, c);
            const tk_seg_t *s = &e->seg[r->seg];
            if (e->p2_pos >= s->off && e->p2_pos < s->off + s->len) {
                kmp_step(r, &r->st_own, &r->n_own, c);
            }
        }
    }
}

uint8_t tk_engine_finish2(tk_engine_t *e)
{
    if (e->phase != 1 || e->p2_pos != e->total) {
        return ENG_NEED_PASS2;
    }
    decide(e, true);
    return ENG_DONE;
}

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

void tk_engine_record(const tk_engine_t *e, uint32_t i, uint8_t *out)
{
    const tk_seg_t *s = &e->seg[i];
    put32(out, s->off);
    put32(out + 4, s->len);
    out[8] = s->act;
    put32(out + 9, s->hash);
}
