export const MARKET_FLAGS: Record<string, string> = {
  GB: '🇬🇧', US: '🇺🇸', AU: '🇦🇺', CA: '🇨🇦', IE: '🇮🇪',
  ES: '🇪🇸', FR: '🇫🇷', DE: '🇩🇪', HK: '🇭🇰', SG: '🇸🇬',
};

export const flagFor = (code: string): string => MARKET_FLAGS[code] ?? code;
