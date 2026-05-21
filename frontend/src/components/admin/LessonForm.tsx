import type { AdminLesson } from '@/api/admin';

interface LessonFormProps {
  moduleId: string;
  lesson?: AdminLesson;
  nextOrderIndex: number;
  onClose: () => void;
}

export default function LessonForm({ onClose }: LessonFormProps) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60">
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-6">
        <p className="text-slate-50">Lesson form (coming soon)</p>
        <button type="button" onClick={onClose} className="mt-2 text-sm text-blue-400">Close</button>
      </div>
    </div>
  );
}
