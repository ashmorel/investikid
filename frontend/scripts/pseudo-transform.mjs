const MAP = { a: 'ä', e: 'ё', i: 'ï', o: 'ö', u: 'ü', A: 'Ä', E: 'Ё', O: 'Ö' };

// Transform a single string, leaving {{interpolation}} placeholders intact.
export function pseudo(s) {
  let out = '';
  let i = 0;
  while (i < s.length) {
    if (s.startsWith('{{', i)) {
      const end = s.indexOf('}}', i);
      if (end === -1) {
        // Malformed — no closing }}; append the rest and stop.
        out += s.slice(i);
        break;
      }
      out += s.slice(i, end + 2);
      i = end + 2;
      continue;
    }
    out += MAP[s[i]] ?? s[i];
    i += 1;
  }
  return `[${out}]`;
}

export function pseudoTree(obj) {
  if (typeof obj === 'string') return pseudo(obj);
  const out = {};
  for (const [k, v] of Object.entries(obj)) out[k] = pseudoTree(v);
  return out;
}
