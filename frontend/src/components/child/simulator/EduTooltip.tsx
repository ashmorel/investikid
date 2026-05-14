import { Info } from 'lucide-react';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';

type EduTooltipProps = {
  term: string;
  explanation: string;
  children?: React.ReactNode;
};

export function EduTooltip({ term, explanation, children }: EduTooltipProps) {
  return (
    <TooltipProvider>
      <span className="inline-flex items-center gap-1">
        {children ?? <span>{term}</span>}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="inline-flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground"
              aria-label={`Info about ${term}`}
            >
              <Info className="h-3.5 w-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-sm">
            {explanation}
          </TooltipContent>
        </Tooltip>
      </span>
    </TooltipProvider>
  );
}
