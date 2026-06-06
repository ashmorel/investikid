import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MissionBanner } from '@/components/child/simulator/MissionBanner';

const mission = { id: 'm1', lesson_id: 'l1', mission_type: 'diversify',
  title: 'Hold 3 different stocks', prompt: 'Spread your money out', params_json: { n: 3 } };

describe('MissionBanner', () => {
  it('shows the active mission goal', () => {
    render(<MissionBanner mission={mission} />);
    expect(screen.getByText(/hold 3 different stocks/i)).toBeInTheDocument();
    expect(screen.getByText(/spread your money out/i)).toBeInTheDocument();
  });

  it('returns nothing when there is no mission', () => {
    const { container } = render(<MissionBanner mission={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
