import { useQuery } from '@tanstack/react-query';
import { authApi, type Me } from '@/api/auth';
import { ApiError } from '@/api/client';
import { isNativeApp } from '@/lib/platform';

export function useChildSession() {
  return useQuery<Me | null>({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    // Native (WKWebView) can lag the session cookie set by /auth/login behind the
    // very next request, so the first /me after login 401s and the auth guard
    // bounces back to a blank login form ("first login fails, second works").
    // Briefly retry a native 401 to absorb that cookie-sync race. Web has no
    // such race (same-origin cookies), and isNativeApp() is false in tests, so
    // this changes nothing off-device.
    retry: (failureCount, error) =>
      isNativeApp() &&
      error instanceof ApiError &&
      error.status === 401 &&
      failureCount < 3,
    retryDelay: 200,
    staleTime: 5 * 60_000,
  });
}
