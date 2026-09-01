"use strict";
// स्वयं जनितम् — generated from vak/translit.py; do not edit.
// Longest key first, across every table at once: matching per-table
// would let `~` beat `~N`, turning अङ्क into अँण्क.
const TABLE = [["chh", "C", "छ"], ["RRi", "V", "ऋ", "ृ"], ["R^i", "V", "ऋ", "ृ"], ["kh", "C", "ख"], ["gh", "C", "घ"], ["ch", "C", "च"], ["Ch", "C", "छ"], ["jh", "C", "झ"], ["Th", "C", "ठ"], ["Dh", "C", "ढ"], ["th", "C", "थ"], ["dh", "C", "ध"], ["ph", "C", "फ"], ["bh", "C", "भ"], ["sh", "C", "श"], ["Sh", "C", "ष"], ["GY", "C", "ज्ञ"], ["jn", "C", "ज्ञ"], ["~N", "C", "ङ"], ["ng", "C", "ङ"], ["~n", "C", "ञ"], ["ny", "C", "ञ"], ["N^", "C", "ङ"], ["JN", "C", "ज्ञ"], ["aa", "V", "आ", "ा"], ["ii", "V", "ई", "ी"], ["ee", "V", "ई", "ी"], ["uu", "V", "ऊ", "ू"], ["oo", "V", "ऊ", "ू"], ["ai", "V", "ऐ", "ै"], ["au", "V", "औ", "ौ"], ["Ri", "V", "ऋ", "ृ"], [".n", "M", "ं"], [".h", "M", "्"], ["k", "C", "क"], ["g", "C", "ग"], ["c", "C", "च"], ["j", "C", "ज"], ["T", "C", "ट"], ["D", "C", "ड"], ["N", "C", "ण"], ["t", "C", "त"], ["d", "C", "द"], ["n", "C", "न"], ["p", "C", "प"], ["b", "C", "ब"], ["m", "C", "म"], ["y", "C", "य"], ["r", "C", "र"], ["l", "C", "ल"], ["L", "C", "ळ"], ["v", "C", "व"], ["w", "C", "व"], ["S", "C", "ष"], ["z", "C", "श"], ["s", "C", "स"], ["h", "C", "ह"], ["f", "C", "फ"], ["q", "C", "क"], ["x", "C", "क्ष"], ["A", "V", "आ", "ा"], ["I", "V", "ई", "ी"], ["U", "V", "ऊ", "ू"], ["a", "V", "अ", ""], ["i", "V", "इ", "ि"], ["u", "V", "उ", "ु"], ["e", "V", "ए", "े"], ["o", "V", "ओ", "ो"], ["M", "M", "ं"], ["~", "M", "ँ"], ["H", "M", "ः"]];
const DIGITS = {"0": "०", "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७", "8": "८", "9": "९"};
const VIRAMA = "्";

function devanagari(text, digits) {
  let out = "", i = 0, pending = false;
  outer:
  while (i < text.length) {
    for (const entry of TABLE) {
      const key = entry[0];
      if (!text.startsWith(key, i)) continue;
      const kind = entry[1];
      if (kind === "C") {
        if (pending) out += VIRAMA;
        out += entry[2];
        pending = true;
      } else if (kind === "V") {
        out += pending ? entry[3] : entry[2];
        pending = false;
      } else {
        out += out.length ? entry[2] : key;
        pending = false;
      }
      i += key.length;
      continue outer;
    }
    if (pending) { out += VIRAMA; pending = false; }
    const ch = text[i];
    out += (digits && DIGITS[ch]) ? DIGITS[ch] : ch;
    i += 1;
  }
  if (pending) out += VIRAMA;
  return out;
}

module.exports = { devanagari };
