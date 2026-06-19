import { describe, expect, it } from 'vitest';
import { formatRewardToast } from '../../../lib/marketReward';

describe('formatRewardToast', () => {
  it('returns coin copy for an enroll grant', () => {
    const t = (k: string, o?: Record<string, unknown>) => `${k} ${JSON.stringify(o ?? {})}`;
    const msg = formatRewardToast(t as never, { coins: 25, badge_name: null, badge_icon: null }, 'France');
    expect(msg).toContain('reward.enroll');
    expect(msg).toContain('25');
  });
  it('returns completion copy when a badge is present', () => {
    const t = (k: string, o?: Record<string, unknown>) => `${k} ${JSON.stringify(o ?? {})}`;
    const msg = formatRewardToast(t as never, { coins: 250, badge_name: 'Market Mastered: United Kingdom', badge_icon: '🇬🇧' }, 'United Kingdom');
    expect(msg).toContain('reward.completion');
  });
  it('returns null when nothing granted', () => {
    const t = (k: string) => k;
    expect(formatRewardToast(t as never, { coins: 0, badge_name: null, badge_icon: null }, 'France')).toBeNull();
  });
});
