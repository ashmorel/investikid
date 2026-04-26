export type ChildStatusInput = {
  is_active: boolean;
  parent_consent_given_at: string | null;
  consent_declined_at: string | null;
  deleted_at: string | null;
};

export type ChildStatus = 'active' | 'pending' | 'frozen' | 'declined' | 'deleted';

export function childStatus(c: ChildStatusInput): ChildStatus {
  if (c.deleted_at) return 'deleted';
  if (c.consent_declined_at) return 'declined';
  if (!c.parent_consent_given_at) return 'pending';
  return c.is_active ? 'active' : 'frozen';
}

export function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return iso.slice(0, 10);
}
