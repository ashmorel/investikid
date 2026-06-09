import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { Lightbulb } from 'lucide-react';
import { SectionCard } from '../SectionCard';

describe('SectionCard', () => {
  it('renders the title, an icon, and a count pill', () => {
    render(<SectionCard title="My Section" icon={Lightbulb} count={7}><p>Body</p></SectionCard>);
    expect(screen.getByRole('heading', { name: /my section/i })).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('Body')).toBeInTheDocument();
  });

  it('non-collapsible: no button, content always visible', () => {
    render(<SectionCard title="Static"><p>Always</p></SectionCard>);
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByText('Always')).toBeVisible();
  });

  it('collapsible defaultOpen: content shown, toggles closed', async () => {
    render(<SectionCard title="Tips" collapsible defaultOpen><p>Inside</p></SectionCard>);
    const btn = screen.getByRole('button', { name: /tips/i });
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Inside')).toBeInTheDocument();
    await userEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Inside')).toBeNull();
  });

  it('collapsible defaultOpen=false: content hidden until expanded', async () => {
    render(<SectionCard title="News" collapsible defaultOpen={false}><p>Hidden</p></SectionCard>);
    const btn = screen.getByRole('button', { name: /news/i });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Hidden')).toBeNull();
    await userEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Hidden')).toBeInTheDocument();
  });

  it('collapsible header controls the content region via aria-controls', async () => {
    render(<SectionCard title="Region" collapsible defaultOpen><p>RegionBody</p></SectionCard>);
    const btn = screen.getByRole('button', { name: /region/i });
    const controls = btn.getAttribute('aria-controls');
    expect(controls).toBeTruthy();
    expect(document.getElementById(controls as string)).toContainHTML('RegionBody');
  });

  it('has no axe violations (open and collapsed)', async () => {
    const open = render(<SectionCard title="A" collapsible defaultOpen><p>x</p></SectionCard>);
    expect(await axe(open.container)).toHaveNoViolations();
    const closed = render(<SectionCard title="B" collapsible defaultOpen={false}><p>y</p></SectionCard>);
    expect(await axe(closed.container)).toHaveNoViolations();
  });
});
