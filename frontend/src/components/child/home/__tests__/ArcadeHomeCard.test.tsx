import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import ArcadeHomeCard from '../ArcadeHomeCard';

describe('ArcadeHomeCard', () => {
  it('links to the arcade hub and is accessible', async () => {
    const { container } = render(<MemoryRouter><ArcadeHomeCard /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /arcade/i })).toHaveAttribute('href', '/arcade');
    expect(await axe(container)).toHaveNoViolations();
  });
});
