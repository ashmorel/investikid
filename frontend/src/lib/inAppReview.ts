// B5 — fire the native OS in-app-review prompt at a delight moment, gated.
import { InAppReview } from '@capacitor-community/in-app-review';
import { isNativeApp } from './platform';
import { shouldAskForReview, recordReviewAsked } from './inAppReviewCooldown';

/** The delight moment that triggered the ask (kept for call-site clarity / future analytics). */
export type ReviewSignal = 'streak' | 'mastery';

/**
 * Ask for an app-store review IF the moment is right. Native-only, cooldown-gated, and
 * never throws into the calling flow (a lesson-completion handler).
 *
 * The native prompt is a no-op on web. The OS itself throttles how often the real dialog
 * shows; we only decide *when* it's polite to ask (a streak milestone or a level mastery).
 */
export async function maybeRequestReview(_signal: ReviewSignal): Promise<void> {
  if (!isNativeApp()) return;
  if (!shouldAskForReview()) return;
  try {
    await InAppReview.requestReview();
    recordReviewAsked();
  } catch {
    // Never let a review prompt failure surface in the lesson flow.
  }
}
