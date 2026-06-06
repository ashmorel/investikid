import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MissionBanner } from '@/components/child/simulator/MissionBanner';

describe('a11y: MissionBanner', () => {
  it('has no axe violations', async () => {
    const { container } = render(<MissionBanner mission={{ id: 'm1', lesson_id: 'l1',
      mission_type: 'first_buy', title: 'Buy a share', prompt: 'Go!', params_json: {} }} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
