import type { HTMLAttributes, ReactNode } from 'react';

export function VisuallyHidden({
  children,
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { children: ReactNode }) {
  return (
    <span {...rest} className={`sr-only ${rest.className ?? ''}`}>
      {children}
    </span>
  );
}
