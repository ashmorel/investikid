import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { CoachChat } from '@/components/child/CoachChat';

type CoachPanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function CoachPanel({ open, onOpenChange }: CoachPanelProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="bottom"
        className="inset-x-0 bottom-0 flex h-[85svh] flex-col rounded-t-2xl border-brand-100 bg-white p-4 pb-[calc(1rem+var(--safe-bottom))] sm:bottom-4 sm:left-auto sm:right-4 sm:h-[min(720px,calc(100svh-2rem))] sm:w-[420px] sm:rounded-2xl sm:border"
      >
        <SheetHeader className="sr-only">
          <SheetTitle>Coach Penny</SheetTitle>
          <SheetDescription>Ask Coach Penny for learning help.</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 pt-7 sm:pt-5">
          <CoachChat onNavigate={() => onOpenChange(false)} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
