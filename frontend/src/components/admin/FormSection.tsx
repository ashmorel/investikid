import type { ReactNode } from 'react';

/**
 * Groups a set of related form fields into a labelled card so dense admin
 * forms read as scannable sections instead of one long input stack. Title +
 * optional one-line helper, a divider, then the fields (a gap-4 column).
 */
export function FormSection({
  title,
  helper,
  children,
}: {
  title: string;
  helper?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-line bg-card p-5">
      <h3 className="text-base font-extrabold text-ink">{title}</h3>
      {helper && <p className="mt-0.5 text-xs text-muted-foreground">{helper}</p>}
      <div className="mt-3 flex flex-col gap-4 border-t border-brand-100 pt-4">{children}</div>
    </section>
  );
}
