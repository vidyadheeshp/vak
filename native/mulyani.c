/*
 * mulyani.c — मूल्यानि / the runtime values of Vāk in C.
 *
 * Values are a small tagged union; strings, lists, dictionaries and closures
 * live on the heap with a reference count. Printing follows the Python
 * implementation exactly, because the two must produce identical output.
 */
#include "vak.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ------------------------------------------------------------------ रचना */
static void *smrti(size_t n) {
    void *p = malloc(n);
    if (!p) { fputs("स्मृतिः क्षीणा / out of memory\n", stderr); exit(70); }
    return p;
}

Mulyam shunyam_mulyam(void)        { Mulyam m; m.prakara = P_SHUNYAM; m.as.purnanka = 0; return m; }
Mulyam satyata_mulyam(bool b)      { Mulyam m; m.prakara = P_SATYATA; m.as.satyata = b; return m; }
Mulyam purnanka_mulyam(int64_t n)  { Mulyam m; m.prakara = P_PURNANKA; m.as.purnanka = n; return m; }
Mulyam dashamsha_mulyam(double d)  { Mulyam m; m.prakara = P_DASHAMSHA; m.as.dashamsha = d; return m; }
Mulyam antarnihitam_mulyam(int i)  { Mulyam m; m.prakara = P_ANTARNIHITAM; m.as.antarnihitam = i; return m; }

static Vastu *vastu_rachaya(size_t size, Prakara prakara) {
    Vastu *v = (Vastu *)smrti(size);
    v->nirdeshah = 1;
    v->prakara = prakara;
    return v;
}

Mulyam shabda_mulyam(const char *bytes, int len) {
    Shabda *s = (Shabda *)vastu_rachaya(sizeof(Shabda), P_SHABDA);
    s->baits = len;
    s->akshara = -1;
    s->paatha = (char *)smrti((size_t)len + 1);
    if (len) memcpy(s->paatha, bytes, (size_t)len);
    s->paatha[len] = '\0';
    Mulyam m; m.prakara = P_SHABDA; m.as.vastu = (Vastu *)s; return m;
}

Mulyam shabda_mulyam_c(const char *bytes) {
    return shabda_mulyam(bytes, (int)strlen(bytes));
}

Mulyam suchi_mulyam(void) {
    Suchi *s = (Suchi *)vastu_rachaya(sizeof(Suchi), P_SUCHI);
    s->dirghata = 0; s->avakasha = 0; s->angani = NULL;
    Mulyam m; m.prakara = P_SUCHI; m.as.vastu = (Vastu *)s; return m;
}

Mulyam kosha_mulyam(void) {
    Kosha *k = (Kosha *)vastu_rachaya(sizeof(Kosha), P_KOSHA);
    k->dirghata = 0; k->avakasha = 0; k->yugmani = NULL;
    Mulyam m; m.prakara = P_KOSHA; m.as.vastu = (Vastu *)k; return m;
}

Mulyam avarana_mulyam(const SankalitaKaryam *karyam, Parivesha *parivesha) {
    Avarana *a = (Avarana *)vastu_rachaya(sizeof(Avarana), P_AVARANA);
    a->karyam = karyam;
    a->parivesha = parivesha_grah(parivesha);
    Mulyam m; m.prakara = P_AVARANA; m.as.vastu = (Vastu *)a; return m;
}

Mulyam punaravartaka_mulyam(Mulyam angani) {
    Punaravartaka *p = (Punaravartaka *)vastu_rachaya(sizeof(Punaravartaka), P_PUNARAVARTAKA);
    p->angani = grah(angani);
    p->sthanam = 0;
    Mulyam m; m.prakara = P_PUNARAVARTAKA; m.as.vastu = (Vastu *)p; return m;
}

Shabda *as_shabda(Mulyam m) { return (Shabda *)m.as.vastu; }
Suchi  *as_suchi(Mulyam m)  { return (Suchi *)m.as.vastu; }
Kosha  *as_kosha(Mulyam m)  { return (Kosha *)m.as.vastu; }

static bool vastumat(Mulyam m) {
    return m.prakara == P_SHABDA || m.prakara == P_SUCHI
        || m.prakara == P_KOSHA || m.prakara == P_AVARANA
        || m.prakara == P_PUNARAVARTAKA;
}

Mulyam grah(Mulyam m) {
    if (vastumat(m)) m.as.vastu->nirdeshah++;
    return m;
}

void muncha(Mulyam m) {
    if (!vastumat(m)) return;
    if (--m.as.vastu->nirdeshah > 0) return;
    switch (m.prakara) {
    case P_SHABDA:
        free(as_shabda(m)->paatha);
        break;
    case P_SUCHI: {
        Suchi *s = as_suchi(m);
        for (int i = 0; i < s->dirghata; i++) muncha(s->angani[i]);
        free(s->angani);
        break;
    }
    case P_KOSHA: {
        Kosha *k = as_kosha(m);
        for (int i = 0; i < k->dirghata; i++) {
            muncha(k->yugmani[i].kunjika);
            muncha(k->yugmani[i].mulyam);
        }
        free(k->yugmani);
        break;
    }
    case P_AVARANA:
        parivesha_muncha(((Avarana *)m.as.vastu)->parivesha);
        break;
    case P_PUNARAVARTAKA:
        muncha(((Punaravartaka *)m.as.vastu)->angani);
        break;
    default: break;
    }
    free(m.as.vastu);
}

/* -------------------------------------------------------------- सूची / कोशः */
void suchi_yojaya(Mulyam suchi, Mulyam item) {
    Suchi *s = as_suchi(suchi);
    if (s->dirghata == s->avakasha) {
        s->avakasha = s->avakasha ? s->avakasha * 2 : 8;
        s->angani = (Mulyam *)realloc(s->angani, sizeof(Mulyam) * (size_t)s->avakasha);
        if (!s->angani) { fputs("स्मृतिः क्षीणा\n", stderr); exit(70); }
    }
    s->angani[s->dirghata++] = grah(item);
}

Mulyam suchi_grihana(Mulyam suchi, int index) {
    return as_suchi(suchi)->angani[index];
}

int kosha_sthanam(Mulyam kosha, Mulyam key) {
    Kosha *k = as_kosha(kosha);
    for (int i = 0; i < k->dirghata; i++)
        if (samam(k->yugmani[i].kunjika, key)) return i;
    return -1;
}

bool kosha_grihana(Mulyam kosha, Mulyam key, Mulyam *out) {
    int at = kosha_sthanam(kosha, key);
    if (at < 0) return false;
    *out = as_kosha(kosha)->yugmani[at].mulyam;
    return true;
}

void kosha_nyasaya(Mulyam kosha, Mulyam key, Mulyam value) {
    Kosha *k = as_kosha(kosha);
    int at = kosha_sthanam(kosha, key);
    if (at >= 0) {
        Mulyam purva = k->yugmani[at].mulyam;
        k->yugmani[at].mulyam = grah(value);
        muncha(purva);
        return;
    }
    if (k->dirghata == k->avakasha) {
        k->avakasha = k->avakasha ? k->avakasha * 2 : 8;
        k->yugmani = (KoshaYugma *)realloc(k->yugmani,
                                           sizeof(KoshaYugma) * (size_t)k->avakasha);
        if (!k->yugmani) { fputs("स्मृतिः क्षीणा\n", stderr); exit(70); }
    }
    k->yugmani[k->dirghata].kunjika = grah(key);
    k->yugmani[k->dirghata].mulyam = grah(value);
    k->dirghata++;
}

/* ---------------------------------------------------------------- UTF-8 */
int utf8_padam(const char *s, int offset) {
    unsigned char c = (unsigned char)s[offset];
    if (c < 0x80) return 1;
    if ((c & 0xE0) == 0xC0) return 2;
    if ((c & 0xF0) == 0xE0) return 3;
    if ((c & 0xF8) == 0xF0) return 4;
    return 1;
}

int utf8_ganana(const char *s, int baits) {
    int n = 0;
    for (int i = 0; i < baits; ) { i += utf8_padam(s, i); n++; }
    return n;
}

int utf8_sthanam(const char *s, int baits, int index) {
    int i = 0, n = 0;
    while (i < baits && n < index) { i += utf8_padam(s, i); n++; }
    return i;
}

static int shabda_dirghata(Shabda *s) {
    if (s->akshara < 0) s->akshara = utf8_ganana(s->paatha, s->baits);
    return s->akshara;
}

/* ------------------------------------------------------------ प्रकाराः */
const char *prakara_nama(Mulyam m) {
    switch (m.prakara) {
    case P_SHUNYAM:   return "शून्यम्";
    case P_SATYATA:   return "सत्यता";
    case P_PURNANKA:  return "पूर्णाङ्कः";
    case P_DASHAMSHA: return "दशांशः";
    case P_SHABDA:    return "शब्दः";
    case P_SUCHI:     return "सूची";
    case P_KOSHA:     return "कोशः";
    default:          return "कार्यम्";
    }
}

bool satyavat(Mulyam m) {
    switch (m.prakara) {
    case P_SHUNYAM:   return false;
    case P_SATYATA:   return m.as.satyata;
    case P_PURNANKA:  return m.as.purnanka != 0;
    case P_DASHAMSHA: return m.as.dashamsha != 0.0;
    case P_SHABDA:    return as_shabda(m)->baits > 0;
    case P_SUCHI:     return as_suchi(m)->dirghata > 0;
    case P_KOSHA:     return as_kosha(m)->dirghata > 0;
    default:          return true;
    }
}

static bool anka(Mulyam m) {
    return m.prakara == P_PURNANKA || m.prakara == P_DASHAMSHA;
}

static double anka_mulyam(Mulyam m) {
    return m.prakara == P_PURNANKA ? (double)m.as.purnanka : m.as.dashamsha;
}

bool samam(Mulyam a, Mulyam b) {
    if ((a.prakara == P_SATYATA) != (b.prakara == P_SATYATA)) return false;
    if (a.prakara == P_SATYATA) return a.as.satyata == b.as.satyata;
    if (a.prakara == P_SHUNYAM || b.prakara == P_SHUNYAM)
        return a.prakara == P_SHUNYAM && b.prakara == P_SHUNYAM;
    if (anka(a) && anka(b)) {
        if (a.prakara == P_PURNANKA && b.prakara == P_PURNANKA)
            return a.as.purnanka == b.as.purnanka;
        return anka_mulyam(a) == anka_mulyam(b);
    }
    if (a.prakara != b.prakara) return false;
    switch (a.prakara) {
    case P_SHABDA: {
        Shabda *x = as_shabda(a), *y = as_shabda(b);
        return x->baits == y->baits && memcmp(x->paatha, y->paatha, (size_t)x->baits) == 0;
    }
    case P_SUCHI: {
        Suchi *x = as_suchi(a), *y = as_suchi(b);
        if (x->dirghata != y->dirghata) return false;
        for (int i = 0; i < x->dirghata; i++)
            if (!samam(x->angani[i], y->angani[i])) return false;
        return true;
    }
    case P_KOSHA: {
        Kosha *x = as_kosha(a), *y = as_kosha(b);
        if (x->dirghata != y->dirghata) return false;
        for (int i = 0; i < x->dirghata; i++) {
            Mulyam other;
            if (!kosha_grihana(b, x->yugmani[i].kunjika, &other)) return false;
            if (!samam(x->yugmani[i].mulyam, other)) return false;
        }
        return true;
    }
    case P_ANTARNIHITAM: return a.as.antarnihitam == b.as.antarnihitam;
    default: return a.as.vastu == b.as.vastu;
    }
}

/* ------------------------------------------------------------- मुद्रणम् */
typedef struct { char *paatha; int dirghata, avakasha; } Lekha;

static void lekha_yojaya(Lekha *l, const char *s, int n) {
    if (l->dirghata + n + 1 > l->avakasha) {
        while (l->dirghata + n + 1 > l->avakasha)
            l->avakasha = l->avakasha ? l->avakasha * 2 : 64;
        l->paatha = (char *)realloc(l->paatha, (size_t)l->avakasha);
        if (!l->paatha) { fputs("स्मृतिः क्षीणा\n", stderr); exit(70); }
    }
    memcpy(l->paatha + l->dirghata, s, (size_t)n);
    l->dirghata += n;
    l->paatha[l->dirghata] = '\0';
}

static void lekha_yojaya_c(Lekha *l, const char *s) { lekha_yojaya(l, s, (int)strlen(s)); }

/* पैथन्-वत् दशांशस्य लेखनम् — the shortest representation that round-trips */
static void dashamsha_lekhaya(Lekha *l, double d) {
    if (isnan(d))      { lekha_yojaya_c(l, "nan"); return; }
    if (isinf(d))      { lekha_yojaya_c(l, d > 0 ? "inf" : "-inf"); return; }
    if (d == (double)(int64_t)d && fabs(d) < 1e18) {
        char buf[32];
        snprintf(buf, sizeof buf, "%lld", (long long)d);
        lekha_yojaya_c(l, buf);
        return;
    }
    char buf[64];
    for (int p = 1; p <= 17; p++) {
        snprintf(buf, sizeof buf, "%.*g", p, d);
        if (strtod(buf, NULL) == d) break;
    }
    lekha_yojaya_c(l, buf);
}

static void mulyam_lekhaya(Lekha *l, Mulyam m, bool uddhrta) {
    char buf[64];
    switch (m.prakara) {
    case P_SHUNYAM: lekha_yojaya_c(l, "शून्यम्"); return;
    case P_SATYATA: lekha_yojaya_c(l, m.as.satyata ? "सत्य" : "असत्य"); return;
    case P_PURNANKA:
        snprintf(buf, sizeof buf, "%lld", (long long)m.as.purnanka);
        lekha_yojaya_c(l, buf);
        return;
    case P_DASHAMSHA: dashamsha_lekhaya(l, m.as.dashamsha); return;
    case P_SHABDA: {
        Shabda *s = as_shabda(m);
        if (uddhrta) lekha_yojaya_c(l, "\"");
        lekha_yojaya(l, s->paatha, s->baits);
        if (uddhrta) lekha_yojaya_c(l, "\"");
        return;
    }
    case P_SUCHI: {
        Suchi *s = as_suchi(m);
        lekha_yojaya_c(l, "[");
        for (int i = 0; i < s->dirghata; i++) {
            if (i) lekha_yojaya_c(l, ", ");
            mulyam_lekhaya(l, s->angani[i], true);
        }
        lekha_yojaya_c(l, "]");
        return;
    }
    case P_KOSHA: {
        Kosha *k = as_kosha(m);
        lekha_yojaya_c(l, "{");
        for (int i = 0; i < k->dirghata; i++) {
            if (i) lekha_yojaya_c(l, ", ");
            mulyam_lekhaya(l, k->yugmani[i].kunjika, true);
            lekha_yojaya_c(l, ": ");
            mulyam_lekhaya(l, k->yugmani[i].mulyam, true);
        }
        lekha_yojaya_c(l, "}");
        return;
    }
    case P_AVARANA: {
        Avarana *a = (Avarana *)m.as.vastu;
        snprintf(buf, sizeof buf, "/%d>", a->karyam->prachala_ganana);
        lekha_yojaya_c(l, "<कार्यम् ");
        lekha_yojaya_c(l, a->karyam->nama);
        lekha_yojaya_c(l, buf);
        return;
    }
    case P_ANTARNIHITAM:
        lekha_yojaya_c(l, "<अन्तर्निहितम् ");
        lekha_yojaya_c(l, ANTARNIHITANI[m.as.antarnihitam].nama);
        lekha_yojaya_c(l, ">");
        return;
    }
}

char *shabdakr(Mulyam m, bool uddhrta) {
    Lekha l = { NULL, 0, 0 };
    lekha_yojaya_c(&l, "");
    mulyam_lekhaya(&l, m, uddhrta);
    return l.paatha;
}

/* ------------------------------------------------------------ प्रकारपरीक्षा */
bool prakara_melati(Mulyam m, const char *prakara) {
    if (!prakara || strcmp(prakara, "किमपि") == 0) return true;
    const char *vastavika = prakara_nama(m);
    if (strcmp(prakara, vastavika) == 0) return true;
    if (strcmp(prakara, "अङ्कः") == 0) return anka(m);
    if (strcmp(prakara, "दशांशः") == 0) return m.prakara == P_PURNANKA;
    return false;
}

bool prakaram_pariksaya(Mulyam m, const char *prakara, const char *kasya) {
    if (prakara_melati(m, prakara)) return true;
    dosha_utsrja("प्रकारदोषः",
                 "%s: %s अपेक्षितः, %s प्राप्तः / expected %s, got %s",
                 kasya, prakara, prakara_nama(m), prakara, prakara_nama(m));
    return false;
}

/* -------------------------------------------------------------- परिवेशः */
typedef struct { char *nama; Mulyam mulyam; char *prakara; bool dhruva; } Bandha;

struct Parivesha {
    int nirdeshah;
    Parivesha *janaka;
    Bandha *bandhah;
    int dirghata, avakasha;
};

Parivesha *parivesha_rachaya(Parivesha *janaka) {
    Parivesha *p = (Parivesha *)smrti(sizeof(Parivesha));
    p->nirdeshah = 1;
    p->janaka = janaka ? parivesha_grah(janaka) : NULL;
    p->bandhah = NULL;
    p->dirghata = p->avakasha = 0;
    return p;
}

Parivesha *parivesha_grah(Parivesha *p) { if (p) p->nirdeshah++; return p; }
Parivesha *parivesha_janaka(Parivesha *p) { return p ? p->janaka : NULL; }

void parivesha_muncha(Parivesha *p) {
    if (!p || --p->nirdeshah > 0) return;
    for (int i = 0; i < p->dirghata; i++) {
        free(p->bandhah[i].nama);
        free(p->bandhah[i].prakara);
        muncha(p->bandhah[i].mulyam);
    }
    free(p->bandhah);
    if (p->janaka) parivesha_muncha(p->janaka);
    free(p);
}

static char *nakala(const char *s) {
    if (!s) return NULL;
    size_t n = strlen(s) + 1;
    char *d = (char *)smrti(n);
    memcpy(d, s, n);
    return d;
}

static Bandha *bandha_anvishya(Parivesha *p, const char *nama) {
    for (int i = 0; i < p->dirghata; i++)
        if (strcmp(p->bandhah[i].nama, nama) == 0) return &p->bandhah[i];
    return NULL;
}

bool parivesha_ghoshaya(Parivesha *p, const char *nama, Mulyam m,
                        bool dhruva, const char *prakara) {
    if (!prakaram_pariksaya(m, prakara, "")) return false;
    Bandha *b = bandha_anvishya(p, nama);
    if (b) {
        Mulyam purva = b->mulyam;
        b->mulyam = grah(m);
        b->dhruva = dhruva;
        free(b->prakara);
        b->prakara = (prakara && strcmp(prakara, "किमपि") != 0) ? nakala(prakara) : NULL;
        muncha(purva);
        return true;
    }
    if (p->dirghata == p->avakasha) {
        p->avakasha = p->avakasha ? p->avakasha * 2 : 8;
        p->bandhah = (Bandha *)realloc(p->bandhah, sizeof(Bandha) * (size_t)p->avakasha);
        if (!p->bandhah) { fputs("स्मृतिः क्षीणा\n", stderr); exit(70); }
    }
    p->bandhah[p->dirghata].nama = nakala(nama);
    p->bandhah[p->dirghata].mulyam = grah(m);
    p->bandhah[p->dirghata].dhruva = dhruva;
    p->bandhah[p->dirghata].prakara =
        (prakara && strcmp(prakara, "किमपि") != 0) ? nakala(prakara) : NULL;
    p->dirghata++;
    return true;
}

bool parivesha_grihana(Parivesha *p, const char *nama, Mulyam *out) {
    for (Parivesha *q = p; q; q = q->janaka) {
        Bandha *b = bandha_anvishya(q, nama);
        if (b) { *out = b->mulyam; return true; }
    }
    return false;
}

Parivesha *parivesha_sthanam(Parivesha *p, int uttarah, int sthanam,
                             const char *nama) {
    for (int i = 0; i < uttarah && p; i++) p = p->janaka;
    if (!p || sthanam >= p->dirghata) return NULL;
    /* एका तुलना, न सर्वेषाम् — one comparison confirms the place, where the
       search by name would have made one for every binding it passed. */
    if (strcmp(p->bandhah[sthanam].nama, nama) != 0) return NULL;
    return p;
}

Mulyam parivesha_sthanat(Parivesha *p, int sthanam) {
    return p->bandhah[sthanam].mulyam;
}

bool parivesha_asti(Parivesha *p, const char *nama) {
    Mulyam ignored;
    return parivesha_grihana(p, nama, &ignored);
}

bool parivesha_nyasaya(Parivesha *p, const char *nama, Mulyam m) {
    for (Parivesha *q = p; q; q = q->janaka) {
        Bandha *b = bandha_anvishya(q, nama);
        if (!b) continue;
        if (b->dhruva) {
            dosha_utsrja("ध्रुवदोषः",
                         "ध्रुवः '%s' न परिवर्तनीयः / cannot reassign the constant '%s'",
                         nama, nama);
            return false;
        }
        if (b->prakara) {
            char kasya[256];
            snprintf(kasya, sizeof kasya, "चरः '%s'", nama);
            if (!prakaram_pariksaya(m, b->prakara, kasya)) return false;
        }
        Mulyam purva = b->mulyam;
        b->mulyam = grah(m);
        muncha(purva);
        return true;
    }
    dosha_utsrja("नामदोषः",
                 "अपरिभाषितम् नाम '%s' — प्रथमम् 'मान' इति उपयुज्यताम् / "
                 "undefined name '%s'", nama, nama);
    return false;
}

int parivesha_ganana(Parivesha *p) { return p->dirghata; }
const char *parivesha_nama_at(Parivesha *p, int i) { return p->bandhah[i].nama; }
Mulyam parivesha_mulyam_at(Parivesha *p, int i) { return p->bandhah[i].mulyam; }

/* helper used by the built-ins and the VM for string lengths */
int vak_shabda_dirghata(Mulyam m) { return shabda_dirghata(as_shabda(m)); }
