import { describe, expect, it } from 'vitest';
import { tierConfig } from '@/lib/ageTier';

describe('tierConfig home-redesign knobs', () => {
  it('explorer is playful with Penny and emoji', () => {
    expect(tierConfig.explorer.heroVariant).toBe('playful');
    expect(tierConfig.explorer.showPennyAvatar).toBe(true);
    expect(tierConfig.explorer.chipEmoji).toBe(true);
  });
  it('investor is flat, no Penny, no emoji', () => {
    expect(tierConfig.investor.heroVariant).toBe('flat');
    expect(tierConfig.investor.showPennyAvatar).toBe(false);
    expect(tierConfig.investor.chipEmoji).toBe(false);
  });
});
