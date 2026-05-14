/**
 * Convert a 2-letter ISO 3166-1 alpha-2 country code to a flag emoji.
 * Each letter is offset to the Regional Indicator Symbol range.
 */
export function countryFlag(code: string): string {
  if (!code || code.length !== 2) return '';
  const upper = code.toUpperCase();
  const offset = 0x1F1E6 - 0x41; // Regional indicator 'A' minus ASCII 'A'
  return String.fromCodePoint(
    upper.charCodeAt(0) + offset,
    upper.charCodeAt(1) + offset,
  );
}
