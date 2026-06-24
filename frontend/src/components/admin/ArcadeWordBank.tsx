import { useState } from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  useArcadeWords,
  approveArcadeWord,
  rejectArcadeWord,
  suggestArcadeWords,
  type ArcadeWord,
} from '@/api/arcadeWordsAdmin';

type Status = 'pending' | 'approved' | 'rejected';

// ── Per-row component so each row manages its own editable fields ────────────
interface WordRowProps {
  word: ArcadeWord;
  onApprove: (id: string, edits?: { word?: string; definition?: string }) => void;
  onReject: (id: string) => void;
  approving: boolean;
  rejecting: boolean;
}

function WordRow({ word, onApprove, onReject, approving, rejecting }: WordRowProps) {
  const { t } = useTranslation('admin');
  const [editWord, setEditWord] = useState(word.word);
  const [editDef, setEditDef] = useState(word.definition);

  const isPending = word.status === 'pending';

  return (
    <li className="rounded-xl border border-line bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <div className="flex-1 space-y-2">
          {isPending ? (
            <>
              <div className="space-y-1">
                <label
                  htmlFor={`word-${word.id}`}
                  className="block text-xs font-medium text-ink"
                >
                  {t('arcadeWordBank.wordLabel')}
                </label>
                <input
                  id={`word-${word.id}`}
                  type="text"
                  value={editWord}
                  onChange={(e) => setEditWord(e.target.value)}
                  className="min-h-[44px] w-full rounded-md border border-line bg-background px-3 py-2 text-sm font-mono uppercase text-ink"
                />
              </div>
              <div className="space-y-1">
                <label
                  htmlFor={`def-${word.id}`}
                  className="block text-xs font-medium text-ink"
                >
                  {t('arcadeWordBank.definitionLabel')}
                </label>
                <input
                  id={`def-${word.id}`}
                  type="text"
                  value={editDef}
                  onChange={(e) => setEditDef(e.target.value)}
                  className="min-h-[44px] w-full rounded-md border border-line bg-background px-3 py-2 text-sm text-ink"
                />
              </div>
            </>
          ) : (
            <>
              <div className="font-mono text-sm font-semibold uppercase text-ink">
                {word.word}
              </div>
              <div className="text-sm text-muted-foreground">{word.definition}</div>
            </>
          )}
          <div className="text-xs text-muted-foreground">
            {t('arcadeWordBank.meta', {
              language: word.language,
              length: word.length,
              source: word.source,
              status: word.status,
            })}
          </div>
        </div>

        {isPending && (
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              disabled={approving || rejecting}
              onClick={() =>
                onApprove(word.id, {
                  word: editWord !== word.word ? editWord : undefined,
                  definition: editDef !== word.definition ? editDef : undefined,
                })
              }
              className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition active:scale-95 hover:bg-brand-700 active:bg-brand-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
            >
              {approving ? t('arcadeWordBank.approving') : t('arcadeWordBank.approve')}
            </button>
            <button
              type="button"
              disabled={approving || rejecting}
              onClick={() => onReject(word.id)}
              className="min-h-[44px] rounded-md border border-line bg-card px-4 py-2 text-sm font-semibold text-ink transition active:scale-95 hover:bg-muted active:bg-muted/70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
            >
              {rejecting ? t('arcadeWordBank.rejecting') : t('arcadeWordBank.reject')}
            </button>
          </div>
        )}
      </div>
    </li>
  );
}

// ── Page component ───────────────────────────────────────────────────────────
export default function ArcadeWordBank() {
  const { t } = useTranslation('admin');
  const qc = useQueryClient();
  const [status, setStatus] = useState<Status>('pending');
  const [suggestCount, setSuggestCount] = useState(10);
  const [suggestedResult, setSuggestedResult] = useState<number | null>(null);

  const wordsQ = useArcadeWords(status);
  const words = wordsQ.data ?? [];

  const approveMutation = useMutation({
    mutationFn: (v: { id: string; edits?: { word?: string; definition?: string } }) =>
      approveArcadeWord(v.id, v.edits),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'arcade-words'] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectArcadeWord(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'arcade-words'] }),
  });

  const suggestMutation = useMutation({
    mutationFn: () => suggestArcadeWords(suggestCount),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['admin', 'arcade-words'] });
      setSuggestedResult(data?.length ?? 0);
    },
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-extrabold text-ink">{t('arcadeWordBank.heading')}</h1>
      <p className="text-sm text-muted-foreground">{t('arcadeWordBank.subtitle')}</p>

      {/* Suggest panel */}
      <div className="rounded-xl border border-line bg-card p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label htmlFor="suggest-count" className="block text-xs font-medium text-ink">
              {t('arcadeWordBank.suggestCountLabel')}
            </label>
            <input
              id="suggest-count"
              type="number"
              min={1}
              max={50}
              value={suggestCount}
              onChange={(e) => {
                setSuggestCount(Number(e.target.value));
                setSuggestedResult(null);
              }}
              className="min-h-[44px] w-24 rounded-md border border-line bg-background px-3 py-2 text-sm text-ink"
            />
          </div>
          <button
            type="button"
            disabled={suggestMutation.isPending}
            onClick={() => suggestMutation.mutate()}
            className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {t('arcadeWordBank.suggestButton', { count: suggestCount })}
          </button>
        </div>
        {suggestedResult !== null && (
          <p className="mt-2 text-sm text-muted-foreground">
            {t('arcadeWordBank.suggestedResult', { count: suggestedResult })}
          </p>
        )}
      </div>

      {/* Status filter */}
      <div>
        <label htmlFor="status-filter" className="sr-only">
          {t('arcadeWordBank.statusFilterLabel')}
        </label>
        <select
          id="status-filter"
          aria-label={t('arcadeWordBank.statusFilterLabel')}
          value={status}
          onChange={(e) => setStatus(e.target.value as Status)}
          className="min-h-[44px] rounded-md border border-line bg-background px-3 py-2 text-sm text-ink"
        >
          <option value="pending">{t('arcadeWordBank.statusPending')}</option>
          <option value="approved">{t('arcadeWordBank.statusApproved')}</option>
          <option value="rejected">{t('arcadeWordBank.statusRejected')}</option>
        </select>
      </div>

      {wordsQ.isLoading && (
        <p className="text-sm text-muted-foreground">{t('arcadeWordBank.loading')}</p>
      )}

      {words.length === 0 && !wordsQ.isLoading && (
        <p className="text-sm text-muted-foreground">{t('arcadeWordBank.empty')}</p>
      )}

      <ul className="space-y-3">
        {words.map((w) => (
          <WordRow
            key={w.id}
            word={w}
            onApprove={(id, edits) => approveMutation.mutate({ id, edits })}
            onReject={(id) => rejectMutation.mutate(id)}
            approving={approveMutation.isPending && approveMutation.variables?.id === w.id}
            rejecting={rejectMutation.isPending && rejectMutation.variables === w.id}
          />
        ))}
      </ul>
    </div>
  );
}
