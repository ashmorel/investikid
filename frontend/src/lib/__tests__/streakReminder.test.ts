import { describe, it, expect } from 'vitest';
import { decideStreakReminder, ymdLocal } from '../streakReminder';
import { REMINDER } from '../reminderConfig';

const at = (h: number) => new Date(2026, 0, 15, h, 0, 0, 0);

describe('ymdLocal', () => {
  it('formats local YYYY-MM-DD', () => {
    expect(ymdLocal(new Date(2026, 0, 5, 9))).toBe('2026-01-05');
  });
});

describe('decideStreakReminder', () => {
  const base = { enabled: true, practicedToday: false, streakCount: 3 };
  it('cancels when disabled', () => {
    expect(decideStreakReminder({ ...base, enabled: false, now: at(9) })).toEqual({ action: 'cancel' });
  });
  it('cancels when no active streak', () => {
    expect(decideStreakReminder({ ...base, streakCount: 0, now: at(9) })).toEqual({ action: 'cancel' });
  });
  it('cancels when already practiced today', () => {
    expect(decideStreakReminder({ ...base, practicedToday: true, now: at(9) })).toEqual({ action: 'cancel' });
  });
  it('schedules at the primary hour in the morning', () => {
    const d = decideStreakReminder({ ...base, now: at(9) });
    expect(d.action).toBe('schedule');
    if (d.action === 'schedule') expect(d.at.getHours()).toBe(REMINDER.primaryHour);
  });
  it('falls back to the later hour in the evening', () => {
    const d = decideStreakReminder({ ...base, now: at(REMINDER.primaryHour + 1) });
    expect(d.action).toBe('schedule');
    if (d.action === 'schedule') expect(d.at.getHours()).toBe(REMINDER.fallbackHour);
  });
  it('cancels when it is too late at night', () => {
    expect(decideStreakReminder({ ...base, now: at(REMINDER.fallbackHour + 1) })).toEqual({ action: 'cancel' });
  });
});
