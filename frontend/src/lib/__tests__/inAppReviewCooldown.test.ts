import { describe, it, expect, beforeEach } from 'vitest';
import {
  markSessionSeen,
  shouldAskForReview,
  recordReviewAsked,
  COOLDOWN_MS,
} from '../inAppReviewCooldown';

beforeEach(() => {
  localStorage.clear();
});

describe('inAppReviewCooldown', () => {
  it('never asks in the very first session (boot count < 2)', () => {
    markSessionSeen(); // first boot
    expect(shouldAskForReview()).toBe(false);
  });

  it('asks once a second session has started and it has never been asked', () => {
    markSessionSeen(); // boot 1
    markSessionSeen(); // boot 2 (a later app open)
    expect(shouldAskForReview()).toBe(true);
  });

  it('does not ask again within the cooldown window', () => {
    markSessionSeen();
    markSessionSeen();
    const t0 = 1_000_000_000_000;
    recordReviewAsked(t0);
    expect(shouldAskForReview(t0 + COOLDOWN_MS - 1)).toBe(false);
  });

  it('asks again after the cooldown window elapses', () => {
    markSessionSeen();
    markSessionSeen();
    const t0 = 1_000_000_000_000;
    recordReviewAsked(t0);
    expect(shouldAskForReview(t0 + COOLDOWN_MS)).toBe(true);
  });

  it('recordReviewAsked persists the timestamp', () => {
    markSessionSeen();
    markSessionSeen();
    recordReviewAsked(1234567890);
    // a fresh read (no in-memory state) still sees the cooldown
    expect(shouldAskForReview(1234567890 + 1)).toBe(false);
  });
});
