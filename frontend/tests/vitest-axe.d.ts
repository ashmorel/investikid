// Local ambient augmentation: vitest-axe's bundled `extend-expect.d.ts`
// only augments the legacy global `Vi.Assertion` namespace, but our tests
// `expect(...)` against `Assertion<T>` from the `vitest` module. Mirror the
// matcher shape onto vitest's `Assertion` (and `AsymmetricMatchersContaining`)
// so `toHaveNoViolations()` typechecks under `tsc -b`.
//
// Runtime registration still happens in `tests/setup.ts` via
// `expect.extend(matchers)`.

import 'vitest';

declare module 'vitest' {
  interface Assertion {
    toHaveNoViolations(): void;
  }
  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): void;
  }
}

export {};
