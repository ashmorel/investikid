import { cloneElement, useId, type ReactElement } from 'react';
import { Label } from '@/components/ui/label';

type ControlProps = {
  id?: string;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
};

type Props = {
  id: string;
  label: string;
  error?: string | null;
  hint?: string;
  children: ReactElement<ControlProps>;
};

export function Field({ id, label, error, hint, children }: Props) {
  const errorId = useId();
  const hintId = useId();
  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ') ||
    undefined;

  const control = cloneElement(children, {
    id,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy,
  });

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {control}
      {hint && (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
