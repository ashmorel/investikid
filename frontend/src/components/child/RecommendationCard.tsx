import { Link } from 'react-router-dom';
import type { RecommendationCategoryItem } from '@/api/ai';

type Category = 'continue_learning' | 'practise_again' | 'something_new';

const CATEGORY_COLORS: Record<Category, { border: string; text: string; chip: string; chipText: string }> = {
  continue_learning: {
    border: 'border-l-success-500',
    text: 'text-success-500',
    chip: 'bg-success-900/30',
    chipText: 'text-success-500',
  },
  practise_again: {
    border: 'border-l-accent-400',
    text: 'text-accent-500',
    chip: 'bg-accent-900/30',
    chipText: 'text-accent-500',
  },
  something_new: {
    border: 'border-l-brand-400',
    text: 'text-brand-400',
    chip: 'bg-brand-900/30',
    chipText: 'text-brand-400',
  },
};

type RecommendationCardProps = {
  item: RecommendationCategoryItem;
  category: Category;
  moduleTitle: string;
  completedCount: number;
  totalCount: number;
};

export function RecommendationCard({
  item,
  category,
  moduleTitle,
  completedCount,
  totalCount,
}: RecommendationCardProps) {
  const colors = CATEGORY_COLORS[category];
  const href = item.lesson_id
    ? `/lessons/${item.module_id}/${item.lesson_id}`
    : `/lessons/${item.module_id}`;

  return (
    <Link
      to={href}
      className={`block rounded-xl border-l-4 ${colors.border} bg-slate-800 p-4 transition-colors hover:bg-slate-700`}
    >
      {item.level_title && (
        <p className={`${colors.text} text-[11px] font-semibold uppercase tracking-wide`}>
          {item.level_title}
        </p>
      )}
      <p className="font-semibold text-white text-sm">{moduleTitle}</p>

      {category === 'continue_learning' && totalCount > 0 && (
        <>
          <p className="text-slate-400 text-xs mt-1">{completedCount} of {totalCount}</p>
          <div
            role="progressbar"
            aria-valuenow={completedCount}
            aria-valuemin={0}
            aria-valuemax={totalCount}
            aria-label={`${completedCount} of ${totalCount} lessons completed`}
            className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-600"
          >
            <div
              className="h-full rounded-full bg-success-500"
              style={{ width: `${(completedCount / totalCount) * 100}%` }}
            />
          </div>
        </>
      )}

      {category === 'practise_again' && item.weak_concepts.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {item.weak_concepts.map((concept) => (
            <span
              key={concept}
              className={`${colors.chip} ${colors.chipText} rounded-full px-2 py-0.5 text-xs`}
            >
              {concept}
            </span>
          ))}
        </div>
      )}

      <p className={`${colors.text} text-xs mt-2`}>{item.reason}</p>
    </Link>
  );
}
