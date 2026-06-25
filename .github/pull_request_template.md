## Summary

<!-- What does this change and why? Link the spec/plan in docs/superpowers/ if applicable. -->

## Type

- [ ] Feature
- [ ] Fix
- [ ] Refactor / chore
- [ ] Docs
- [ ] CI / infra

## Checklist

- [ ] Backend: `ruff check .` + `pytest` pass
- [ ] Frontend: `tsc`, `npm run lint`, `npm test`, `npm run build` pass (+ `vitest-axe` for new UI)
- [ ] DB change is a single chained Alembic migration (`alembic heads` == 1) — or N/A
- [ ] Kept it safe (LLM output moderated, premium server-gated) and accessible (WCAG 2.2 AA) — or N/A
- [ ] Docs / `MASTER-BACKLOG.md` updated — or N/A

## Screenshots / notes

<!-- For UI changes, attach before/after. Note any deploy or migration considerations. -->
