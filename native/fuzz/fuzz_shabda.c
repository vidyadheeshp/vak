/*
 * fuzz_shabda.c — libFuzzer harness for the string built-ins in
 * antarnihitani.c.
 *
 * These are the one place raw, unvalidated bytes reach the native runtime:
 * पठ() hands whatever came off stdin straight to a Shabda with no UTF-8
 * check, and from there a program can pass it to any of these built-ins.
 * The lexer, by contrast, only ever sees text it has itself validated — so
 * fuzzing it would exercise a path a running program cannot actually reach.
 * This harness instead builds one Shabda directly from the fuzzer's bytes,
 * exactly as पठ() would, and drives every built-in that walks a string's
 * bytes by hand: अक्षराणि (grapheme segmentation), संख्या (string-to-number),
 * देवनागरी, दीर्घता, सूची (character split), अंशः/संकेतः/वर्णः (indexing and
 * codepoint conversion). Every fixed-size buffer this project has looked at
 * closely so far turned out to have a real bug; these are the functions
 * with fixed-size buffers that a fuzzer, rather than a differential test
 * written by hand, is positioned to actually find one in.
 *
 * Build (from the repository root):
 *   clang -std=c11 -g -O1 -fsanitize=fuzzer,address,undefined \
 *       -I native native/fuzz/fuzz_shabda.c native/mulyani.c \
 *       native/antarnihitani.c native/yantram.c -lm -o fuzz_shabda
 *   ./fuzz_shabda -max_total_time=120 native/fuzz/corpus/
 */
#include "vak.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* An emitted program's own C file normally defines these — the module table
   for आनय and the program's entry chunk. This harness calls built-ins
   directly and never runs a program through vak_chalaya, so both are empty. */
const Vibhaga VIBHAGAH[] = { { NULL, NULL } };
const int VIBHAGA_GANANA = 0;

static void try_call(const char *nama, Mulyam *pra, int n) {
    int idx = antarnihitam_anvishya(nama);
    if (idx < 0) return;                       /* the table drifted; nothing to fuzz */
    const Antarnihitam *a = &ANTARNIHITANI[idx];
    if (a->prachala_ganana >= 0 && n != a->prachala_ganana) return;
    for (int i = 0; i < n; i++) grah(pra[i]);
    Mulyam out = a->karyam(pra, n);
    for (int i = 0; i < n; i++) muncha(pra[i]);
    muncha(out);
    /* दोषध्वजम् दोषान्तरम् इव लक्षयति — अगले आह्वाने अवश्यमेव स्वच्छं भवेत्। */
    DOSHA_ASTI = false;
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    /* The fuzzer's bytes become the string exactly as पठ() would hand them
       to a program — no UTF-8 validation, arbitrary bytes, arbitrary length. */
    Mulyam s = shabda_mulyam((const char *)data, (int)size);

    Mulyam one[1] = { s };
    try_call("अक्षराणि", one, 1);
    try_call("संख्या", one, 1);
    try_call("देवनागरी", one, 1);
    try_call("दीर्घता", one, 1);
    try_call("सूची", one, 1);

    /* अंशः/संकेतः derive a start/stop from the tail of the input, so both
       in-range and wildly out-of-range indices get exercised against the
       same string. */
    int64_t start = 0, stop = 0;
    if (size >= 8) {
        memcpy(&start, data, 8);
        if (size >= 16) memcpy(&stop, data + 8, 8);
        else stop = start;
    }
    Mulyam amsha_args[3] = { s, purnanka_mulyam(start), purnanka_mulyam(stop) };
    try_call("अंशः", amsha_args, 3);

    /* संकेतः rejects anything but a single character — exercising that
       error branch is as much the point as the one-character case is. */
    Mulyam sanketah_args[1] = { s };
    try_call("संकेतः", sanketah_args, 1);

    /* वर्णः goes the other way — an arbitrary integer codepoint back into
       UTF-8 bytes, including negative and out-of-Unicode-range values the
       compiler's frontend would never construct but a native program built
       from untrusted input still could. */
    int64_t cp = 0;
    if (size >= 8) memcpy(&cp, data, 8);
    Mulyam varnah_args[1] = { purnanka_mulyam(cp) };
    try_call("वर्णः", varnah_args, 1);

    muncha(s);
    return 0;
}
