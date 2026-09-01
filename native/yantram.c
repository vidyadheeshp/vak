/*
 * yantram.c — संस्कृतयन्त्रम् in C / the native SanskritVM.
 *
 * A stack machine over the same environment chain the Python and Vāk VMs use,
 * so the three agree instruction for instruction. Errors travel by longjmp to
 * the dispatch loop, which then unwinds the प्रयत्नः handler stack.
 */
#include "vak.h"

#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if VAK_WINDOWS
#include <windows.h>
#endif

Dosha VARTAMANA_DOSHA;
bool DOSHA_ASTI = false;

/* दोषः ध्वजेन गच्छति, न लङ्घनेन — setjmp/longjmp is deliberately avoided:
   under MinGW longjmp unwinds through SEH, which optimised frames do not
   survive. Every raise sets this flag, every caller returns at once, and the
   dispatch loop unwinds the प्रयत्नः handlers itself. */
void dosha_utsrja(const char *prakara, const char *fmt, ...) {
    if (DOSHA_ASTI) return;                 /* the first दोषः wins */
    snprintf(VARTAMANA_DOSHA.prakara, sizeof VARTAMANA_DOSHA.prakara, "%s", prakara);
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(VARTAMANA_DOSHA.sandesha, sizeof VARTAMANA_DOSHA.sandesha, fmt, ap);
    va_end(ap);
    VARTAMANA_DOSHA.pankti = 0;
    VARTAMANA_DOSHA.has_mulyam = false;
    DOSHA_ASTI = true;
}

/* ------------------------------------------------------------ ध्रुवस्मृतिः */
typedef struct { const Khanda *khanda; Mulyam *mulyani; } DhruvaSmrti;
static DhruvaSmrti *SMRTAYAH = NULL;
static int SMRTI_GANANA = 0, SMRTI_AVAKASHA = 0;

/* अन्तिमम् स्मृतम् — आवर्तने सः एव खण्डः पुनः पुनः, अतः एकपदिका स्मृतिः
   प्रायः पर्याप्ता, अन्यथा पूर्णा सूची अन्विष्यते।
   A recursive function pushes a frame for the same chunk over and over, so
   remembering the last one answers almost every call without the scan. */
static const Khanda *SMRTA_ANTIMA_KHANDA = NULL;
static Mulyam *SMRTA_ANTIMA_MULYANI = NULL;

static Mulyam *dhruvan_nirmaya(const Khanda *k) {
    if (k == SMRTA_ANTIMA_KHANDA) return SMRTA_ANTIMA_MULYANI;
    for (int i = 0; i < SMRTI_GANANA; i++)
        if (SMRTAYAH[i].khanda == k) {
            SMRTA_ANTIMA_KHANDA = k;
            SMRTA_ANTIMA_MULYANI = SMRTAYAH[i].mulyani;
            return SMRTAYAH[i].mulyani;
        }
    Mulyam *arr = (Mulyam *)malloc(sizeof(Mulyam) * (size_t)(k->dhruva_ganana ? k->dhruva_ganana : 1));
    for (int i = 0; i < k->dhruva_ganana; i++) {
        const Dhruva *d = &k->dhruvah[i];
        switch (d->prakara) {
        case K_PURNANKA:  arr[i] = purnanka_mulyam(d->purnanka); break;
        case K_DASHAMSHA: arr[i] = dashamsha_mulyam(d->dashamsha); break;
        case K_SHABDA:    arr[i] = shabda_mulyam_c(d->shabda); break;
        case K_SATYATA:   arr[i] = satyata_mulyam(d->satyata); break;
        default:          arr[i] = shunyam_mulyam(); break;
        }
    }
    if (SMRTI_GANANA == SMRTI_AVAKASHA) {
        SMRTI_AVAKASHA = SMRTI_AVAKASHA ? SMRTI_AVAKASHA * 2 : 16;
        SMRTAYAH = (DhruvaSmrti *)realloc(SMRTAYAH, sizeof(DhruvaSmrti) * (size_t)SMRTI_AVAKASHA);
    }
    SMRTAYAH[SMRTI_GANANA].khanda = k;
    SMRTAYAH[SMRTI_GANANA].mulyani = arr;
    SMRTI_GANANA++;
    SMRTA_ANTIMA_KHANDA = k;
    SMRTA_ANTIMA_MULYANI = arr;
    return arr;
}

/* ----------------------------------------------------------------- यन्त्रम् */
typedef struct {
    int dosha_sthanam, anta_sthanam;
    Parivesha *parivesha;
    int uchchata;
} Prabandhaka;

typedef struct {
    const Khanda *khanda;
    const Mulyam *dhruvani;
    int sthanam;
    Parivesha *parivesha;
    int adhara;
    const Avarana *avarana;
    Prabandhaka prabandhakah[32];
    int prabandhaka_ganana;
    bool pralambitam;
} Chaukati;

typedef struct { const char *pathah; Mulyam kosha; bool chalati; } VibhagaSmrti;

/* चालनकाले योजिताः विभागाः — modules handed in by खण्डम्_चालय at run time,
   as opposed to those the code generator linked in statically. */
typedef struct { const char *pathah; const Khanda *khanda; } GatikaVibhaga;
static GatikaVibhaga *GATIKAH = NULL;
static int GATIKA_GANANA = 0, GATIKA_AVAKASHA = 0;

typedef struct {
    Mulyam *stupa;
    int stupa_dirghata, stupa_avakasha;
    Chaukati chaukatyah[1024];
    int chaukati_ganana;
    Parivesha *vaishvika;
    VibhagaSmrti *vibhagah;
    int vibhaga_ganana, vibhaga_avakasha;
} Yantram;

static Yantram Y;

static void sthapaya(Mulyam m) {
    if (Y.stupa_dirghata == Y.stupa_avakasha) {
        Y.stupa_avakasha = Y.stupa_avakasha ? Y.stupa_avakasha * 2 : 256;
        Y.stupa = (Mulyam *)realloc(Y.stupa, sizeof(Mulyam) * (size_t)Y.stupa_avakasha);
    }
    Y.stupa[Y.stupa_dirghata++] = m;      /* the reference moves onto the stack */
}

static Mulyam grihana_stupat(void) { return Y.stupa[--Y.stupa_dirghata]; }
static Mulyam shikharam(void)      { return Y.stupa[Y.stupa_dirghata - 1]; }

static void stupam_nyunikuru(int uchchata) {
    while (Y.stupa_dirghata > uchchata) muncha(grihana_stupat());
}

static Chaukati *chaukati(void) { return &Y.chaukatyah[Y.chaukati_ganana - 1]; }

static int vartamana_pankti(void) {
    if (Y.chaukati_ganana == 0) return 0;
    Chaukati *c = chaukati();
    int i = c->sthanam - 1;
    if (i < 0) i = 0;
    if (i >= c->khanda->sanketa_ganana) i = c->khanda->sanketa_ganana - 1;
    return c->khanda->panktayah[i];
}

/* --------------------------------------------------------------- संकारकाः */
static bool anka(Mulyam m) {
    return m.prakara == P_PURNANKA || m.prakara == P_DASHAMSHA;
}
static double anka_mulyam(Mulyam m) {
    return m.prakara == P_PURNANKA ? (double)m.as.purnanka : m.as.dashamsha;
}

static void ankam_apekshasva(Mulyam m, const char *chihna) {
    if (!anka(m))
        dosha_utsrja("प्रकारदोषः",
                     "'%s' इत्यस्य कृते अङ्कः आवश्यकः, प्राप्तम् %s / "
                     "operator '%s' needs a number, got %s",
                     chihna, prakara_nama(m), chihna, prakara_nama(m));
}

static const char *adesha_chihna(int adesha) {
    switch (adesha) {
    case A_VIYOGAH: return "-";
    case A_GUNANAM: return "*";
    case A_BHAGAH:  return "/";
    case A_SHESHAH: return "%";
    case A_GHATAH:  return "^";
    case A_NYUNAM:  return "<";
    case A_NYUNASAMAM: return "<=";
    case A_ADHIKAM: return ">";
    default: return ">=";
    }
}

/* अग्रिमः आदेशः किम् एतम् एव बन्धम् प्रति न्यस्यति? — does the instruction
   after this one assign back to a binding that currently holds `m`, and would
   that assignment succeed?  The name is read from the same constant table the
   assignment will read it from, the value is compared by identity, and a ध्रुव
   or a refusing प्रकारः disqualifies it — because the growth happens first and
   a failed assignment must leave nothing behind. */
static bool vardhitum_shakyate(const Chaukati *c, Mulyam m) {
    const int *s = c->khanda->sanketah;
    int at = c->sthanam;
    if (at >= c->khanda->sanketa_ganana) return false;
    const char *nama = NULL;
    if (s[at] == A_NYASAYA) {
        if (at + 1 >= c->khanda->sanketa_ganana) return false;
        nama = c->khanda->dhruvah[s[at + 1]].shabda;
    } else if (s[at] == A_STHANE_NYASAYA) {
        if (at + 3 >= c->khanda->sanketa_ganana) return false;
        nama = c->khanda->dhruvah[s[at + 3]].shabda;
    } else {
        return false;
    }
    return nama && parivesha_vardhaniyam(c->parivesha, nama, m);
}

static Mulyam yojanam(Mulyam vama, Mulyam dakshina) {
    /* उभौ शब्दौ चेत् — the common case, and the one that must not copy thrice */
    if (vama.prakara == P_SHABDA && dakshina.prakara == P_SHABDA) {
        Shabda *a = as_shabda(vama), *b = as_shabda(dakshina);
        return shabda_yugmam(a->paatha, a->baits, b->paatha, b->baits);
    }
    if (vama.prakara == P_SHABDA || dakshina.prakara == P_SHABDA) {
        char *a = shabdakr(vama, false), *b = shabdakr(dakshina, false);
        int na = (int)strlen(a), nb = (int)strlen(b);
        char *buf = (char *)malloc((size_t)(na + nb + 1));
        memcpy(buf, a, (size_t)na);
        memcpy(buf + na, b, (size_t)nb);
        buf[na + nb] = '\0';
        Mulyam out = shabda_mulyam(buf, na + nb);
        free(a); free(b); free(buf);
        return out;
    }
    if (vama.prakara == P_SUCHI && dakshina.prakara == P_SUCHI) {
        Mulyam out = suchi_mulyam();
        Suchi *a = as_suchi(vama), *b = as_suchi(dakshina);
        for (int i = 0; i < a->dirghata; i++) suchi_yojaya(out, a->angani[i]);
        for (int i = 0; i < b->dirghata; i++) suchi_yojaya(out, b->angani[i]);
        return out;
    }
    ankam_apekshasva(vama, "+");
    ankam_apekshasva(dakshina, "+");
    if (DOSHA_ASTI) return shunyam_mulyam();
    if (vama.prakara == P_PURNANKA && dakshina.prakara == P_PURNANKA)
        return purnanka_mulyam(vama.as.purnanka + dakshina.as.purnanka);
    return dashamsha_mulyam(anka_mulyam(vama) + anka_mulyam(dakshina));
}

static Mulyam ganitam(int adesha, Mulyam vama, Mulyam dakshina) {
    if (adesha == A_GUNANAM && vama.prakara == P_SHABDA
        && dakshina.prakara == P_PURNANKA) {
        Shabda *s = as_shabda(vama);
        int64_t n = dakshina.as.purnanka;
        if (n < 0) n = 0;
        char *buf = (char *)malloc((size_t)(s->baits * (int)n + 1));
        int j = 0;
        for (int64_t i = 0; i < n; i++) { memcpy(buf + j, s->paatha, (size_t)s->baits); j += s->baits; }
        buf[j] = '\0';
        Mulyam out = shabda_mulyam(buf, j);
        free(buf);
        return out;
    }
    const char *chihna = adesha_chihna(adesha);
    ankam_apekshasva(vama, chihna);
    ankam_apekshasva(dakshina, chihna);
    if (DOSHA_ASTI) return shunyam_mulyam();
    bool purnau = vama.prakara == P_PURNANKA && dakshina.prakara == P_PURNANKA;
    switch (adesha) {
    case A_VIYOGAH:
        return purnau ? purnanka_mulyam(vama.as.purnanka - dakshina.as.purnanka)
                      : dashamsha_mulyam(anka_mulyam(vama) - anka_mulyam(dakshina));
    case A_GUNANAM:
        return purnau ? purnanka_mulyam(vama.as.purnanka * dakshina.as.purnanka)
                      : dashamsha_mulyam(anka_mulyam(vama) * anka_mulyam(dakshina));
    case A_BHAGAH: {
        if (anka_mulyam(dakshina) == 0.0) {
            dosha_utsrja("गणितदोषः", "भागहारः शून्येन न शक्यः / division by zero");
            return shunyam_mulyam();
        }
        double r = anka_mulyam(vama) / anka_mulyam(dakshina);
        if (purnau && r == (double)(int64_t)r) return purnanka_mulyam((int64_t)r);
        return dashamsha_mulyam(r);
    }
    case A_SHESHAH: {
        if (anka_mulyam(dakshina) == 0.0) {
            dosha_utsrja("गणितदोषः", "शून्येन शेषः न शक्यः / modulo by zero");
            return shunyam_mulyam();
        }
        if (purnau) {
            int64_t a = vama.as.purnanka, b = dakshina.as.purnanka;
            int64_t r = a % b;
            if (r != 0 && ((r < 0) != (b < 0))) r += b;   /* Python semantics */
            return purnanka_mulyam(r);
        }
        double a = anka_mulyam(vama), b = anka_mulyam(dakshina);
        double r = a - b * (double)(int64_t)(a / b);
        if (r != 0 && ((r < 0) != (b < 0))) r += b;
        return dashamsha_mulyam(r);
    }
    default:
        if (purnau && dakshina.as.purnanka >= 0) {
            int64_t out = 1, b = vama.as.purnanka;
            for (int64_t i = 0; i < dakshina.as.purnanka; i++) out *= b;
            return purnanka_mulyam(out);
        }
        return dashamsha_mulyam(pow(anka_mulyam(vama), anka_mulyam(dakshina)));
    }
}

static bool tulana_kuru(int adesha, Mulyam vama, Mulyam dakshina) {
    if (!(vama.prakara == P_SHABDA && dakshina.prakara == P_SHABDA)) {
        const char *chihna = adesha_chihna(adesha);
        ankam_apekshasva(vama, chihna);
        ankam_apekshasva(dakshina, chihna);
        if (DOSHA_ASTI) return false;
        double a = anka_mulyam(vama), b = anka_mulyam(dakshina);
        switch (adesha) {
        case A_NYUNAM: return a < b;
        case A_NYUNASAMAM: return a <= b;
        case A_ADHIKAM: return a > b;
        default: return a >= b;
        }
    }
    Shabda *x = as_shabda(vama), *y = as_shabda(dakshina);
    int n = x->baits < y->baits ? x->baits : y->baits;
    int c = memcmp(x->paatha, y->paatha, (size_t)n);
    if (c == 0) c = (x->baits < y->baits) ? -1 : (x->baits > y->baits ? 1 : 0);
    switch (adesha) {
    case A_NYUNAM: return c < 0;
    case A_NYUNASAMAM: return c <= 0;
    case A_ADHIKAM: return c > 0;
    default: return c >= 0;
    }
}

/* ---------------------------------------------------------------- सूचकाः */
static int64_t suchakam_pariksaya(Mulyam suchaka) {
    if (!anka(suchaka)) {
        dosha_utsrja("प्रकारदोषः",
                     "सूचकः अङ्कः भवेत् / the index must be a number, got %s",
                     prakara_nama(suchaka));
        return 0;
    }
    return (int64_t)anka_mulyam(suchaka);
}

static Mulyam suchakat_grihana(Mulyam lakshya, Mulyam suchaka) {
    if (lakshya.prakara == P_SUCHI || lakshya.prakara == P_SHABDA) {
        int64_t at = suchakam_pariksaya(suchaka);
        if (DOSHA_ASTI) return shunyam_mulyam();
        int dirghata = (lakshya.prakara == P_SUCHI)
                     ? as_suchi(lakshya)->dirghata
                     : utf8_ganana(as_shabda(lakshya)->paatha, as_shabda(lakshya)->baits);
        int64_t norm = at < 0 ? at + dirghata : at;
        if (norm < 0 || norm >= dirghata) {
            dosha_utsrja("सूचकदोषः",
                         "सूचकः परिधेः बहिः %lld / index %lld is out of range",
                         (long long)at, (long long)at);
            return shunyam_mulyam();
        }
        if (lakshya.prakara == P_SUCHI) return grah(as_suchi(lakshya)->angani[norm]);
        Shabda *s = as_shabda(lakshya);
        int a = utf8_sthanam(s->paatha, s->baits, (int)norm);
        return shabda_mulyam(s->paatha + a, utf8_padam(s->paatha, a));
    }
    if (lakshya.prakara == P_KOSHA) {
        Mulyam out;
        if (!kosha_grihana(lakshya, suchaka, &out)) {
            char *k = shabdakr(suchaka, true);
            dosha_utsrja("कुञ्जिकादोषः",
                         "कुञ्जिका न विद्यते %s / no such key %s", k, k);
            free(k);
            return shunyam_mulyam();
        }
        return grah(out);
    }
    dosha_utsrja("प्रकारदोषः",
                 "%s इत्यस्मिन् सूचकः न प्रयोज्यः / cannot index a %s",
                 prakara_nama(lakshya), prakara_nama(lakshya));
    return shunyam_mulyam();
}

static void suchake_nyasaya(Mulyam lakshya, Mulyam suchaka, Mulyam mulyam) {
    if (lakshya.prakara == P_SUCHI) {
        Suchi *s = as_suchi(lakshya);
        int64_t at = suchakam_pariksaya(suchaka);
        if (DOSHA_ASTI) return;
        int64_t norm = at < 0 ? at + s->dirghata : at;
        if (norm < 0 || norm >= s->dirghata) {
            dosha_utsrja("सूचकदोषः",
                         "सूचकः परिधेः बहिः %lld / index %lld is out of range",
                         (long long)at, (long long)at);
            return;
        }
        Mulyam purva = s->angani[norm];
        s->angani[norm] = grah(mulyam);
        muncha(purva);
        return;
    }
    if (lakshya.prakara == P_KOSHA) { kosha_nyasaya(lakshya, suchaka, mulyam); return; }
    dosha_utsrja("प्रकारदोषः",
                 "%s इत्यस्मिन् न स्थापयितुं शक्यते / cannot assign into a %s",
                 prakara_nama(lakshya), prakara_nama(lakshya));
}

/* ------------------------------------------------------------- आह्वानम् */
static void chaukatim_yojaya(const Khanda *k, Parivesha *p, const Avarana *a, int adhara) {
    if (Y.chaukati_ganana >= (int)(sizeof(Y.chaukatyah) / sizeof(Y.chaukatyah[0]))) {
        dosha_utsrja("कार्यकालदोषः", "अतिगभीरम् आवर्तनम् / recursion too deep");
        return;
    }
    Chaukati *c = &Y.chaukatyah[Y.chaukati_ganana++];
    c->khanda = k;
    c->dhruvani = dhruvan_nirmaya(k);
    c->sthanam = 0;
    c->parivesha = p;
    c->adhara = adhara;
    c->avarana = a;
    c->prabandhaka_ganana = 0;
    c->pralambitam = false;
}

static void karakaih_kramaya(const SankalitaKaryam *k, Mulyam *prachalah, int ganana,
                             const char **karakah, Mulyam *out) {
    bool purnani[32];
    for (int i = 0; i < k->prachala_ganana; i++) { purnani[i] = false; out[i] = shunyam_mulyam(); }
    for (int i = 0; i < ganana; i++) {
        if (!karakah[i]) continue;
        int at = -1;
        for (int j = 0; j < k->prachala_ganana; j++)
            if (k->prachalah[j].karakam && strcmp(k->prachalah[j].karakam, karakah[i]) == 0) at = j;
        if (at < 0) {
            dosha_utsrja("कारकदोषः",
                         "अस्मिन् कार्ये %s इति कारकम् नास्ति / this कार्यम् declares no %s parameter",
                         karakah[i], karakah[i]);
            return;
        }
        if (purnani[at]) {
            dosha_utsrja("कारकदोषः",
                         "%s इति कारकम् द्विः दत्तम् / the %s argument was given twice",
                         karakah[i], karakah[i]);
            return;
        }
        out[at] = prachalah[i];
        purnani[at] = true;
    }
    int next = 0;
    for (int i = 0; i < ganana; i++) {
        if (karakah[i]) continue;
        while (next < k->prachala_ganana && purnani[next]) next++;
        if (next >= k->prachala_ganana) {
            dosha_utsrja("प्राचलदोषः", "अतिरिक्ताः प्राचलाः / too many arguments");
            return;
        }
        out[next] = prachalah[i];
        purnani[next] = true;
    }
    for (int i = 0; i < k->prachala_ganana; i++)
        if (!purnani[i]) {
            dosha_utsrja("प्राचलदोषः", "न्यूनाः प्राचलाः / missing argument(s)");
            return;
        }
}

static void ahvanam_kuru(Mulyam ahveyam, Mulyam *prachalah, int ganana,
                         const char **karakah) {
    if (ahveyam.prakara == P_ANTARNIHITAM) {
        const Antarnihitam *a = &ANTARNIHITANI[ahveyam.as.antarnihitam];
        if (karakah)
            dosha_utsrja("कारकदोषः",
                         "कारकनामभिः आह्वानम् केवलम् कारकयुक्तस्य कार्यस्य कृते / "
                         "kāraka labels need a कार्यम् whose parameters declare roles");
        if (a->prachala_ganana >= 0 && ganana != a->prachala_ganana) {
            dosha_utsrja("प्राचलदोषः",
                         "%s: %d प्राचलाः अपेक्षिताः, %d प्राप्ताः / "
                         "expected %d argument(s), got %d",
                         a->nama, a->prachala_ganana, ganana,
                         a->prachala_ganana, ganana);
            for (int i = 0; i < ganana; i++) muncha(prachalah[i]);
            return;
        }
        Mulyam out = a->karyam(prachalah, ganana);
        for (int i = 0; i < ganana; i++) muncha(prachalah[i]);
        if (DOSHA_ASTI) { muncha(out); return; }
        sthapaya(out);
        return;
    }
    if (ahveyam.prakara != P_AVARANA) {
        dosha_utsrja("प्रकारदोषः",
                     "%s आह्वातुं न शक्यते / %s is not callable",
                     prakara_nama(ahveyam), prakara_nama(ahveyam));
        for (int i = 0; i < ganana; i++) muncha(prachalah[i]);
        return;
    }

    Avarana *a = (Avarana *)ahveyam.as.vastu;
    const SankalitaKaryam *k = a->karyam;
    Mulyam kramitah[32];
    if (karakah) {
        karakaih_kramaya(k, prachalah, ganana, karakah, kramitah);
        if (DOSHA_ASTI) return;
        ganana = k->prachala_ganana;
    } else {
        for (int i = 0; i < ganana && i < 32; i++) kramitah[i] = prachalah[i];
    }
    if (ganana != k->prachala_ganana) {
        dosha_utsrja("प्राचलदोषः",
                     "%s: %d प्राचलाः अपेक्षिताः, %d प्राप्ताः / "
                     "expected %d argument(s), got %d",
                     k->nama, k->prachala_ganana, ganana, k->prachala_ganana, ganana);
        for (int i = 0; i < ganana; i++) muncha(kramitah[i]);
        return;
    }

    Parivesha *p = parivesha_rachaya(a->parivesha);
    for (int i = 0; i < k->prachala_ganana; i++) {
        /* सन्देशः तदा एव रच्यते यदा दोषः — the message that names the parameter
           is only worth building once the check has actually failed.  Formatting
           it first cost an snprintf per argument per call, always discarded. */
        if (!prakara_melati(kramitah[i], k->prachalah[i].prakara)) {
            char kasya[256];
            snprintf(kasya, sizeof kasya, "%s इत्यस्य प्राचलः '%s'",
                     k->nama, k->prachalah[i].nama);
            prakaram_pariksaya(kramitah[i], k->prachalah[i].prakara, kasya);
            for (int j = 0; j < k->prachala_ganana; j++) muncha(kramitah[j]);
            parivesha_muncha(p);
            return;
        }
        parivesha_prachalam_dhara(p, k->prachalah[i].nama, kramitah[i],
                                  k->prachalah[i].prakara);
    }
    for (int i = 0; i < k->prachala_ganana; i++) muncha(kramitah[i]);
    chaukatim_yojaya(k->khanda, p, a, Y.stupa_dirghata);
}

/* नामनिधिः — बन्धः नाम न प्रतिलिखति, अतः यत् नाम अत्र गण्यते तत् आह्वानात्
   परम् अपि जीवेत्।  आयाताः अल्पाः, विभागाः च स्मर्यन्ते, अतः एतत् एकवारम्
   स्थाप्यते, न च कदापि मुच्यते — तत् एव अभिप्रेतम्।
   A binding borrows its name, so a name *derived* at run time must outlive the
   call that derived it.  The only such name is a module's, worked out from its
   path when no alias was given.  Imports are few and modules are cached, so it
   is interned once here and deliberately never freed. */
static const char *nama_sthapaya(const char *s) {
    static char **nidhi = NULL;
    static int ganana = 0, avakasha = 0;
    for (int i = 0; i < ganana; i++)
        if (strcmp(nidhi[i], s) == 0) return nidhi[i];
    if (ganana == avakasha) {
        avakasha = avakasha ? avakasha * 2 : 8;
        nidhi = (char **)realloc(nidhi, sizeof(char *) * (size_t)avakasha);
        if (!nidhi) { fputs("स्मृतिः क्षीणा\n", stderr); exit(70); }
    }
    size_t n = strlen(s) + 1;
    char *d = (char *)malloc(n);
    if (!d) { fputs("स्मृतिः क्षीणा\n", stderr); exit(70); }
    memcpy(d, s, n);
    nidhi[ganana++] = d;
    return d;
}

/* ---------------------------------------------------------------- आयातः */
static Mulyam vibhagam_anaya(const char *pathah);

static void ayatam_kuru(Chaukati *c, const Dhruva *d) {
    Mulyam vibhaga = vibhagam_anaya(d->shabda);
    if (DOSHA_ASTI) return;
    if (d->shabda_ganana > 0) {
        for (int i = 0; i < d->shabda_ganana; i++) {
            const char *nama = d->shabdah[i + 1];
            Mulyam key = shabda_mulyam_c(nama), out;
            if (!kosha_grihana(vibhaga, key, &out)) {
                muncha(key);
                dosha_utsrja("आयातदोषः",
                             "'%s' इत्यस्मिन् '%s' इति नास्ति / module '%s' has no '%s'",
                             d->shabda, nama, d->shabda, nama);
                return;
            }
            parivesha_ghoshaya(c->parivesha, nama, out, false, "किमपि");
            muncha(key);
        }
        return;
    }
    const char *bandhanam = d->shabdah[0];
    char mula[256];
    if (!bandhanam) {
        const char *slash = strrchr(d->shabda, '/');
        const char *base = slash ? slash + 1 : d->shabda;
        snprintf(mula, sizeof mula, "%s", base);
        char *dot = strrchr(mula, '.');
        if (dot && strcmp(dot, ".vak") == 0) *dot = '\0';
        bandhanam = nama_sthapaya(mula);
    }
    parivesha_ghoshaya(c->parivesha, bandhanam, vibhaga, false, "किमपि");
}

/* --------------------------------------------------------- मुख्यम् चक्रम् */
static Mulyam adeshan_chalaya(int virama_gabhirata);

static bool prasaraya(Mulyam dosha_kosha, int virama_gabhirata) {
    while (Y.chaukati_ganana > virama_gabhirata) {
        Chaukati *c = chaukati();
        while (c->prabandhaka_ganana > 0) {
            Prabandhaka p = c->prabandhakah[--c->prabandhaka_ganana];
            stupam_nyunikuru(p.uchchata);
            c->parivesha = p.parivesha;
            if (p.dosha_sthanam >= 0) {
                sthapaya(grah(dosha_kosha));
                c->sthanam = p.dosha_sthanam;
                return true;
            }
            if (p.anta_sthanam >= 0) {
                c->pralambitam = true;
                c->sthanam = p.anta_sthanam;
                return true;
            }
        }
        if (Y.chaukati_ganana - 1 <= virama_gabhirata) return false;
        stupam_nyunikuru(c->adhara);
        parivesha_muncha(c->parivesha);
        Y.chaukati_ganana--;
    }
    return false;
}

static Mulyam dosha_kosham_rachaya(void) {
    if (VARTAMANA_DOSHA.has_mulyam && VARTAMANA_DOSHA.mulyam.prakara == P_KOSHA) {
        Mulyam thrown = VARTAMANA_DOSHA.mulyam;   /* ownership moves out */
        VARTAMANA_DOSHA.has_mulyam = false;
        VARTAMANA_DOSHA.mulyam = shunyam_mulyam();
        Mulyam key = shabda_mulyam_c("पङ्क्तिः"), had;
        bool zero = !kosha_grihana(thrown, key, &had)
                    || (had.prakara == P_PURNANKA && had.as.purnanka == 0);
        if (zero) {
            Mulyam line = purnanka_mulyam(VARTAMANA_DOSHA.pankti);
            kosha_nyasaya(thrown, key, line);
            muncha(line);
        }
        muncha(key);
        return thrown;
    }
    Mulyam k = kosha_mulyam();
    Mulyam key, val;
    key = shabda_mulyam_c("प्रकारः"); val = shabda_mulyam_c(VARTAMANA_DOSHA.prakara);
    kosha_nyasaya(k, key, val); muncha(key); muncha(val);
    key = shabda_mulyam_c("सन्देशः"); val = shabda_mulyam_c(VARTAMANA_DOSHA.sandesha);
    kosha_nyasaya(k, key, val); muncha(key); muncha(val);
    key = shabda_mulyam_c("पङ्क्तिः"); val = purnanka_mulyam(VARTAMANA_DOSHA.pankti);
    kosha_nyasaya(k, key, val); muncha(key); muncha(val);
    if (VARTAMANA_DOSHA.has_mulyam) {
        key = shabda_mulyam_c("मूल्यम्");
        kosha_nyasaya(k, key, VARTAMANA_DOSHA.mulyam);
        muncha(key);
    }
    return k;
}

static Mulyam chakram(int virama_gabhirata) {
    for (;;) {
        Mulyam phalam = adeshan_chalaya(virama_gabhirata);
        if (!DOSHA_ASTI) return phalam;
        DOSHA_ASTI = false;
        if (VARTAMANA_DOSHA.pankti == 0) VARTAMANA_DOSHA.pankti = vartamana_pankti();
        Mulyam dosha_kosha = dosha_kosham_rachaya();
        bool grihitam = prasaraya(dosha_kosha, virama_gabhirata);
        muncha(dosha_kosha);
        if (grihitam) continue;
        if (virama_gabhirata > 0) { DOSHA_ASTI = true; return shunyam_mulyam(); }
        fflush(stdout);
        fprintf(stderr, "%s (Runtime Error) \xe2\x80\x94 %d\n    %s\n",
                VARTAMANA_DOSHA.prakara, VARTAMANA_DOSHA.pankti,
                VARTAMANA_DOSHA.sandesha);
        exit(70);
    }
}

static Mulyam adeshan_chalaya(int virama_gabhirata) {
    for (;;) {
        if (DOSHA_ASTI) return shunyam_mulyam();
        Chaukati *c = chaukati();
        const int *sanketah = c->khanda->sanketah;
        int adesha = sanketah[c->sthanam++];

        switch (adesha) {
        case A_STHAPAYA:
            sthapaya(grah(c->dhruvani[sanketah[c->sthanam++]]));
            break;
        case A_SHUNYAM: sthapaya(shunyam_mulyam()); break;
        case A_SATYAM:  sthapaya(satyata_mulyam(true)); break;
        case A_ASATYAM: sthapaya(satyata_mulyam(false)); break;
        case A_TYAJA:   muncha(grihana_stupat()); break;
        case A_DVITVAM: sthapaya(grah(shikharam())); break;

        case A_GHOSHAYA:
        case A_DHRUVAM_GHOSHAYA: {
            const char *nama = c->khanda->dhruvah[sanketah[c->sthanam]].shabda;
            const char *prakara = c->khanda->dhruvah[sanketah[c->sthanam + 1]].shabda;
            c->sthanam += 2;
            Mulyam m = grihana_stupat();
            char kasya[256];
            snprintf(kasya, sizeof kasya, "चरः '%s'", nama);
            if (prakaram_pariksaya(m, prakara, kasya))
                parivesha_ghoshaya(c->parivesha, nama, m,
                                   adesha == A_DHRUVAM_GHOSHAYA, prakara);
            muncha(m);
            break;
        }
        case A_GRIHANA: {
            const char *nama = c->khanda->dhruvah[sanketah[c->sthanam++]].shabda;
            Mulyam out;
            if (parivesha_grihana(c->parivesha, nama, &out)) { sthapaya(grah(out)); break; }
            int a = antarnihitam_anvishya(nama);
            if (a >= 0) { sthapaya(antarnihitam_mulyam(a)); break; }
            dosha_utsrja("नामदोषः",
                         "अपरिभाषितम् नाम '%s' / undefined name '%s'", nama, nama);
            break;
        }
        /* संकलकेन निश्चितम् यत् एतत् नाम अन्तर्निहितम् एव, प्रोग्रामः तत् क्वापि न
           घोषयति — अतः परिवेशशृङ्खलायाम् अन्वेषणम् एव न आवश्यकम्। */
        case A_ANTARNIHITAM_GRIHANA: {
            const char *nama = c->khanda->dhruvah[sanketah[c->sthanam++]].shabda;
            int a = antarnihitam_anvishya(nama);
            if (a >= 0) { sthapaya(antarnihitam_mulyam(a)); break; }
            dosha_utsrja("नामदोषः",
                         "अपरिभाषितम् नाम '%s' / undefined name '%s'", nama, nama);
            break;
        }
        /* स्थाननिर्णीतौ — (कति परिवेशाः उपरि, कतमः बन्धः, किं नाम).
           The name is checked, so a scope that is not shaped the way the
           compiler expected costs one comparison and falls back to the
           search — the answer is the same either way. */
        case A_STHANAT_GRIHANA: {
            int uttarah = sanketah[c->sthanam++];
            int sthanam = sanketah[c->sthanam++];
            const char *nama = c->khanda->dhruvah[sanketah[c->sthanam++]].shabda;
            Parivesha *p = parivesha_sthanam(c->parivesha, uttarah, sthanam, nama);
            if (p) { sthapaya(grah(parivesha_sthanat(p, sthanam))); break; }
            Mulyam out;
            if (parivesha_grihana(c->parivesha, nama, &out)) { sthapaya(grah(out)); break; }
            int a = antarnihitam_anvishya(nama);
            if (a >= 0) { sthapaya(antarnihitam_mulyam(a)); break; }
            dosha_utsrja("नामदोषः",
                         "अपरिभाषितम् नाम '%s' / undefined name '%s'", nama, nama);
            break;
        }
        case A_STHANE_NYASAYA: {
            int uttarah = sanketah[c->sthanam++];
            int sthanam = sanketah[c->sthanam++];
            const char *nama = c->khanda->dhruvah[sanketah[c->sthanam++]].shabda;
            Parivesha *p = parivesha_sthanam(c->parivesha, uttarah, sthanam, nama);
            parivesha_nyasaya(p ? p : c->parivesha, nama, shikharam());
            break;
        }
        case A_NYASAYA: {
            const char *nama = c->khanda->dhruvah[sanketah[c->sthanam++]].shabda;
            parivesha_nyasaya(c->parivesha, nama, shikharam());
            break;
        }

        case A_YOGAH: {
            Mulyam b = grihana_stupat(), a = grihana_stupat();
            /* `x = x + y` — यदि अग्रिमः आदेशः तम् एव बन्धम् प्रति न्यस्यति, तर्हि
               तस्य निर्देशः शीघ्रम् त्यक्ष्यते, अतः स्थाने वर्धयितुम् शक्यते।
               If the next instruction assigns back to a binding that holds this
               very string, that reference is about to be dropped — so this is
               the only other holder, and the string may be grown in place.
               Both facts are checked; anything else falls through. */
            if (a.prakara == P_SHABDA && b.prakara == P_SHABDA &&
                a.as.vastu->nirdeshah == 2 && vardhitum_shakyate(c, a)) {
                Shabda *sb = as_shabda(b);
                if (shabda_vardhaya(a, sb->paatha, sb->baits)) {
                    muncha(b);
                    sthapaya(a);          /* the reference from the stack pop */
                    break;
                }
            }
            Mulyam r = yojanam(a, b);
            muncha(a); muncha(b);
            sthapaya(r);
            break;
        }
        case A_VIYOGAH: case A_GUNANAM: case A_BHAGAH:
        case A_SHESHAH: case A_GHATAH: {
            Mulyam b = grihana_stupat(), a = grihana_stupat();
            Mulyam r = ganitam(adesha, a, b);
            muncha(a); muncha(b);
            sthapaya(r);
            break;
        }
        case A_RINAM: {
            Mulyam m = grihana_stupat();
            ankam_apekshasva(m, "-");
            Mulyam r = (m.prakara == P_PURNANKA) ? purnanka_mulyam(-m.as.purnanka)
                                                 : dashamsha_mulyam(-m.as.dashamsha);
            muncha(m);
            sthapaya(r);
            break;
        }
        case A_NISHEDHAH: {
            Mulyam m = grihana_stupat();
            bool r = !satyavat(m);
            muncha(m);
            sthapaya(satyata_mulyam(r));
            break;
        }

        case A_SAMAM: case A_ASAMAM: {
            Mulyam b = grihana_stupat(), a = grihana_stupat();
            bool r = samam(a, b);
            muncha(a); muncha(b);
            sthapaya(satyata_mulyam(adesha == A_SAMAM ? r : !r));
            break;
        }
        case A_NYUNAM: case A_NYUNASAMAM: case A_ADHIKAM: case A_ADHIKASAMAM: {
            Mulyam b = grihana_stupat(), a = grihana_stupat();
            bool r = tulana_kuru(adesha, a, b);
            muncha(a); muncha(b);
            sthapaya(satyata_mulyam(r));
            break;
        }

        case A_LANGHAYA: c->sthanam += sanketah[c->sthanam] + 1; break;
        case A_ASATYE_LANGHAYA: {
            int d = sanketah[c->sthanam++];
            if (!satyavat(shikharam())) c->sthanam += d;
            break;
        }
        case A_SATYE_LANGHAYA: {
            int d = sanketah[c->sthanam++];
            if (satyavat(shikharam())) c->sthanam += d;
            break;
        }
        case A_PUNARAGACCHA: { int d = sanketah[c->sthanam++]; c->sthanam -= d; break; }

        case A_PARIVESHAM_ARABHA:
            c->parivesha = parivesha_rachaya(c->parivesha);
            break;
        case A_PARIVESHAM_TYAJA: {
            Parivesha *purva = c->parivesha;
            c->parivesha = parivesha_grah(parivesha_janaka(purva));
            parivesha_muncha(purva);
            break;
        }

        case A_SUCHIM_RACHAYA: {
            int n = sanketah[c->sthanam++];
            Mulyam out = suchi_mulyam();
            for (int i = 0; i < n; i++) suchi_yojaya(out, Y.stupa[Y.stupa_dirghata - n + i]);
            for (int i = 0; i < n; i++) muncha(grihana_stupat());
            sthapaya(out);
            break;
        }
        case A_KOSHAM_RACHAYA: {
            int n = sanketah[c->sthanam++];
            Mulyam out = kosha_mulyam();
            for (int i = 0; i < n; i++) {
                Mulyam k = Y.stupa[Y.stupa_dirghata - 2 * n + 2 * i];
                Mulyam v = Y.stupa[Y.stupa_dirghata - 2 * n + 2 * i + 1];
                if (k.prakara == P_SUCHI || k.prakara == P_KOSHA)
                    dosha_utsrja("प्रकारदोषः",
                                 "%s कुञ्जिका न भवति / %s cannot be a key",
                                 prakara_nama(k), prakara_nama(k));
                kosha_nyasaya(out, k, v);
            }
            for (int i = 0; i < 2 * n; i++) muncha(grihana_stupat());
            sthapaya(out);
            break;
        }
        case A_SUCHAKAT_GRIHANA: {
            Mulyam s = grihana_stupat(), l = grihana_stupat();
            Mulyam r = suchakat_grihana(l, s);
            muncha(s); muncha(l);
            sthapaya(r);
            break;
        }
        case A_SUCHAKE_NYASAYA: {
            Mulyam v = grihana_stupat(), s = grihana_stupat(), l = grihana_stupat();
            suchake_nyasaya(l, s, v);
            muncha(s); muncha(l);
            sthapaya(v);
            break;
        }

        case A_AVARANAM: {
            const SankalitaKaryam *k = c->khanda->dhruvah[sanketah[c->sthanam++]].karyam;
            sthapaya(avarana_mulyam(k, c->parivesha));
            break;
        }
        case A_AHVAYA: case A_KARAKAIH_AHVAYA: {
            int n = sanketah[c->sthanam++];
            const char **karakah = NULL;
            if (adesha == A_KARAKAIH_AHVAYA)
                karakah = c->khanda->dhruvah[sanketah[c->sthanam++]].shabdah;
            Mulyam prachalah[32];
            for (int i = 0; i < n; i++) prachalah[i] = Y.stupa[Y.stupa_dirghata - n + i];
            Y.stupa_dirghata -= n;
            Mulyam ahveyam = grihana_stupat();
            ahvanam_kuru(ahveyam, prachalah, n, karakah);
            muncha(ahveyam);
            break;
        }
        case A_PRATYAGACCHA: {
            Mulyam m = grihana_stupat();
            if (c->avarana) {
                char kasya[256];
                snprintf(kasya, sizeof kasya, "%s इत्यस्य प्रतिफलम्", c->avarana->karyam->nama);
                if (!prakaram_pariksaya(m, c->avarana->karyam->pratiphala_prakara, kasya)) {
                    muncha(m);
                    break;
                }
            }
            stupam_nyunikuru(c->adhara);
            parivesha_muncha(c->parivesha);
            Y.chaukati_ganana--;
            if (Y.chaukati_ganana <= virama_gabhirata) return m;
            sthapaya(m);
            break;
        }

        case A_MUDRAYA: {
            int n = sanketah[c->sthanam++];
            for (int i = 0; i < n; i++) {
                if (i) fputs(" ", stdout);
                char *s = shabdakr(Y.stupa[Y.stupa_dirghata - n + i], false);
                fputs(s, stdout);
                free(s);
            }
            fputs("\n", stdout);
            for (int i = 0; i < n; i++) muncha(grihana_stupat());
            break;
        }

        case A_PUNARAVARTAKAM_RACHAYA: {
            Mulyam sangraha = grihana_stupat();
            Mulyam angani;
            if (sangraha.prakara == P_KOSHA) {
                angani = suchi_mulyam();
                Kosha *k = as_kosha(sangraha);
                for (int i = 0; i < k->dirghata; i++) suchi_yojaya(angani, k->yugmani[i].kunjika);
            } else if (sangraha.prakara == P_SUCHI || sangraha.prakara == P_SHABDA) {
                Mulyam one = sangraha;
                angani = ANTARNIHITANI[antarnihitam_anvishya("सूची")].karyam(&one, 1);
            } else if (anka(sangraha)) {
                angani = suchi_mulyam();
                for (int64_t i = 0; i < (int64_t)anka_mulyam(sangraha); i++) {
                    Mulyam v = purnanka_mulyam(i);
                    suchi_yojaya(angani, v);
                }
            } else {
                dosha_utsrja("प्रकारदोषः",
                             "%s इत्यस्य उपरि न भ्रमितुं शक्यते / cannot iterate over %s",
                             prakara_nama(sangraha), prakara_nama(sangraha));
                angani = suchi_mulyam();
            }
            muncha(sangraha);
            Mulyam it = punaravartaka_mulyam(angani);
            muncha(angani);
            sthapaya(it);
            break;
        }
        case A_PUNARAVARTAYA: {
            int d = sanketah[c->sthanam++];
            Punaravartaka *p = (Punaravartaka *)shikharam().as.vastu;
            Suchi *s = as_suchi(p->angani);
            if (p->sthanam < s->dirghata) {
                sthapaya(grah(s->angani[p->sthanam++]));
            } else {
                muncha(grihana_stupat());
                c->sthanam += d;
            }
            break;
        }

        case A_PRAYATNAM_ARABHA: {
            int dosha_sthanam = sanketah[c->sthanam];
            int anta_sthanam = sanketah[c->sthanam + 1];
            c->sthanam += 2;
            Prabandhaka p;
            p.dosha_sthanam = dosha_sthanam;
            p.anta_sthanam = anta_sthanam;
            p.parivesha = c->parivesha;
            p.uchchata = Y.stupa_dirghata;
            c->prabandhakah[c->prabandhaka_ganana++] = p;
            break;
        }
        case A_PRAYATNAM_TYAJA: c->prabandhaka_ganana--; break;
        case A_UTSRJA: {
            Mulyam m = grihana_stupat();
            if (m.prakara == P_KOSHA) {
                Mulyam key = shabda_mulyam_c("प्रकारः"), out;
                const char *prakara = "उपयोक्तृदोषः";
                char *pbuf = NULL;
                if (kosha_grihana(m, key, &out)) { pbuf = shabdakr(out, false); prakara = pbuf; }
                muncha(key);
                key = shabda_mulyam_c("सन्देशः");
                char *sbuf = NULL;
                if (kosha_grihana(m, key, &out)) sbuf = shabdakr(out, false);
                muncha(key);
                key = shabda_mulyam_c("पङ्क्तिः");
                int pankti = 0;
                if (kosha_grihana(m, key, &out) && anka(out)) pankti = (int)anka_mulyam(out);
                muncha(key);
                char prakara_copy[64];
                snprintf(prakara_copy, sizeof prakara_copy, "%s", prakara);
                char sandesha_copy[512];
                snprintf(sandesha_copy, sizeof sandesha_copy, "%s", sbuf ? sbuf : "");
                free(pbuf); free(sbuf);
                dosha_utsrja(prakara_copy, "%s", sandesha_copy);
                VARTAMANA_DOSHA.pankti = pankti;   /* after: the raise resets it */
                if (VARTAMANA_DOSHA.has_mulyam) muncha(VARTAMANA_DOSHA.mulyam);
                VARTAMANA_DOSHA.mulyam = m;        /* the कोशः travels whole */
                VARTAMANA_DOSHA.has_mulyam = true;
            } else {
                char *s = shabdakr(m, false);
                char copy[512];
                snprintf(copy, sizeof copy, "%s", s);
                free(s);
                muncha(m);
                dosha_utsrja("उपयोक्तृदोषः", "%s", copy);
            }
            break;
        }
        case A_ANTATAH_SAMAPAYA:
            if (c->pralambitam) {
                c->pralambitam = false;
                dosha_utsrja(VARTAMANA_DOSHA.prakara, "%s", VARTAMANA_DOSHA.sandesha);
            }
            break;

        case A_ANAYA:
            ayatam_kuru(c, &c->khanda->dhruvah[sanketah[c->sthanam++]]);
            break;

        case A_VIRAMA:
            return shunyam_mulyam();

        default:
            dosha_utsrja("यन्त्रदोषः", "अज्ञातः आदेशः %d / unknown opcode %d", adesha, adesha);
        }
    }
}

/* ---------------------------------------------------------------- आयातः */
static Mulyam vibhagam_anaya(const char *pathah) {
    for (int i = 0; i < Y.vibhaga_ganana; i++) {
        if (strcmp(Y.vibhagah[i].pathah, pathah) != 0) continue;
        if (Y.vibhagah[i].chalati) {
            dosha_utsrja("आयातदोषः", "चक्रीयः आयातः '%s' / circular import of '%s'",
                         pathah, pathah);
            return shunyam_mulyam();
        }
        return Y.vibhagah[i].kosha;
    }
    const Khanda *khanda = NULL;
    for (int i = 0; i < VIBHAGA_GANANA; i++)
        if (strcmp(VIBHAGAH[i].pathah, pathah) == 0) khanda = VIBHAGAH[i].khanda;
    for (int i = 0; i < GATIKA_GANANA && !khanda; i++)   /* चालनकाले योजिताः */
        if (strcmp(GATIKAH[i].pathah, pathah) == 0) khanda = GATIKAH[i].khanda;
    if (!khanda) {
        dosha_utsrja("आयातदोषः", "सञ्चिका न प्राप्ता '%s' / cannot read module '%s'",
                     pathah, pathah);
        return shunyam_mulyam();
    }

    if (Y.vibhaga_ganana == Y.vibhaga_avakasha) {
        Y.vibhaga_avakasha = Y.vibhaga_avakasha ? Y.vibhaga_avakasha * 2 : 8;
        Y.vibhagah = (VibhagaSmrti *)realloc(Y.vibhagah,
                                             sizeof(VibhagaSmrti) * (size_t)Y.vibhaga_avakasha);
    }
    int at = Y.vibhaga_ganana++;
    Y.vibhagah[at].pathah = pathah;
    Y.vibhagah[at].chalati = true;
    Y.vibhagah[at].kosha = shunyam_mulyam();

    Parivesha *p = parivesha_rachaya(NULL);
    int gabhirata = Y.chaukati_ganana;
    chaukatim_yojaya(khanda, p, NULL, Y.stupa_dirghata);
    Mulyam ignored = chakram(gabhirata);
    muncha(ignored);
    if (Y.chaukati_ganana > gabhirata) Y.chaukati_ganana = gabhirata;

    Mulyam kosha = kosha_mulyam();
    for (int i = 0; i < parivesha_ganana(p); i++) {
        Mulyam key = shabda_mulyam_c(parivesha_nama_at(p, i));
        kosha_nyasaya(kosha, key, parivesha_mulyam_at(p, i));
        muncha(key);
    }
    parivesha_muncha(p);
    Y.vibhagah[at].kosha = kosha;
    Y.vibhagah[at].chalati = false;
    return kosha;
}

/* ============================================================ कोशात् खण्डम्
   The Vāk compiler emits a chunk as ordinary कोशाः. To run it here it must
   become the same static shapes the code generator emits, so we build them at
   runtime. The allocations live as long as the process, like emitted code. */
static char *shabdat_nakala(Mulyam m) {
    char *s = shabdakr(m, false);
    return s;                              /* already a fresh allocation */
}

static Mulyam kosha_mulyam_at(Mulyam k, const char *kunjika) {
    Mulyam key = shabda_mulyam_c(kunjika), out;
    if (!kosha_grihana(k, key, &out)) out = shunyam_mulyam();
    muncha(key);
    return out;
}

static const Khanda *khandam_nirmaya(Mulyam k);

static void dhruvam_nirmaya(Dhruva *d, Mulyam m) {
    memset(d, 0, sizeof *d);
    switch (m.prakara) {
    case P_PURNANKA:  d->prakara = K_PURNANKA;  d->purnanka = m.as.purnanka; return;
    case P_DASHAMSHA: d->prakara = K_DASHAMSHA; d->dashamsha = m.as.dashamsha; return;
    case P_SATYATA:   d->prakara = K_SATYATA;   d->satyata = m.as.satyata; return;
    case P_SHABDA:    d->prakara = K_SHABDA;    d->shabda = shabdat_nakala(m); return;
    case P_SHUNYAM:   d->prakara = K_SHUNYAM;   return;
    case P_SUCHI: {
        Suchi *s = as_suchi(m);
        /* आयातभारः [पथः, उपनाम, नामानि] अथवा कारकनामानि [नाम, शून्य, ...] */
        bool ayatah = s->dirghata == 3 && s->angani[0].prakara == P_SHABDA
                      && s->angani[2].prakara == P_SUCHI;
        d->prakara = K_SUCHI_SHABDANAM;
        if (ayatah) {
            Suchi *namani = as_suchi(s->angani[2]);
            const char **arr = (const char **)malloc(sizeof(char *) * (size_t)(namani->dirghata + 2));
            arr[0] = (s->angani[1].prakara == P_SHABDA) ? shabdat_nakala(s->angani[1]) : NULL;
            for (int i = 0; i < namani->dirghata; i++)
                arr[i + 1] = shabdat_nakala(namani->angani[i]);
            arr[namani->dirghata + 1] = NULL;
            d->shabda = shabdat_nakala(s->angani[0]);
            d->shabdah = arr;
            d->shabda_ganana = namani->dirghata;
            return;
        }
        const char **arr = (const char **)malloc(sizeof(char *) * (size_t)(s->dirghata + 1));
        for (int i = 0; i < s->dirghata; i++)
            arr[i] = (s->angani[i].prakara == P_SHABDA) ? shabdat_nakala(s->angani[i]) : NULL;
        arr[s->dirghata] = NULL;
        d->shabdah = arr;
        d->shabda_ganana = s->dirghata;
        return;
    }
    case P_KOSHA: {                         /* संकलितम् कार्यम् */
        Mulyam prachalah = kosha_mulyam_at(m, "प्राचलाः");
        Suchi *ps = (prachalah.prakara == P_SUCHI) ? as_suchi(prachalah) : NULL;
        int ganana = ps ? ps->dirghata : 0;
        Prachala *arr = (Prachala *)malloc(sizeof(Prachala) * (size_t)(ganana ? ganana : 1));
        for (int i = 0; i < ganana; i++) {
            Mulyam p = ps->angani[i];
            Mulyam karakam = kosha_mulyam_at(p, "कारकम्");
            arr[i].nama = shabdat_nakala(kosha_mulyam_at(p, "नाम"));
            arr[i].prakara = shabdat_nakala(kosha_mulyam_at(p, "प्रकारः"));
            arr[i].karakam = (karakam.prakara == P_SHABDA) ? shabdat_nakala(karakam) : NULL;
        }
        SankalitaKaryam *fn = (SankalitaKaryam *)malloc(sizeof(SankalitaKaryam));
        fn->nama = shabdat_nakala(kosha_mulyam_at(m, "नाम"));
        fn->prachalah = arr;
        fn->prachala_ganana = ganana;
        fn->pratiphala_prakara = shabdat_nakala(kosha_mulyam_at(m, "प्रतिफलप्रकारः"));
        fn->khanda = khandam_nirmaya(kosha_mulyam_at(m, "खण्डः"));
        d->prakara = K_KARYAM;
        d->karyam = fn;
        return;
    }
    default:
        d->prakara = K_SHUNYAM;
        return;
    }
}

static int *ankan_nirmaya(Mulyam suchi, int *ganana) {
    if (suchi.prakara != P_SUCHI) { *ganana = 0; return (int *)calloc(1, sizeof(int)); }
    Suchi *s = as_suchi(suchi);
    int *arr = (int *)malloc(sizeof(int) * (size_t)(s->dirghata ? s->dirghata : 1));
    for (int i = 0; i < s->dirghata; i++) {
        Mulyam m = s->angani[i];
        arr[i] = (m.prakara == P_PURNANKA) ? (int)m.as.purnanka
               : (m.prakara == P_DASHAMSHA) ? (int)m.as.dashamsha : 0;
    }
    *ganana = s->dirghata;
    return arr;
}

static const Khanda *khandam_nirmaya(Mulyam k) {
    Khanda *out = (Khanda *)malloc(sizeof(Khanda));
    memset(out, 0, sizeof *out);
    if (k.prakara != P_KOSHA) {
        dosha_utsrja("प्रकारदोषः",
                     "खण्डम्_चालय कोशम् एव इच्छति / खण्डम्_चालय expects a कोशः");
        return out;
    }
    out->nama = shabdat_nakala(kosha_mulyam_at(k, "नाम"));
    int ganana = 0;
    out->sanketah = ankan_nirmaya(kosha_mulyam_at(k, "सङ्केताः"), &ganana);
    out->sanketa_ganana = ganana;
    int pankti_ganana = 0;
    out->panktayah = ankan_nirmaya(kosha_mulyam_at(k, "पङ्क्तयः"), &pankti_ganana);

    Mulyam dhruvah = kosha_mulyam_at(k, "ध्रुवाः");
    int dganana = (dhruvah.prakara == P_SUCHI) ? as_suchi(dhruvah)->dirghata : 0;
    Dhruva *arr = (Dhruva *)malloc(sizeof(Dhruva) * (size_t)(dganana ? dganana : 1));
    for (int i = 0; i < dganana; i++)
        dhruvam_nirmaya(&arr[i], as_suchi(dhruvah)->angani[i]);
    out->dhruvah = arr;
    out->dhruva_ganana = dganana;
    return out;
}

Mulyam vak_khandam_chalaya(Mulyam khanda_kosha, Mulyam vibhagah) {
    if (vibhagah.prakara == P_SUCHI) {          /* [[पथः, खण्डः], ...] */
        Suchi *s = as_suchi(vibhagah);
        for (int i = 0; i < s->dirghata; i++) {
            Mulyam pair = s->angani[i];
            if (pair.prakara != P_SUCHI || as_suchi(pair)->dirghata < 2) continue;
            if (GATIKA_GANANA == GATIKA_AVAKASHA) {
                GATIKA_AVAKASHA = GATIKA_AVAKASHA ? GATIKA_AVAKASHA * 2 : 8;
                GATIKAH = (GatikaVibhaga *)realloc(
                    GATIKAH, sizeof(GatikaVibhaga) * (size_t)GATIKA_AVAKASHA);
            }
            GATIKAH[GATIKA_GANANA].pathah = shabdat_nakala(as_suchi(pair)->angani[0]);
            GATIKAH[GATIKA_GANANA].khanda = khandam_nirmaya(as_suchi(pair)->angani[1]);
            GATIKA_GANANA++;
        }
    }
    const Khanda *khanda = khandam_nirmaya(khanda_kosha);
    if (DOSHA_ASTI) return shunyam_mulyam();

    Parivesha *p = parivesha_rachaya(NULL);
    int gabhirata = Y.chaukati_ganana;
    chaukatim_yojaya(khanda, p, NULL, Y.stupa_dirghata);
    if (DOSHA_ASTI) { parivesha_muncha(p); return shunyam_mulyam(); }
    Mulyam out = chakram(gabhirata);
    if (Y.chaukati_ganana > gabhirata) Y.chaukati_ganana = gabhirata;
    parivesha_muncha(p);
    return out;
}

/* ----------------------------------------------------------------- प्रवेशः */
int vak_chalaya(const Khanda *mukhyam) {
#if VAK_WINDOWS
    SetConsoleOutputCP(65001);
#endif
    Y.stupa = NULL; Y.stupa_dirghata = Y.stupa_avakasha = 0;
    Y.chaukati_ganana = 0;
    Y.vibhagah = NULL; Y.vibhaga_ganana = Y.vibhaga_avakasha = 0;
    Y.vaishvika = parivesha_rachaya(NULL);
    chaukatim_yojaya(mukhyam, Y.vaishvika, NULL, 0);
    Mulyam out = chakram(0);
    muncha(out);
    fflush(stdout);
    return 0;
}
