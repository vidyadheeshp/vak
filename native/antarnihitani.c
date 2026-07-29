/*
 * antarnihitani.c — अन्तर्निहितानि कार्याणि / the standard library in C.
 *
 * Every function here mirrors its Python counterpart in vak/builtins.py,
 * including the wording of the errors it raises, so that a natively compiled
 * program prints exactly what the interpreted one prints.
 */
#include "vak.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

int vak_shabda_dirghata(Mulyam m);

/* ------------------------------------------------------------ साधनानि */
static const char *DEVA_ANKAH[10] = {
    "०", "१", "२", "३", "४", "५", "६", "७", "८", "९"
};

static bool anka(Mulyam m) {
    return m.prakara == P_PURNANKA || m.prakara == P_DASHAMSHA;
}
static double anka_mulyam(Mulyam m) {
    return m.prakara == P_PURNANKA ? (double)m.as.purnanka : m.as.dashamsha;
}

static Mulyam shabda_nirmaya(const char *s) { return shabda_mulyam_c(s); }

/* एकः देवनागरी-अङ्कः रोमन्-अङ्कः वा? */
static int deva_anka_sankhya(const char *s, int offset, int len) {
    if (offset + 3 > len) return -1;
    for (int d = 0; d < 10; d++)
        if (memcmp(s + offset, DEVA_ANKAH[d], 3) == 0) return d;
    return -1;
}

/* ------------------------------------------------------------ मुद्रणम् */
static Mulyam a_likh(Mulyam *pra, int n) {
    for (int i = 0; i < n; i++) {
        if (i) fputs(" ", stdout);
        char *s = shabdakr(pra[i], false);
        fputs(s, stdout);
        free(s);
    }
    fputs("\n", stdout);
    return shunyam_mulyam();
}

static Mulyam a_patha(Mulyam *pra, int n) {
    if (n > 0) { char *s = shabdakr(pra[0], false); fputs(s, stdout); free(s); }
    fflush(stdout);
    char buf[4096];
    if (!fgets(buf, sizeof buf, stdin)) return shabda_mulyam_c("");
    int len = (int)strlen(buf);
    while (len > 0 && (buf[len - 1] == '\n' || buf[len - 1] == '\r')) len--;
    return shabda_mulyam(buf, len);
}

/* -------------------------------------------------------- परिवर्तनम् */
static Mulyam a_prakara(Mulyam *pra, int n) {
    (void)n;
    return shabda_nirmaya(prakara_nama(pra[0]));
}

static Mulyam a_shabda(Mulyam *pra, int n) {
    (void)n;
    char *s = shabdakr(pra[0], false);
    Mulyam m = shabda_mulyam_c(s);
    free(s);
    return m;
}

static Mulyam a_sankhya(Mulyam *pra, int n) {
    (void)n;
    Mulyam m = pra[0];
    if (m.prakara == P_SATYATA) return purnanka_mulyam(m.as.satyata ? 1 : 0);
    if (anka(m)) return m;
    if (m.prakara != P_SHABDA) {
        dosha_utsrja("कार्यकालदोषः",
                     "अङ्कः न भवति %s / cannot convert %s to a number",
                     prakara_nama(m), prakara_nama(m));
        return shunyam_mulyam();
    }
    Shabda *s = as_shabda(m);
    char buf[256];
    int j = 0;
    for (int i = 0; i < s->baits && j < (int)sizeof buf - 1; ) {
        int d = deva_anka_sankhya(s->paatha, i, s->baits);
        if (d >= 0) { buf[j++] = (char)('0' + d); i += 3; continue; }
        char c = s->paatha[i];
        if (c != ' ' && c != '\t' && c != '\n' && c != '\r') buf[j++] = c;
        i++;
    }
    buf[j] = '\0';
    char *end = NULL;
    long long whole = strtoll(buf, &end, 10);
    if (end && *end == '\0' && end != buf) return purnanka_mulyam(whole);
    double d = strtod(buf, &end);
    if (end && *end == '\0' && end != buf) return dashamsha_mulyam(d);
    dosha_utsrja("कार्यकालदोषः",
                 "अङ्कः न भवति '%s' / cannot read '%s' as a number",
                 s->paatha, s->paatha);
    return shunyam_mulyam();
}

static Mulyam a_devanagari(Mulyam *pra, int n) {
    (void)n;
    char *s = shabdakr(pra[0], false);
    int len = (int)strlen(s);
    char *out = (char *)malloc((size_t)len * 3 + 1);
    int j = 0;
    for (int i = 0; i < len; i++) {
        if (s[i] >= '0' && s[i] <= '9') {
            memcpy(out + j, DEVA_ANKAH[s[i] - '0'], 3);
            j += 3;
        } else {
            out[j++] = s[i];
        }
    }
    out[j] = '\0';
    Mulyam m = shabda_mulyam(out, j);
    free(out); free(s);
    return m;
}

/* -------------------------------------------------------------- संग्रहाः */
static Mulyam a_dirghata(Mulyam *pra, int n) {
    (void)n;
    Mulyam m = pra[0];
    if (m.prakara == P_SHABDA) return purnanka_mulyam(vak_shabda_dirghata(m));
    if (m.prakara == P_SUCHI)  return purnanka_mulyam(as_suchi(m)->dirghata);
    if (m.prakara == P_KOSHA)  return purnanka_mulyam(as_kosha(m)->dirghata);
    dosha_utsrja("कार्यकालदोषः", "%s इत्यस्य दीर्घता नास्ति / %s has no length",
                 prakara_nama(m), prakara_nama(m));
    return shunyam_mulyam();
}

static Mulyam a_suchi(Mulyam *pra, int n) {
    Mulyam out = suchi_mulyam();
    if (n == 0) return out;
    Mulyam m = pra[0];
    if (m.prakara == P_SUCHI) {
        Suchi *s = as_suchi(m);
        for (int i = 0; i < s->dirghata; i++) suchi_yojaya(out, s->angani[i]);
        return out;
    }
    if (m.prakara == P_SHABDA) {
        Shabda *s = as_shabda(m);
        for (int i = 0; i < s->baits; ) {
            int w = utf8_padam(s->paatha, i);
            Mulyam ch = shabda_mulyam(s->paatha + i, w);
            suchi_yojaya(out, ch);
            muncha(ch);
            i += w;
        }
        return out;
    }
    if (m.prakara == P_KOSHA) {
        Kosha *k = as_kosha(m);
        for (int i = 0; i < k->dirghata; i++) suchi_yojaya(out, k->yugmani[i].kunjika);
        return out;
    }
    muncha(out);
    dosha_utsrja("कार्यकालदोषः", "सूची न कर्तुं शक्यते %s / cannot make a सूची from %s",
                 prakara_nama(m), prakara_nama(m));
    return shunyam_mulyam();
}

static Mulyam a_parasa(Mulyam *pra, int n) {
    int64_t arambha = 0, anta = 0, padam = 1;
    for (int i = 0; i < n; i++) {
        if (!anka(pra[i]) || pra[i].prakara == P_SATYATA) {
            dosha_utsrja("कार्यकालदोषः", "परासः अङ्कान् एव इच्छति / परास expects numbers");
            return shunyam_mulyam();
        }
    }
    if (n == 1) { anta = (int64_t)anka_mulyam(pra[0]); }
    else if (n >= 2) {
        arambha = (int64_t)anka_mulyam(pra[0]);
        anta = (int64_t)anka_mulyam(pra[1]);
        if (n >= 3) padam = (int64_t)anka_mulyam(pra[2]);
    }
    if (padam == 0) {
        dosha_utsrja("कार्यकालदोषः",
                     "परासस्य पदम् शून्यम् न भवेत् / the step of परास cannot be zero");
        return shunyam_mulyam();
    }
    Mulyam out = suchi_mulyam();
    if (padam > 0) for (int64_t i = arambha; i < anta; i += padam) {
        Mulyam v = purnanka_mulyam(i); suchi_yojaya(out, v);
    } else for (int64_t i = arambha; i > anta; i += padam) {
        Mulyam v = purnanka_mulyam(i); suchi_yojaya(out, v);
    }
    return out;
}

static Mulyam a_yojaya(Mulyam *pra, int n) {
    if (n < 1 || pra[0].prakara != P_SUCHI) {
        dosha_utsrja("कार्यकालदोषः", "योजयः सूचीम् एव इच्छति / योजय expects a सूची");
        return shunyam_mulyam();
    }
    for (int i = 1; i < n; i++) suchi_yojaya(pra[0], pra[i]);
    return grah(pra[0]);
}

static Mulyam a_nishkasa(Mulyam *pra, int n) {
    if (n >= 1 && pra[0].prakara == P_SUCHI) {
        Suchi *s = as_suchi(pra[0]);
        if (s->dirghata == 0) {
            dosha_utsrja("कार्यकालदोषः",
                         "रिक्ता सूची / cannot remove from an empty सूची");
            return shunyam_mulyam();
        }
        int64_t at = (n >= 2) ? (int64_t)anka_mulyam(pra[1]) : -1;
        if (at < 0) at += s->dirghata;
        if (at < 0 || at >= s->dirghata) {
            dosha_utsrja("सूचकदोषः", "सूचकः परिधेः बहिः %lld / index %lld is out of range",
                         (long long)at, (long long)at);
            return shunyam_mulyam();
        }
        Mulyam out = s->angani[at];
        for (int i = (int)at; i < s->dirghata - 1; i++) s->angani[i] = s->angani[i + 1];
        s->dirghata--;
        return out;                       /* the reference moves to the caller */
    }
    if (n >= 2 && pra[0].prakara == P_KOSHA) {
        int at = kosha_sthanam(pra[0], pra[1]);
        if (at < 0) {
            char *k = shabdakr(pra[1], true);
            dosha_utsrja("कुञ्जिकादोषः", "कुञ्जिका न विद्यते %s / no such key %s", k, k);
            free(k);
            return shunyam_mulyam();
        }
        Kosha *k = as_kosha(pra[0]);
        Mulyam out = k->yugmani[at].mulyam;
        muncha(k->yugmani[at].kunjika);
        for (int i = at; i < k->dirghata - 1; i++) k->yugmani[i] = k->yugmani[i + 1];
        k->dirghata--;
        return out;
    }
    dosha_utsrja("कार्यकालदोषः",
                 "निष्कासः सूचीम् कोशम् वा इच्छति / निष्कास expects a सूची or कोश");
    return shunyam_mulyam();
}

static Mulyam a_asti(Mulyam *pra, int n) {
    (void)n;
    Mulyam sangraha = pra[0], item = pra[1];
    if (sangraha.prakara == P_SUCHI) {
        Suchi *s = as_suchi(sangraha);
        for (int i = 0; i < s->dirghata; i++)
            if (samam(s->angani[i], item)) return satyata_mulyam(true);
        return satyata_mulyam(false);
    }
    if (sangraha.prakara == P_KOSHA)
        return satyata_mulyam(kosha_sthanam(sangraha, item) >= 0);
    if (sangraha.prakara == P_SHABDA && item.prakara == P_SHABDA) {
        Shabda *h = as_shabda(sangraha), *nd = as_shabda(item);
        if (nd->baits == 0) return satyata_mulyam(true);
        for (int i = 0; i + nd->baits <= h->baits; i++)
            if (memcmp(h->paatha + i, nd->paatha, (size_t)nd->baits) == 0)
                return satyata_mulyam(true);
        return satyata_mulyam(false);
    }
    dosha_utsrja("कार्यकालदोषः",
                 "अस्ति इत्यस्य संग्रहः आवश्यकः / अस्ति expects a collection");
    return shunyam_mulyam();
}

static Mulyam a_kunjika(Mulyam *pra, int n) {
    (void)n;
    if (pra[0].prakara != P_KOSHA) {
        dosha_utsrja("कार्यकालदोषः", "कुञ्जिकाः कोशम् एव इच्छन्ति / कुञ्जिकाः expects a कोश");
        return shunyam_mulyam();
    }
    Mulyam out = suchi_mulyam();
    Kosha *k = as_kosha(pra[0]);
    for (int i = 0; i < k->dirghata; i++) suchi_yojaya(out, k->yugmani[i].kunjika);
    return out;
}

static Mulyam a_mulyani(Mulyam *pra, int n) {
    (void)n;
    if (pra[0].prakara != P_KOSHA) {
        dosha_utsrja("कार्यकालदोषः", "मूल्यानि कोशम् एव इच्छन्ति / मूल्यानि expects a कोश");
        return shunyam_mulyam();
    }
    Mulyam out = suchi_mulyam();
    Kosha *k = as_kosha(pra[0]);
    for (int i = 0; i < k->dirghata; i++) suchi_yojaya(out, k->yugmani[i].mulyam);
    return out;
}

/* क्रम — a stable insertion sort, as Python's sorted() is stable */
static int tulana(Mulyam a, Mulyam b, bool *ashakyam) {
    bool a_anka = anka(a) && a.prakara != P_SATYATA;
    bool b_anka = anka(b) && b.prakara != P_SATYATA;
    if (a_anka && b_anka) {
        double x = anka_mulyam(a), y = anka_mulyam(b);
        return x < y ? -1 : (x > y ? 1 : 0);
    }
    if (a.prakara == P_SHABDA && b.prakara == P_SHABDA) {
        Shabda *x = as_shabda(a), *y = as_shabda(b);
        int n = x->baits < y->baits ? x->baits : y->baits;
        int c = memcmp(x->paatha, y->paatha, (size_t)n);
        if (c) return c < 0 ? -1 : 1;
        return x->baits < y->baits ? -1 : (x->baits > y->baits ? 1 : 0);
    }
    *ashakyam = true;
    return 0;
}

static Mulyam a_krama(Mulyam *pra, int n) {
    if (pra[0].prakara != P_SUCHI) {
        dosha_utsrja("कार्यकालदोषः", "क्रमः सूचीम् एव इच्छति / क्रम expects a सूची");
        return shunyam_mulyam();
    }
    bool viparita = (n >= 2) && satyavat(pra[1]);
    Suchi *s = as_suchi(pra[0]);
    Mulyam out = suchi_mulyam();
    for (int i = 0; i < s->dirghata; i++) suchi_yojaya(out, s->angani[i]);
    Suchi *o = as_suchi(out);
    bool ashakyam = false;
    for (int i = 1; i < o->dirghata; i++) {
        Mulyam key = o->angani[i];
        int j = i - 1;
        while (j >= 0) {
            int c = tulana(o->angani[j], key, &ashakyam);
            if (ashakyam) {
                muncha(out);
                dosha_utsrja("कार्यकालदोषः",
                             "मिश्रितप्रकाराः न तुलनीयाः / cannot sort a सूची of mixed types");
                return shunyam_mulyam();
            }
            if (viparita ? (c < 0) : (c > 0)) { o->angani[j + 1] = o->angani[j]; j--; }
            else break;
        }
        o->angani[j + 1] = key;
    }
    return out;
}

/* -------------------------------------------------------------- अक्षराणि */
static bool samyojakah(unsigned cp) {          /* Devanagari combining marks */
    return (cp >= 0x0900 && cp <= 0x0903) || cp == 0x093A || cp == 0x093B
        || cp == 0x093C || (cp >= 0x093E && cp <= 0x094F)
        || (cp >= 0x0951 && cp <= 0x0957) || (cp >= 0x0962 && cp <= 0x0963)
        || cp == 0x200C || cp == 0x200D;
}

static unsigned utf8_sanketa(const char *s, int offset, int width) {
    unsigned char c = (unsigned char)s[offset];
    if (width == 1) return c;
    if (width == 2) return (unsigned)((c & 0x1F) << 6) | ((unsigned char)s[offset+1] & 0x3F);
    if (width == 3) return (unsigned)((c & 0x0F) << 12)
                         | (((unsigned char)s[offset+1] & 0x3F) << 6)
                         | ((unsigned char)s[offset+2] & 0x3F);
    return (unsigned)((c & 0x07) << 18) | (((unsigned char)s[offset+1] & 0x3F) << 12)
         | (((unsigned char)s[offset+2] & 0x3F) << 6) | ((unsigned char)s[offset+3] & 0x3F);
}

static Mulyam a_aksharani(Mulyam *pra, int n) {
    (void)n;
    if (pra[0].prakara != P_SHABDA) {
        dosha_utsrja("कार्यकालदोषः",
                     "अक्षराणि शब्दम् एव इच्छन्ति / अक्षराणि expects a शब्दः");
        return shunyam_mulyam();
    }
    Shabda *s = as_shabda(pra[0]);
    Mulyam out = suchi_mulyam();
    int arambha = -1, i = 0;
    unsigned antima = 0;
    while (i < s->baits) {
        int w = utf8_padam(s->paatha, i);
        unsigned cp = utf8_sanketa(s->paatha, i, w);
        bool anuvartate = (arambha >= 0) && (samyojakah(cp) || antima == 0x094D || antima == 0x200D);
        if (!anuvartate) {
            if (arambha >= 0) {
                Mulyam c = shabda_mulyam(s->paatha + arambha, i - arambha);
                suchi_yojaya(out, c); muncha(c);
            }
            arambha = i;
        }
        antima = cp;
        i += w;
    }
    if (arambha >= 0) {
        Mulyam c = shabda_mulyam(s->paatha + arambha, s->baits - arambha);
        suchi_yojaya(out, c); muncha(c);
    }
    return out;
}

static Mulyam a_viparyaya(Mulyam *pra, int n) {
    (void)n;
    if (pra[0].prakara == P_SUCHI) {
        Suchi *s = as_suchi(pra[0]);
        Mulyam out = suchi_mulyam();
        for (int i = s->dirghata - 1; i >= 0; i--) suchi_yojaya(out, s->angani[i]);
        return out;
    }
    if (pra[0].prakara == P_SHABDA) {
        Mulyam aks = a_aksharani(pra, 1);
        Suchi *s = as_suchi(aks);
        Mulyam out;
        int total = 0;
        for (int i = 0; i < s->dirghata; i++) total += as_shabda(s->angani[i])->baits;
        char *buf = (char *)malloc((size_t)total + 1);
        int j = 0;
        for (int i = s->dirghata - 1; i >= 0; i--) {
            Shabda *c = as_shabda(s->angani[i]);
            memcpy(buf + j, c->paatha, (size_t)c->baits);
            j += c->baits;
        }
        buf[j] = '\0';
        out = shabda_mulyam(buf, j);
        free(buf); muncha(aks);
        return out;
    }
    dosha_utsrja("कार्यकालदोषः",
                 "विपर्ययः सूचीम् शब्दम् वा इच्छति / विपर्यय expects a सूची or शब्द");
    return shunyam_mulyam();
}

static Mulyam a_vibhaja(Mulyam *pra, int n) {
    if (pra[0].prakara != P_SHABDA) {
        dosha_utsrja("कार्यकालदोषः", "विभजः शब्दम् एव इच्छति / विभज expects a शब्द");
        return shunyam_mulyam();
    }
    Shabda *s = as_shabda(pra[0]);
    const char *sep = " ";
    int seplen = 1;
    if (n >= 2) {
        if (pra[1].prakara != P_SHABDA) {
            dosha_utsrja("कार्यकालदोषः", "विभाजकः शब्दः भवेत् / the separator must be a शब्दः");
            return shunyam_mulyam();
        }
        sep = as_shabda(pra[1])->paatha;
        seplen = as_shabda(pra[1])->baits;
    }
    Mulyam out = suchi_mulyam();
    if (seplen == 0) return a_suchi(pra, 1);
    int start = 0;
    for (int i = 0; i + seplen <= s->baits; ) {
        if (memcmp(s->paatha + i, sep, (size_t)seplen) == 0) {
            Mulyam part = shabda_mulyam(s->paatha + start, i - start);
            suchi_yojaya(out, part); muncha(part);
            i += seplen;
            start = i;
        } else {
            i += utf8_padam(s->paatha, i);
        }
    }
    Mulyam part = shabda_mulyam(s->paatha + start, s->baits - start);
    suchi_yojaya(out, part); muncha(part);
    return out;
}

static Mulyam a_samyoja(Mulyam *pra, int n) {
    if (pra[0].prakara != P_SUCHI) {
        dosha_utsrja("कार्यकालदोषः", "संयोजः सूचीम् एव इच्छति / संयोज expects a सूची");
        return shunyam_mulyam();
    }
    char *sep = (n >= 2) ? shabdakr(pra[1], false) : NULL;
    const char *s = sep ? sep : "";
    Suchi *list = as_suchi(pra[0]);
    int total = 0;
    char **parts = (char **)malloc(sizeof(char *) * (size_t)(list->dirghata ? list->dirghata : 1));
    for (int i = 0; i < list->dirghata; i++) {
        parts[i] = shabdakr(list->angani[i], false);
        total += (int)strlen(parts[i]);
    }
    total += (int)strlen(s) * (list->dirghata > 0 ? list->dirghata - 1 : 0);
    char *buf = (char *)malloc((size_t)total + 1);
    int j = 0;
    for (int i = 0; i < list->dirghata; i++) {
        if (i) { int n2 = (int)strlen(s); memcpy(buf + j, s, (size_t)n2); j += n2; }
        int n2 = (int)strlen(parts[i]);
        memcpy(buf + j, parts[i], (size_t)n2);
        j += n2;
        free(parts[i]);
    }
    buf[j] = '\0';
    Mulyam out = shabda_mulyam(buf, j);
    free(buf); free(parts); free(sep);
    return out;
}

/* -------------------------------------------------------------- गणितम् */
static bool anka_suchi(Mulyam m, const char *who) {
    if (m.prakara != P_SUCHI || as_suchi(m)->dirghata == 0) {
        dosha_utsrja("कार्यकालदोषः",
                     "%s अरिक्ताम् सूचीम् इच्छति / %s expects a non-empty सूची", who, who);
        return false;
    }
    Suchi *s = as_suchi(m);
    for (int i = 0; i < s->dirghata; i++) {
        if (!anka(s->angani[i]) || s->angani[i].prakara == P_SATYATA) {
            dosha_utsrja("कार्यकालदोषः",
                         "%s अङ्कान् एव इच्छति / %s expects numbers", who, who);
            return false;
        }
    }
    return true;
}

static Mulyam a_yoga(Mulyam *pra, int n) {
    (void)n;
    if (!anka_suchi(pra[0], "योगः")) return shunyam_mulyam();
    Suchi *s = as_suchi(pra[0]);
    bool purna = true;
    for (int i = 0; i < s->dirghata; i++)
        if (s->angani[i].prakara == P_DASHAMSHA) purna = false;
    if (purna) {
        int64_t total = 0;
        for (int i = 0; i < s->dirghata; i++) total += s->angani[i].as.purnanka;
        return purnanka_mulyam(total);
    }
    double total = 0;
    for (int i = 0; i < s->dirghata; i++) total += anka_mulyam(s->angani[i]);
    return dashamsha_mulyam(total);
}

static Mulyam a_nyunatama(Mulyam *pra, int n) {
    (void)n;
    if (!anka_suchi(pra[0], "न्यूनतमम्")) return shunyam_mulyam();
    Suchi *s = as_suchi(pra[0]);
    Mulyam best = s->angani[0];
    for (int i = 1; i < s->dirghata; i++)
        if (anka_mulyam(s->angani[i]) < anka_mulyam(best)) best = s->angani[i];
    return grah(best);
}

static Mulyam a_adhikatama(Mulyam *pra, int n) {
    (void)n;
    if (!anka_suchi(pra[0], "अधिकतमम्")) return shunyam_mulyam();
    Suchi *s = as_suchi(pra[0]);
    Mulyam best = s->angani[0];
    for (int i = 1; i < s->dirghata; i++)
        if (anka_mulyam(s->angani[i]) > anka_mulyam(best)) best = s->angani[i];
    return grah(best);
}

static Mulyam a_mula(Mulyam *pra, int n) {
    (void)n;
    if (!anka(pra[0]) || pra[0].prakara == P_SATYATA) {
        dosha_utsrja("कार्यकालदोषः", "मूलम् अङ्कम् एव इच्छति / मूल expects a number");
        return shunyam_mulyam();
    }
    double d = anka_mulyam(pra[0]);
    if (d < 0) {
        dosha_utsrja("कार्यकालदोषः",
                     "ऋणसंख्यायाः मूलम् नास्ति / no real square root of a negative number");
        return shunyam_mulyam();
    }
    return dashamsha_mulyam(sqrt(d));
}

static Mulyam a_purna(Mulyam *pra, int n) {
    (void)n;
    if (!anka(pra[0]) || pra[0].prakara == P_SATYATA) {
        dosha_utsrja("कार्यकालदोषः", "पूर्णम् अङ्कम् एव इच्छति / पूर्ण expects a number");
        return shunyam_mulyam();
    }
    return purnanka_mulyam((int64_t)anka_mulyam(pra[0]));
}

static Mulyam a_yadrcchika(Mulyam *pra, int n) {
    static bool bijam = false;
    if (!bijam) { srand((unsigned)time(NULL)); bijam = true; }
    if (n == 0) return dashamsha_mulyam((double)rand() / ((double)RAND_MAX + 1.0));
    int64_t lo = 0, hi;
    if (n == 1) hi = (int64_t)anka_mulyam(pra[0]);
    else { lo = (int64_t)anka_mulyam(pra[0]); hi = (int64_t)anka_mulyam(pra[1]); }
    if (hi < lo) { int64_t t = lo; lo = hi; hi = t; }
    return purnanka_mulyam(lo + (int64_t)(rand() % (int)(hi - lo + 1)));
}

static int PRACHALA_GANANA = 0;
static char **PRACHALAH = NULL;

#if VAK_WINDOWS
#include <windows.h>
#include <shellapi.h>          /* CommandLineToArgvW */
#else
#include <dirent.h>            /* opendir / readdir — निर्देशिका */
#endif

/* विण्डोज़-प्रणाल्याम् argv ANSI-रूपेण आगच्छति, अतः देवनागरी नश्यति —
   तस्मात् UTF-16 आदेशपङ्क्तिः गृह्यते, ततः UTF-8 इति परिवर्त्यते.
   Windows hands main() an ANSI argv, which mangles Devanagari; take the
   real UTF-16 command line instead and convert it. */
void vak_prachalan_sthapaya(int argc, char **argv) {
#if VAK_WINDOWS
    int wide_ganana = 0;
    LPWSTR *wide = CommandLineToArgvW(GetCommandLineW(), &wide_ganana);
    if (wide) {
        char **utf8 = (char **)malloc(sizeof(char *) * (size_t)wide_ganana);
        for (int i = 0; i < wide_ganana; i++) {
            int n = WideCharToMultiByte(CP_UTF8, 0, wide[i], -1, NULL, 0, NULL, NULL);
            utf8[i] = (char *)malloc((size_t)(n > 0 ? n : 1));
            if (n > 0) WideCharToMultiByte(CP_UTF8, 0, wide[i], -1, utf8[i], n, NULL, NULL);
            else utf8[i][0] = '\0';
        }
        LocalFree(wide);
        PRACHALA_GANANA = wide_ganana;
        PRACHALAH = utf8;
        return;
    }
#endif
    PRACHALA_GANANA = argc;
    PRACHALAH = argv;
}

static Mulyam a_prachalah(Mulyam *pra, int n) {
    (void)pra; (void)n;
    Mulyam out = suchi_mulyam();
    for (int i = 1; i < PRACHALA_GANANA; i++) {      /* skip the program itself */
        Mulyam s = shabda_mulyam_c(PRACHALAH[i]);
        suchi_yojaya(out, s);
        muncha(s);
    }
    return out;
}

static Mulyam a_kala(Mulyam *pra, int n) {
    (void)pra; (void)n;
    return dashamsha_mulyam((double)time(NULL));
}

static Mulyam a_sanketa(Mulyam *pra, int n) {
    (void)n;
    if (pra[0].prakara != P_SHABDA || vak_shabda_dirghata(pra[0]) != 1) {
        dosha_utsrja("कार्यकालदोषः",
                     "संकेतः एकम् अक्षरम् एव इच्छति / संकेतः expects a single character");
        return shunyam_mulyam();
    }
    Shabda *s = as_shabda(pra[0]);
    return purnanka_mulyam((int64_t)utf8_sanketa(s->paatha, 0, utf8_padam(s->paatha, 0)));
}

static Mulyam a_varna(Mulyam *pra, int n) {
    (void)n;
    if (!anka(pra[0]) || pra[0].prakara == P_SATYATA) {
        dosha_utsrja("कार्यकालदोषः", "वर्णः अङ्कम् एव इच्छति / वर्णः expects a number");
        return shunyam_mulyam();
    }
    unsigned cp = (unsigned)anka_mulyam(pra[0]);
    char buf[5];
    int j = 0;
    if (cp < 0x80) buf[j++] = (char)cp;
    else if (cp < 0x800) {
        buf[j++] = (char)(0xC0 | (cp >> 6));
        buf[j++] = (char)(0x80 | (cp & 0x3F));
    } else if (cp < 0x10000) {
        buf[j++] = (char)(0xE0 | (cp >> 12));
        buf[j++] = (char)(0x80 | ((cp >> 6) & 0x3F));
        buf[j++] = (char)(0x80 | (cp & 0x3F));
    } else {
        buf[j++] = (char)(0xF0 | (cp >> 18));
        buf[j++] = (char)(0x80 | ((cp >> 12) & 0x3F));
        buf[j++] = (char)(0x80 | ((cp >> 6) & 0x3F));
        buf[j++] = (char)(0x80 | (cp & 0x3F));
    }
    return shabda_mulyam(buf, j);
}

static Mulyam a_amsha(Mulyam *pra, int n) {
    if (n < 2) {
        dosha_utsrja("कार्यकालदोषः", "अंशः द्वौ प्राचलौ इच्छति / अंशः needs at least two arguments");
        return shunyam_mulyam();
    }
    int64_t start = (int64_t)anka_mulyam(pra[1]);
    if (pra[0].prakara == P_SHABDA) {
        Shabda *s = as_shabda(pra[0]);
        int total = vak_shabda_dirghata(pra[0]);
        int64_t stop = (n >= 3) ? (int64_t)anka_mulyam(pra[2]) : total;
        if (start < 0) start += total;
        if (stop < 0) stop += total;
        if (start < 0) start = 0;
        if (stop > total) stop = total;
        if (stop < start) stop = start;
        int a = utf8_sthanam(s->paatha, s->baits, (int)start);
        int b = utf8_sthanam(s->paatha, s->baits, (int)stop);
        return shabda_mulyam(s->paatha + a, b - a);
    }
    if (pra[0].prakara == P_SUCHI) {
        Suchi *s = as_suchi(pra[0]);
        int64_t stop = (n >= 3) ? (int64_t)anka_mulyam(pra[2]) : s->dirghata;
        if (start < 0) start += s->dirghata;
        if (stop < 0) stop += s->dirghata;
        if (start < 0) start = 0;
        if (stop > s->dirghata) stop = s->dirghata;
        Mulyam out = suchi_mulyam();
        for (int64_t i = start; i < stop; i++) suchi_yojaya(out, s->angani[i]);
        return out;
    }
    dosha_utsrja("कार्यकालदोषः",
                 "अंशः शब्दम् सूचीम् वा इच्छति / अंशः expects a शब्दः or सूची");
    return shunyam_mulyam();
}

/* -------------------------------------------------------------- सञ्चिकाः */
/* विण्डोज़्-प्रणाल्याम् fopen ANSI-पथम् एव गृह्णाति, अतः देवनागरी-पथः न उद्घाट्यते —
   तस्मात् UTF-16 इति परिवर्त्य _wfopen प्रयुज्यते.
   fopen() takes an ANSI path on Windows, so a Devanagari path simply fails to
   open; convert to UTF-16 and use _wfopen instead. */
#if VAK_WINDOWS
#include <windows.h>

static wchar_t *vistrta(const char *utf8) {
    int n = MultiByteToWideChar(CP_UTF8, 0, utf8, -1, NULL, 0);
    if (n <= 0) return NULL;
    wchar_t *wide = (wchar_t *)malloc(sizeof(wchar_t) * (size_t)n);
    MultiByteToWideChar(CP_UTF8, 0, utf8, -1, wide, n);
    return wide;
}

static FILE *vak_fopen(const char *path, const char *mode) {
    wchar_t *wpath = vistrta(path);
    wchar_t wmode[8];
    int i = 0;
    for (; mode[i] && i < 7; i++) wmode[i] = (wchar_t)mode[i];
    wmode[i] = 0;
    FILE *f = wpath ? _wfopen(wpath, wmode) : fopen(path, mode);
    free(wpath);
    return f;
}

static int vak_remove(const char *path) {
    wchar_t *wpath = vistrta(path);
    int r = wpath ? _wremove(wpath) : remove(path);
    free(wpath);
    return r;
}
#else
#define vak_fopen fopen
#define vak_remove remove
#endif

static const char *pathah(Mulyam m, const char *who) {
    if (m.prakara != P_SHABDA) {
        dosha_utsrja("कार्यकालदोषः", "%s पथम् (शब्दम्) इच्छति / %s expects a path string",
                     who, who);
        return NULL;
    }
    return as_shabda(m)->paatha;
}

static Mulyam a_sanchikapatha(Mulyam *pra, int n) {
    (void)n;
    const char *p = pathah(pra[0], "सञ्चिकापठ");
    if (!p) return shunyam_mulyam();
    FILE *f = vak_fopen(p, "rb");
    if (!f) {
        dosha_utsrja("सञ्चिकादोषः",
                     "सञ्चिकायाम् पठनम् न सिद्धम् '%s' / cannot read '%s'", p, p);
        return shunyam_mulyam();
    }
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buf = (char *)malloc((size_t)len + 1);
    size_t got = fread(buf, 1, (size_t)len, f);
    fclose(f);
    buf[got] = '\0';
    Mulyam m = shabda_mulyam(buf, (int)got);
    free(buf);
    return m;
}

static Mulyam a_sanchikapanktayah(Mulyam *pra, int n) {
    Mulyam whole = a_sanchikapatha(pra, n);
    if (whole.prakara != P_SHABDA) return whole;
    Shabda *s = as_shabda(whole);
    Mulyam out = suchi_mulyam();
    int start = 0;
    for (int i = 0; i <= s->baits; i++) {
        if (i == s->baits || s->paatha[i] == '\n') {
            int end = i;
            if (end > start && s->paatha[end - 1] == '\r') end--;
            if (i == s->baits && start == i) break;      /* no trailing empty line */
            Mulyam line = shabda_mulyam(s->paatha + start, end - start);
            suchi_yojaya(out, line); muncha(line);
            start = i + 1;
        }
    }
    muncha(whole);
    return out;
}

static Mulyam sanchika_likh(Mulyam *pra, int n, const char *mode, const char *who) {
    const char *p = pathah(pra[0], who);
    if (!p) return shunyam_mulyam();
    char *content = (n >= 2) ? shabdakr(pra[1], false) : shabdakr(shabda_mulyam_c(""), false);
    FILE *f = vak_fopen(p, mode);
    if (!f) {
        free(content);
        dosha_utsrja("सञ्चिकादोषः",
                     "सञ्चिकायाम् लेखनम् न सिद्धम् '%s' / cannot write '%s'", p, p);
        return shunyam_mulyam();
    }
    int len = (int)strlen(content);
    fwrite(content, 1, (size_t)len, f);
    fclose(f);
    int akshara = utf8_ganana(content, len);
    free(content);
    return purnanka_mulyam(akshara);
}

static Mulyam a_sanchikalikh(Mulyam *pra, int n)   { return sanchika_likh(pra, n, "wb", "सञ्चिकालिख"); }
static Mulyam a_sanchikayojaya(Mulyam *pra, int n) { return sanchika_likh(pra, n, "ab", "सञ्चिकायोजय"); }

static Mulyam a_sanchikasti(Mulyam *pra, int n) {
    (void)n;
    const char *p = pathah(pra[0], "सञ्चिकास्ति");
    if (!p) return shunyam_mulyam();
    FILE *f = vak_fopen(p, "rb");
    if (f) { fclose(f); return satyata_mulyam(true); }
    return satyata_mulyam(false);
}

static Mulyam a_sanchikanashaya(Mulyam *pra, int n) {
    (void)n;
    const char *p = pathah(pra[0], "सञ्चिकानाशय");
    if (!p) return shunyam_mulyam();
    return satyata_mulyam(vak_remove(p) == 0);
}

static Mulyam a_nirdeshika(Mulyam *pra, int n) {
    const char *p = (n >= 1) ? pathah(pra[0], "निर्देशिका") : ".";
    if (n >= 1 && !p) return shunyam_mulyam();
    Mulyam out = suchi_mulyam();
#if VAK_WINDOWS
    char pattern[1024];
    snprintf(pattern, sizeof pattern, "%s\\*", p);
    wchar_t *wpattern = vistrta(pattern);
    WIN32_FIND_DATAW data;
    HANDLE h = wpattern ? FindFirstFileW(wpattern, &data) : INVALID_HANDLE_VALUE;
    free(wpattern);
    if (h == INVALID_HANDLE_VALUE) {
        muncha(out);
        dosha_utsrja("सञ्चिकादोषः",
                     "निर्देशिका न प्राप्ता '%s' / cannot read directory '%s'", p, p);
        return shunyam_mulyam();
    }
    do {
        if (wcscmp(data.cFileName, L".") == 0 || wcscmp(data.cFileName, L"..") == 0)
            continue;
        int len = WideCharToMultiByte(CP_UTF8, 0, data.cFileName, -1, NULL, 0, NULL, NULL);
        char *utf8 = (char *)malloc((size_t)(len > 0 ? len : 1));
        if (len > 0)
            WideCharToMultiByte(CP_UTF8, 0, data.cFileName, -1, utf8, len, NULL, NULL);
        else utf8[0] = '\0';
        Mulyam name = shabda_mulyam_c(utf8);
        suchi_yojaya(out, name);
        muncha(name);
        free(utf8);
    } while (FindNextFileW(h, &data));
    FindClose(h);
#else
    /* POSIX — पथाः तत्रैव UTF-8, अतः परिवर्तनम् न आवश्यकम्।
       Paths are already UTF-8 here, so nothing needs converting. */
    DIR *d = opendir(p);
    if (!d) {
        muncha(out);
        dosha_utsrja("सञ्चिकादोषः",
                     "निर्देशिका न प्राप्ता '%s' / cannot read directory '%s'", p, p);
        return shunyam_mulyam();
    }
    for (struct dirent *e = readdir(d); e; e = readdir(d)) {
        if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0) continue;
        Mulyam name = shabda_mulyam_c(e->d_name);
        suchi_yojaya(out, name);
        muncha(name);
    }
    closedir(d);
#endif
    /* पैथन्-वत् क्रमबद्धम् / sorted, as Python's sorted() leaves it */
    Suchi *s = as_suchi(out);
    for (int i = 1; i < s->dirghata; i++) {
        Mulyam key = s->angani[i];
        int j = i - 1;
        while (j >= 0) {
            Shabda *a = as_shabda(s->angani[j]), *b = as_shabda(key);
            int n2 = a->baits < b->baits ? a->baits : b->baits;
            int c = memcmp(a->paatha, b->paatha, (size_t)n2);
            if (c == 0) c = (a->baits < b->baits) ? -1 : (a->baits > b->baits ? 1 : 0);
            if (c > 0) { s->angani[j + 1] = s->angani[j]; j--; } else break;
        }
        s->angani[j + 1] = key;
    }
    return out;
}

static Mulyam a_khandam_chalaya(Mulyam *pra, int n) {
    Mulyam vibhagah = (n >= 2) ? pra[1] : shunyam_mulyam();
    return vak_khandam_chalaya(pra[0], vibhagah);
}

static Mulyam a_dosha(Mulyam *pra, int n) {
    char *sandesha = (n >= 1) ? shabdakr(pra[0], false) : NULL;
    char *prakara  = (n >= 2) ? shabdakr(pra[1], false) : NULL;
    dosha_utsrja(prakara ? prakara : "उपयोक्तृदोषः", "%s", sandesha ? sandesha : "दोषः");
    free(sandesha); free(prakara);
    return shunyam_mulyam();
}

/* ------------------------------------------------------------- सूचिका */
const Antarnihitam ANTARNIHITANI[] = {
    { "लिख", -1, a_likh },
    { "मुद्रय", -1, a_likh },
    { "पठ", -1, a_patha },
    { "प्रकार", 1, a_prakara },
    { "संख्या", 1, a_sankhya },
    { "शब्द", 1, a_shabda },
    { "देवनागरी", 1, a_devanagari },
    { "दीर्घता", 1, a_dirghata },
    { "सूची", -1, a_suchi },
    { "परास", -1, a_parasa },
    { "योजय", -1, a_yojaya },
    { "निष्कास", -1, a_nishkasa },
    { "अस्ति", 2, a_asti },
    { "कुञ्जिकाः", 1, a_kunjika },
    { "मूल्यानि", 1, a_mulyani },
    { "क्रम", -1, a_krama },
    { "विपर्यय", 1, a_viparyaya },
    { "विभज", -1, a_vibhaja },
    { "संयोज", -1, a_samyoja },
    { "योग", 1, a_yoga },
    { "न्यूनतम", 1, a_nyunatama },
    { "अधिकतम", 1, a_adhikatama },
    { "मूल", 1, a_mula },
    { "पूर्ण", 1, a_purna },
    { "यादृच्छिक", -1, a_yadrcchika },
    { "काल", 0, a_kala },
    { "प्राचलाः", 0, a_prachalah },
    { "दोष", -1, a_dosha },
    { "अक्षराणि", 1, a_aksharani },
    { "संकेतः", 1, a_sanketa },
    { "वर्णः", 1, a_varna },
    { "अंशः", -1, a_amsha },
    { "सञ्चिकापठ", 1, a_sanchikapatha },
    { "सञ्चिकापङ्क्तयः", 1, a_sanchikapanktayah },
    { "सञ्चिकालिख", -1, a_sanchikalikh },
    { "सञ्चिकायोजय", -1, a_sanchikayojaya },
    { "सञ्चिकास्ति", 1, a_sanchikasti },
    { "सञ्चिकानाशय", 1, a_sanchikanashaya },
    { "निर्देशिका", -1, a_nirdeshika },
    { "खण्डम्_चालय", -1, a_khandam_chalaya },
};

const int ANTARNIHITA_GANANA = (int)(sizeof(ANTARNIHITANI) / sizeof(ANTARNIHITANI[0]));

/* अन्तर्निहितानाम् सूची एकवारम् एव पठ्यते, ततः नाम्नः स्थानम् एकेन एव पदेन ज्ञायते।
   The table is read once into an open-addressed index, so finding a built-in
   costs one hash and one comparison instead of a walk down the whole list. */
#define ANTARNIHITA_KOSHA_MAP 128      /* > 2 × ANTARNIHITA_GANANA, a power of two */
static int ANTARNIHITA_MAP[ANTARNIHITA_KOSHA_MAP];
static bool ANTARNIHITA_MAP_SIDDHA = false;

static unsigned nama_hash(const char *s) {
    unsigned h = 2166136261u;                   /* FNV-1a */
    for (; *s; s++) { h ^= (unsigned char)*s; h *= 16777619u; }
    return h;
}

static void antarnihita_map_rachaya(void) {
    for (int i = 0; i < ANTARNIHITA_KOSHA_MAP; i++) ANTARNIHITA_MAP[i] = -1;
    for (int i = 0; i < ANTARNIHITA_GANANA; i++) {
        unsigned at = nama_hash(ANTARNIHITANI[i].nama) & (ANTARNIHITA_KOSHA_MAP - 1);
        while (ANTARNIHITA_MAP[at] >= 0) at = (at + 1) & (ANTARNIHITA_KOSHA_MAP - 1);
        ANTARNIHITA_MAP[at] = i;
    }
    ANTARNIHITA_MAP_SIDDHA = true;
}

int antarnihitam_anvishya(const char *nama) {
    if (!ANTARNIHITA_MAP_SIDDHA) antarnihita_map_rachaya();
    unsigned at = nama_hash(nama) & (ANTARNIHITA_KOSHA_MAP - 1);
    while (ANTARNIHITA_MAP[at] >= 0) {
        int i = ANTARNIHITA_MAP[at];
        if (strcmp(ANTARNIHITANI[i].nama, nama) == 0) return i;
        at = (at + 1) & (ANTARNIHITA_KOSHA_MAP - 1);
    }
    return -1;
}
