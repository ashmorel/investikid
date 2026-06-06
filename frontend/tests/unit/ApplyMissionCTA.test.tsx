import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ApplyMissionCTA } from '@/components/child/lesson/ApplyMissionCTA';

const mission = { id: 'm1', lesson_id: 'l1', mission_type: 'first_buy',
  title: 'Buy your first share', prompt: 'Now try it for real!', params_json: {} };

describe('ApplyMissionCTA', () => {
  it('renders prompt and links into the simulator primed for the mission', () => {
    render(<MemoryRouter><ApplyMissionCTA mission={mission} /></MemoryRouter>);
    expect(screen.getByText(/now try it for real/i)).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /try it in the simulator/i });
    expect(link).toHaveAttribute('href', '/simulator?mission=m1');
  });
});
