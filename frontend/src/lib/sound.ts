/**
 * Web Audio sound effects — synthesized, no assets (juice pack, spec A).
 *
 * Each sound is a tiny composition: layered harmonics for warmth, detuned
 * double-voices for thickness, percussive exponential envelopes (marimba-like
 * plucks), vibrato wobbles, filtered-noise sparkle, and a touch of echo on the
 * fanfares. Everything routes through a master gain + compressor so stacked
 * voices can never clip or startle (kids' ears first).
 *
 * Silent no-op when muted or when AudioContext is unavailable (jsdom / old
 * browsers); every non-essential node type is feature-detected.
 */

export type SoundName =
  | 'correct' | 'wrong' | 'lessonComplete' | 'mastery'
  | 'xpTick' | 'streak' | 'badge' | 'trade';

export interface Tone {
  /** Start frequency in Hz. */
  freq: number;
  /** Optional sweep target frequency (whooshes / pitch bends). */
  freqEnd?: number;
  /** Tone length in seconds. */
  duration: number;
  type: OscillatorType;
  /** Peak gain — keep ≤ 0.15 per voice. */
  gain: number;
  /** Start offset from playback begin, in seconds. */
  at: number;
  /** Extra partials as frequency multipliers (e.g. [2, 3] adds octave + twelfth). */
  harmonics?: number[];
  /** Adds a second voice detuned by ± this many cents (chorus thickness). */
  detune?: number;
  /** Playful pitch wobble. */
  vibrato?: { freq: number; depth: number };
  /** Percussive pluck: instant attack, exponential decay (marimba/bell feel). */
  perc?: boolean;
}

export interface Noise {
  at: number;
  duration: number;
  /** Keep ≤ 0.1 — noise reads louder than tones. */
  gain: number;
  /** Bandpass centre frequency. */
  freq: number;
  /** Optional sweep target for shimmer rises. */
  freqEnd?: number;
  q?: number;
}

export interface Recipe {
  tones: Tone[];
  noises?: Noise[];
  /** Subtle feedback echo (fanfares only). */
  echo?: { delay: number; feedback: number; level: number };
}

// Note frequencies (equal temperament).
const A3 = 220, D4 = 293.66, C5 = 523.25, E5 = 659.25, G5 = 783.99;
const C6 = 1046.5, E6 = 1318.51, G6 = 1567.98, B6 = 1975.53, A6 = 1760;
// Bell timbre: an inharmonic partial makes sines ring like a real bell.
const BELL = [2.76];

export const SOUND_RECIPES: Record<SoundName, Recipe> = {
  // Playful marimba triplet rising to a sparkle — "yes!"
  correct: {
    tones: [
      { freq: E5, duration: 0.14, type: 'sine', gain: 0.13, at: 0, harmonics: [3], detune: 6, perc: true },
      { freq: G5, duration: 0.14, type: 'sine', gain: 0.13, at: 0.07, harmonics: [3], detune: 6, perc: true },
      { freq: C6, duration: 0.22, type: 'sine', gain: 0.14, at: 0.14, harmonics: [2], detune: 6, perc: true },
    ],
    noises: [{ at: 0.14, duration: 0.16, gain: 0.035, freq: 6000, freqEnd: 9000, q: 1.2 }],
  },
  // Friendly comedic "boo-boop" — a shrug, never a buzzer.
  wrong: {
    tones: [
      { freq: D4, freqEnd: D4 * 0.94, duration: 0.12, type: 'sine', gain: 0.09, at: 0, harmonics: [2], perc: true },
      { freq: A3, freqEnd: A3 * 0.92, duration: 0.16, type: 'sine', gain: 0.08, at: 0.13, harmonics: [2], perc: true },
    ],
  },
  // Four-note arpeggio with echo + sparkle — a small earned fanfare.
  lessonComplete: {
    tones: [
      { freq: C5, duration: 0.16, type: 'sine', gain: 0.12, at: 0, harmonics: [2], detune: 5, perc: true },
      { freq: E5, duration: 0.16, type: 'sine', gain: 0.12, at: 0.09, harmonics: [2], detune: 5, perc: true },
      { freq: G5, duration: 0.16, type: 'sine', gain: 0.12, at: 0.18, harmonics: [2], detune: 5, perc: true },
      { freq: C6, duration: 0.32, type: 'sine', gain: 0.13, at: 0.27, harmonics: [2, 3], detune: 5, perc: true },
    ],
    noises: [{ at: 0.27, duration: 0.25, gain: 0.04, freq: 5000, freqEnd: 9500, q: 1.2 }],
    echo: { delay: 0.13, feedback: 0.25, level: 0.18 },
  },
  // The big one: timpani thump, brassy fanfare, closing high chord + shimmer.
  mastery: {
    tones: [
      { freq: 180, freqEnd: 85, duration: 0.28, type: 'sine', gain: 0.13, at: 0, perc: true },
      { freq: C5, duration: 0.14, type: 'triangle', gain: 0.11, at: 0.05, harmonics: [2], detune: 7, perc: true },
      { freq: E5, duration: 0.14, type: 'triangle', gain: 0.11, at: 0.15, harmonics: [2], detune: 7, perc: true },
      { freq: G5, duration: 0.14, type: 'triangle', gain: 0.11, at: 0.25, harmonics: [2], detune: 7, perc: true },
      // Closing chord — three voices at once (compressor keeps the sum safe).
      { freq: C6, duration: 0.55, type: 'sine', gain: 0.09, at: 0.36, harmonics: [2], detune: 6, perc: true },
      { freq: E6, duration: 0.55, type: 'sine', gain: 0.08, at: 0.36, detune: 6, perc: true },
      { freq: G6, duration: 0.55, type: 'sine', gain: 0.08, at: 0.36, detune: 6, perc: true },
    ],
    noises: [{ at: 0.33, duration: 0.5, gain: 0.045, freq: 4000, freqEnd: 11000, q: 1 }],
    echo: { delay: 0.15, feedback: 0.3, level: 0.2 },
  },
  // Cute upward chirp — rapid-fire safe.
  xpTick: {
    tones: [{ freq: 1400, freqEnd: 2000, duration: 0.035, type: 'sine', gain: 0.06, at: 0, perc: true }],
  },
  // Rising wobble-gliss with a double pop and shimmer — momentum!
  streak: {
    tones: [
      { freq: 350, freqEnd: 1050, duration: 0.22, type: 'sine', gain: 0.09, at: 0, vibrato: { freq: 9, depth: 14 } },
      { freq: 1100, duration: 0.05, type: 'square', gain: 0.1, at: 0.2, perc: true },
      { freq: 1480, duration: 0.07, type: 'square', gain: 0.1, at: 0.26, perc: true },
    ],
    noises: [{ at: 0.2, duration: 0.16, gain: 0.04, freq: 6500, freqEnd: 9000, q: 1.5 }],
  },
  // Two bright bell strikes (inharmonic partials ring like real metal).
  badge: {
    tones: [
      { freq: E6, duration: 0.28, type: 'sine', gain: 0.11, at: 0, harmonics: BELL, perc: true },
      { freq: B6, duration: 0.34, type: 'sine', gain: 0.1, at: 0.12, harmonics: BELL, perc: true },
    ],
    noises: [{ at: 0.12, duration: 0.2, gain: 0.035, freq: 7000, freqEnd: 10000, q: 1.3 }],
  },
  // "Ka-ching": click + low thunk + two coin bells.
  trade: {
    tones: [
      { freq: 220, duration: 0.08, type: 'sine', gain: 0.08, at: 0, perc: true },
      { freq: E6, duration: 0.18, type: 'sine', gain: 0.1, at: 0.05, harmonics: BELL, perc: true },
      { freq: A6, duration: 0.22, type: 'sine', gain: 0.1, at: 0.13, harmonics: BELL, perc: true },
    ],
    noises: [{ at: 0, duration: 0.03, gain: 0.09, freq: 3000, q: 0.8 }],
    echo: { delay: 0.1, feedback: 0.18, level: 0.12 },
  },
};

const STORAGE_KEY = 'investikid-sound';

export function isSoundEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== '0';
  } catch {
    return true;
  }
}

export function setSoundEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0');
  } catch {
    // Storage unavailable — sounds stay enabled for this session.
  }
}

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let noiseBuffer: AudioBuffer | null = null;

function getContext(): AudioContext | null {
  if (ctx) return ctx;
  if (typeof window === 'undefined') return null;
  const Ctor = window.AudioContext
    ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  try {
    ctx = new Ctor();
  } catch {
    return null;
  }
  return ctx;
}

/** Master gain → (compressor if available) → destination. Caps stacked voices. */
function getMaster(audio: AudioContext): AudioNode {
  if (master) return master;
  master = audio.createGain();
  master.gain.setValueAtTime(0.9, audio.currentTime);
  if (typeof audio.createDynamicsCompressor === 'function') {
    const comp = audio.createDynamicsCompressor();
    master.connect(comp);
    comp.connect(audio.destination);
  } else {
    master.connect(audio.destination);
  }
  return master;
}

function getNoiseBuffer(audio: AudioContext): AudioBuffer | null {
  if (noiseBuffer) return noiseBuffer;
  if (typeof audio.createBuffer !== 'function') return null;
  const length = Math.floor(audio.sampleRate * 0.6);
  noiseBuffer = audio.createBuffer(1, length, audio.sampleRate);
  const data = noiseBuffer.getChannelData(0);
  for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1;
  return noiseBuffer;
}

function envelope(gain: GainNode, peak: number, start: number, end: number, perc?: boolean): void {
  gain.gain.setValueAtTime(0.0001, start);
  // Perc = near-instant attack then exponential ring-down (pluck/bell feel).
  gain.gain.linearRampToValueAtTime(peak, start + (perc ? 0.004 : 0.012));
  gain.gain.exponentialRampToValueAtTime(0.0001, end);
}

function playVoice(
  audio: AudioContext, out: AudioNode, tone: Tone,
  freqMul: number, gainMul: number, detuneCents: number,
): void {
  const start = audio.currentTime + tone.at;
  const end = start + tone.duration;
  const osc = audio.createOscillator();
  const gain = audio.createGain();
  osc.type = tone.type;
  osc.frequency.setValueAtTime(tone.freq * freqMul, start);
  if (tone.freqEnd) osc.frequency.exponentialRampToValueAtTime(tone.freqEnd * freqMul, end);
  if (detuneCents && osc.detune) osc.detune.setValueAtTime(detuneCents, start);
  if (tone.vibrato) {
    const lfo = audio.createOscillator();
    const lfoGain = audio.createGain();
    lfo.frequency.setValueAtTime(tone.vibrato.freq, start);
    lfoGain.gain.setValueAtTime(tone.vibrato.depth, start);
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);
    lfo.start(start);
    lfo.stop(end + 0.05);
  }
  envelope(gain, tone.gain * gainMul, start, end, tone.perc);
  osc.connect(gain);
  gain.connect(out);
  osc.start(start);
  osc.stop(end + 0.05);
}

function playNoise(audio: AudioContext, out: AudioNode, noise: Noise): void {
  const buffer = getNoiseBuffer(audio);
  if (!buffer || typeof audio.createBufferSource !== 'function'
    || typeof audio.createBiquadFilter !== 'function') return;
  const start = audio.currentTime + noise.at;
  const end = start + noise.duration;
  const src = audio.createBufferSource();
  src.buffer = buffer;
  const filter = audio.createBiquadFilter();
  filter.type = 'bandpass';
  filter.frequency.setValueAtTime(noise.freq, start);
  if (noise.freqEnd) filter.frequency.exponentialRampToValueAtTime(noise.freqEnd, end);
  filter.Q.setValueAtTime(noise.q ?? 1, start);
  const gain = audio.createGain();
  envelope(gain, noise.gain, start, end, true);
  src.connect(filter);
  filter.connect(gain);
  gain.connect(out);
  src.start(start);
  src.stop(end + 0.05);
}

function playRecipe(audio: AudioContext, recipe: Recipe): void {
  const masterOut = getMaster(audio);
  // Per-play bus so an optional echo only colours this sound.
  const bus = audio.createGain();
  bus.gain.setValueAtTime(1, audio.currentTime);
  bus.connect(masterOut);

  if (recipe.echo && typeof audio.createDelay === 'function') {
    const delay = audio.createDelay(1);
    delay.delayTime.setValueAtTime(recipe.echo.delay, audio.currentTime);
    const feedback = audio.createGain();
    feedback.gain.setValueAtTime(recipe.echo.feedback, audio.currentTime);
    const level = audio.createGain();
    level.gain.setValueAtTime(recipe.echo.level, audio.currentTime);
    bus.connect(delay);
    delay.connect(feedback);
    feedback.connect(delay);
    delay.connect(level);
    level.connect(masterOut);
  }

  for (const tone of recipe.tones) {
    playVoice(audio, bus, tone, 1, 1, 0);
    if (tone.detune) playVoice(audio, bus, tone, 1, 0.5, tone.detune);
    for (const [i, h] of (tone.harmonics ?? []).entries()) {
      playVoice(audio, bus, tone, h, 0.35 / (i + 1), 0);
    }
  }
  for (const noise of recipe.noises ?? []) playNoise(audio, bus, noise);
}

/** Play a named sound. Total no-op when muted or audio is unavailable. */
export function playSound(name: SoundName): void {
  if (!isSoundEnabled()) return;
  const audio = getContext();
  if (!audio) return;
  try {
    if (audio.state === 'suspended') void audio.resume();
    playRecipe(audio, SOUND_RECIPES[name]);
  } catch {
    // Never let a sound effect break the app.
  }
}
