"use strict";
// स्वयं जनितम् — generated from vaak/translit.py; do not edit.
// Longest key first, across every table at once: matching per-table
// would let `~` beat `~N`, turning अङ्क into अँण्क.
const TABLE = [["chh", "C", "छ"], ["RRi", "V", "ऋ", "ृ"], ["R^i", "V", "ऋ", "ृ"], ["kh", "C", "ख"], ["gh", "C", "घ"], ["ch", "C", "च"], ["Ch", "C", "छ"], ["jh", "C", "झ"], ["Th", "C", "ठ"], ["Dh", "C", "ढ"], ["th", "C", "थ"], ["dh", "C", "ध"], ["ph", "C", "फ"], ["bh", "C", "भ"], ["sh", "C", "श"], ["Sh", "C", "ष"], ["GY", "C", "ज्ञ"], ["jn", "C", "ज्ञ"], ["~N", "C", "ङ"], ["ng", "C", "ङ"], ["~n", "C", "ञ"], ["ny", "C", "ञ"], ["N^", "C", "ङ"], ["JN", "C", "ज्ञ"], ["aa", "V", "आ", "ा"], ["ii", "V", "ई", "ी"], ["ee", "V", "ई", "ी"], ["uu", "V", "ऊ", "ू"], ["oo", "V", "ऊ", "ू"], ["ai", "V", "ऐ", "ै"], ["au", "V", "औ", "ौ"], ["Ri", "V", "ऋ", "ृ"], [".n", "M", "ं"], [".h", "M", "्"], ["k", "C", "क"], ["g", "C", "ग"], ["c", "C", "च"], ["j", "C", "ज"], ["T", "C", "ट"], ["D", "C", "ड"], ["N", "C", "ण"], ["t", "C", "त"], ["d", "C", "द"], ["n", "C", "न"], ["p", "C", "प"], ["b", "C", "ब"], ["m", "C", "म"], ["y", "C", "य"], ["r", "C", "र"], ["l", "C", "ल"], ["L", "C", "ळ"], ["v", "C", "व"], ["w", "C", "व"], ["S", "C", "ष"], ["z", "C", "श"], ["s", "C", "स"], ["h", "C", "ह"], ["f", "C", "फ"], ["q", "C", "क"], ["x", "C", "क्ष"], ["A", "V", "आ", "ा"], ["I", "V", "ई", "ी"], ["U", "V", "ऊ", "ू"], ["a", "V", "अ", ""], ["i", "V", "इ", "ि"], ["u", "V", "उ", "ु"], ["e", "V", "ए", "े"], ["o", "V", "ओ", "ो"], ["M", "M", "ं"], ["~", "M", "ँ"], ["H", "M", "ः"]];
const DIGITS = {"0": "०", "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७", "8": "८", "9": "९"};
const VIRAMA = "्";
const KEYWORDS = {"māna": "मान", "mana": "मान", "dhruva": "ध्रुव", "kāryam": "कार्यम्", "karyam": "कार्यम्", "kārya": "कार्यम्", "karya": "कार्यम्", "pratyāgaccha": "प्रत्यागच्छ", "pratyagaccha": "प्रत्यागच्छ", "pratidā": "प्रत्यागच्छ", "pratida": "प्रत्यागच्छ", "yadi": "यदि", "anyathā": "अन्यथा", "anyatha": "अन्यथा", "yāvat": "यावत्", "yavat": "यावत्", "pratyekam": "प्रत्येकम्", "antaḥ": "अन्तः", "antah": "अन्तः", "āvṛttiḥ": "आवृत्तिः", "avrttih": "आवृत्तिः", "virama": "विरम", "anuvarta": "अनुवर्त", "mudraya": "मुद्रय", "ānaya": "आनय", "anaya": "आनय", "iti": "इति", "taḥ": "तः", "tah": "तः", "vikalpaḥ": "विकल्पः", "vikalpah": "विकल्पः", "pakṣe": "पक्षे", "pakshe": "पक्षे", "prayatnaḥ": "प्रयत्नः", "prayatnah": "प्रयत्नः", "doṣe": "दोषे", "doshe": "दोषे", "gṛhāṇa": "दोषे", "grihana": "दोषे", "antataḥ": "अन्ततः", "antatah": "अन्ततः", "utsṛja": "उत्सृज", "utsrja": "उत्सृज", "kṣipa": "उत्सृज", "kshipa": "उत्सृज", "satya": "सत्य", "asatya": "असत्य", "śūnya": "शून्य", "shunya": "शून्य", "sunya": "शून्य", "ca": "च", "vā": "वा", "va": "वा", "na": "न", "likh": "लिख", "patha": "पठ", "prakara": "प्रकार", "sankhya": "संख्या", "shabda": "शब्द", "devanagari": "देवनागरी", "dirghata": "दीर्घता", "suchi": "सूची", "parasa": "परास", "yojaya": "योजय", "nishkasa": "निष्कास", "asti": "अस्ति", "kunjika": "कुञ्जिकाः", "mulyani": "मूल्यानि", "krama": "क्रम", "viparyaya": "विपर्यय", "aksharani": "अक्षराणि", "sanketa": "संकेतः", "varna": "वर्णः", "amsha": "अंशः", "vibhaja": "विभज", "samyoja": "संयोज", "yoga": "योग", "nyunatama": "न्यूनतम", "adhikatama": "अधिकतम", "mula": "मूल", "purna": "पूर्ण", "yadrcchika": "यादृच्छिक", "kala": "काल", "prachalah": "प्राचलाः", "khandam_chalaya": "खण्डम्_चालय", "dosha": "दोष", "sanchikapatha": "सञ्चिकापठ", "sanchikapanktayah": "सञ्चिकापङ्क्तयः", "sanchikalikh": "सञ्चिकालिख", "sanchikayojaya": "सञ्चिकायोजय", "sanchikasti": "सञ्चिकास्ति", "sanchikanashaya": "सञ्चिकानाशय", "nirdeshika": "निर्देशिका"};

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

function convert(word, digits) {
  return KEYWORDS[word] || devanagari(word, digits);
}

module.exports = { devanagari, convert };
