// Run once: node scripts/generate-icons.js
const fs = require('fs');
const path = require('path');

const sizes = [192, 512];
const outDir = path.join(__dirname, '..', 'public', 'icons');
fs.mkdirSync(outDir, { recursive: true });

for (const size of sizes) {
  const r = size / 2;
  const fontSize = Math.round(size * 0.32);

  const regularSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#f97316"/>
    </linearGradient>
  </defs>
  <circle cx="${r}" cy="${r}" r="${r}" fill="url(#g)"/>
  <text x="${r}" y="${r}" dy="0.35em" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="800" font-size="${fontSize}" fill="white">IE</text>
</svg>`;

  const pad = Math.round(size * 0.1);
  const innerR = r - pad;
  const maskableSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect width="${size}" height="${size}" fill="#fffbeb"/>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#f97316"/>
    </linearGradient>
  </defs>
  <circle cx="${r}" cy="${r}" r="${innerR}" fill="url(#g)"/>
  <text x="${r}" y="${r}" dy="0.35em" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="800" font-size="${fontSize}" fill="white">IE</text>
</svg>`;

  fs.writeFileSync(path.join(outDir, `icon-${size}.svg`), regularSvg);
  fs.writeFileSync(path.join(outDir, `icon-${size}-maskable.svg`), maskableSvg);
  console.log(`Generated ${size}x${size} regular + maskable`);
}

console.log('Done. Icons in public/icons/');
