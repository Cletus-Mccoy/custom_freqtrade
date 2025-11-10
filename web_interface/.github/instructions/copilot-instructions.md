# Copilot – Repository Instructions

**Operating mode:** analysis-first, small diffs, staged rollout.  
**Single source of truth:** `ARCHITECTURE.md` (Roadmap & Action Log).

---

## 0) General guardrails
- Do **not** modify files until you first propose a plan referencing **exact paths** and functions.
- Keep changes **mechanical and reversible**; prefer extractions/aliases over rewrites.
- Never change public routes or JSON shapes without an explicit “Approval Gate” logged in `ARCHITECTURE.md`.
- Keep diffs small (<120 LOC where possible) and scoped to the files you list in the plan.
- Prefer built-in Flask refactors (Blueprints, `url_for`, `render_template`) over ad-hoc patterns.
- If ambiguity or missing context: **stop**, log an “Open Questions” block in `ARCHITECTURE.md`, and wait.
- Always keep the single source of truth up to date: `ARCHITECTURE.md` (Roadmap & Action Log + actual contents).

## 1) Required workflow for every task
1. **Discovery (no edits):** scan the repo for the concrete items relevant to the task; cite file paths and symbols.
2. **Plan:** propose the smallest viable change set and list *exact files* you intend to touch.
3. **Log the action BEFORE edits:** append a new entry to `ARCHITECTURE.md` under `## Roadmap & Action Log` **at the top**, with status `Planned` and the template below.
4. **Wait for approval** (the human will reply “Proceed [ID]”).
5. **Apply edits** exactly as planned; generate a unified diff.
6. **Update the same entry** to `Done` with the commit hash and verification results. If rolled back, set `Reverted` and note the revert hash.

### Action Log entry template (use this verbatim)

[A/B/C-#.##] Title (Status: Planned | In-Progress | Done | Reverted)

**Date (UTC):** YYYY-MM-DD HH:MM

**Owner:** Copilot

**Scope:** <files and directories>

**Rationale:** <1–3 sentences>

**Steps:**
1. <mechanical step>
2. <mechanical step>

**Verification:**
- **Commands:** <curl/pytest/flask routes etc.>
- **Criteria:** <expected outputs / routes still resolve>

**Rollback:** git revert <TBD> or restore <files>

**Commit:** <hash once known>

**Notes:** <edge cases / follow-ups>

## 2) Staging model for upgrades
- **Stage A (low risk):** mechanical extractions, aliases, moving routes into Blueprints without behavior changes; feature flags only if needed.
- **Stage B (adapter seam):** introduce small provider/repository interfaces behind existing routes; keep URL contracts; add tests/characterization.
- **Stage C (UI/Template normalization):** consolidate templates/macros; preserve data shape; remove duplication after parity checks.

Each staged action must have its own Action Log entry: `[A-x.yy]`, `[B-x.yy]`, `[C-x.yy]`.

## 3) Flask-specific expectations
- Prefer **Blueprints** over `app.route` expansions.
- Keep legacy routes working; add new surfaces under a prefix (e.g., `/tables`) behind a guard if needed.
- Use `url_for` for links; avoid hard-coded paths.
- If using Docker SDK: guard import (`try: import docker except: ...`) and fail gracefully.
- If validating tab/table rows: use Pydantic **only if already in deps**; otherwise dataclasses with `asdict`.

## 4) Verification (every change)
- Run/produce: `flask routes`, quick `curl` calls for affected endpoints, and any existing tests/lints.
- Confirm templates render and JS still fetches expected `{columns, rows}`.
- Note verification commands + success criteria in the Action Log entry.

## 5) Commit hygiene
- One concern per commit.
- Commit message: `[Stage] Short summary` followed by a bullet list of edited files.
- No drive-by refactors; no unrelated formatting.

## 6) Stop conditions
- Conflicting guidance between code and docs → log in `ARCHITECTURE.md` “Open Questions” and stop.
- Changes required outside the declared Scope → update the plan/log first; do not proceed silently.

---

## 7) Quick prompts you can use in Copilot Chat (for maintainers)
- **“Analyze tabs now (no edits)”** → Inventory routes/templates/data access with precise paths.
- **“Plan Stage A for <area>”** → Minimal mechanical extraction + file list.
- **“Append Roadmap entry [ID]”** → Add `Planned` entry using the template above.
- **“Apply [ID] exactly”** → Make the edits; produce a diff; update entry to `Done` with hash.
