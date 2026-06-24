import type { ReactNode } from 'react';

// Skin = Penny body-gradient recolour, keyed by CosmeticItem.slug. No skin → classic (mood) gradient.
export const SKIN: Record<string, [string, string]> = {
  skin_pink: ['#f9a8d4', '#db2777'],
  skin_sky: ['#38bdf8', '#2563eb'],
  skin_mint: ['#6ee7b7', '#059669'],
  skin_gold: ['#fcd34d', '#d97706'],
  skin_lavender: ['#c4b5fd', '#7c3aed'],
};

// BACKGROUND scenes — decorative physical-colour scenes drawn in a 0–100 viewBox, behind Penny.
// Hardcoded hex is intentional (do NOT theme these).
export const BACKGROUND: Record<string, ReactNode> = {
  bg_beach: (
    <>
      <defs>
        <linearGradient id="bgBeachSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#bae6fd" />
          <stop offset="1" stopColor="#e0f2fe" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill="url(#bgBeachSky)" />
      <circle cx="80" cy="22" r="16" fill="#fde047" fillOpacity="0.35" />
      <circle cx="80" cy="22" r="10" fill="#fde047" />
      <circle cx="80" cy="22" r="7" fill="#fef08a" />
      <ellipse cx="28" cy="30" rx="9" ry="5" fill="#ffffff" fillOpacity="0.95" />
      <ellipse cx="36" cy="31" rx="7" ry="4" fill="#ffffff" fillOpacity="0.95" />
      <ellipse cx="60" cy="16" rx="7" ry="4" fill="#ffffff" fillOpacity="0.9" />
      <rect y="62" width="100" height="14" fill="#38bdf8" />
      <rect y="62" width="100" height="2" fill="#7dd3fc" />
      <rect y="74" width="100" height="26" fill="#fde68a" />
      <ellipse cx="50" cy="74" rx="72" ry="9" fill="#fcd34d" />
      <rect y="88" width="100" height="12" fill="#fcd34d" fillOpacity="0.6" />
    </>
  ),
  bg_forest: (
    <>
      <defs>
        <linearGradient id="bgForestSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#bae6fd" />
          <stop offset="1" stopColor="#e0f7ff" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill="url(#bgForestSky)" />
      <circle cx="80" cy="20" r="9" fill="#fde047" fillOpacity="0.85" />
      <ellipse cx="50" cy="72" rx="72" ry="15" fill="#bbf7d0" />
      <rect y="74" width="100" height="26" fill="#86efac" />
      <rect y="74" width="100" height="2" fill="#bbf7d0" />
      <rect x="24" y="58" width="3" height="17" fill="#a16207" />
      <polygon points="25.5,40 16,60 35,60" fill="#16a34a" />
      <polygon points="25.5,46 18,62 33,62" fill="#15803d" />
      <rect x="70" y="60" width="3" height="15" fill="#a16207" />
      <polygon points="71.5,46 63,64 80,64" fill="#16a34a" />
      <ellipse cx="50" cy="71" rx="9" ry="6.5" fill="#22c55e" />
    </>
  ),
  bg_city: (
    <>
      <defs>
        <linearGradient id="bgCitySky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#4338ca" />
          <stop offset="0.6" stopColor="#3730a3" />
          <stop offset="1" stopColor="#0b1226" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill="url(#bgCitySky)" />
      <circle cx="78" cy="20" r="8" fill="#fcd34d" fillOpacity="0.9" />
      <rect x="8" y="50" width="16" height="50" fill="#312e81" />
      <rect x="64" y="44" width="18" height="56" fill="#312e81" />
      <rect x="22" y="58" width="14" height="42" fill="#475569" />
      <rect x="40" y="46" width="16" height="54" fill="#334155" />
      <rect x="58" y="56" width="14" height="44" fill="#475569" />
      <rect x="78" y="40" width="14" height="60" fill="#334155" />
      <rect x="26" y="62" width="2.5" height="2.5" fill="#fbbf24" />
      <rect x="31" y="62" width="2.5" height="2.5" fill="#fbbf24" />
      <rect x="45" y="50" width="2.5" height="2.5" fill="#fbbf24" />
      <rect x="50" y="56" width="2.5" height="2.5" fill="#fbbf24" />
      <rect x="62" y="60" width="2.5" height="2.5" fill="#fbbf24" />
      <rect x="82" y="44" width="2.5" height="2.5" fill="#fbbf24" />
      <rect x="82" y="50" width="2.5" height="2.5" fill="#fbbf24" />
    </>
  ),
  bg_space: (
    <>
      <defs>
        <linearGradient id="bgSpaceSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3730a3" />
          <stop offset="1" stopColor="#0b1026" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill="url(#bgSpaceSky)" />
      <circle cx="14" cy="16" r="1.4" fill="#fff" />
      <circle cx="30" cy="9" r="1" fill="#fff" />
      <circle cx="52" cy="14" r="1.5" fill="#fff" />
      <circle cx="68" cy="8" r="0.9" fill="#fff" />
      <circle cx="88" cy="20" r="1.2" fill="#fff" />
      <circle cx="20" cy="44" r="1" fill="#fff" />
      <circle cx="44" cy="54" r="0.8" fill="#fff" />
      <circle cx="92" cy="48" r="1.3" fill="#fff" />
      <circle cx="10" cy="70" r="1" fill="#fff" />
      <circle cx="36" cy="78" r="0.9" fill="#fff" />
      <circle cx="62" cy="86" r="1.1" fill="#fff" />
      <circle cx="84" cy="74" r="0.8" fill="#fff" />
      <ellipse cx="74" cy="30" rx="17" ry="5" fill="none" stroke="#c4b5fd" strokeWidth="2.2" />
      <circle cx="74" cy="30" r="9" fill="#a78bfa" />
      <ellipse cx="77.5" cy="31.5" rx="6.5" ry="7" fill="#7c3aed" fillOpacity="0.55" />
      <circle cx="20" cy="22" r="6" fill="#fde68a" />
      <circle cx="22.5" cy="20.5" r="5" fill="#3730a3" />
    </>
  ),
  bg_vault: (
    <>
      <defs>
        <linearGradient id="bgVaultBg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fffbeb" />
          <stop offset="1" stopColor="#fde68a" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill="url(#bgVaultBg)" />
      <circle cx="50" cy="40" r="22" fill="#fcd34d" fillOpacity="0.45" />
      <circle cx="50" cy="40" r="16" fill="none" stroke="#f59e0b" strokeWidth="2" />
      <circle cx="50" cy="40" r="3" fill="#f59e0b" />
      <circle cx="50" cy="26" r="1.4" fill="#f59e0b" />
      <circle cx="64" cy="40" r="1.4" fill="#f59e0b" />
      <circle cx="50" cy="54" r="1.4" fill="#f59e0b" />
      <circle cx="36" cy="40" r="1.4" fill="#f59e0b" />
      <rect x="20" y="80" width="26" height="8" rx="2" fill="#f59e0b" />
      <rect x="24" y="72" width="20" height="8" rx="2" fill="#fbbf24" />
      <rect x="54" y="80" width="26" height="8" rx="2" fill="#f59e0b" />
      <rect x="58" y="72" width="20" height="8" rx="2" fill="#fbbf24" />
      <circle cx="50" cy="84" r="5" fill="#fcd34d" stroke="#f59e0b" strokeWidth="1" />
    </>
  ),
};
