import { markSimulatorVisited, hasVisitedSimulator } from '@/lib/simulatorVisited';

beforeEach(() => localStorage.clear());

it('records and reports a simulator visit', () => {
  expect(hasVisitedSimulator()).toBe(false);
  markSimulatorVisited();
  expect(hasVisitedSimulator()).toBe(true);
});
