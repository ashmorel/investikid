export type GateChallenge = { a: number; b: number; prompt: string; answer: number };

/** A small "ask a grown-up" arithmetic challenge. Friction, NOT authentication —
 *  the real spend authorization is the OS purchase sheet + Ask-to-Buy. */
export function makeChallenge(rng: () => number = Math.random): GateChallenge {
  const a = 3 + Math.floor(rng() * 7); // 3..9
  const b = 3 + Math.floor(rng() * 7); // 3..9
  return { a, b, prompt: `${a} × ${b}`, answer: a * b };
}

export function checkAnswer(c: GateChallenge, input: string): boolean {
  const n = Number(input.trim());
  return Number.isInteger(n) && n === c.answer;
}
