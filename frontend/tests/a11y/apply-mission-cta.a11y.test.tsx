import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { ApplyMissionCTA } from '@/components/child/lesson/ApplyMissionCTA';

describe('a11y: ApplyMissionCTA', () => {
  it('has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter><ApplyMissionCTA mission={{ id: 'm1', lesson_id: 'l1', mission_type: 'first_buy',
        title: 'Buy your first share', prompt: 'Try it!', params_json: {} }} /></MemoryRouter>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
