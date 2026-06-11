/**
 * Haptic feedback wrapper (juice pack, spec B). Native-only — silent no-op
 * on web/jsdom. `@capacitor/haptics` is dynamically imported so web bundles
 * don't pay for it. Requires `npx cap sync ios` + Xcode rebuild on device.
 */
import { isNativeApp } from '@/lib/platform';

export type HapticKind = 'success' | 'warning' | 'medium' | 'heavy';

export async function haptic(kind: HapticKind): Promise<void> {
  if (!isNativeApp()) return;
  try {
    const { Haptics, NotificationType, ImpactStyle } = await import('@capacitor/haptics');
    switch (kind) {
      case 'success':
        await Haptics.notification({ type: NotificationType.Success });
        break;
      case 'warning':
        await Haptics.notification({ type: NotificationType.Warning });
        break;
      case 'medium':
        await Haptics.impact({ style: ImpactStyle.Medium });
        break;
      case 'heavy':
        await Haptics.impact({ style: ImpactStyle.Heavy });
        break;
    }
  } catch {
    // Haptics are decorative — never let them throw.
  }
}
