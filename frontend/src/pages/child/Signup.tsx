import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { authApi, type RegisterBody, PRIVACY_NOTICE_VERSION } from '@/api/auth';
import { TOPIC_OPTIONS } from '@/api/content';
import { ApiError } from '@/api/client';
import { ageInYears, needsParentalConsent } from '@/lib/consent';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { PrivacyNotice } from '@/components/PrivacyNotice';

const COUNTRIES: ReadonlyArray<{ code: string; name: string; currency: string }> = [
  { code: 'GB', name: 'United Kingdom', currency: 'GBP' },
  { code: 'US', name: 'United States', currency: 'USD' },
  { code: 'IE', name: 'Ireland', currency: 'EUR' },
  { code: 'NL', name: 'Netherlands', currency: 'EUR' },
  { code: 'DE', name: 'Germany', currency: 'EUR' },
  { code: 'LU', name: 'Luxembourg', currency: 'EUR' },
  { code: 'SK', name: 'Slovakia', currency: 'EUR' },
  { code: 'HR', name: 'Croatia', currency: 'EUR' },
  { code: 'HK', name: 'Hong Kong', currency: 'HKD' },
];

export default function Signup() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [step, setStep] = useState<1 | 2>(1);

  // Step 1
  const [dob, setDob] = useState('');
  const [country, setCountry] = useState('');

  // Step 2
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [parentEmail, setParentEmail] = useState('');
  const [currency, setCurrency] = useState('');
  const [topic, setTopic] = useState<string>('');
  const [fieldError, setFieldError] = useState<{ field: 'email' | 'username' | 'top'; msg: string } | null>(null);
  const [policyAccepted, setPolicyAccepted] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);

  const passwordsMatch = password === confirmPassword;
  const showMismatch = confirmPassword.length > 0 && !passwordsMatch;

  const today = useMemo(() => new Date(), []);
  const dobValid = !!dob && !Number.isNaN(Date.parse(dob));
  const age = dobValid ? ageInYears(new Date(dob), today) : null;
  const needsConsent = dobValid && country
    ? needsParentalConsent(new Date(dob), country, today)
    : null;

  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? '';
  const countryDefaultCurrency = COUNTRIES.find((c) => c.code === country)?.currency ?? '';

  function handleCountryChange(cc: string) {
    setCountry(cc);
    const def = COUNTRIES.find((c) => c.code === cc)?.currency;
    if (def && !currency) setCurrency(def);
  }

  const step1Valid = dobValid && !!country && age !== null && age >= 8;

  const submit = useMutation({
    mutationFn: async () => {
      const body: RegisterBody = {
        email, username, password, dob,
        country_code: country, currency_code: currency || countryDefaultCurrency,
        parent_email: needsConsent ? parentEmail : undefined,
        topic_path: topic === '' ? null : topic,
        policy_version_accepted: PRIVACY_NOTICE_VERSION,
      };
      // Over-threshold: backend register sets auth + csrf cookies directly.
      // Under-threshold: backend returns { status: 'pending_consent' } (no cookies).
      return await authApi.register(body);
    },
    onSuccess: async (resp) => {
      if (resp && typeof resp === 'object' && 'status' in resp && (resp as { status: string }).status === 'pending_consent') {
        navigate(`/pending-consent?email=${encodeURIComponent(email)}`, { replace: true });
        return;
      }
      await qc.invalidateQueries({ queryKey: ['me'] });
      navigate('/home', { replace: true });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        if (/email/i.test(err.detail)) setFieldError({ field: 'email', msg: err.detail });
        else if (/username/i.test(err.detail)) setFieldError({ field: 'username', msg: err.detail });
        else setFieldError({ field: 'top', msg: err.detail });
        return;
      }
      if (err instanceof ApiError) {
        setFieldError({ field: 'top', msg: err.detail });
        return;
      }
      setFieldError({ field: 'top', msg: 'Something went wrong. Please try again.' });
    },
  });

  if (step === 1) {
    return (
      <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
        <h1 className="text-2xl font-semibold">Create your account</h1>
        <p className="mt-1 text-sm text-muted-foreground">Step 1 of 2</p>
        <form
          className="mt-6 space-y-4"
          onSubmit={(e) => { e.preventDefault(); if (step1Valid) setStep(2); }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="dob">Date of birth</Label>
            <Input id="dob" type="date" required value={dob}
              onChange={(e) => setDob(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="country">Country</Label>
            <select id="country" required
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={country} onChange={(e) => handleCountryChange(e.target.value)}>
              <option value="">Select…</option>
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
          </div>
          {age !== null && age < 8 && (
            <p role="alert" className="text-sm text-destructive">
              You must be at least 8 years old to use Invest-Ed.
            </p>
          )}
          {step1Valid && needsConsent && (
            <p className="rounded-md border bg-muted/30 p-3 text-sm">
              You're <span className="font-medium">{age}</span> in {countryName} — your parent's
              email will be required to set up your account.
            </p>
          )}
          {step1Valid && !needsConsent && (
            <p className="rounded-md border bg-muted/30 p-3 text-sm">
              You're <span className="font-medium">{age}</span> in {countryName} — you can set up
              your own account.
            </p>
          )}
          <Button type="submit" disabled={!step1Valid} className="w-full">Next</Button>
        </form>
        <p className="mt-6 text-sm text-muted-foreground">
          Already have an account? <Link to="/login" className="underline">Sign in</Link>.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-semibold">Create your account</h1>
      <p className="mt-1 text-sm text-muted-foreground">Step 2 of 2</p>
      <form
        className="mt-6 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!passwordsMatch) {
            setConfirmPassword((v) => v); // keep value; error shown below
            return;
          }
          setFieldError(null);
          submit.mutate();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            aria-invalid={fieldError?.field === 'email'} />
          {fieldError?.field === 'email' &&
            <p className="text-xs text-destructive">{fieldError.msg}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="username">Username</Label>
          <Input id="username" required minLength={3} autoComplete="username"
            value={username} onChange={(e) => setUsername(e.target.value)}
            aria-invalid={fieldError?.field === 'username'} />
          {fieldError?.field === 'username' &&
            <p className="text-xs text-destructive">{fieldError.msg}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password (min 12 characters, must include letter + digit)</Label>
          <Input id="password" type="password" required minLength={12}
            autoComplete="new-password"
            value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirm_password">Confirm password</Label>
          <Input id="confirm_password" type="password" required
            autoComplete="new-password"
            value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
            aria-invalid={showMismatch} aria-describedby="confirm-password-error" />
          {showMismatch && (
            <p id="confirm-password-error" role="alert" className="text-xs text-destructive">
              Passwords don't match.
            </p>
          )}
        </div>
        {needsConsent && (
          <div className="space-y-1.5">
            <Label htmlFor="parent_email">Parent email</Label>
            <Input id="parent_email" type="email" required
              value={parentEmail} onChange={(e) => setParentEmail(e.target.value)} />
            <p className="text-xs text-muted-foreground">
              We'll email your parent to approve your account.
            </p>
          </div>
        )}
        <div className="space-y-1.5">
          <Label htmlFor="currency">Currency</Label>
          <Input id="currency" required value={currency}
            onChange={(e) => setCurrency(e.target.value.toUpperCase())} maxLength={3} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="topic">Interest area</Label>
          <select id="topic"
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            value={topic} onChange={(e) => setTopic(e.target.value)}>
            {TOPIC_OPTIONS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        {fieldError?.field === 'top' && (
          <p role="alert" className="text-sm text-destructive">{fieldError.msg}</p>
        )}
        <label className="flex items-start gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={policyAccepted}
            onChange={(e) => setPolicyAccepted(e.target.checked)} className="mt-1" />
          <span>I (or my grown-up) have read the{' '}
            <button type="button" onClick={() => setPrivacyOpen(true)}
              className="underline text-amber-700">privacy notice</button>.</span>
        </label>
        <div className="flex gap-3">
          <Button type="button" variant="outline" onClick={() => setStep(1)}>Back</Button>
          <Button type="submit"
            disabled={submit.isPending || !policyAccepted || !passwordsMatch}
            className="flex-1">
            {submit.isPending ? 'Creating account…' : 'Create account'}
          </Button>
        </div>
      </form>

      <Dialog open={privacyOpen} onOpenChange={setPrivacyOpen}>
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Privacy Notice</DialogTitle>
            <DialogDescription>How Invest-Ed collects, uses, and protects your information.</DialogDescription>
          </DialogHeader>
          <PrivacyNotice />
        </DialogContent>
      </Dialog>
    </main>
  );
}
