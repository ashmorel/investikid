import { useState } from 'react';
import { useCreateLesson, useUpdateLesson } from '@/api/admin';
import type { AdminLesson } from '@/api/admin';

const TYPES = ['card', 'quiz', 'scenario'] as const;
type LessonType = (typeof TYPES)[number];

const DEFAULT_XP: Record<LessonType, number> = { card: 10, quiz: 25, scenario: 20 };

interface LessonFormProps {
  moduleId: string;
  lesson?: AdminLesson;
  nextOrderIndex: number;
  onClose: () => void;
}

export default function LessonForm({ moduleId, lesson, nextOrderIndex, onClose }: LessonFormProps) {
  const isEdit = !!lesson;
  const createLesson = useCreateLesson();
  const updateLesson = useUpdateLesson();

  const [type, setType] = useState<LessonType>((lesson?.type as LessonType) ?? 'card');
  const [xpReward, setXpReward] = useState(lesson?.xp_reward ?? DEFAULT_XP.card);

  // Initialize content fields from existing lesson data
  const cj = lesson ? (lesson.content_json as Record<string, unknown>) : undefined;

  // Card fields
  const [cardTitle, setCardTitle] = useState(lesson?.type === 'card' ? ((cj?.title as string) ?? '') : '');
  const [cardBody, setCardBody] = useState(lesson?.type === 'card' ? ((cj?.body as string) ?? '') : '');

  // Quiz fields
  const [question, setQuestion] = useState(lesson?.type === 'quiz' ? ((cj?.question as string) ?? '') : '');
  const [choices, setChoices] = useState<string[]>(lesson?.type === 'quiz' ? ((cj?.choices as string[]) ?? ['', '']) : ['', '']);
  const [answerIndex, setAnswerIndex] = useState(lesson?.type === 'quiz' ? ((cj?.answer_index as number) ?? 0) : 0);
  const [explanation, setExplanation] = useState(lesson?.type === 'quiz' ? ((cj?.explanation as string) ?? '') : '');

  // Scenario fields
  const [prompt, setPrompt] = useState(lesson?.type === 'scenario' ? ((cj?.prompt as string) ?? '') : '');
  const [scenarioChoices, setScenarioChoices] = useState<{ label: string; outcome: string }[]>(
    lesson?.type === 'scenario'
      ? ((cj?.choices as { label: string; outcome: string }[]) ?? [{ label: '', outcome: '' }, { label: '', outcome: '' }])
      : [{ label: '', outcome: '' }, { label: '', outcome: '' }]
  );
  const [correctIndex, setCorrectIndex] = useState(lesson?.type === 'scenario' ? ((cj?.correct_index as number) ?? 0) : 0);

  function handleTypeChange(newType: LessonType) {
    setType(newType);
    setXpReward(DEFAULT_XP[newType]);
  }

  function buildContentJson(): Record<string, unknown> {
    if (type === 'card') return { title: cardTitle, body: cardBody };
    if (type === 'quiz') return { question, choices, answer_index: answerIndex, explanation };
    return { prompt, choices: scenarioChoices, correct_index: correctIndex };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const content_json = buildContentJson();
    if (isEdit && lesson) {
      await updateLesson.mutateAsync({ id: lesson.id, type, content_json, xp_reward: xpReward });
    } else {
      await createLesson.mutateAsync({ moduleId, type, content_json, xp_reward: xpReward, order_index: nextOrderIndex });
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded-lg border border-slate-700 bg-slate-900 p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="mb-4 text-lg font-semibold text-slate-50">
          {isEdit ? 'Edit Lesson' : 'New Lesson'}
        </h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Type selector */}
          <div className="flex gap-2">
            {TYPES.map((t) => (
              <button
                key={t}
                type="button"
                aria-label={t}
                onClick={() => handleTypeChange(t)}
                className={`rounded-full px-4 py-1 text-sm ${
                  type === t ? 'bg-blue-600 text-white' : 'border border-slate-600 text-slate-400'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* XP Reward */}
          <div>
            <label htmlFor="lesson-xp" className="mb-1 block text-sm text-slate-400">XP Reward</label>
            <input id="lesson-xp" type="number" value={xpReward} onChange={(e) => setXpReward(Number(e.target.value))}
              className="w-24 rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>

          {/* Card fields */}
          {type === 'card' && (
            <>
              <div>
                <label htmlFor="card-title" className="mb-1 block text-sm text-slate-400">Title</label>
                <input id="card-title" value={cardTitle} onChange={(e) => setCardTitle(e.target.value)} required
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
              <div>
                <label htmlFor="card-body" className="mb-1 block text-sm text-slate-400">Body</label>
                <textarea id="card-body" value={cardBody} onChange={(e) => setCardBody(e.target.value)} required rows={3}
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
            </>
          )}

          {/* Quiz fields */}
          {type === 'quiz' && (
            <>
              <div>
                <label htmlFor="quiz-question" className="mb-1 block text-sm text-slate-400">Question</label>
                <input id="quiz-question" value={question} onChange={(e) => setQuestion(e.target.value)} required
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
              <div>
                <span className="mb-1 block text-sm text-slate-400">Choices</span>
                {choices.map((c, i) => (
                  <div key={i} className="mb-2 flex items-center gap-2">
                    <input
                      type="radio"
                      name="quiz-answer"
                      checked={answerIndex === i}
                      onChange={() => setAnswerIndex(i)}
                      className="h-4 w-4"
                      aria-label={`Mark choice ${i + 1} as correct`}
                    />
                    <input
                      value={c}
                      onChange={(e) => { const nc = [...choices]; nc[i] = e.target.value; setChoices(nc); }}
                      className="flex-1 rounded-md border border-slate-600 bg-slate-800 px-3 py-1 text-slate-50"
                      placeholder={`Choice ${i + 1}`}
                      required
                    />
                    {choices.length > 2 && (
                      <button type="button" onClick={() => {
                        const nc = choices.filter((_, j) => j !== i);
                        setChoices(nc);
                        if (answerIndex >= nc.length) setAnswerIndex(nc.length - 1);
                      }} className="text-red-400">✕</button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => setChoices([...choices, ''])}
                  className="text-sm text-blue-400">+ Add Choice</button>
              </div>
              <div>
                <label htmlFor="quiz-explanation" className="mb-1 block text-sm text-slate-400">Explanation</label>
                <input id="quiz-explanation" value={explanation} onChange={(e) => setExplanation(e.target.value)} required
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
            </>
          )}

          {/* Scenario fields */}
          {type === 'scenario' && (
            <>
              <div>
                <label htmlFor="scenario-prompt" className="mb-1 block text-sm text-slate-400">Prompt</label>
                <textarea id="scenario-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} required rows={2}
                  className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
              </div>
              <div>
                <span className="mb-1 block text-sm text-slate-400">Choices</span>
                {scenarioChoices.map((c, i) => (
                  <div key={i} className="mb-3 rounded-md border border-slate-700 bg-slate-800 p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <input
                        type="radio"
                        name="scenario-correct"
                        checked={correctIndex === i}
                        onChange={() => setCorrectIndex(i)}
                        className="h-4 w-4"
                        aria-label={`Mark choice ${i + 1} as correct`}
                      />
                      <input
                        value={c.label}
                        onChange={(e) => { const nc = [...scenarioChoices]; nc[i] = { ...nc[i], label: e.target.value }; setScenarioChoices(nc); }}
                        className="flex-1 rounded-md border border-slate-600 bg-slate-900 px-3 py-1 text-slate-50"
                        placeholder="Label"
                        required
                      />
                      {scenarioChoices.length > 2 && (
                        <button type="button" onClick={() => {
                          const nc = scenarioChoices.filter((_, j) => j !== i);
                          setScenarioChoices(nc);
                          if (correctIndex >= nc.length) setCorrectIndex(nc.length - 1);
                        }} className="text-red-400">✕</button>
                      )}
                    </div>
                    <input
                      value={c.outcome}
                      onChange={(e) => { const nc = [...scenarioChoices]; nc[i] = { ...nc[i], outcome: e.target.value }; setScenarioChoices(nc); }}
                      className="ml-6 w-[calc(100%-1.5rem)] rounded-md border border-slate-600 bg-slate-900 px-3 py-1 text-sm text-slate-50"
                      placeholder="Outcome message"
                      required
                    />
                  </div>
                ))}
                <button type="button" onClick={() => setScenarioChoices([...scenarioChoices, { label: '', outcome: '' }])}
                  className="text-sm text-blue-400">+ Add Choice</button>
              </div>
            </>
          )}

          <div className="mt-2 flex gap-3">
            <button type="submit" className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500">
              {isEdit ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={onClose}
              className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
