import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { OfflineNotice } from '../OfflineNotice';

describe('OfflineNotice', () => {
  it('renders the friendly offline message as a status region', () => {
    render(<OfflineNotice />);
    const notice = screen.getByRole('status');
    expect(notice).toHaveTextContent(/you're offline — live prices need the internet/i);
    expect(notice).toHaveTextContent(/your lessons still work/i);
  });

  it('has no axe violations', async () => {
    const { container } = render(<OfflineNotice />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
