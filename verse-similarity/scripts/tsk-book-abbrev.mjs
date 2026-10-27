/**
 * OpenBible.info TSK book abbreviations → canonical book number (1–66).
 * Gospel helpers focus on Matt=40 … John=43.
 */

export const TSK_ABBREV_TO_BOOK_NUM = {
  Gen: 1,
  Exod: 2,
  Lev: 3,
  Num: 4,
  Deut: 5,
  Josh: 6,
  Judg: 7,
  Ruth: 8,
  '1Sam': 9,
  '2Sam': 10,
  '1Kgs': 11,
  '2Kgs': 12,
  '1Chr': 13,
  '2Chr': 14,
  Ezra: 15,
  Neh: 16,
  Esth: 17,
  Job: 18,
  Ps: 19,
  Prov: 20,
  Eccl: 21,
  Song: 22,
  Isa: 23,
  Jer: 24,
  Lam: 25,
  Ezek: 26,
  Dan: 27,
  Hos: 28,
  Joel: 29,
  Amos: 30,
  Obad: 31,
  Jonah: 32,
  Mic: 33,
  Nah: 34,
  Hab: 35,
  Zeph: 36,
  Hag: 37,
  Zech: 38,
  Mal: 39,
  Matt: 40,
  Mark: 41,
  Luke: 42,
  John: 43,
  Acts: 44,
  Rom: 45,
  '1Cor': 46,
  '2Cor': 47,
  Gal: 48,
  Eph: 49,
  Phil: 50,
  Col: 51,
  '1Thess': 52,
  '2Thess': 53,
  '1Tim': 54,
  '2Tim': 55,
  Titus: 56,
  Phlm: 57,
  Heb: 58,
  Jas: 59,
  '1Pet': 60,
  '2Pet': 61,
  '1John': 62,
  '2John': 63,
  '3John': 64,
  Jude: 65,
  Rev: 66,
};

export const BOOK_NUM_TO_NAME = {
  1: 'Genesis',
  2: 'Exodus',
  3: 'Leviticus',
  4: 'Numbers',
  5: 'Deuteronomy',
  6: 'Joshua',
  7: 'Judges',
  8: 'Ruth',
  9: '1 Samuel',
  10: '2 Samuel',
  11: '1 Kings',
  12: '2 Kings',
  13: '1 Chronicles',
  14: '2 Chronicles',
  15: 'Ezra',
  16: 'Nehemiah',
  17: 'Esther',
  18: 'Job',
  19: 'Psalms',
  20: 'Proverbs',
  21: 'Ecclesiastes',
  22: 'Song of Solomon',
  23: 'Isaiah',
  24: 'Jeremiah',
  25: 'Lamentations',
  26: 'Ezekiel',
  27: 'Daniel',
  28: 'Hosea',
  29: 'Joel',
  30: 'Amos',
  31: 'Obadiah',
  32: 'Jonah',
  33: 'Micah',
  34: 'Nahum',
  35: 'Habakkuk',
  36: 'Zephaniah',
  37: 'Haggai',
  38: 'Zechariah',
  39: 'Malachi',
  40: 'Matthew',
  41: 'Mark',
  42: 'Luke',
  43: 'John',
  44: 'Acts',
  45: 'Romans',
  46: '1 Corinthians',
  47: '2 Corinthians',
  48: 'Galatians',
  49: 'Ephesians',
  50: 'Philippians',
  51: 'Colossians',
  52: '1 Thessalonians',
  53: '2 Thessalonians',
  54: '1 Timothy',
  55: '2 Timothy',
  56: 'Titus',
  57: 'Philemon',
  58: 'Hebrews',
  59: 'James',
  60: '1 Peter',
  61: '2 Peter',
  62: '1 John',
  63: '2 John',
  64: '3 John',
  65: 'Jude',
  66: 'Revelation',
};

/** Matthew=40 … John=43 */
export const GOSPEL_BOOK_NUMS = new Set([40, 41, 42, 43]);

export function isGospelBook(bookNum) {
  return GOSPEL_BOOK_NUMS.has(bookNum);
}

export function isGospelVid(vid) {
  const book = Math.floor(vid / 1_000_000);
  return isGospelBook(book);
}

export function tskTokenToVid(token) {
  const match = token.match(/^([A-Za-z0-9]+)\.(\d+)\.(\d+)$/);
  if (!match) return null;
  const bookNum = TSK_ABBREV_TO_BOOK_NUM[match[1]];
  if (!bookNum) return null;
  const chapter = parseInt(match[2], 10);
  const verse = parseInt(match[3], 10);
  if (!chapter || !verse) return null;
  return bookNum * 1_000_000 + chapter * 1_000 + verse;
}

export function expandTskTarget(targetPart) {
  const range = targetPart.match(
    /^([A-Za-z0-9]+)\.(\d+)\.(\d+)-([A-Za-z0-9]+)\.(\d+)\.(\d+)$/,
  );
  if (range) {
    const startVid = tskTokenToVid(`${range[1]}.${range[2]}.${range[3]}`);
    const endVid = tskTokenToVid(`${range[4]}.${range[5]}.${range[6]}`);
    if (startVid == null || endVid == null || endVid < startVid) return [];
    const out = [];
    const startBook = Math.floor(startVid / 1_000_000);
    const endBook = Math.floor(endVid / 1_000_000);
    const startChapter = Math.floor((startVid % 1_000_000) / 1_000);
    const endChapter = Math.floor((endVid % 1_000_000) / 1_000);
    const startVerse = startVid % 1_000;
    const endVerse = endVid % 1_000;
    if (startBook !== endBook || startChapter !== endChapter) {
      out.push(startVid);
      if (endVid !== startVid) out.push(endVid);
      return out;
    }
    for (let v = startVerse; v <= endVerse; v += 1) {
      out.push(startBook * 1_000_000 + startChapter * 1_000 + v);
    }
    return out;
  }

  const single = tskTokenToVid(targetPart);
  return single == null ? [] : [single];
}

export function parseTskLine(line) {
  const parts = line.split('\t');
  if (parts.length < 3) return null;
  const [fromToken, toToken, votesRaw] = parts;
  const votes = parseInt(votesRaw, 10);
  if (!votes) return null;
  const fromVid = tskTokenToVid(fromToken.trim());
  if (fromVid == null) return null;
  const targets = expandTskTarget(toToken.trim());
  if (!targets.length) return null;
  return { fromVid, targets, votes };
}
