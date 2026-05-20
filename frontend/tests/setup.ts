import '@testing-library/jest-dom/vitest';
import { expect } from 'vitest';
import * as matchers from 'vitest-axe/matchers';

expect.extend(matchers);

// Make TS happy for the custom matcher across the suite.
declare module 'vitest' {
  interface Assertion<T = unknown> extends matchers.TestingLibraryMatchers<unknown, T> {
    toHaveNoViolations(): Promise<void>;
  }
}
