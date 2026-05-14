import { describe, it, expect } from 'vitest';
import { formatCurrency, getCurrencySymbol } from '@/lib/currency';

describe('formatCurrency', () => {
  it('formats USD', () => {
    expect(formatCurrency('185.42', 'USD')).toBe('$185.42 USD');
  });
  it('formats GBP', () => {
    expect(formatCurrency('12.34', 'GBP')).toBe('£12.34 GBP');
  });
  it('formats HKD', () => {
    expect(formatCurrency('234.00', 'HKD')).toBe('HK$234.00 HKD');
  });
  it('formats unknown currency with code only', () => {
    expect(formatCurrency('100.00', 'JPY')).toBe('¥100.00 JPY');
  });
  it('handles whole numbers', () => {
    expect(formatCurrency('10000', 'USD')).toBe('$10,000.00 USD');
  });
});

describe('getCurrencySymbol', () => {
  it('returns $ for USD', () => expect(getCurrencySymbol('USD')).toBe('$'));
  it('returns £ for GBP', () => expect(getCurrencySymbol('GBP')).toBe('£'));
  it('returns HK$ for HKD', () => expect(getCurrencySymbol('HKD')).toBe('HK$'));
});
