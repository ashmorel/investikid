import { readdirSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pseudoTree } from './pseudo-transform.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const enDir = join(here, '..', 'src', 'locales', 'en');
const xaDir = join(here, '..', 'src', 'locales', 'en-XA');
mkdirSync(xaDir, { recursive: true });
for (const f of readdirSync(enDir).filter((n) => n.endsWith('.json'))) {
  const src = JSON.parse(readFileSync(join(enDir, f), 'utf-8'));
  writeFileSync(join(xaDir, f), JSON.stringify(pseudoTree(src), null, 2));
}
console.log('Generated en-XA pseudo-locale.');
