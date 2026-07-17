---
name: adversarial-review
cli-support: [all]
description: Get a cross-harness second opinion by spawning a DIFFERENT agent (Claude Code spawns Codex; Codex spawns Claude) to review either a code change (diff/branch/PR) or arbitrary file/dir content (specs, RFCs, design docs, configs) and return structured findings. Use before opening/finalizing a largish PR, when you want an in-session review from a different model to catch your own blind spots, when you want a skeptical pass over a spec or RFC that the team hasn't engaged with, or on requests like "review this branch", "review PR #123", "review this spec adversarially", "get a second opinion on this design doc", or "adversarially review my diff".
allowed-tools: Bash(node:*)
---

# Adversarial review

Spawn a **different harness + model** than the one that wrote the change to review it. The whole point is that a same-model reviewer rationalizes away the author-model's blind spots; a different harness/model does not. Output is **advisory** — you read the findings and decide what to address.

When you (the author agent) are about to commit or open a non-trivial PR, run this and address or explicitly justify each `request_changes` / `escalate` finding before shipping.

## Quickstart

From the repo root (or anywhere inside the worktree):

```bash
# Default: review this branch vs origin/main, 1 reviewer = the OTHER harness, auto-detected.
node .agent/skills/adversarial-review/scripts/review.mjs --intent "what this change does and why"
```

It prints a markdown report (overall verdict + findings grouped by file + per-reviewer summaries). Read it, then act.

## What to review

```bash
node .../review.mjs                              # auto: branch commits + uncommitted/staged  [default]
node .../review.mjs --source branch              # only committed branch diff vs origin/main
node .../review.mjs --source working-tree        # only uncommitted changes vs HEAD
node .../review.mjs --source staged              # only staged changes
node .../review.mjs --base origin/develop        # change the base for branch/auto mode
node .../review.mjs --pr 12345                   # a GitHub PR diff (uses gh)
node .../review.mjs --paths docs/spec.md         # review FULL CONTENT of arbitrary file(s)/dir(s)
node .../review.mjs --paths docs/rfc,docs/api    # comma-separated or repeated --paths
```

The `auto` default is what you want before committing or opening a PR — it covers committed branch commits AND uncommitted/staged work in one pass. Use the explicit modes when you want to scope to just one slice.

### `paths` mode (not just code)

`--paths` reviews the **full content** of one or more files or directories — not a diff. Use it for things that aren't a diff yet (or aren't code at all): an RFC the team hasn't engaged with, a design doc that needs a skeptical pass, a spec you suspect has gaps, a config file, a generated README. The cross-harness mechanism is identical; the rubric shifts from correctness/tests/security to logical consistency, gaps, unstated assumptions, scope clarity, weak reasoning, and any factual/technical claims that look wrong. If any of the content is code, the code-shaped facets still apply.

Directories are walked recursively; `.git`, `node_modules`, `dist`, `build`, `.next`, `.turbo`, `.cache`, `.pnpm-store` are skipped, as are binary files (by extension and a null-byte check) and any single file over 100 KB. Total content is capped by `--max-diff-bytes`.

Always pass `--intent` when you can — the reviewer is much sharper when it knows the goal. If omitted, intent is inferred from the branch name + commit subjects (or PR title).

## Reviewers (default 1 = the other harness; fan out when it matters)

The author harness is auto-detected from `LINDY_HARNESS` (falls back to `CLAUDECODE`/`CODEX_*`). Default reviewer = the opposite harness.

To fan out one-or-many reviewers, pass `--reviewers` as a JSON array. Each entry is a harness string, or `{ harness, model?, focus? }`:

```bash
# Two reviewers, one focused on security:
node .../review.mjs --reviewers '[{"harness":"codex","model":"gpt-5"},{"harness":"claude","focus":"security and authz"}]'

# Force a single Claude reviewer regardless of who is asking:
node .../review.mjs --reviewers '["claude"]'
```

- `harness`: `claude` | `codex` (required)
- `model`: passed through to the CLI (`--model` for claude, `-m` for codex); omit for the harness default
- `focus`: the reviewer prioritizes this concern above the general rubric ("you review this for X")

Reviewers run **concurrently**. Use a focused fan-out for high-stakes diffs; the single cross-harness reviewer is the cheap default.

## Rubric

Each reviewer gets the house rubric — correctness, root-cause-vs-band-aid, tests, scope creep, security, reuse/simplicity — **plus** an explicit adversarial mandate: *you are a different model than the author; hunt for the blind spots it would be overconfident about; flag band-aids; disagree.* A per-reviewer `focus` overrides/augments that.

## Output contract

Per reviewer: `{ verdict: approve | request_changes | escalate, findings: [{ severity, file, line?, issue, suggestion }], summary }`. The script merges all reviewers into one report — findings grouped by file, deduped, each tagged by which model raised it; **overall verdict = the worst** across reviewers. Add `--json <path>` to also write the aggregated report as JSON for programmatic use.

Verdict meanings: `approve` = ship it; `request_changes` = concrete fixable issues; `escalate` = needs a human/product decision (surface it to the user).

## Safety

- Reviewers cannot **write**:
    - Codex with `--sandbox read-only` — kernel-enforced, no writes possible.
    - Claude with a strict `--allowed-tools` allowlist of `Read`, `Grep`, `Glob` — `Bash`, `Edit`/`Write`, `Task`, and every MCP tool are out of reach entirely (not just disallowed-list).
- **Recursion guard**: spawned reviewers inherit `ADVERSARIAL_REVIEW_ACTIVE=1`; if this skill is invoked with that set, it no-ops — so a reviewer can't recursively spawn its own review.
- **Reviewer failures don't get silently approved.** If any reviewer crashes or returns unparseable output, the overall verdict is `escalate` — you see the failure surfaced, not buried.
- Advisory only: the script never blocks, commits, or edits. It exits 0 with a report; you decide what to do.

**Threat model — read carefully.** This skill is designed for the eng-agent reviewing **its own work in its own trusted sandbox**. It is **not a security boundary** against a hostile diff. Specifically:

- The reviewer inherits the parent process's environment and can `Read` any file in the worktree, including `.env` and any cookie jars (e.g. `cookiejar.evals.hidden.txt`).
- A diff that contains adversarial instructions could try to prompt-inject the reviewer into reading a secret and emitting it in the JSON output.
- Do not point this skill at PR diffs from untrusted authors without first scrubbing the child env / running the reviewer against a sanitized worktree. That hardening is not yet built.

## Notes

- This is the **local, cross-harness** complement to the managed `code-review` skill (whose `ultra` mode runs a multi-agent review in the cloud). Use `adversarial-review` for a fast in-session second opinion from the other harness; use `code-review ultra` for the heavy cloud pass.
- Large diffs are truncated at 200 KB (`--max-diff-bytes`); reviewers are told to read files for the rest.
