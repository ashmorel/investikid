import type { ReactNode } from 'react';

/**
 * Quiet uppercase zone label used to give the parent dashboard landmarks
 * (mirrors the child Home "zones" pattern). Rendered as an h2 — the page
 * keeps a single sr-only h1, so heading order stays valid.
 */
export function ParentZoneHeading({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-2 px-1 text-xs font-bold uppercase tracking-wider text-muted-foreground">
      {children}
    </h2>
  );
}

/**
 * A labelled dashboard zone: a heading plus a stack of cards. The child
 * cards each manage their own outer margins for standalone use, so we
 * neutralise those here and let `space-y` own the rhythm inside a zone.
 */
export function ParentSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <ParentZoneHeading>{title}</ParentZoneHeading>
      <div className="space-y-3 [&>*]:mt-0! [&>*]:mb-0!">{children}</div>
    </section>
  );
}
