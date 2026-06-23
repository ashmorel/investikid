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
      <rect width="100" height="100" fill="#7dd3fc" />
      <rect y="64" width="100" height="36" fill="#fde68a" />
      <circle cx="82" cy="22" r="11" fill="#fde047" />
    </>
  ),
  bg_forest: (
    <>
      <rect width="100" height="100" fill="#bae6fd" />
      <rect y="70" width="100" height="30" fill="#86efac" />
      <polygon points="26,72 40,40 54,72" fill="#16a34a" />
      <polygon points="52,72 66,46 80,72" fill="#15803d" />
    </>
  ),
  bg_city: (
    <>
      <rect width="100" height="100" fill="#1e3a8a" />
      <rect x="14" y="52" width="14" height="48" fill="#475569" />
      <rect x="34" y="38" width="14" height="62" fill="#334155" />
      <rect x="54" y="48" width="14" height="52" fill="#475569" />
      <rect x="74" y="34" width="14" height="66" fill="#334155" />
      <rect x="18" y="58" width="3" height="3" fill="#fbbf24" />
      <rect x="78" y="42" width="3" height="3" fill="#fbbf24" />
    </>
  ),
  bg_space: (
    <>
      <rect width="100" height="100" fill="#1e1b4b" />
      <circle cx="18" cy="20" r="1.4" fill="#fff" />
      <circle cx="60" cy="14" r="1.4" fill="#fff" />
      <circle cx="84" cy="34" r="1.4" fill="#fff" />
      <circle cx="40" cy="44" r="1.4" fill="#fff" />
      <circle cx="78" cy="68" r="9" fill="#a78bfa" />
    </>
  ),
  bg_vault: (
    <>
      <rect width="100" height="100" fill="#fef3c7" />
      <rect x="22" y="74" width="56" height="9" rx="2" fill="#f59e0b" />
      <rect x="28" y="63" width="44" height="9" rx="2" fill="#fbbf24" />
      <rect x="34" y="52" width="32" height="9" rx="2" fill="#f59e0b" />
    </>
  ),
};
