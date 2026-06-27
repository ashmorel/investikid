const KEY = 'ik:visitedSimulator';

export function markSimulatorVisited(): void {
  try { localStorage.setItem(KEY, '1'); } catch { /* private mode — best effort */ }
}

export function hasVisitedSimulator(): boolean {
  try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
}
