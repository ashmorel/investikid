import { Link } from 'react-router-dom';
import { CoachChat } from '@/components/child/CoachChat';

export default function Coach() {
  return (
    <div className="mx-auto flex h-[calc(100svh-8rem)] max-w-2xl flex-col px-4 py-4">
      <Link
        to="/home"
        aria-label="Back to home"
        className="mb-3 inline-flex w-fit items-center text-sm font-medium text-brand-700 hover:text-brand-900"
      >
        ← Back
      </Link>
      <CoachChat />
    </div>
  );
}
