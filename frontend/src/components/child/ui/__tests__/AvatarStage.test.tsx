import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { AvatarStage } from '../AvatarStage';

describe('AvatarStage', () => {
  it('renders with role="img" and the supplied aria-label', () => {
    const label = 'Penny wearing sky skin, crown, in outer space';
    const { getByRole } = render(
      <AvatarStage background="bg_space" skin="skin_sky" accessories={['crown']} label={label} />,
    );
    expect(getByRole('img', { name: label })).toBeTruthy();
  });

  it('renders a Penny SVG inside the stage', () => {
    const { container } = render(
      <AvatarStage background="bg_space" skin="skin_sky" accessories={['crown']} label="test" />,
    );
    const svgs = container.querySelectorAll('svg');
    // At least two SVGs: background scene + Penny
    expect(svgs.length).toBeGreaterThanOrEqual(2);
  });

  it('renders the background scene aria-hidden with the space fill colour', () => {
    const { container } = render(
      <AvatarStage background="bg_space" skin="skin_sky" accessories={['crown']} label="test" />,
    );
    // The background svg wrapper is aria-hidden
    const bgSvg = container.querySelector('svg[aria-hidden="true"][viewBox="0 0 100 100"]');
    expect(bgSvg).toBeTruthy();
    // The space bg rect fill is present
    const rects = bgSvg!.querySelectorAll('rect');
    const fills = Array.from(rects).map((r) => r.getAttribute('fill'));
    expect(fills).toContain('#1e1b4b');
  });

  it('skips the background scene when background is null', () => {
    const { container } = render(
      <AvatarStage background={null} skin="skin_sky" label="Penny, no background" />,
    );
    // No background SVG with viewBox 0 0 100 100
    const bgSvg = container.querySelector('svg[viewBox="0 0 100 100"]');
    expect(bgSvg).toBeNull();
    // But Penny still renders
    const pennySvg = container.querySelector('svg[viewBox="0 0 56 56"]');
    expect(pennySvg).toBeTruthy();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      <AvatarStage
        background="bg_space"
        skin="skin_sky"
        accessories={['crown']}
        label="Penny wearing sky skin, crown, in outer space"
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
