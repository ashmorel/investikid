/**
 * Web Audio sound effects — synthesized, no assets (juice pack, spec A).
 * Gains stay ≤ 0.15: kids' ears, never startling. Silent no-op when muted
 * or when AudioContext is unavailable (jsdom / old browsers).
 */

export type SoundName =
  | 'correct' | 'wrong' | 'lessonComplete' | 'mastery'
  | 'xpTick' | 'streak' | 'badge' | 'trade';

export interface Tone {
  /** Start frequency in Hz. */
  freq: number;
  /** Optional sweep target frequency (whooshes). */
  freqEnd?: number;
  /** Tone length in seconds. */
  duration: number;
  type: OscillatorType;
  /** Peak gain — keep ≤ 0.15. */
  gain: number;
  /** Start offset from playback begin, in seconds. */
  at: number;
}

// Note frequencies (equal temperament).
const G3 = 196, C5 = 523.25, E5 = 659.25, G5 = 783.99, C6 = 1046.5;
const E6 = 1318.51, G6 = 1567.98, B6 = 1975.53;

export const SOUND_RECIPES: Record<SoundName, Tone[]> = {
  // Bright two-note ding.
  correct: [
    { freq: E5, duration: 0.08, type: 'sine', gain: 0.12, at: 0 },
    { freq: G5, duration: 0.1, type: 'sine', gain: 0.12, at: 0.08 },
  ],
  // Soft low "doot" — never harsh.
  wrong: [{ freq: G3, duration: 0.15, type: 'triangle', gain: 0.08, at: 0 }],
  // Three-note rising.
  lessonComplete: [
    { freq: C5, duration: 0.1, type: 'sine', gain: 0.12, at: 0 },
    { freq: E5, duration: 0.1, type: 'sine', gain: 0.12, at: 0.1 },
    { freq: G5, duration: 0.16, type: 'sine', gain: 0.12, at: 0.2 },
  ],
  // Bigger four-note fanfare.
  mastery: [
    { freq: C5, duration: 0.11, type: 'sine', gain: 0.13, at: 0 },
    { freq: E5, duration: 0.11, type: 'sine', gain: 0.13, at: 0.11 },
    { freq: G5, duration: 0.11, type: 'sine', gain: 0.13, at: 0.22 },
    { freq: C6, duration: 0.22, type: 'sine', gain: 0.13, at: 0.33 },
  ],
  // Tiny click — rapid-fire safe at low gain.
  xpTick: [{ freq: 2000, duration: 0.02, type: 'sine', gain: 0.05, at: 0 }],
  // Rising whoosh + pop.
  streak: [
    { freq: 300, freqEnd: 900, duration: 0.18, type: 'sine', gain: 0.08, at: 0 },
    { freq: 1200, duration: 0.05, type: 'square', gain: 0.1, at: 0.18 },
  ],
  // Sparkle arpeggio.
  badge: [
    { freq: E6, duration: 0.06, type: 'sine', gain: 0.1, at: 0 },
    { freq: G6, duration: 0.06, type: 'sine', gain: 0.1, at: 0.05 },
    { freq: B6, duration: 0.1, type: 'sine', gain: 0.1, at: 0.1 },
  ],
  // Woodblock-ish click + soft chime.
  trade: [
    { freq: 800, duration: 0.06, type: 'square', gain: 0.1, at: 0 },
    { freq: E6, duration: 0.12, type: 'sine', gain: 0.08, at: 0.06 },
  ],
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

function playTones(audio: AudioContext, tones: Tone[]): void {
  const now = audio.currentTime;
  for (const tone of tones) {
    const start = now + tone.at;
    const end = start + tone.duration;
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = tone.type;
    osc.frequency.setValueAtTime(tone.freq, start);
    if (tone.freqEnd) osc.frequency.exponentialRampToValueAtTime(tone.freqEnd, end);
    // Quick attack, exponential decay — no clicks, no startle.
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.linearRampToValueAtTime(tone.gain, start + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, end);
    osc.connect(gain);
    gain.connect(audio.destination);
    osc.start(start);
    osc.stop(end + 0.05);
  }
}

/** Play a named sound. Total no-op when muted or audio is unavailable. */
export function playSound(name: SoundName): void {
  if (!isSoundEnabled()) return;
  const audio = getContext();
  if (!audio) return;
  try {
    if (audio.state === 'suspended') void audio.resume();
    playTones(audio, SOUND_RECIPES[name]);
  } catch {
    // Never let a sound effect break the app.
  }
}
