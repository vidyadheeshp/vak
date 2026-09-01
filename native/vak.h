/*
 * vak.h — वाक्-भाषायाः देशीयः चालकः / the native runtime of Vāk.
 *
 * This is a C implementation of the SanskritVM. A compiled program is emitted
 * as C data (see vak/native.py) and linked against this runtime, producing a
 * standalone executable that needs neither Python nor the Vāk toolchain.
 *
 * Identifiers keep the Sanskrit vocabulary in transliteration, since C names
 * must be ASCII: Mulyam (मूल्यम्, a value), Shabda (शब्दः), Suchi (सूची),
 * Kosha (कोशः), Avarana (आवरणम्, a closure), Parivesha (परिवेशः, a scope),
 * Yantram (यन्त्रम्, the machine).
 */
#ifndef VAK_H
#define VAK_H

#include <stdbool.h>

/* तन्त्रनिर्णयः — विण्डोज़् किंवा POSIX, एकः एव निर्णयः सर्वेषाम् सञ्चिकानाम् कृते।
   One decision, shared by every file.  -DVAK_POSIX forces the POSIX branch even
   on Windows, so the code only Linux and macOS will run can still be run and
   tested wherever we happen to be building. */
#if defined(_WIN32) && !defined(VAK_POSIX)
#  define VAK_WINDOWS 1
#else
#  define VAK_WINDOWS 0
#endif
#include <stddef.h>
#include <stdint.h>

/* ------------------------------------------------------------------ आदेशाः */
enum Adesha {
    A_STHAPAYA = 0, A_SHUNYAM = 1, A_SATYAM = 2, A_ASATYAM = 3,
    A_TYAJA = 4, A_DVITVAM = 5,
    A_GHOSHAYA = 10, A_DHRUVAM_GHOSHAYA = 11, A_GRIHANA = 12, A_NYASAYA = 13,
    A_STHANAT_GRIHANA = 14, A_STHANE_NYASAYA = 15,
    A_ANTARNIHITAM_GRIHANA = 16,
    A_YOGAH = 20, A_VIYOGAH = 21, A_GUNANAM = 22, A_BHAGAH = 23,
    A_SHESHAH = 24, A_GHATAH = 25, A_RINAM = 26, A_NISHEDHAH = 27,
    A_SAMAM = 30, A_ASAMAM = 31, A_NYUNAM = 32, A_NYUNASAMAM = 33,
    A_ADHIKAM = 34, A_ADHIKASAMAM = 35,
    A_LANGHAYA = 40, A_ASATYE_LANGHAYA = 41, A_SATYE_LANGHAYA = 42,
    A_PUNARAGACCHA = 43,
    A_PARIVESHAM_ARABHA = 50, A_PARIVESHAM_TYAJA = 51,
    A_SUCHIM_RACHAYA = 60, A_KOSHAM_RACHAYA = 61,
    A_SUCHAKAT_GRIHANA = 62, A_SUCHAKE_NYASAYA = 63,
    A_AVARANAM = 70, A_AHVAYA = 71, A_KARAKAIH_AHVAYA = 72, A_PRATYAGACCHA = 73,
    A_MUDRAYA = 80,
    A_PUNARAVARTAKAM_RACHAYA = 90, A_PUNARAVARTAYA = 91,
    A_PRAYATNAM_ARABHA = 100, A_PRAYATNAM_TYAJA = 101,
    A_UTSRJA = 102, A_ANTATAH_SAMAPAYA = 103,
    A_ANAYA = 110,
    A_VIRAMA = 255
};

/* ----------------------------------------------------------------- प्रकाराः */
typedef enum {
    P_SHUNYAM,      /* शून्यम्   */
    P_SATYATA,      /* सत्यता    */
    P_PURNANKA,     /* पूर्णाङ्कः */
    P_DASHAMSHA,    /* दशांशः    */
    P_SHABDA,       /* शब्दः     */
    P_SUCHI,        /* सूची      */
    P_KOSHA,        /* कोशः      */
    P_AVARANA,      /* कार्यम् — a closure          */
    P_ANTARNIHITAM, /* कार्यम् — a built-in function */
    P_PUNARAVARTAKA /* पुनरावर्तकः — an internal loop cursor */
} Prakara;

typedef struct Vastu Vastu;     /* वस्तु — a heap object with a refcount */

typedef struct {
    Prakara prakara;
    union {
        bool satyata;
        int64_t purnanka;
        double dashamsha;
        Vastu *vastu;
        int antarnihitam;       /* index into the built-in table */
    } as;
} Mulyam;

struct Vastu { int nirdeshah; Prakara prakara; };   /* निर्देशाः — refcount */

typedef struct {                /* शब्दः — a UTF-8 string */
    Vastu vastu;
    int baits;                  /* bytes, excluding the NUL */
    int avakasha;               /* bytes allocated, so growth is amortised */
    int akshara;                /* code points (cached, -1 = not counted) */
    unsigned sanjna;            /* hash (cached, 0 = not computed yet) */
    char *paatha;
} Shabda;

typedef struct {                /* सूची */
    Vastu vastu;
    int dirghata, avakasha;
    Mulyam *angani;
} Suchi;

typedef struct { Mulyam kunjika, mulyam; } KoshaYugma;

typedef struct {                /* कोशः — insertion-ordered */
    Vastu vastu;
    int dirghata, avakasha;
    KoshaYugma *yugmani;
} Kosha;

typedef struct Parivesha Parivesha;
typedef struct SankalitaKaryam SankalitaKaryam;

typedef struct {                /* पुनरावर्तकः — internal to प्रत्येकम् */
    Vastu vastu;
    Mulyam angani;              /* a सूची of the items to walk */
    int sthanam;
} Punaravartaka;

typedef struct {                /* आवरणम् — a closure */
    Vastu vastu;
    const SankalitaKaryam *karyam;
    Parivesha *parivesha;
} Avarana;

/* ------------------------------------------------- संकलितम् / compiled code */
typedef struct {                /* प्राचलः */
    const char *nama;
    const char *prakara;
    const char *karakam;        /* NULL when the parameter declares no role */
} Prachala;

typedef enum {                  /* what a constant descriptor holds */
    K_PURNANKA, K_DASHAMSHA, K_SHABDA, K_SATYATA, K_SHUNYAM,
    K_KARYAM, K_SUCHI_SHABDANAM
} DhruvaPrakara;

typedef struct Dhruva {
    DhruvaPrakara prakara;
    int64_t purnanka;
    double dashamsha;
    const char *shabda;         /* also the module path for imports */
    bool satyata;
    const SankalitaKaryam *karyam;
    const char **shabdah;       /* NULL-terminated; NULL entries mean शून्य   */
    int shabda_ganana;
} Dhruva;

typedef struct {                /* खण्डः — one chunk of code */
    const char *nama;
    const int *sanketah;
    int sanketa_ganana;
    const int *panktayah;
    const Dhruva *dhruvah;
    int dhruva_ganana;
} Khanda;

struct SankalitaKaryam {
    const char *nama;
    const Prachala *prachalah;
    int prachala_ganana;
    const char *pratiphala_prakara;
    const Khanda *khanda;
};

typedef struct {                /* an importable module, resolved at compile time */
    const char *pathah;
    const Khanda *khanda;
} Vibhaga;

/* -------------------------------------------------------- चालकस्य प्रवेशः */
/* Emitted programs define these. */
extern const Khanda MUKHYAM_KHANDA;
extern const Vibhaga VIBHAGAH[];
extern const int VIBHAGA_GANANA;

int vak_chalaya(const Khanda *mukhyam);   /* run a program; returns an exit code */

/* ------------------------------------------------------------- मूल्यसाधनानि */
Mulyam shunyam_mulyam(void);
Mulyam satyata_mulyam(bool b);
Mulyam purnanka_mulyam(int64_t n);
Mulyam dashamsha_mulyam(double d);
Mulyam shabda_mulyam(const char *bytes, int len);
Mulyam shabda_mulyam_c(const char *bytes);
Mulyam shabda_yugmam(const char *a, int na, const char *b, int nb);
bool shabda_vardhaya(Mulyam m, const char *b, int nb);
Mulyam suchi_mulyam(void);
Mulyam kosha_mulyam(void);
Mulyam avarana_mulyam(const SankalitaKaryam *karyam, Parivesha *parivesha);
Mulyam antarnihitam_mulyam(int index);
Mulyam punaravartaka_mulyam(Mulyam angani);

Mulyam grah(Mulyam m);            /* गृह् — retain   */
void   muncha(Mulyam m);          /* मुञ्च — release */

const char *prakara_nama(Mulyam m);
bool satyavat(Mulyam m);
bool samam(Mulyam a, Mulyam b);
char *shabdakr(Mulyam m, bool uddhrta);   /* stringify; caller frees */

Shabda *as_shabda(Mulyam m);
Suchi  *as_suchi(Mulyam m);
Kosha  *as_kosha(Mulyam m);

void suchi_yojaya(Mulyam suchi, Mulyam item);
Mulyam suchi_grihana(Mulyam suchi, int index);
void kosha_nyasaya(Mulyam kosha, Mulyam key, Mulyam value);
bool kosha_grihana(Mulyam kosha, Mulyam key, Mulyam *out);
int kosha_sthanam(Mulyam kosha, Mulyam key);

/* UTF-8 helpers — Vāk counts and indexes strings by code point */
int utf8_ganana(const char *s, int baits);
int utf8_sthanam(const char *s, int baits, int index);  /* byte offset of cp #index */
int utf8_padam(const char *s, int offset);              /* byte length of cp at offset */

/* --------------------------------------------------------------------- दोषाः */
typedef struct {
    char prakara[64];
    char sandesha[512];
    int pankti;
    Mulyam mulyam;      /* the thrown value, when it was not a कोशः */
    bool has_mulyam;
} Dosha;

void dosha_utsrja(const char *prakara, const char *fmt, ...);
extern Dosha VARTAMANA_DOSHA;
extern bool DOSHA_ASTI;

/* ------------------------------------------------------------- अन्तर्निहितानि */
typedef struct {
    const char *nama;
    int prachala_ganana;        /* -1 = variadic */
    Mulyam (*karyam)(Mulyam *prachalah, int ganana);
} Antarnihitam;

extern const Antarnihitam ANTARNIHITANI[];
extern const int ANTARNIHITA_GANANA;
int antarnihitam_anvishya(const char *nama);   /* -1 when not found */
void vak_prachalan_sthapaya(int argc, char **argv);   /* आदेशपङ्क्त्याः प्राचलाः */

/* कोशरूपेण संकलितम् खण्डम् साक्षात् एतस्मिन् एव यन्त्रे चालयति — द्वितीयम् यन्त्रम्
   न आवश्यकम्. Run a chunk that arrives as कोशाः on this very machine, so a
   self-hosted compiler needs no second VM to interpret its output. */
Mulyam vak_khandam_chalaya(Mulyam khanda_kosha, Mulyam vibhagah);

/* -------------------------------------------------------------- परिवेशाः */
Parivesha *parivesha_rachaya(Parivesha *janaka);
Parivesha *parivesha_grah(Parivesha *p);
Parivesha *parivesha_janaka(Parivesha *p);
void parivesha_muncha(Parivesha *p);
bool parivesha_ghoshaya(Parivesha *p, const char *nama, Mulyam m,
                        bool dhruva, const char *prakara);
bool parivesha_grihana(Parivesha *p, const char *nama, Mulyam *out);
/* स्थानम् — the scope a resolved instruction means, once it is checked that
   the binding really is the one the compiler had in mind. */
Parivesha *parivesha_sthanam(Parivesha *p, int uttarah, int sthanam,
                             const char *nama);
Mulyam parivesha_sthanat(Parivesha *p, int sthanam);
bool parivesha_nyasaya(Parivesha *p, const char *nama, Mulyam m);
bool parivesha_asti(Parivesha *p, const char *nama);
bool parivesha_vardhaniyam(Parivesha *p, const char *nama, Mulyam m);
void parivesha_prachalam_dhara(Parivesha *p, const char *nama, Mulyam m,
                               const char *prakara);
int  parivesha_ganana(Parivesha *p);
const char *parivesha_nama_at(Parivesha *p, int i);
Mulyam parivesha_mulyam_at(Parivesha *p, int i);

/* प्रकारपरीक्षा */
bool prakara_melati(Mulyam m, const char *prakara);
bool prakaram_pariksaya(Mulyam m, const char *prakara, const char *kasya);

#endif /* VAK_H */
