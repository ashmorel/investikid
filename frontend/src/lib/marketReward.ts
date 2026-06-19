import type { TFunction } from 'i18next';
import type { RewardGrant } from '../api/market';

/** Build a celebratory toast string for a reward grant, or null if nothing was granted. */
export function formatRewardToast(t: TFunction, reward: RewardGrant | undefined, marketName: string): string | null {
  if (!reward || (reward.coins === 0 && !reward.badge_name)) return null;
  if (reward.badge_name) {
    return t('reward.completion', { coins: reward.coins, market: marketName });
  }
  return t('reward.enroll', { coins: reward.coins, market: marketName });
}
