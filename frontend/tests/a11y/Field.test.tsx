import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { Field } from '@/components/a11y/Field';

describe('Field', () => {
  it('associates label, control, and error', () => {
    render(
      <Field id="email" label="Email" error="Required">
        <input id="email" />
      </Field>,
    );
    const input = screen.getByLabelText('Email');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    const describedBy = input.getAttribute('aria-describedby')!;
    expect(document.getElementById(describedBy)).toHaveTextContent('Required');
  });

  it('renders without error and is axe-clean', async () => {
    const { container } = render(
      <Field id="name" label="Name">
        <input id="name" />
      </Field>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
