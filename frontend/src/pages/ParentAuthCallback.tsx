import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { parentApi } from '@/api/parent';
import { ApiError } from '@/api/client';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Button } from '@/components/ui/button';

type State = 'pending' | 'gone' | 'error';

export default function ParentAuthCallback() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const navigate = useNavigate();
  const [state, setState] = useState<State>('pending');

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- setting 'gone' synchronously when token is missing avoids an unnecessary async round-trip
    if (!token) { setState('gone'); return; }
    parentApi.magicCallback(token)
      .then(() => navigate('/parent', { replace: true }))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 410) setState('gone');
        else setState('error');
      });
  }, [token, navigate]);

  if (state === 'pending') {
    return <main className="mx-auto max-w-md p-6"><p>Signing you in…</p></main>;
  }

  return (
    <main className="mx-auto max-w-md p-6">
      <ErrorBanner
        title={state === 'gone' ? 'Sign-in link expired' : 'Could not sign you in'}
        message={
          state === 'gone'
            ? 'This link is invalid, expired, or already used.'
            : 'Please try again in a moment.'
        }
        action={
          <Button asChild variant="outline">
            <Link to="/parent/login">Request a new link</Link>
          </Button>
        }
      />
    </main>
  );
}
