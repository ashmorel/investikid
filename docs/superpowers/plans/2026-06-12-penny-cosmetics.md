# Penny Cosmetics (M8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. (This run: executed inline by the controller, TDD + commit per task.)

**Goal:** Per `docs/superpowers/specs/2026-06-12-penny-cosmetics-design.md` — learning-coins economy (1 coin/XP), cosmetics catalog + shop, equipped accessory on Penny.

### Task 1: migration + coins in record_xp + seed
- [ ] Migration (off `b9c0d1e2f3a4`): create `cosmetic_items` (+ new `slug` unique, `emoji` cols on the model) + `user_cosmetics` tables; data backfill `virtual_coins = xp WHERE virtual_coins = 0`.
- [ ] `record_xp` also grants coins 1:1 (`virtual_coins`); `UserProgressOut` += `virtual_coins`.
- [ ] `app/seed/cosmetics.py` idempotent upsert of the 8 items (by slug), registered in the seed runner.
- [ ] Tests: coins accrue with XP; seed idempotent; progress payload.
- [ ] Commit `feat(m8): learning-coins economy + cosmetics catalog seed`.

### Task 2: cosmetics API
- [ ] `app/routers/cosmetics.py`: GET /cosmetics, POST buy (SAVEPOINT, balance/premium/dup guards), POST equip (exclusive) + unequip. Register in main.py.
- [ ] Tests: full matrix per spec.
- [ ] Commit `feat(m8): cosmetics shop API`.

### Task 3: Penny accessory + shop UI
- [ ] `Penny` accessory overlay (emoji slug map); `useCosmetics` hook; HomeHero passes equipped slug.
- [ ] `/shop` page (balance, item grid, Buy confirm, Equip, premium → paywall), route + ProfileMenu entry.
- [ ] Tests + axe; HomeHero accessory test.
- [ ] Commit `feat(m8): Penny's Shop UI + equipped accessory`.

### Task 4: verify + push + docs
- [ ] Full gates both stacks (pytest exit codes checked directly); cap sync; CI green; roadmap/memory.
