import { Link } from 'react-router-dom';

// Public, no-login page satisfying the App Store / Google Play account-deletion
// requirement: a reachable URL explaining how to delete an account + its data.
export default function DeleteAccount() {
  return (
    <main className="mx-auto max-w-2xl space-y-5 p-6">
      <h1 className="text-2xl font-semibold">Delete your InvestiKid account</h1>
      <p className="text-muted-foreground">
        This page explains how to delete an InvestiKid account and the personal data linked to it.
      </p>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Delete from within the app</h2>
        <p>
          Sign in at{' '}
          <a className="underline" href="https://app.investikid.ai">app.investikid.ai</a>, open the{' '}
          <strong>Parent dashboard</strong>, and use <strong>Delete account</strong>. You confirm by
          entering the account email address. The account is deactivated immediately.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Can&rsquo;t sign in?</h2>
        <p>
          Email{' '}
          <a className="underline" href="mailto:privacy@investikid.ai">privacy@investikid.ai</a> from the
          email address on the account (or the parent/guardian email linked to a child&rsquo;s account) and
          ask us to delete it. We will verify your request and process it.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">What is deleted</h2>
        <p>
          We permanently erase the personal data tied to the account — username, email address,
          parent/guardian email, password, learning progress and topic choices, and any messages sent to
          the in-app coach. The account is deactivated straight away and this personal data is permanently
          removed within <strong>30 days</strong>.
        </p>
        <p>
          A small amount of non-identifying information (such as date of birth, country, and currency) may be
          kept in anonymised form for age-verification audit records and aggregate statistics. Once the
          identifying details above are removed, this information can no longer be linked back to you.
        </p>
      </section>

      <p className="text-sm text-muted-foreground">
        See our <Link to="/privacy" className="underline">Privacy Notice</Link> for more about how we
        handle your data.
      </p>
    </main>
  );
}
