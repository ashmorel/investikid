import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { authApi, type Me } from '@/api/auth';
import { TOPIC_OPTIONS } from '@/api/content';
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

export function ProfileMenu({ username }: { username: string }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isMobile = !useMediaQuery('(min-width: 768px)');
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState('');

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
          Interest area
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
      <Button
        type="button"
        disabled={save.isPending}
        onClick={() => save.mutate(topic === '' ? null : topic)}
      >
        {save.isPending ? 'Saving…' : 'Save'}
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
            Profile
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => logout.mutate()}>Log out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {isMobile ? (
        <BottomSheet open={open} onOpenChange={setOpen} title="Your interest area">
          {editorContent}
        </BottomSheet>
      ) : (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Your interest area</DialogTitle>
            </DialogHeader>
            {editorContent}
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
