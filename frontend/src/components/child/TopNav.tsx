import { Link, NavLink } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';
import { ProfileMenu } from './ProfileMenu';
import { cn } from '@/lib/utils';

const COMING_SOON: ReadonlyArray<{ label: string }> = [
  { label: 'Simulator' }, { label: 'Stats' },
];

export function TopNav({ username }: { username: string }) {
  return (
    <TooltipProvider>
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
          <Link to="/home" className="text-lg font-semibold">Invest-Ed</Link>

          <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Primary">
            <NavLink to="/home"
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
                isActive && 'bg-muted font-medium',
              )}>Home</NavLink>
            <NavLink to="/lessons"
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm rounded-md hover:bg-muted',
                isActive && 'bg-muted font-medium',
              )}>Lessons</NavLink>
            {COMING_SOON.map((item) => (
              <Tooltip key={item.label}>
                <TooltipTrigger asChild>
                  <button
                    type="button" disabled aria-disabled="true"
                    className="cursor-not-allowed px-3 py-1.5 text-sm text-muted-foreground"
                  >{item.label}</button>
                </TooltipTrigger>
                <TooltipContent>Coming soon</TooltipContent>
              </Tooltip>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left">
                <nav className="mt-6 flex flex-col gap-1" aria-label="Primary mobile">
                  <NavLink to="/home"
                    className={({ isActive }) => cn(
                      'rounded-md px-3 py-2 text-sm hover:bg-muted',
                      isActive && 'bg-muted font-medium',
                    )}>Home</NavLink>
                  {COMING_SOON.map((item) => (
                    <span key={item.label} aria-disabled="true"
                      className="rounded-md px-3 py-2 text-sm text-muted-foreground">
                      {item.label} <span className="text-xs">(coming soon)</span>
                    </span>
                  ))}
                </nav>
              </SheetContent>
            </Sheet>
            <ProfileMenu username={username} />
          </div>
        </div>
      </header>
    </TooltipProvider>
  );
}
