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
import { maybeRequestReview } from '../inAppReview';

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
