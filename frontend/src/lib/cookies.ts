export function readCookie(name: string): string | null {
  const all = document.cookie ? document.cookie.split('; ') : [];
  for (const part of all) {
    const eq = part.indexOf('=');
    const k = eq < 0 ? part : part.slice(0, eq);
    if (k === name) {
      const v = eq < 0 ? '' : part.slice(eq + 1);
      try { return decodeURIComponent(v); } catch { return v; }
    }
  }
  return null;
}
