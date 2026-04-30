import { describe, it, expect } from 'vitest';
import { consentThreshold, ageInYears, needsParentalConsent, EU_COUNTRIES_16 } from '@/lib/consent';

describe('consentThreshold', () => {
  it('returns 16 for each EU_COUNTRIES_16 member', () => {
    for (const cc of EU_COUNTRIES_16) {
      expect(consentThreshold(cc)).toBe(16);
    }
  });
  it('returns 13 for UK', () => { expect(consentThreshold('GB')).toBe(13); });
  it('returns 13 for US', () => { expect(consentThreshold('US')).toBe(13); });
  it('returns 13 for Hong Kong', () => { expect(consentThreshold('HK')).toBe(13); });
});

describe('ageInYears', () => {
  it('returns whole years on a non-birthday day', () => {
    expect(ageInYears(new Date('2010-01-01'), new Date('2026-04-29'))).toBe(16);
  });
  it('returns one less when birthday hasnt happened yet this year', () => {
    expect(ageInYears(new Date('2010-12-31'), new Date('2026-04-29'))).toBe(15);
  });
  it('returns exact age on the birthday itself', () => {
    expect(ageInYears(new Date('2010-04-29'), new Date('2026-04-29'))).toBe(16);
  });
});

describe('needsParentalConsent', () => {
  const today = new Date('2026-04-29');
  it('UK 11 needs consent', () => {
    expect(needsParentalConsent(new Date('2015-01-01'), 'GB', today)).toBe(true);
  });
  it('UK 13 today does not need consent', () => {
    expect(needsParentalConsent(new Date('2013-04-29'), 'GB', today)).toBe(false);
  });
  it('IE 14 needs consent (16 threshold)', () => {
    expect(needsParentalConsent(new Date('2012-01-01'), 'IE', today)).toBe(true);
  });
  it('IE 16 today does not need consent', () => {
    expect(needsParentalConsent(new Date('2010-04-29'), 'IE', today)).toBe(false);
  });
  it('US 14 does not need consent (13 threshold)', () => {
    expect(needsParentalConsent(new Date('2012-01-01'), 'US', today)).toBe(false);
  });
});
