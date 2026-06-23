import React from 'react';

// Skin = Penny body-gradient recolour, keyed by CosmeticItem.slug. No skin → classic (mood) gradient.
export const SKIN: Record<string, [string, string]> = {
  skin_pink: ['#f9a8d4', '#db2777'],
  skin_sky: ['#38bdf8', '#2563eb'],
  skin_mint: ['#6ee7b7', '#059669'],
  skin_gold: ['#fcd34d', '#d97706'],
  skin_lavender: ['#c4b5fd', '#7c3aed'],
};

// BACKGROUND map will be added in Task 5.

// React import kept for future JSX use in this file (Task 5 will add JSX).
void React;
