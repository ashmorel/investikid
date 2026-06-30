import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@capacitor-community/in-app-review', () => ({
  InAppReview: { requestReview: vi.fn() },
}));
vi.mock('../platform', () => ({ isNativeApp: vi.fn() }));
vi.mock('../inAppReviewCooldown', () => ({
  shouldAskForReview: vi.fn(),
  recordReviewAsked: vi.fn(),
}));

import { InAppReview } from '@capacitor-community/in-app-review';
import { isNativeApp } from '../platform';
import { shouldAskForReview, recordReviewAsked } from '../inAppReviewCooldown';
import { maybeRequestReview, reviewSignalForCompletion } from '../inAppReview';

const requestReview = InAppReview.requestReview as unknown as ReturnType<typeof vi.fn>;
const mockIsNative = isNativeApp as unknown as ReturnType<typeof vi.fn>;
const mockShould = shouldAskForReview as unknown as ReturnType<typeof vi.fn>;
const mockRecord = recordReviewAsked as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
  requestReview.mockResolvedValue(undefined);
});

describe('maybeRequestReview', () => {
  it('prompts and records when native + cooldown allows', async () => {
    mockIsNative.mockReturnValue(true);
    mockShould.mockReturnValue(true);
    await maybeRequestReview('streak');
    expect(requestReview).toHaveBeenCalledTimes(1);
    expect(mockRecord).toHaveBeenCalledTimes(1);
  });

  it('never prompts on web', async () => {
    mockIsNative.mockReturnValue(false);
    mockShould.mockReturnValue(true);
    await maybeRequestReview('mastery');
    expect(requestReview).not.toHaveBeenCalled();
    expect(mockRecord).not.toHaveBeenCalled();
  });

  it('does not prompt while within cooldown / first session', async () => {
    mockIsNative.mockReturnValue(true);
    mockShould.mockReturnValue(false);
    await maybeRequestReview('streak');
    expect(requestReview).not.toHaveBeenCalled();
    expect(mockRecord).not.toHaveBeenCalled();
  });

  it('swallows a plugin error and does NOT burn the cooldown', async () => {
    mockIsNative.mockReturnValue(true);
    mockShould.mockReturnValue(true);
    requestReview.mockRejectedValue(new Error('no activity'));
    await expect(maybeRequestReview('streak')).resolves.toBeUndefined();
    expect(mockRecord).not.toHaveBeenCalled();
  });
});

describe('reviewSignalForCompletion', () => {
  const base = { already_completed: false };

  it('returns "streak" when a milestone was reached', () => {
    expect(reviewSignalForCompletion({ ...base, streak_milestone_reached: 7 })).toBe('streak');
  });

  it('returns "mastery" when a level was mastered and no streak milestone', () => {
    expect(reviewSignalForCompletion({ ...base, level_mastered: true })).toBe('mastery');
  });

  it('prefers streak over mastery when both fire', () => {
    expect(
      reviewSignalForCompletion({ ...base, streak_milestone_reached: 14, level_mastered: true }),
    ).toBe('streak');
  });

  it('returns null when neither signal is present', () => {
    expect(reviewSignalForCompletion({ ...base })).toBeNull();
    expect(reviewSignalForCompletion({ ...base, streak_milestone_reached: null })).toBeNull();
  });

  it('returns null on an already-completed replay even if flags are set', () => {
    expect(
      reviewSignalForCompletion({ already_completed: true, streak_milestone_reached: 7, level_mastered: true }),
    ).toBeNull();
  });
});
