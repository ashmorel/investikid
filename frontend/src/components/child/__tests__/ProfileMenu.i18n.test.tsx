import { describe, expect, it } from 'vitest';
import en from '../../../locales/en/settings.json';

// Guards that representative strings live in the catalog, not the component.
describe('ProfileMenu i18n catalog', () => {
  it('contains the extracted preference strings', () => {
    expect(en).toMatchObject({
      sounds: { label: 'Sounds' },
      dailyGoal: { legend: 'Daily goal' },
    });
  });
});
