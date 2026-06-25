import { useId, useState, type ReactNode } from 'react';
import { ChevronDown, type LucideIcon } from 'lucide-react';

type Props = {
  title: string;
  icon?: LucideIcon;
  count?: number;
  collapsible?: boolean;
  defaultOpen?: boolean;
  headingLevel?: 2 | 3;
  children: ReactNode;
};

export function SectionCard({
  title,
  icon: Icon,
  count,
  collapsible = false,
  defaultOpen = true,
  headingLevel = 2,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  const Heading = headingLevel === 3 ? 'h3' : 'h2';
  const isOpen = collapsible ? open : true;

  const inner = (
    <>
      {Icon && <Icon className="h-5 w-5 flex-shrink-0 text-brand-700" aria-hidden="true" />}
      <span className="text-lg font-semibold text-ink">{title}</span>
      {typeof count === 'number' && (
        <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700">
          {count}
        </span>
      )}
    </>
  );

  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-card p-4">
      <Heading className="m-0">
        {collapsible ? (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={isOpen}
            aria-controls={contentId}
            className="flex min-h-[44px] w-full items-center gap-2 rounded-lg text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            {inner}
            <ChevronDown
              className={`ml-auto h-5 w-5 flex-shrink-0 text-brand-700 transition-transform ${isOpen ? 'rotate-180' : ''}`}
              aria-hidden="true"
            />
          </button>
        ) : (
          <span className="flex items-center gap-2">{inner}</span>
        )}
      </Heading>
      {isOpen && (
        <div id={contentId} className="mt-3">
          {children}
        </div>
      )}
    </div>
  );
}
