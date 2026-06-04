import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { parentApi } from '@/api/parent';
import { parentAuthApi } from '@/api/parentAuth';
import { socialIdToken } from '@/lib/socialLogin';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ParentLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [touched, setTouched] = useState(false);
  const [socialError, setSocialError] = useState<string | null>(null);
  const [socialPending, setSocialPending] = useState<'apple' | 'google' | null>(null);
  const valid = EMAIL_RE.test(email);
  const showError = touched && !valid;

  const submit = useMutation({
    mutationFn: () => parentApi.requestMagicLink(email),
  });

  async function handleSocial(provider: 'apple' | 'google') {
    setSocialError(null);
    setSocialPending(provider);
    try {
      const { idToken, nonce } = await socialIdToken(provider);
      await parentAuthApi.oauthSignIn(provider, idToken, nonce);
      navigate('/parent');
    } catch {
      setSocialError(
        "We couldn't sign you in with that account. Ask your child to sign up with your email first, or use the email link below.",
      );
    } finally {
      setSocialPending(null);
    }
  }

  if (submit.isSuccess) {
    return (
      <AuthPage title="Check your inbox">
        <p className="text-sm text-muted-foreground">
          If an InvestiKid account is linked to {email}, we've sent a sign-in link.
          The link will expire in 15 minutes.
        </p>
      </AuthPage>
    );
  }

  return (
    <AuthPage title="Parents' sign-in" subtitle="Manage your child's account.">
      <p className="text-sm text-muted-foreground">
        Enter the email address you used when your child signed up.
      </p>

      {/* Social login buttons */}
      <div className="mt-6 space-y-3">
        <Button
          type="button"
          variant="outline"
          className="w-full text-base"
          disabled={socialPending !== null}
          onClick={() => handleSocial('apple')}
        >
          {socialPending === 'apple' ? 'Signing in…' : 'Continue with Apple'}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="w-full text-base"
          disabled={socialPending !== null}
          onClick={() => handleSocial('google')}
        >
          {socialPending === 'google' ? 'Signing in…' : 'Continue with Google'}
        </Button>
      </div>

      {socialError && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {socialError}
        </p>
      )}

      {/* Divider */}
      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-border" aria-hidden="true" />
        <span className="text-xs text-muted-foreground">or</span>
        <div className="h-px flex-1 bg-border" aria-hidden="true" />
      </div>

      {/* Magic-link form */}
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          setTouched(true);
          if (valid) submit.mutate();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email" type="email" autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={showError}
          />
          {showError && <p className="text-xs text-destructive">Enter a valid email address.</p>}
        </div>
        <Button type="submit" disabled={submit.isPending} className="w-full">
          {submit.isPending ? 'Sending…' : 'Send sign-in link'}
        </Button>
      </form>
    </AuthPage>
  );
}
