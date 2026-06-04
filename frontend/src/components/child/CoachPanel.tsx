import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from '@/components/ui/sheet';
import { CoachChat } from '@/components/child/CoachChat';
import { Penny } from '@/components/child/ui/Penny';
import { useMediaQuery } from '@/hooks/useMediaQuery';

type CoachPanelProps = { open: boolean; onOpenChange: (open: boolean) => void };

export function CoachPanel({ open, onOpenChange }: CoachPanelProps) {
  const isDesktop = useMediaQuery('(min-width: 640px)');
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side={isDesktop ? 'right' : 'bottom'}
        className={
          isDesktop
            ? 'flex h-full w-full max-w-md flex-col gap-0 border-brand-100 bg-white p-0 sm:max-w-md'
            : 'flex h-[85svh] flex-col gap-0 rounded-t-2xl border-brand-100 bg-white p-0'
        }
      >
        <SheetHeader className="flex-row items-center gap-2 border-b border-brand-100 px-4 py-3 text-left">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
            <Penny size={28} mood="happy" />
          </span>
          <div>
            <SheetTitle>Coach Penny</SheetTitle>
            <SheetDescription>Ask Coach Penny for learning help.</SheetDescription>
          </div>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-hidden px-4 py-3 pb-[calc(0.75rem+var(--safe-bottom))]">
          <CoachChat onNavigate={() => onOpenChange(false)} showHeader={false} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
