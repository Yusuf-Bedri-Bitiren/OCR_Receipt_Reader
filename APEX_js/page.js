//https://unpkg.com/tesseract.js@4.0.2/dist/tesseract.min.js

function fixCommonOcrErrors(text) {
  const replacements = {
    'O': '0', 'o': '0', 'I': '1', 'i': '1', 'İ': '1', 'l': '1', 'S': '5', 'B': '8', '/': '.', '-': '.'
  };
  return text.split('').map(c => replacements[c] || c).join('');
}

function fixDateOcrErrors(dateStr) {
  if (dateStr.length !== 10) return dateStr;
  let [day, month, year] = [dateStr.slice(0, 2), dateStr.slice(3, 5), dateStr.slice(6)];
  if (!year.startsWith('20')) year = '20' + year.slice(2);
  if (!['0', '1', '2'].includes(year[2])) year = year.slice(0, 2) + '2' + year.slice(3);
  if (!['0', '1', '2', '3'].includes(day[0])) day = '0' + day[1];
  return `${day}.${month}.${year}`;
}

function fixAndParseFloat(s) {
  s = fixCommonOcrErrors(s).replace(/\s/g, '');
  if (s.includes('.') && s.includes(',')) {
    s = s.lastIndexOf('.') > s.lastIndexOf(',') ? s.replace(/,/g, '') : s.replace(/\./g, '').replace(',', '.');
  } else if (s.includes(',')) {
    s = s.replace(',', '.');
  }
  s = s.replace(/[^\d.]/g, '');
  const val = parseFloat(s);
  return isNaN(val) ? null : val;
}

function extractFields(text) {

  const fields = {
    'Tarih': null,
    'Fatura No': null,
    'Toplam': null
  };

  const reList = {
    'Tarih': /\b(\d{2}[./-]\d{2}[./-]\d{4})\b/i,
    'Fiş No': /(?:f[ıiİl1|][şs5]\s*no|fiş\s*no|fişno)[^\d\n]{0,5}[\s\n]*([\d]{1,4})\b/i,
    'Toplam': /(?<!ara\s)(?<!4ra\s)(?<!afa\s)(?<!kdv(?:[’'`´]li?)?\s)(?<!kdu\s)(?<!kdy\s)(?<!kdi\s)(?<!kdw\s)(?<!kdn\s)(?<!kdx\s)\btoplam(?:\s+tutar(?!ı))?\b[^\d]{0,3}[*x»:/-]?\s*([\dOolIıİi.,\s]{1,20}\d)/i,
    'Toplam KDV': /(?:toplam\s+kdv|topkdv|topkdu|TOPVP|topkov|topkdy|topkdi|ToOPKDV|TOPKÜV|topkdw|topkdı|topkvu|topkd|topkdvı)[^\dO]{0,3}[*x»]?\s*([\dOolIıİi.,\s]{1,15}\d)/i,
    'KDV Oranı': /kdv\s*oran[ıiİl1][^\d\n]{0,40}(?:\n[^\d\n]{0,40}){0,3}[^0-9]{0,10}(\d{1,2})\b/i,
    'Fatura No': /(?:fatura\s*(?:no|nu|n[o0])|fat\s*no)[^\w\d]{0,4}[:-]?\s*([A-ZİŞĞÜÇÖ]{1,4}[\s-]?\d{10,16})/i,
    'Ticaret Sicil No': /(?:ticaret\s*sicil\s*no|t\.?\s*s\.?\s*no|tic\s*sic\s*no|tsn|sicil\s*no)[^\d]{0,3}[*x»:]?\s*([\dOolIıİi]{6})\b/i,
    'Mersis No': /(?:mersis\s*no|mersis\s*number|mersis\s*nu|mers\s*no)[^\d]{0,3}[*x»:]?\s*(\d{16})\b/i,
    'ETTN': /(?:[eEfF][\s.:,;_-]*[tT1İil][\s.:,;_-]*[tT1İil][\s.:,;_-]*[nNhHmM])[\s.:,;_-]*[:\-]?\s*([a-fA-F0-9\-]{36})/i,
    'Vergi Kimlik No': /(?:vergi\s*kimlik\s*no|vkn)[^\dOolIıİ]{0,3}[*x»:]?\s*([0-9OolIıİ]{10})\b/i
  };

  for (const [key, regex] of Object.entries(reList)) {
    const match = text.match(regex);
    if (!match) continue;
    let val = fixCommonOcrErrors(match[1]);
    if (key === 'Tarih') val = fixDateOcrErrors(val);
    else if (key === 'Toplam' || key === 'Toplam KDV') val = fixAndParseFloat(val);
    else if (key === 'KDV Oranı') {
      const parsed = parseInt(val);
      if ([0, 1, 8, 10, 18, 20].includes(parsed)) val = parsed; else continue;
    } else if (key === 'Vergi Kimlik No') {
      val = val.replace(/\D/g, '');
      if (val === '5240008809') continue;
    }
    fields[key] = val;
  }
  return fields;
}

async function extractText(image, psm = 6, lang = 'tur') {
  const { data: { text } } = await Tesseract.recognize(image, lang, {
    logger: m => {},
    config: {
      tessedit_pageseg_mode: psm,  // Pass psm directly as an integer
    },
  });
  return text;
}

// ───────────────────────────────────────────────────────────────────────
// Helper: pull out each line between your start/end markers,
// skip calculation lines, and regex-match on [description, KDV, amount].
function parseItems(rawText, test = false) {
    const lines = rawText
      .split(/\r?\n/)
      .map(l => l.trim())
      .filter(l => l.length > 0);

    let startIdx = lines.findIndex(l => /Sipariş\s+Numara(sı|si)/i.test(l));
    if(test && startIdx > 0) console.log("Sipariş no found at line: " + startIdx);
    

    if (startIdx < 0) {
        startIdx = lines.findIndex(l => /F[İIıi1]?[İIıi1]?[İIıi1]?[ŞŞşsS]?\s*NO\s*:?\s*\d+/i.test(l));
        if(test && startIdx > 0) console.log("Fiş no found at line: " + startIdx);
    }
    if (startIdx < 0) startIdx = 0; // If you can't find the start index just start from the beginning

    let endIdx = lines.findIndex(l => /^SS\s+TOPKDV\b/i.test(l));

    if (endIdx < 0) {
        endIdx = lines.findIndex(l => /\bToplam\b/i.test(l));
    }

    if (endIdx < 0) endIdx = lines.length;

    if (test) {
        console.log("Start Index is:" + startIdx);
        console.log("End Index is:" + endIdx);
    }

    if (startIdx < 0 || endIdx < 0 || endIdx <= startIdx) {
        return [];  // no block found
    }

    const itemLines = lines.slice(startIdx + 1, endIdx);
    const Alt_Kalemler = [];

    // Regex:  
    // 1) description  
    // 2) up to 3 of x or * (OCR noise) 
    // 3) rate token (01,08,10,18,20 or their 3‑digit OCR-corrupted variants) - could be improved
    // 4) amount (e.g. 1.234,56) - now does allow spaces in between (i.e 0, 25) 
    // 5) allow any trailing non‑digits
    const itemRe = /^(.+?)\s+[&x\*]{0,3}\s*(1|8|01|08|10|18|20|401|408|410|418|420|101|108|110|118|120)\b.*?([\d.]+)\s*,\s*(\d{2})(?:\D*)$/i;

    for (const line of itemLines) {
        // skip lines that are just a calculation or garbage, e.g. "3 X 35,50 a"
        if (/^\d+\s*[Xx]\b/.test(line)) continue;

        const m = line.match(itemRe);
        if (!m) continue;

        const [, rawName, rateStr, intPart, fracPart] = m;
        const amountStr = `${intPart.replace(/\./g, '')},${fracPart}`;
        const total     = parseFloat(amountStr.replace(',', '.'));
        const name  = rawName.trim();
        let kdv = parseInt(rateStr, 10);

        // If the rate is a 3-digit number starting with 4 or 1, remove the first digit
        if (rateStr.length === 3 && (rateStr.startsWith('4') || rateStr.startsWith('1'))) {
            kdv = parseInt(rateStr.slice(1), 10);  // Omit the first digit
        }        

        Alt_Kalemler.push({
            "Masraf Açıklama": name,
            "KDV Oranı":      kdv,
            "Harcama Tutarı": total
        });
    }

    if (test) {
        const sum = Alt_Kalemler
            .reduce((acc, item) => acc + (item["Harcama Tutarı"] || 0), 0);
        console.log(`Toplam Harcama Kalemleri: ${sum.toFixed(2)}`);
    }

    return Alt_Kalemler;
}

function mergeFieldResults(results) {
  const final = {};
  const grouped = {};

  results.forEach(r => {
    for (const [key, val] of Object.entries(r)) {
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(val);
    }
  });

  for (const [key, values] of Object.entries(grouped)) {
    const counts = values.reduce((acc, v) => {
      acc[v] = (acc[v] || 0) + 1;
      return acc;
    }, {});
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const [topVal, topCount] = sorted[0];

    let override = false;
    if (typeof topVal === 'number') {
      for (const [val] of sorted.slice(0, 2)) {
        if (String(val).startsWith('4') || String(val).startsWith('1')) {
          const stripped = parseFloat(String(val).slice(1));
          if (counts[stripped] >= 2) {
            final[key] = stripped;
            override = true;
            break;
          }
        }
      }
    }
    if (!override) final[key] = topVal;
  }
  return final;
}

function isReceipt(rawText) {
  if (!rawText) return false;

  const fisNoRegex = new RegExp(
    [
      // Variants of "Fiş No" with common OCR mistakes
      '(?:', 
        'f[ıiİl1|]',         // fı, fi, f1, fİ, etc.
        '[şs5]',             // ş, s, 5
        '[\\s.:,-_]*',       // optional space or punctuation
        '(?:no|n[o0]|nu)',   // no, n0, nu
      ')'
    ].join(''),
    'i'
  );

  return fisNoRegex.test(rawText);
}
