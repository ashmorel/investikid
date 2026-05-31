import { Link } from 'react-router-dom';
import { PrivacyNotice } from '@/components/PrivacyNotice';

export default function Privacy() {
  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="text-2xl font-semibold">Privacy Notice</h1>
      <PrivacyNotice />
      <p className="mt-8 text-sm text-muted-foreground">
        <Link to="/signup" className="underline">Back to sign up</Link>
        {' · '}
        <Link to="/login" className="underline">Sign in</Link>
      </p>
    </main>
  );
}
