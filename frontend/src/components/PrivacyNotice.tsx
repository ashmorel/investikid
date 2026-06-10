import { PRIVACY_NOTICE_VERSION } from '@/api/auth';

/**
 * The privacy notice body — shared between the standalone /privacy page
 * and the modal shown during signup (so the content lives in one place).
 */
export function PrivacyNotice() {
  return (
    <div>
      <p className="text-sm text-muted-foreground">
        Version {PRIVACY_NOTICE_VERSION} · Written for learners aged 8 and above
      </p>

      <p className="mt-4 text-sm">
        When you sign up to InvestiKid, we show you this notice and record that you (or your parent
        or guardian) agreed to it. If we make important changes, we will show you the updated
        notice and ask you to agree again before you can keep using the app.
      </p>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">What is InvestiKid?</h2>
        <p className="mt-2 text-sm">
          InvestiKid is a learning app that teaches you about money — how to save it, how to spend
          it wisely, and how the world of investing works. To do that, we need to know a few things
          about you so the app works properly and keeps you safe.
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">What information do we collect?</h2>
        <p className="mt-2 text-sm">When you join, we collect:</p>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>Your username</strong> — the name you use to log in. It does not have to be your real name.</li>
          <li><strong>Your date of birth</strong> — so we know your age and can give you the right level of protection.</li>
          <li><strong>Your country</strong> — so we know which rules apply to your data and which currency to show you.</li>
          <li><strong>A password</strong> — stored in a scrambled form so no one can read it, not even us.</li>
        </ul>
        <p className="mt-3 text-sm">We also collect:</p>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>Your email address</strong> — only if you are old enough to have one under the rules in your country.</li>
          <li><strong>A parent or guardian's email address</strong> — if you are below the age of digital consent, we ask for their permission first.</li>
          <li><strong>Your learning progress</strong> — lessons completed, XP earned, level, and streak count.</li>
          <li><strong>Which topics you are learning about</strong> — so we can show you the right lessons.</li>
        </ul>
        <p className="mt-3 text-sm">We do <strong>not</strong> collect your home address, phone number, photo, or information about your family's finances.</p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Why do we collect it?</h2>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>Username and password</strong> — so you can log in safely.</li>
          <li><strong>Date of birth</strong> — to check your age and keep you safe.</li>
          <li><strong>Country</strong> — to follow the right rules for your country.</li>
          <li><strong>Parent or guardian email</strong> — to get their permission if you are young.</li>
          <li><strong>Learning progress</strong> — so the app remembers what you have done.</li>
          <li><strong>Topic choice</strong> — to show you the right lessons.</li>
          <li><strong>Your email (if given)</strong> — to send you account messages.</li>
        </ul>
        <p className="mt-3 text-sm">
          We only use your information to run the app and keep it safe. We do not use it to sell
          you things or to follow you around the internet.
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Who can see your information?</h2>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>You</strong> — you can always see your own information inside the app.</li>
          <li><strong>Your parent or guardian</strong> — if they gave permission for your account, they can see your progress and ask for a copy of your data.</li>
          <li><strong>The InvestiKid team</strong> — to keep the app running, fix problems, and make sure it is safe. The team is not allowed to share your information with anyone else.</li>
        </ul>
        <p className="mt-3 text-sm">
          We do <strong>not</strong> share your personal information with advertisers, data brokers,
          or any other company.
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Lesson videos (YouTube)</h2>
        <p className="mt-2 text-sm">
          Some lessons include educational videos embedded from YouTube. When a video loads,
          YouTube (a Google service) may receive technical data — such as device and IP
          information — so it can play the video. We use YouTube's privacy-enhanced mode
          (<strong>youtube-nocookie.com</strong>), which does not set tracking cookies unless a
          video is actually played. We do <strong>not</strong> share your child's account
          details with YouTube. Google handles this technical data under its own privacy policy.
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">How long do we keep your information?</h2>
        <p className="mt-2 text-sm">
          We keep your information for as long as you have an account with us.
        </p>
        <p className="mt-2 text-sm">If you or your parent or guardian asks us to delete your account:</p>
        <ol className="mt-2 list-decimal pl-5 text-sm space-y-1">
          <li>We close the account straight away. You will not be able to log in.</li>
          <li>After 30 days, we delete most of your personal information. We keep your year of birth and country briefly — without your name or email, this cannot identify you.</li>
          <li>We keep a record of when you joined and when you asked us to delete your account, because the law requires it.</li>
        </ol>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Your choices</h2>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>Personalised recommendations</strong> — switched <strong>off</strong> by default. You can turn it on in account settings.</li>
          <li><strong>Marketing messages</strong> — switched <strong>off</strong> by default. You can change this in account settings.</li>
          <li><strong>Delete your account</strong> — you or your parent or guardian can ask at any time.</li>
          <li><strong>See your data</strong> — you can ask for a copy of all the information we hold about you.</li>
          <li><strong>Fix your information</strong> — if something is wrong, you can update it in your profile settings.</li>
        </ul>
        <p className="mt-3 text-sm text-muted-foreground">
          If you are below the age limit in your country, your parent or guardian manages these
          choices for you — to make sure a grown-up is looking out for you.
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Contact us</h2>
        <p className="mt-2 text-sm">
          If you have a question about your information, or want to ask for a copy of your data or
          delete your account, please contact us at{' '}
          <strong>privacy@invest-ed.app</strong>. We will respond within 30 days.
        </p>
        <p className="mt-2 text-sm">
          If you are not happy with how we have handled your information, you have the right to
          complain to the data protection authority in your country — for example, the Information
          Commissioner's Office (ICO) in the UK.
        </p>
      </section>
    </div>
  );
}
