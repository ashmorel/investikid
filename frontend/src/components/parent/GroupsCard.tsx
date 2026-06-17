import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { parentApi, type ParentGroup } from '@/api/parent';
import { ApiError } from '@/api/client';
import { GROUP } from '@/lib/groupConfig';
import { useToast } from '@/hooks/use-toast';

type ChildLite = { user_id: string; username: string };

const GROUPS_KEY = ['parent-groups'];

function joinErrorMessage(err: unknown, t: (key: string) => string): string {
  const detail = err instanceof ApiError ? err.detail : '';
  if (/full/i.test(detail)) return t('groups.joinError.full');
  return t('groups.joinError.generic');
}

export function GroupsCard({ childrenList }: { childrenList: ChildLite[] }) {
  const { t } = useTranslation('parent');
  const qc = useQueryClient();
  const { toast } = useToast();
  const invalidate = () => qc.invalidateQueries({ queryKey: GROUPS_KEY });

  const groupsQuery = useQuery({ queryKey: GROUPS_KEY, queryFn: parentApi.listGroups });

  const [newName, setNewName] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [selectedChild, setSelectedChild] = useState(childrenList[0]?.user_id ?? '');

  const create = useMutation({
    mutationFn: () => parentApi.createGroup(newName.trim()),
    onSuccess: () => {
      setNewName('');
      invalidate();
    },
    onError: () =>
      toast({
        title: t('groups.toast.createErrorTitle'),
        description: t('groups.toast.createErrorDesc'),
        variant: 'destructive',
      }),
  });

  const join = useMutation({
    mutationFn: () => parentApi.joinGroup(joinCode.trim(), effectiveChild),
    onSuccess: () => {
      setJoinCode('');
      invalidate();
    },
  });

  const remove = useMutation({
    mutationFn: ({ groupId, childUserId }: { groupId: string; childUserId: string }) =>
      parentApi.removeGroupMember(groupId, childUserId),
    onSuccess: invalidate,
    onError: () =>
      toast({
        title: t('groups.toast.removeErrorTitle'),
        description: t('groups.toast.removeErrorDesc'),
        variant: 'destructive',
      }),
  });

  const destroy = useMutation({
    mutationFn: (groupId: string) => parentApi.deleteGroup(groupId),
    onSuccess: invalidate,
    onError: () =>
      toast({
        title: t('groups.toast.deleteErrorTitle'),
        description: t('groups.toast.deleteErrorDesc'),
        variant: 'destructive',
      }),
  });

  const copyCode = async (code: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(code);
      } catch {
        // ignore — copy is a convenience, the code is visible on screen
      }
    }
  };

  const groups = groupsQuery.data ?? [];

  // Children not yet a member of any group — eligible to be added.
  const memberIds = new Set(
    groups.flatMap((g) => (g.members ?? []).map((m) => m.child_user_id)),
  );
  const eligibleChildren = childrenList.filter((c) => !memberIds.has(c.user_id));
  const effectiveChild = eligibleChildren.some((c) => c.user_id === selectedChild)
    ? selectedChild
    : '';

  return (
    <section className="mt-6 rounded-2xl border border-brand-100 bg-card p-4 text-foreground">
      <h2 className="text-lg font-semibold">{t('groups.heading')}</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {t('groups.subheading')}
      </p>

      {/* Create group */}
      <form
        className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          if (newName.trim()) create.mutate();
        }}
      >
        <div className="flex-1">
          <label htmlFor="group-name" className="block text-sm font-medium">
            {t('groups.newGroupLabel')}
          </label>
          <input
            id="group-name"
            value={newName}
            maxLength={GROUP.maxNameLength}
            onChange={(e) => setNewName(e.target.value)}
            className="mt-1 flex h-11 w-full rounded-md border border-brand-100 bg-background px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
        <Button type="submit" disabled={!newName.trim() || create.isPending}>
          {create.isPending ? t('groups.creating') : t('groups.createGroup')}
        </Button>
      </form>

      {/* Group list */}
      {groupsQuery.isLoading && (
        <p className="mt-4 text-sm text-muted-foreground">{t('groups.loadingGroups')}</p>
      )}
      {!groupsQuery.isLoading && groups.length === 0 && (
        <p className="mt-4 text-sm text-muted-foreground">{t('groups.noGroups')}</p>
      )}
      {groups.length > 0 && (
        <ul className="mt-4 space-y-3">
          {groups.map((g: ParentGroup) => (
            <li key={g.id} className="rounded-xl border border-brand-100 p-3">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium">{g.name}</h3>
                {g.is_owner && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (window.confirm(t('groups.deleteConfirm', { name: g.name })))
                        destroy.mutate(g.id);
                    }}
                    disabled={destroy.isPending}
                  >
                    {t('groups.deleteGroup')}
                  </Button>
                )}
              </div>

              {g.is_owner && g.code && (
                <div className="mt-1 flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">{t('groups.code')}</span>
                  <span className="font-mono font-semibold">{g.code}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => g.code && copyCode(g.code)}
                    aria-label={t('groups.copyAriaLabel', { name: g.name })}
                  >
                    {t('groups.copy')}
                  </Button>
                </div>
              )}

              {(g.members ?? []).length > 0 && (
                <ul className="mt-2 space-y-1">
                  {(g.members ?? []).map((m) => (
                    <li key={m.child_user_id} className="flex items-center justify-between text-sm">
                      <span>{m.username}</span>
                      {/* eslint-disable i18next/no-literal-string -- decorative glyph, aria-label carries the accessible name */}
                      <button
                        type="button"
                        aria-label={t('groups.removeAriaLabel', { username: m.username })}
                        className="rounded px-2 py-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => {
                          if (window.confirm(t('groups.removeChildConfirm', { username: m.username, groupName: g.name })))
                            remove.mutate({ groupId: g.id, childUserId: m.child_user_id });
                        }}
                        disabled={remove.isPending}
                      >
                        ✕
                      </button>
                      {/* eslint-enable i18next/no-literal-string */}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Add a child to a group via code */}
      <form
        className="mt-6 border-t border-brand-100 pt-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (joinCode.trim() && effectiveChild) join.mutate();
        }}
      >
        <h3 className="text-sm font-semibold">{t('groups.addChildHeading')}</h3>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="join-code" className="block text-sm font-medium">
              {t('groups.joinCodeLabel')}
            </label>
            <input
              id="join-code"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              className="mt-1 flex h-11 w-full rounded-md border border-brand-100 bg-background px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
          <div className="flex-1">
            <label htmlFor="join-child" className="block text-sm font-medium">
              {t('groups.joinChildLabel')}
            </label>
            <select
              id="join-child"
              value={effectiveChild}
              onChange={(e) => setSelectedChild(e.target.value)}
              className="mt-1 flex h-11 w-full rounded-md border border-brand-100 bg-background px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="" disabled>
                {t('groups.joinChildPlaceholder')}
              </option>
              {eligibleChildren.map((c) => (
                <option key={c.user_id} value={c.user_id}>
                  {c.username}
                </option>
              ))}
            </select>
          </div>
          <Button
            type="submit"
            disabled={!joinCode.trim() || !effectiveChild || join.isPending}
          >
            {join.isPending ? t('groups.joining') : t('groups.join')}
          </Button>
        </div>
        {join.isError && (
          <p className="mt-2 text-sm text-danger-700" role="alert">
            {joinErrorMessage(join.error, t)}
          </p>
        )}
      </form>
    </section>
  );
}
