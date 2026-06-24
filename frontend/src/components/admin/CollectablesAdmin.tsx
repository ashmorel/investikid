import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  usePool, useDrops, useScheduleDrop, useEditDrop, useUnscheduleDrop,
  UNLOCK_TYPES, RARITIES, type Drop, type Rarity, type UnlockType,
} from '@/api/adminCollectables';
import ConfirmDialog from '@/components/admin/ConfirmDialog';

function fromLocalInput(local: string): string {
  return new Date(local).toISOString();
}

function toLocalInput(iso: string | null | undefined): string {
  return iso ? iso.slice(0, 16) : '';
}

export default function CollectablesAdmin() {
  const { t } = useTranslation('admin');
  const { data: pool = [] } = usePool();
  const { data: drops = [] } = useDrops();
  const schedule = useScheduleDrop();
  const edit = useEditDrop();
  const unschedule = useUnscheduleDrop();

  const [itemId, setItemId] = useState('');
  const [rarity, setRarity] = useState<Rarity>('rare');
  const [unlockType, setUnlockType] = useState<UnlockType>('streak_days');
  const [threshold, setThreshold] = useState(5);
  const [from, setFrom] = useState('');
  const [until, setUntil] = useState('');

  const [confirm, setConfirm] = useState<{ kind: 'end' | 'unschedule'; drop: Drop } | null>(null);
  const [editing, setEditing] = useState<Drop | null>(null);

  function startEdit(drop: Drop) {
    setEditing(drop);
    setRarity(drop.rarity ?? 'rare');
    setUnlockType(drop.unlock_type ?? 'streak_days');
    setThreshold(drop.unlock_threshold ?? 5);
    setFrom(toLocalInput(drop.available_from));
    setUntil(toLocalInput(drop.available_until));
  }

  function cancelEdit() {
    setEditing(null);
    setItemId('');
    setRarity('rare');
    setUnlockType('streak_days');
    setThreshold(5);
    setFrom('');
    setUntil('');
  }

  async function onSchedule(e: React.FormEvent) {
    e.preventDefault();
    if (editing) {
      if (!from || !until) return;
      await edit.mutateAsync({
        itemId: editing.item_id,
        body: {
          rarity,
          unlock_type: unlockType,
          unlock_threshold: threshold,
          available_from: fromLocalInput(from),
          available_until: fromLocalInput(until),
        },
      });
      cancelEdit();
    } else {
      if (!itemId || !from || !until) return;
      await schedule.mutateAsync({
        item_id: itemId, rarity, unlock_type: unlockType, unlock_threshold: threshold,
        available_from: fromLocalInput(from), available_until: fromLocalInput(until),
      });
      setItemId(''); setFrom(''); setUntil('');
    }
  }

  return (
    <div className="max-w-3xl">
      <h2 className="mb-4 text-xl font-semibold text-ink">{t('collectables.title')}</h2>

      {/* Scheduled drops list */}
      <h3 className="mb-2 text-sm font-bold text-muted-foreground">{t('collectables.scheduledHeading')}</h3>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50 text-left">
              <th className="px-3 py-2">{t('collectables.colItem')}</th>
              <th className="px-3 py-2">{t('collectables.colRarity')}</th>
              <th className="px-3 py-2">{t('collectables.colUnlock')}</th>
              <th className="px-3 py-2">{t('collectables.colStatus')}</th>
              <th className="px-3 py-2">{t('collectables.colOwned')}</th>
              <th className="px-3 py-2"><span className="sr-only">{t('collectables.colActions')}</span></th>
            </tr>
          </thead>
          <tbody>
            {drops.map((d) => (
              <tr key={d.item_id} className="border-b last:border-b-0">
                <td className="px-3 py-2"><span aria-hidden="true">{d.emoji}</span> {d.name}</td>
                <td className="px-3 py-2">{d.rarity}</td>
                <td className="px-3 py-2">
                  {d.unlock_type ? t(`collectables.unlock.${d.unlock_type}`) : ''} ≥ {d.unlock_threshold}
                </td>
                <td className="px-3 py-2">{t(`collectables.status${d.status[0].toUpperCase()}${d.status.slice(1)}`)}</td>
                <td className="px-3 py-2">{d.owned_count}</td>
                <td className="px-3 py-2 text-right space-x-3">
                  {d.status === 'scheduled' && (
                    <>
                      <button type="button" className="text-sm font-bold text-brand-700"
                        onClick={() => startEdit(d)}>
                        {t('collectables.edit')}
                      </button>
                      <button type="button" className="text-sm font-bold text-brand-700"
                        onClick={() => setConfirm({ kind: 'unschedule', drop: d })}>
                        {t('collectables.unschedule')}
                      </button>
                    </>
                  )}
                  {d.status === 'live' && (
                    <button type="button" className="text-sm font-bold text-red-700"
                      onClick={() => setConfirm({ kind: 'end', drop: d })}>
                      {t('collectables.endEarly')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Schedule / Edit a drop */}
      <h3 className="mb-2 mt-8 text-sm font-bold text-muted-foreground">
        {editing ? t('collectables.editHeading') : t('collectables.scheduleHeading')}
      </h3>
      {!editing && pool.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('collectables.poolEmpty')}</p>
      ) : (
        <form onSubmit={onSchedule} className="flex max-w-lg flex-col gap-3">
          {editing ? (
            <p className="text-sm text-muted-foreground">
              <span aria-hidden="true">{editing.emoji}</span>{' '}
              {t('collectables.editingLabel', { name: editing.name })}
            </p>
          ) : (
            <label className="flex flex-col gap-1 text-sm">
              {t('collectables.poolItemLabel')}
              <select className="rounded border px-2 py-2 text-base" value={itemId}
                onChange={(e) => setItemId(e.target.value)} required>
                <option value="" disabled>—</option>
                {pool.map((p) => <option key={p.item_id} value={p.item_id}>{p.emoji} {p.name}</option>)}
              </select>
            </label>
          )}
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.rarityLabel')}
            <select className="rounded border px-2 py-2 text-base" value={rarity}
              onChange={(e) => setRarity(e.target.value as Rarity)}>
              {RARITIES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.unlockTypeLabel')}
            <select className="rounded border px-2 py-2 text-base" value={unlockType}
              onChange={(e) => setUnlockType(e.target.value as UnlockType)}>
              {UNLOCK_TYPES.map((u) => <option key={u} value={u}>{t(`collectables.unlock.${u}`)}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.thresholdLabel')}
            <input type="number" min={1} className="rounded border px-2 py-2 text-base" value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))} required />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.fromLabel')}
            <input type="datetime-local" className="rounded border px-2 py-2 text-base" value={from}
              onChange={(e) => setFrom(e.target.value)} required />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t('collectables.untilLabel')}
            <input type="datetime-local" className="rounded border px-2 py-2 text-base" value={until}
              onChange={(e) => setUntil(e.target.value)} required />
          </label>
          <div className="flex gap-3">
            <button type="submit" disabled={schedule.isPending || edit.isPending}
              className="min-h-[44px] rounded-xl bg-brand-600 px-4 font-bold text-white hover:bg-brand-700">
              {t('collectables.save')}
            </button>
            {editing && (
              <button type="button" onClick={cancelEdit}
                className="min-h-[44px] rounded-xl border px-4 font-bold hover:bg-muted">
                {t('collectables.cancelEdit')}
              </button>
            )}
          </div>
        </form>
      )}

      {confirm && (
        <ConfirmDialog
          open
          title={confirm.kind === 'end' ? t('collectables.endEarly') : t('collectables.unschedule')}
          message={
            (confirm.kind === 'end' ? t('collectables.confirmEndEarly') : t('collectables.confirmUnschedule')) +
            (confirm.drop.owned_count > 0 ? ' ' + t('collectables.ownedNote', { count: confirm.drop.owned_count }) : '')
          }
          onCancel={() => setConfirm(null)}
          onConfirm={async () => {
            if (confirm.kind === 'end') {
              await edit.mutateAsync({ itemId: confirm.drop.item_id, body: { available_until: new Date().toISOString() } });
            } else {
              await unschedule.mutateAsync(confirm.drop.item_id);
            }
            setConfirm(null);
          }}
        />
      )}
    </div>
  );
}


