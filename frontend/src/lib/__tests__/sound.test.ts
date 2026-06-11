import { describe, it, expect, beforeEach, vi } from 'vitest';

/** Minimal fake Web Audio graph that records node creation. */
function makeFakeAudioContext() {
  const param = () => ({
    setValueAtTime: vi.fn(),
    linearRampToValueAtTime: vi.fn(),
    exponentialRampToValueAtTime: vi.fn(),
  });
  const createOscillator = vi.fn(() => ({
    type: 'sine',
    frequency: param(),
    connect: vi.fn((node: unknown) => node),
    start: vi.fn(),
    stop: vi.fn(),
  }));
  const createGain = vi.fn(() => ({
    gain: param(),
    connect: vi.fn((node: unknown) => node),
  }));
  const ctx = {
    currentTime: 0,
    state: 'running',
    destination: {},
    resume: vi.fn(async () => {}),
    createOscillator,
    createGain,
  };
  return { ctx, createOscillator, createGain };
}

async function freshSound() {
  vi.resetModules();
  return await import('../sound');
}

beforeEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
});

describe('sound enable/disable', () => {
  it('is enabled by default', async () => {
    const { isSoundEnabled } = await freshSound();
    expect(isSoundEnabled()).toBe(true);
  });

  it('setSoundEnabled(false) persists and isSoundEnabled reflects it', async () => {
    const { isSoundEnabled, setSoundEnabled } = await freshSound();
    setSoundEnabled(false);
    expect(isSoundEnabled()).toBe(false);
    expect(localStorage.getItem('investikid-sound')).toBe('0');
    setSoundEnabled(true);
    expect(isSoundEnabled()).toBe(true);
  });
});

describe('playSound', () => {
  it('never throws in jsdom (no AudioContext available)', async () => {
    const { playSound } = await freshSound();
    expect(() => playSound('correct')).not.toThrow();
    expect(() => playSound('xpTick')).not.toThrow();
  });

  it('creates oscillator/gain nodes for a known recipe when AudioContext exists', async () => {
    const { ctx, createOscillator, createGain } = makeFakeAudioContext();
    vi.stubGlobal('AudioContext', vi.fn(() => ctx));
    const { playSound, SOUND_RECIPES } = await freshSound();

    playSound('correct');
    // Layered voices (harmonics/detune) mean MORE oscillators than tones.
    expect(createOscillator.mock.calls.length).toBeGreaterThanOrEqual(
      SOUND_RECIPES.correct.tones.length,
    );
    expect(createGain.mock.calls.length).toBeGreaterThanOrEqual(
      SOUND_RECIPES.correct.tones.length,
    );
  });

  it('does NOT create nodes when muted', async () => {
    const { ctx, createOscillator } = makeFakeAudioContext();
    vi.stubGlobal('AudioContext', vi.fn(() => ctx));
    const { playSound, setSoundEnabled } = await freshSound();

    setSoundEnabled(false);
    playSound('correct');
    expect(createOscillator).not.toHaveBeenCalled();
  });

  it('resumes a suspended context before playing', async () => {
    const fake = makeFakeAudioContext();
    fake.ctx.state = 'suspended';
    vi.stubGlobal('AudioContext', vi.fn(() => fake.ctx));
    const { playSound } = await freshSound();

    playSound('trade');
    expect(fake.ctx.resume).toHaveBeenCalled();
  });
});

describe('recipe registry', () => {
  it('contains all 8 sound names with non-empty tone lists and kid-safe gains', async () => {
    const { SOUND_RECIPES } = await freshSound();
    const names = [
      'correct', 'wrong', 'lessonComplete', 'mastery',
      'xpTick', 'streak', 'badge', 'trade',
    ] as const;
    expect(Object.keys(SOUND_RECIPES).sort()).toEqual([...names].sort());
    for (const name of names) {
      const recipe = SOUND_RECIPES[name];
      expect(recipe.tones.length).toBeGreaterThan(0);
      for (const tone of recipe.tones) expect(tone.gain).toBeLessThanOrEqual(0.15);
      for (const noise of recipe.noises ?? []) expect(noise.gain).toBeLessThanOrEqual(0.1);
    }
  });
});
