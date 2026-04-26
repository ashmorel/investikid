import { describe, it, expect } from 'vitest';
import { childStatus, formatDate } from '@/lib/format';

describe('childStatus', () => {
  it('returns deleted when deleted_at set', () => {
    expect(childStatus({
      is_active: false, parent_consent_given_at: '2026-01-01T00:00:00Z',
      consent_declined_at: null, deleted_at: '2026-02-01T00:00:00Z',
    })).toBe('deleted');
  });

  it('returns declined when consent_declined_at set', () => {
    expect(childStatus({
      is_active: false, parent_consent_given_at: null,
      consent_declined_at: '2026-01-01T00:00:00Z', deleted_at: null,
    })).toBe('declined');
  });

  it('returns pending when no consent decision', () => {
    expect(childStatus({
      is_active: false, parent_consent_given_at: null,
      consent_declined_at: null, deleted_at: null,
    })).toBe('pending');
  });

  it('returns frozen when consent given but inactive', () => {
    expect(childStatus({
      is_active: false, parent_consent_given_at: '2026-01-01T00:00:00Z',
      consent_declined_at: null, deleted_at: null,
    })).toBe('frozen');
  });

  it('returns active when consent given and is_active', () => {
    expect(childStatus({
      is_active: true, parent_consent_given_at: '2026-01-01T00:00:00Z',
      consent_declined_at: null, deleted_at: null,
    })).toBe('active');
  });
});

describe('formatDate', () => {
  it('returns ISO date portion for valid input', () => {
    expect(formatDate('2026-04-26T10:11:12Z')).toMatch(/^2026-04-26/);
  });
  it('returns dash for null', () => {
    expect(formatDate(null)).toBe('—');
  });
});
