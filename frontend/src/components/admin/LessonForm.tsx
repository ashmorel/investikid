import { useState } from 'react';
import { useCreateLesson, useUpdateLesson, useCreateLevelLesson, presignVideo, uploadToPresigned } from '@/api/admin';
import type { AdminLesson, ApplyMission, MissionType } from '@/api/admin';

const MISSION_TYPES: { value: MissionType; label: string }[] = [
  { value: 'first_buy', label: 'Buy a share' },
  { value: 'first_sell', label: 'Sell a share' },
  { value: 'diversify', label: 'Diversify (hold N stocks)' },
  { value: 'invest_amount', label: 'Invest an amount' },
];

const MAX_VIDEO_BYTES = 200 * 1024 * 1024; // 200 MB

const TYPES = ['card', 'quiz', 'scenario', 'video'] as const;
type LessonType = (typeof TYPES)[number];

const DEFAULT_XP: Record<LessonType, number> = { card: 10, quiz: 25, scenario: 20, video: 15 };

// Accepts a full YouTube URL or a raw 11-char ID; returns the 11-char ID (or the trimmed input if no match).
function extractYoutubeId(input: string): string {
  const s = input.trim();
  const m = s.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/))([A-Za-z0-9_-]{11})/);
  if (m) return m[1];
  const bare = s.match(/^[A-Za-z0-9_-]{11}$/);
  return bare ? s : s;
}

interface LessonFormProps {
  moduleId: string;
  levelId?: string;
  lesson?: AdminLesson;
  nextOrderIndex: number;
  onClose: () => void;
}

export default function LessonForm({ moduleId, levelId, lesson, nextOrderIndex, onClose }: LessonFormProps) {
  const isEdit = !!lesson;
  const createLesson = useCreateLesson();
  const createLevelLesson = useCreateLevelLesson(levelId ?? '');
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

  // Video fields
  const [youtubeInput, setYoutubeInput] = useState(lesson?.type === 'video' ? ((cj?.youtube_id as string) ?? '') : '');
  const [videoCaption, setVideoCaption] = useState(lesson?.type === 'video' ? ((cj?.caption as string) ?? '') : '');
  const [videoSource, setVideoSource] = useState<'youtube' | 'hosted'>(
    lesson?.type === 'video' && (cj?.video_source as string) === 'hosted' ? 'hosted' : 'youtube',
  );
  const [videoUrl, setVideoUrl] = useState(lesson?.type === 'video' ? ((cj?.video_url as string) ?? '') : '');
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);

  // Apply-mission fields
  const [missionEnabled, setMissionEnabled] = useState(!!lesson?.apply_mission);
  const [missionType, setMissionType] = useState<MissionType>(lesson?.apply_mission?.mission_type ?? 'first_buy');
  const [missionTitle, setMissionTitle] = useState(lesson?.apply_mission?.title ?? '');
  const [missionPrompt, setMissionPrompt] = useState(lesson?.apply_mission?.prompt ?? '');
  const [missionXp, setMissionXp] = useState<string>(String(lesson?.apply_mission?.xp_reward ?? 20));
  const [missionCash, setMissionCash] = useState<string>(lesson?.apply_mission?.cash_reward ?? '');
  const [missionN, setMissionN] = useState<string>(String(lesson?.apply_mission?.params_json?.n ?? 2));
  const [missionAmount, setMissionAmount] = useState<string>(String(lesson?.apply_mission?.params_json?.amount ?? '500'));

  async function handleVideoFile(file: File) {
    setUploadErr(null);
    if (file.type !== 'video/mp4') {
      setUploadErr('Please choose an MP4 file.');
      return;
    }
    if (file.size > MAX_VIDEO_BYTES) {
      setUploadErr('File too large (max 200 MB).');
      return;
    }
    try {
      setUploadPct(0);
      const res = await presignVideo(file.name, file.type, file.size);
      await uploadToPresigned(res.upload_url, file, setUploadPct);
      setVideoUrl(res.public_url);
      setUploadPct(100);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Upload failed';
      setUploadErr(/not_configured/i.test(msg) ? 'Video upload not configured.' : msg);
      setUploadPct(null);
    }
  }

  function handleTypeChange(newType: LessonType) {
    setType(newType);
    setXpReward(DEFAULT_XP[newType]);
  }

  function buildContentJson(): Record<string, unknown> {
    if (type === 'card') return { title: cardTitle, body: cardBody };
    if (type === 'quiz') return { question, choices, answer_index: answerIndex, explanation };
    if (type === 'video') {
      return videoSource === 'hosted'
        ? { video_source: 'hosted', video_url: videoUrl, caption: videoCaption }
        : { video_source: 'youtube', youtube_id: extractYoutubeId(youtubeInput), caption: videoCaption };
    }
    return { prompt, choices: scenarioChoices, correct_index: correctIndex };
  }

  function buildApplyMission(): ApplyMission | null {
    if (!missionEnabled) return null;
    const params =
      missionType === 'diversify' ? { n: Number(missionN) }
      : missionType === 'invest_amount' ? { amount: missionAmount }
      : {};
    return {
      mission_type: missionType,
      params_json: params,
      title: missionTitle,
      prompt: missionPrompt,
      xp_reward: Number(missionXp),
      cash_reward: missionCash ? missionCash : null,
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (type === 'video' && videoSource === 'hosted' && !videoUrl) {
      setUploadErr('Please upload a video file first.');
      return;
    }
    const content_json = buildContentJson();
    const apply_mission = buildApplyMission();
    if (isEdit && lesson) {
      await updateLesson.mutateAsync({ id: lesson.id, type, content_json, xp_reward: xpReward, apply_mission });
    } else if (levelId) {
      await createLevelLesson.mutateAsync({ type, content_json, xp_reward: xpReward, order_index: nextOrderIndex, apply_mission });
    } else {
      await createLesson.mutateAsync({ moduleId, type, content_json, xp_reward: xpReward, order_index: nextOrderIndex, apply_mission });
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded-lg border border-line bg-card p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="mb-4 text-lg font-semibold text-ink">
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
                  type === t ? 'bg-brand-600 text-white' : 'border border-input text-muted-foreground'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* XP Reward */}
          <div>
            <label htmlFor="lesson-xp" className="mb-1 block text-sm text-ink">XP Reward</label>
            <input id="lesson-xp" type="number" value={xpReward} onChange={(e) => setXpReward(Number(e.target.value))}
              className="w-24 rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>

          {/* Card fields */}
          {type === 'card' && (
            <>
              <div>
                <label htmlFor="card-title" className="mb-1 block text-sm text-ink">Title</label>
                <input id="card-title" value={cardTitle} onChange={(e) => setCardTitle(e.target.value)} required
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
              </div>
              <div>
                <label htmlFor="card-body" className="mb-1 block text-sm text-ink">Body</label>
                <textarea id="card-body" value={cardBody} onChange={(e) => setCardBody(e.target.value)} required rows={3}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
              </div>
            </>
          )}

          {/* Quiz fields */}
          {type === 'quiz' && (
            <>
              <div>
                <label htmlFor="quiz-question" className="mb-1 block text-sm text-ink">Question</label>
                <input id="quiz-question" value={question} onChange={(e) => setQuestion(e.target.value)} required
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
              </div>
              <div>
                <span className="mb-1 block text-sm text-ink">Choices</span>
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
                      className="flex-1 rounded-md border border-input bg-background px-3 py-1 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
                      placeholder={`Choice ${i + 1}`}
                      required
                    />
                    {choices.length > 2 && (
                      <button type="button" onClick={() => {
                        const nc = choices.filter((_, j) => j !== i);
                        setChoices(nc);
                        if (answerIndex >= nc.length) setAnswerIndex(nc.length - 1);
                      }} className="text-danger-500">✕</button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => setChoices([...choices, ''])}
                  className="text-sm text-brand-600">+ Add Choice</button>
              </div>
              <div>
                <label htmlFor="quiz-explanation" className="mb-1 block text-sm text-ink">Explanation</label>
                <input id="quiz-explanation" value={explanation} onChange={(e) => setExplanation(e.target.value)} required
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
              </div>
            </>
          )}

          {/* Scenario fields */}
          {type === 'scenario' && (
            <>
              <div>
                <label htmlFor="scenario-prompt" className="mb-1 block text-sm text-ink">Prompt</label>
                <textarea id="scenario-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} required rows={2}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
              </div>
              <div>
                <span className="mb-1 block text-sm text-ink">Choices</span>
                {scenarioChoices.map((c, i) => (
                  <div key={i} className="mb-3 rounded-md border border-line bg-card p-3">
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
                        className="flex-1 rounded-md border border-input bg-background px-3 py-1 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
                        placeholder="Label"
                        required
                      />
                      {scenarioChoices.length > 2 && (
                        <button type="button" onClick={() => {
                          const nc = scenarioChoices.filter((_, j) => j !== i);
                          setScenarioChoices(nc);
                          if (correctIndex >= nc.length) setCorrectIndex(nc.length - 1);
                        }} className="text-danger-500">✕</button>
                      )}
                    </div>
                    <input
                      value={c.outcome}
                      onChange={(e) => { const nc = [...scenarioChoices]; nc[i] = { ...nc[i], outcome: e.target.value }; setScenarioChoices(nc); }}
                      className="ml-6 w-[calc(100%-1.5rem)] rounded-md border border-input bg-background px-3 py-1 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
                      placeholder="Outcome message"
                      required
                    />
                  </div>
                ))}
                <button type="button" onClick={() => setScenarioChoices([...scenarioChoices, { label: '', outcome: '' }])}
                  className="text-sm text-brand-600">+ Add Choice</button>
              </div>
            </>
          )}

          {/* Video fields */}
          {type === 'video' && (
            <>
              <fieldset>
                <legend className="mb-1 block text-sm text-ink">Video source</legend>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input
                      type="radio"
                      name="video-source"
                      className="h-4 w-4"
                      checked={videoSource === 'youtube'}
                      onChange={() => setVideoSource('youtube')}
                    />
                    YouTube
                  </label>
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input
                      type="radio"
                      name="video-source"
                      className="h-4 w-4"
                      checked={videoSource === 'hosted'}
                      onChange={() => setVideoSource('hosted')}
                    />
                    Uploaded video
                  </label>
                </div>
              </fieldset>

              {videoSource === 'youtube' ? (
                <div>
                  <label htmlFor="video-youtube" className="mb-1 block text-sm text-ink">YouTube URL or ID</label>
                  <input id="video-youtube" value={youtubeInput} onChange={(e) => setYoutubeInput(e.target.value)} required
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
                    placeholder="Paste a YouTube link or 11-character ID." />
                </div>
              ) : (
                <div className="space-y-2">
                  <label htmlFor="video-file" className="mb-1 block text-sm text-ink">Video file (MP4, ≤200 MB)</label>
                  <input
                    id="video-file"
                    type="file"
                    accept="video/mp4"
                    className="block w-full text-sm text-ink file:mr-3 file:rounded-md file:border file:border-input file:bg-background file:px-3 file:py-1 file:text-sm file:text-ink"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleVideoFile(f); }}
                  />
                  {uploadPct !== null && (
                    <p className="text-sm text-muted-foreground">Uploading… {uploadPct}%</p>
                  )}
                  {videoUrl && (
                    <video
                      aria-label="Uploaded video preview"
                      className="mt-2 w-full max-w-md rounded-md border border-input"
                      src={videoUrl}
                      controls
                      playsInline
                      preload="metadata"
                    >
                      <track kind="captions" />
                    </video>
                  )}
                  {uploadErr && <p className="text-sm text-danger-600">{uploadErr}</p>}
                </div>
              )}

              <div>
                <label htmlFor="video-caption" className="mb-1 block text-sm text-ink">Caption</label>
                <input id="video-caption" value={videoCaption} onChange={(e) => setVideoCaption(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
              </div>
            </>
          )}

          {/* Apply-mission block */}
          <div className="mt-2 border-t border-line pt-4">
            <div className="flex items-center gap-2">
              <input id="mission-enabled" type="checkbox" checked={missionEnabled}
                onChange={(e) => setMissionEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-input bg-background" />
              <label htmlFor="mission-enabled" className="text-sm text-ink">Apply mission (simulator)</label>
            </div>

            {missionEnabled && (
              <div className="mt-3 flex flex-col gap-3">
                <div>
                  <label htmlFor="mission-type" className="mb-1 block text-sm text-ink">Mission type</label>
                  <select id="mission-type" value={missionType}
                    onChange={(e) => setMissionType(e.target.value as MissionType)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink focus:ring-2 focus:ring-brand-300">
                    {MISSION_TYPES.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>

                {missionType === 'diversify' && (
                  <div>
                    <label htmlFor="mission-n" className="mb-1 block text-sm text-ink">Number of stocks (N)</label>
                    <input id="mission-n" type="number" min="1" step="1" value={missionN}
                      onChange={(e) => setMissionN(e.target.value)}
                      className="w-24 rounded-md border border-input bg-background px-3 py-2 text-base text-ink focus:ring-2 focus:ring-brand-300" />
                  </div>
                )}

                {missionType === 'invest_amount' && (
                  <div>
                    <label htmlFor="mission-amount" className="mb-1 block text-sm text-ink">Amount to invest</label>
                    <input id="mission-amount" type="number" min="0" step="0.01" value={missionAmount}
                      onChange={(e) => setMissionAmount(e.target.value)}
                      className="w-40 rounded-md border border-input bg-background px-3 py-2 text-base text-ink focus:ring-2 focus:ring-brand-300" />
                  </div>
                )}

                <div>
                  <label htmlFor="mission-title" className="mb-1 block text-sm text-ink">Mission title</label>
                  <input id="mission-title" value={missionTitle}
                    onChange={(e) => setMissionTitle(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
                </div>

                <div>
                  <label htmlFor="mission-prompt" className="mb-1 block text-sm text-ink">Mission prompt</label>
                  <textarea id="mission-prompt" value={missionPrompt} rows={2}
                    onChange={(e) => setMissionPrompt(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
                </div>

                <div className="flex gap-4">
                  <div>
                    <label htmlFor="mission-xp" className="mb-1 block text-sm text-ink">Mission XP</label>
                    <input id="mission-xp" type="number" min="0" step="1" value={missionXp}
                      onChange={(e) => setMissionXp(e.target.value)}
                      className="w-24 rounded-md border border-input bg-background px-3 py-2 text-base text-ink focus:ring-2 focus:ring-brand-300" />
                  </div>
                  <div>
                    <label htmlFor="mission-cash" className="mb-1 block text-sm text-ink">Mission cash reward (optional)</label>
                    <input id="mission-cash" type="number" min="0" step="0.01" value={missionCash}
                      onChange={(e) => setMissionCash(e.target.value)} placeholder="None"
                      className="w-40 rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-2 flex gap-3">
            <button type="submit" className="rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700">
              {isEdit ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={onClose}
              className="rounded-md border border-line px-6 py-2 text-sm text-muted-foreground hover:bg-brand-50">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
