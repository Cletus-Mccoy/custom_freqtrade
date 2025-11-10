applyTo:
  - "**/*.py"
  - "templates/**/*.html"
---

- Prefer creating or extending **Blueprints** rather than adding routes to the app object.
- Never remove or rename existing routes without an approved Action Log entry.
- Keep diffs atomic: moves/renames in one commit; logic changes in the next.
- When touching templates, reuse macros/partials where possible and avoid duplicating table markup.