import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { authApi, type Me } from '@/api/auth';
import { useChildSession } from '@/hooks/useChildSession';
import { TOPIC_OPTIONS } from '@/api/content';
import type { Progress } from '@/api/content';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { FeedbackDialog } from '@/components/child/FeedbackDialog';
import { RegionSwitcher } from '@/components/child/RegionSwitcher';
import { CurrencySelector } from '@/components/child/CurrencySelector';
import { LanguageSwitcher } from '@/components/settings/LanguageSwitcher';
import ConfirmDialog from '@/components/admin/ConfirmDialog';
import { simulatorApi } from '@/api/simulator';
import type { RegionCode } from '@/lib/region';
import { isNativeApp } from '@/lib/platform';
import { contentApi, type DailyGoalSize } from '@/api/content';
import { useProgress } from '@/hooks/useProgress';
import { disablePush, enablePush, isPushRegistered } from '@/lib/push';
import { addBioAccount, biometric, getBioAccounts, getDeviceId, removeBioAccount } from '@/lib/biometric';

const GOAL_SIZES: { value: DailyGoalSize; label: string }[] = [
  { value: 10, label: 'Chill' },
  { value: 30, label: 'Steady' },
  { value: 50, label: 'Super' },
];
import { isSoundEnabled, playSound, setSoundEnabled } from '@/lib/sound';
import { REMINDER } from '@/lib/reminderConfig';
import { requestReminderPermission, syncStreakReminder } from '@/lib/streakReminder';

export function ProfileMenu({ username }: { username: string }) {
  const { t } = useTranslation('settings');
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: session } = useChildSession();
  const isMobile = !useMediaQuery('(min-width: 768px)');
  const [open, setOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [topic, setTopic] = useState('');
  const [reminderOn, setReminderOn] = useState(() => localStorage.getItem(REMINDER.storageKey) === '1');
  const [reminderDenied, setReminderDenied] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [soundOn, setSoundOn] = useState(() => isSoundEnabled());

  const { data: progressData } = useProgress();
  const goalXp = progressData?.daily_goal_xp ?? 30;
  const setGoal = useMutation({
    mutationFn: (size: DailyGoalSize) => contentApi.setDailyGoal(size),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['progress'] }),
  });

  const parentPushEnabled = session?.push_enabled ?? false;
  const bioAllowed = session?.biometric_allowed ?? false;
  const bioKey = session?.id ? `child:${session.id}` : '';
  const [bioAvailable, setBioAvailable] = useState(false);
  const [bioOn, setBioOn] = useState(() => getBioAccounts().some((a) => a.key === bioKey));
  useEffect(() => { void biometric.isAvailable().then(setBioAvailable); }, []);
  async function toggleBiometric(next: boolean) {
    if (!session?.id) return;
    const label = session.username ?? 'Me';
    if (next) {
      if (!(await biometric.verify('Set up Face ID sign-in'))) return;
      const res = await authApi.biometricEnroll(getDeviceId(), label);
      if (res?.secret) {
        await biometric.enroll(bioKey, label, res.secret);
        addBioAccount({ key: bioKey, label, kind: 'child' });
        setBioOn(true);
      }
    } else {
      await authApi.biometricUnenroll(getDeviceId());
      await biometric.clear(bioKey);
      removeBioAccount(bioKey);
      setBioOn(false);
    }
  }
  const [pushOn, setPushOn] = useState(() => isPushRegistered());
  const [pushDenied, setPushDenied] = useState(false);
  async function togglePush(next: boolean) {
    setPushDenied(false);
    if (next) {
      const result = await enablePush(parentPushEnabled);
      if (result === 'registered') {
        setPushOn(true);
      } else {
        setPushOn(false);
        if (result === 'permission-denied') setPushDenied(true);
      }
    } else {
      await disablePush();
      setPushOn(false);
    }
  }

  function toggleSound(next: boolean) {
    setSoundEnabled(next);
    setSoundOn(next);
    if (next) playSound('correct'); // instant audition so kids hear what they enabled
  }

  const resetPf = useMutation({
    mutationFn: () => simulatorApi.resetPortfolio(),
    onSuccess: () => {
      for (const key of [['portfolio'], ['portfolio-history']]) qc.invalidateQueries({ queryKey: key });
      setConfirmReset(false);
    },
  });

  const me = qc.getQueryData<Me>(['me']);
  const currentRegion = (me?.content_region ?? me?.country_code ?? 'US') as RegionCode;
  const currentCurrency = me?.currency_code ?? 'USD';

  function openEditor() {
    const me = qc.getQueryData<Me>(['me']);
    setTopic(me?.topic_path ?? '');
    setOpen(true);
  }

  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      qc.removeQueries({ queryKey: ['me'] });
      navigate('/login', { replace: true });
    },
  });

  async function goToParentArea() {
    try { await authApi.parentFromSession(); } catch { /* dashboard guard will redirect if needed */ }
    navigate('/parent');
  }

  async function toggleReminder(next: boolean) {
    if (next) {
      let granted: boolean;
      try {
        granted = await requestReminderPermission();
      } catch {
        granted = false;
      }
      if (!granted) { setReminderDenied(true); setReminderOn(false); return; }
      localStorage.setItem(REMINDER.storageKey, '1');
      setReminderDenied(false);
      setReminderOn(true);
    } else {
      localStorage.removeItem(REMINDER.storageKey);
      setReminderOn(false);
    }
    const progress = qc.getQueryData<Progress>(['progress']);
    void syncStreakReminder({
      lastActivity: progress?.last_activity_date ?? null,
      streakCount: progress?.streak_count ?? 0,
    }).catch(() => {});
  }

  const save = useMutation({
    mutationFn: (topic_path: string | null) => authApi.updatePreferences({ topic_path }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me'] });
      setOpen(false);
    },
  });

  const editorContent = (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label htmlFor="profile-topic" className="text-sm font-medium">
          {t('interestArea')}
        </label>
        <select
          id="profile-topic"
          className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        >
          {TOPIC_OPTIONS.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>
      <div className="space-y-3 border-t border-line pt-4">
        <p className="text-sm font-semibold text-muted-foreground">{t('preferences')}</p>
        <div className="space-y-1.5">
          {/* RegionSwitcher carries its own role="group" label, so this heading
              is decorative-only (aria-hidden) to avoid a double accessible name. */}
          <span aria-hidden="true" className="text-sm font-medium">{t('learningRegion')}</span>
          <RegionSwitcher currentRegion={currentRegion} />
        </div>
        <CurrencySelector currentCurrency={currentCurrency} />
        <LanguageSwitcher />
        <div className="space-y-1.5">
          <label className="flex min-h-[44px] items-center justify-between gap-3 text-sm font-medium">
            <span>{t('sounds.label')}</span>
            <input
              type="checkbox"
              checked={soundOn}
              onChange={(e) => toggleSound(e.target.checked)}
              className="h-5 w-5"
              aria-describedby="sound-help"
            />
          </label>
          <p id="sound-help" className="text-xs text-muted-foreground">
            {t('sounds.help')}
          </p>
        </div>
        <fieldset className="space-y-1.5">
          <legend className="text-sm font-medium">{t('dailyGoal.legend')}</legend>
          <div role="radiogroup" aria-label="Daily goal size" className="flex gap-2">
            {GOAL_SIZES.map((g) => (
              <label
                key={g.value}
                className={`flex min-h-[44px] flex-1 cursor-pointer items-center justify-center rounded-md border px-2 text-xs font-bold ${
                  goalXp === g.value ? 'border-brand-600 bg-brand-50 text-brand-800' : 'border-line text-gray-700'
                }`}
              >
                <input
                  type="radio"
                  name="daily-goal"
                  value={g.value}
                  checked={goalXp === g.value}
                  onChange={() => setGoal.mutate(g.value)}
                  className="sr-only"
                />
                {g.label} · {g.value} XP
              </label>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">{t('dailyGoal.help')}</p>
        </fieldset>
        <Link
          to="/shop"
          className="flex min-h-[44px] w-full items-center justify-between rounded-md border border-line px-3 text-sm font-medium text-brand-700 hover:bg-brand-50"
        >
          <span>{t('shop.label')}</span>
          <span className="font-bold" aria-label={`${progressData?.virtual_coins ?? 0} coins`}>
            <span aria-hidden="true">🪙 </span>{progressData?.virtual_coins ?? 0}
          </span>
        </Link>
        <button
          type="button"
          onClick={() => setConfirmReset(true)}
          className="min-h-[44px] w-full rounded-md border border-line px-3 text-sm font-medium text-brand-700 hover:bg-brand-50"
        >
          {t('startFresh')}
        </button>
        <ConfirmDialog
          open={confirmReset}
          title="Start fresh?"
          message={`Start your practice portfolio over in ${currentCurrency}? This clears your current play holdings and history. Your XP and badges are safe.`}
          onConfirm={() => resetPf.mutate()}
          onCancel={() => setConfirmReset(false)}
        />
        {isNativeApp() && (
          <div className="space-y-1.5 border-t border-line pt-3">
            <label className="flex items-center justify-between gap-3 text-sm font-medium">
              <span>{t('reminders.streak')}</span>
              <input
                type="checkbox"
                checked={reminderOn}
                onChange={(e) => void toggleReminder(e.target.checked)}
                className="h-5 w-5"
                aria-describedby={reminderDenied ? 'reminder-help reminder-denied' : 'reminder-help'}
              />
            </label>
            <p id="reminder-help" className="text-xs text-muted-foreground">
              {t('reminders.streakHelp')}
            </p>
            {reminderDenied && (
              <p id="reminder-denied" className="text-xs text-accent-700">
                {t('reminders.streakDenied')}
              </p>
            )}
            {parentPushEnabled && (
              <>
                <label className="flex items-center justify-between gap-3 text-sm font-medium">
                  <span>{t('reminders.alerts')}</span>
                  <input
                    type="checkbox"
                    checked={pushOn}
                    onChange={(e) => void togglePush(e.target.checked)}
                    className="h-5 w-5"
                    aria-describedby={pushDenied ? 'push-help push-denied' : 'push-help'}
                  />
                </label>
                <p id="push-help" className="text-xs text-muted-foreground">
                  {t('reminders.alertsHelp')}
                </p>
                {pushDenied && (
                  <p id="push-denied" className="text-xs text-accent-700">
                    {t('reminders.alertsDenied')}
                  </p>
                )}
              </>
            )}
            {bioAllowed && bioAvailable && (
              <>
                <label className="flex items-center justify-between gap-3 text-sm font-medium">
                  <span>{t('faceId.label')}</span>
                  <input
                    type="checkbox"
                    checked={bioOn}
                    onChange={(e) => void toggleBiometric(e.target.checked)}
                    className="h-5 w-5"
                    aria-describedby="bio-help"
                  />
                </label>
                <p id="bio-help" className="text-xs text-muted-foreground">
                  {t('faceId.help')}
                </p>
              </>
            )}
          </div>
        )}
      </div>
      <Button
        type="button"
        disabled={save.isPending}
        onClick={() => save.mutate(topic === '' ? null : topic)}
      >
        {save.isPending ? t('saving') : t('save')}
      </Button>
    </div>
  );

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" aria-label={`Account menu for ${username}`}>
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-sm font-medium uppercase">
              {username.slice(0, 1)}
            </span>
            <span className="ml-2 hidden text-sm md:inline">{username}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={openEditor}>
            {t('nav.profile')}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setFeedbackOpen(true)}>
            {t('nav.sendFeedback')}
          </DropdownMenuItem>
          {session?.is_admin && (
            <DropdownMenuItem onSelect={() => navigate('/admin')}>
              {t('nav.admin')}
            </DropdownMenuItem>
          )}
          {session?.is_parent && (
            <DropdownMenuItem onSelect={() => void goToParentArea()}>
              {t('nav.parentArea')}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => logout.mutate()}>{t('nav.logOut')}</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {isMobile ? (
        <BottomSheet open={open} onOpenChange={setOpen} title={t('dialog.title')}>
          {editorContent}
        </BottomSheet>
      ) : (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('dialog.title')}</DialogTitle>
            </DialogHeader>
            {editorContent}
          </DialogContent>
        </Dialog>
      )}

      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} audience="child" />
    </>
  );
}
