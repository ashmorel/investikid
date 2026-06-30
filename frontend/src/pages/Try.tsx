import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Penny } from '@/components/child/ui/Penny';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { CardLesson } from '@/components/child/lesson/CardLesson';
import { QuizLesson } from '@/components/child/lesson/QuizLesson';
import { ScenarioLesson } from '@/components/child/lesson/ScenarioLesson';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';
import { XpCountUp } from '@/components/child/ui/XpCountUp';
import { playSound } from '@/lib/sound';
import demoContent from '@/demo/demoContent.json';

type DemoLesson = { type: string; xp_reward: number; content_json: unknown };
type DemoContent = {
  module_title: string;
  icon: string;
  learning_objectives: string[];
  lessons: DemoLesson[];
  tease: { extra_level_count: number; other_module_count: number };
};

const demo = demoContent as DemoContent;

/** "Levels 2 and 3 are waiting" derived from extra_level_count (the demo is Level 1). */
function teaseLevelsPhrase(extraLevelCount: number): string {
  const levels = Array.from({ length: extraLevelCount }, (_, i) => i + 2);
  if (levels.length === 0) return 'More levels are waiting';
  if (levels.length === 1) return `Level ${levels[0]} is waiting`;
  return `Levels ${levels.slice(0, -1).join(', ')} and ${levels[levels.length - 1]} are waiting`;
}

function DemoLessonStep({ lesson, onComplete }: { lesson: DemoLesson; onComplete: (score: number | null) => void }) {
  switch (lesson.type) {
    case 'card':
      return <CardLesson contentJson={lesson.content_json as { title?: string; body?: string }} onComplete={onComplete} />;
    case 'quiz':
      return <QuizLesson contentJson={lesson.content_json as { question: string; choices: string[]; answer_index: number; explanation: string }} onComplete={onComplete} />;
    case 'scenario':
      return <ScenarioLesson contentJson={lesson.content_json as { prompt: string; choices: { label: string; outcome: string }[]; correct_index: number }} onComplete={onComplete} />;
    case 'video':
      return <VideoLesson contentJson={lesson.content_json as { youtube_id?: string; caption?: string; transcript?: string; captions_available?: boolean }} onComplete={onComplete} />;
    default:
      return null;
  }
}

/**
 * Public demo: the full "What is a Stock?" Level 1 arc with purely local state.
 * No auth, no API calls — completing the arc lands on a sign-up conversion screen.
 */
export default function Try() {
  const { t } = useTranslation('parent');
  const [stage, setStage] = useState<'intro' | 'lesson' | 'done'>('intro');
  const [index, setIndex] = useState(0);
  const [xp, setXp] = useState(0);

  const total = demo.lessons.length;
  const lesson = demo.lessons[index];

  const onComplete = (_score: number | null) => {
    setXp((v) => v + lesson.xp_reward);
    if (index + 1 >= total) {
      playSound('lessonComplete');
      setStage('done');
    } else {
      setIndex((i) => i + 1);
    }
  };

  if (stage === 'intro') {
    return (
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <div className="flex flex-col items-center text-center">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-100">
            <Penny size={52} mood="happy" />
          </span>
          <p className="mt-4 text-3xl" aria-hidden="true">{demo.icon}</p>
          <p className="mt-1 text-sm font-bold uppercase tracking-wide text-brand-700">{demo.module_title}</p>
          <h1 className="mt-2 text-2xl font-extrabold text-gray-900">{t('try.intro.heading')}</h1>
          <p className="mt-1 text-sm text-gray-600">{t('try.intro.subtitle')}</p>
        </div>

        <section aria-labelledby="try-objectives-heading" className="mt-6 rounded-2xl border border-brand-100 bg-brand-50 p-4">
          <h2 id="try-objectives-heading" className="text-sm font-bold text-gray-900">{t('try.intro.objectivesHeading')}</h2>
          <ul className="mt-2 space-y-1.5">
            {demo.learning_objectives.map((obj) => (
              <li key={obj} className="flex items-start gap-2 text-sm text-gray-700">
                {/* eslint-disable-next-line i18next/no-literal-string -- decorative glyph, aria-hidden */}
                <span aria-hidden="true" className="mt-0.5 text-brand-500">★</span>
                <span>{obj}</span>
              </li>
            ))}
          </ul>
        </section>

        <div className="mt-6">
          <GradientButton full onClick={() => setStage('lesson')}>{t('try.intro.start')}</GradientButton>
        </div>
        <p className="mt-4 text-center text-sm text-gray-600">
          {t('try.intro.alreadyHaveAccount')}{' '}<Link to="/login" className="font-medium underline">{t('try.intro.backToLogin')}</Link>
        </p>
        <p className="mt-2 text-center text-xs text-gray-500">
          <Link to="/how-we-measure" className="underline hover:text-gray-700">{t('try.intro.howWeMeasure')}</Link>
        </p>
      </main>
    );
  }

  if (stage === 'done') {
    const teaseLevels = teaseLevelsPhrase(demo.tease.extra_level_count);
    return (
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <div className="flex flex-col items-center text-center">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-100">
            <Penny size={52} mood="excited" />
          </span>
          <h1 className="mt-4 text-2xl font-extrabold text-gray-900">
            {t('try.done.heading')} <span aria-hidden="true">🎉</span>
          </h1>
          <p className="mt-3 inline-block rounded-full bg-brand-gradient px-4 py-1.5 text-sm font-extrabold text-white shadow">
            <XpCountUp value={xp} /> <span aria-hidden="true">XP</span>
          </p>
        </div>

        <section aria-label={t('try.lesson.srHeading', { moduleTitle: demo.module_title })} className="mt-6 space-y-3 rounded-2xl border border-brand-100 bg-brand-50 p-4 text-sm text-gray-700">
          <p className="font-bold text-gray-900">
            {teaseLevels} <span aria-hidden="true">🔒</span>
          </p>
          <p>
            {t('try.tease.otherModules', { count: demo.tease.other_module_count })}
          </p>
        </section>

        <div className="mt-6">
          <GradientButton full to="/signup">{t('try.done.createAccount')}</GradientButton>
        </div>
        <p className="mt-4 text-center text-sm text-gray-600">
          <Link to="/privacy" className="underline">{t('try.done.parentsLearnMore')}</Link>
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="sr-only">{t('try.lesson.srHeading', { moduleTitle: demo.module_title })}</h1>
      <div className="flex items-center justify-between text-xs font-semibold text-gray-600">
        <span>{t('try.lesson.progress', { current: index + 1, total })}</span>
        <Link to="/signup" className="font-bold text-brand-700 underline hover:text-brand-800">{t('try.lesson.signUp')}</Link>
      </div>
      <div
        className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
        role="progressbar"
        aria-valuenow={index}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={t('try.lesson.progressAriaLabel')}
      >
        <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${Math.round((index / total) * 100)}%` }} />
      </div>
      <div className="mt-4">
        <DemoLessonStep key={index} lesson={lesson} onComplete={onComplete} />
      </div>
    </main>
  );
}
