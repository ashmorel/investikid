import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { ChartDescription } from '@/components/a11y/ChartDescription';

describe('ChartDescription', () => {
  it('renders summary and a hidden data table', () => {
    render(
      <ChartDescription
        summary="Portfolio rose from £100 to £120 over 4 days."
        columns={['Date', 'Value']}
        rows={[
          ['Mon', '100'],
          ['Tue', '105'],
          ['Wed', '115'],
          ['Thu', '120'],
        ]}
      />,
    );
    expect(screen.getByText(/Portfolio rose/)).toBeInTheDocument();
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
    // 1 header row + 4 data rows
    expect(screen.getAllByRole('row')).toHaveLength(5);
  });

  it('is axe-clean', async () => {
    const { container } = render(
      <ChartDescription summary="x" columns={['A']} rows={[['1']]} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
