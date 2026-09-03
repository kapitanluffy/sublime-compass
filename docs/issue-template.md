# Issue / Task Template — Compass Navigator

Canonical template for filing issues and tasks against this repo. It is Linear- and GitHub-compatible.

**How to use**
- **Linear:** copy the body (## Context … ## Out of Scope) into a new team template (Workspace settings → Templates → team → Compass Navigator). Set default properties: Project=Compass Navigator, Status=Triage/Backlog, add the created issue title. Keep both a full template and a slim bug-report variant below.
- **GitHub:** can be used verbatim as `.github/ISSUE_TEMPLATE/*.md`, or converted to a validated YAML form (`.yml`) with `required: true` on `context`, `problem`, `repro` (bugs), and `acceptance`.

**Rules that matter more than the template**
- One issue per problem. If a report bundles two asks, split it before filing.
- Lead with the problem; the solution is negotiable. Title names the work, body explains *why*.
- Reproducible bugs are only triageable if a maintainer can repro them: steps, environment, expected vs actual.
- Reference code with `file:line` (e.g. `src/stack.py:66`). Cross-link related issues (`STR-5`).
- Keep friction low — a long template discourages good reports. Fill only what applies.

**Title**
Format: `<Type> <Verb> <What> [<Context>]` — e.g. `Fix load_window: sheets appended with group 0`, `Scope FILE_STACK.clear() to the closing project`.

Type prefix (also becomes the Linear label): `Bug` · `Task` · `Refactor` · `Debt` · `Docs`. Keep titles under ~72 chars.

---

## Full template (use for tasks, refactors, designs)

```
## Context / Background
Why this matters and where it lives in the codebase. Cite files.
e.g. "Hydration happens in src/core.py:load() → load_window(). Multi-window
setups are broken (STR-5)."

## Problem
What is wrong or missing today, and the user-impact. A concrete scenario beats abstraction.
e.g. "With 2+ windows open at startup, only the last window's MRU stack is
hydrated; others start empty until focused."

## Proposal
The suggested change. If unsure of the approach, state the options and
your leaning — solutions are negotiable, problems are not.
e.g. "Bind the loop variable: lambda w=window: load_window(w)."

## Acceptance Criteria
Define "done" as a checkable list.
- [ ] Multi-window restart populates STACK for every window
- [ ] `compass_dump_stack` shows sheets for each window id

## Verification
How to prove the AC. This repo has no test suite, so include both:
- [ ] `python -m py_compile plugin.py utils.py` and `python -m compileall src`
- [ ] Manual step in Sublime (symlink as `Compass Navigator`, console check)

## Out of Scope
What this deliberately does not touch (keeps the diff reviewable).
e.g. "Unrelated option: promoting STACK_EXPIRY_TIME to a setting."

## Checklist
- [ ] No duplicate issue exists (searched Linear / issues)
- [ ] Title follows Format above; Type label applied
- [ ] Priority set on the rubric below
- [ ] Attached to Compass Navigator project (+ milestone if planning to ship)
```

---

## Slim Bug Report variant (external users, keep short)

```
## What happened
One clear sentence.

## Steps to reproduce
1.
2.
3.

## Expected
What should have happened.

## Actual
What happened instead (console output, screenshot, gif).

## Environment
- Sublime version / build, OS
- Compass Navigator version (Package Control → List Packages)
- `plugins.files.enabled`, `enable_cache`, relevant settings changed from default

## Impact / Severity
Data-loss/crash · major · minor · cosmetic — and who's affected.
```

---

## Priority rubric (Linear priority = urgency, not severity)

| Priority | Meaning | Typical fits |
|---|---|---|
| Urgent (1) | Blocks use, data loss, regressions since last release | STR-5/STR-6 class multi-window bugs |
| High (2) | Core feature wrong; notable user impact; easy win | project-scoped `FILE_STACK`, Escape behavior |
| Medium (3) | Edge cases, portability, correctness in uncommon configs | iteration bugs, cross-platform paths |
| Low (4) | Cleanup, ergonomics, backlog refactor | dedup, tests/CI, packaging hygiene |

Severity (impact) and priority (urgency) differ — a cosmetic bug can be High priority before a release; an exotic crash can be Low if unreachable. Record severity in the issue body; store priority in the property.

## Label set (keep small)
`Bug` `Feature` `Debt` `Refactor` `Docs` `Test` `packaging` `multi-window`

## Definition of done (applies to every issue)
- Code change compiled (`py_compile`/`compileall`) and manually exercised in Sublime
- `Default.sublime-keymap` stays commented; `messages.json` referenced versions stay intact
- Untracked WIP stubs (`src/file_watcher.py`, `src/plugins_registry.py`, `artifacts/`) not committed as-is
- This file's assumptions updated if the workflow changes (per AGENTS.md/PROVENANCE.md)