import '@testing-library/jest-dom/vitest';
import { expect } from 'vitest';
import * as matchers from 'vitest-axe/matchers';

// Matcher TS typing lives in `tests/vitest-axe.d.ts` (vitest-axe's
// bundled extend-expect.d.ts only augments the legacy `Vi.Assertion`
// global). Runtime registration happens here.
expect.extend(matchers);
