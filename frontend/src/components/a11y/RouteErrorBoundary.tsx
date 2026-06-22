import { Component, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * Catches render errors from the routed page so a single page crash no longer
 * unmounts the whole app (which left the user with a blank screen and NO way
 * back — there was previously no error boundary anywhere). Placed INSIDE the
 * Shell, around the routed `<Outlet />`, so the persistent chrome (TopNav +
 * BottomTabBar) stays mounted and usable; only the page content is replaced by
 * the fallback. Because the Shell re-keys the page wrapper by route, navigating
 * to another tab remounts this boundary and clears the error automatically.
 */
function RouteErrorFallback() {
  const { t } = useTranslation('child');
  return (
    <div role="alert" className="mx-auto max-w-xl px-4 py-12 text-center">
      <p className="text-5xl" aria-hidden="true">🛟</p>
      <h1 className="mt-4 text-xl font-extrabold text-gray-900">{t('routeError.title')}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t('routeError.body')}</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="mt-6 min-h-[44px] rounded-full bg-brand-gradient px-6 py-2.5 text-sm font-bold text-white shadow"
      >
        {t('routeError.reload')}
      </button>
    </div>
  );
}

type Props = { children: ReactNode };
type State = { hasError: boolean };

export class RouteErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown, info: unknown) {
    // Surface to the console so the underlying crash stays diagnosable even
    // though the user sees a friendly fallback instead of a blank screen.
    console.error('Route render error:', error, info);
  }

  render() {
    if (this.state.hasError) return <RouteErrorFallback />;
    return this.props.children;
  }
}
