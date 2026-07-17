#!/usr/bin/env node
// adversarial-review: spawn a DIFFERENT harness+model to review a diff and return
// structured findings. Runs locally; no network beyond what the spawned CLI does.
//
//   node review.mjs                         # review branch vs origin/main, 1 reviewer = the OTHER harness
//   node review.mjs --source working-tree   # review uncommitted changes
//   node review.mjs --pr 12345              # review a GitHub PR diff
//   node review.mjs --reviewers '[{"harness":"codex","model":"gpt-5"},{"harness":"claude","focus":"security"}]'
//
// Output: a markdown report on stdout (the calling agent reads it). Advisory.

import { spawn } from "node:child_process"
import { mkdtemp, readdir, readFile, rm, stat, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"

const CLAUDE = "claude"
const CODEX = "codex"
const VERDICTS = ["approve", "request_changes", "escalate"]
const VERDICT_RANK = { approve: 0, request_changes: 1, escalate: 2 }

function fail(msg) {
    console.error(`adversarial-review: ${msg}`)
    process.exit(2)
}

// ---------- args ----------
function parseArgs(argv) {
    const args = {
        // auto = branch (committed vs base) + working-tree (uncommitted+staged vs HEAD).
        // That's what an agent about to ship/commit actually wants reviewed.
        source: "auto", // auto | working-tree | staged | branch | pr | paths
        base: "origin/main",
        pr: null,
        paths: null, // array of file/dir paths to review as full content (not a diff)
        intent: null,
        reviewers: null, // JSON array string, or null => default single other-harness reviewer
        json: null, // optional path to also write the aggregated report as JSON
        maxDiffBytes: 200_000,
        self: null, // override the detected "author" harness (testing)
        reviewerTimeoutMs: 600_000, // per-reviewer subprocess timeout (10 min)
    }
    for (let i = 0; i < argv.length; i += 1) {
        const a = argv[i]
        const next = () => argv[(i += 1)]
        switch (a) {
            case "--source":
                args.source = next()
                break
            case "--base":
                args.base = next()
                break
            case "--pr":
                args.pr = next()
                args.source = "pr"
                break
            case "--paths": {
                // Repeatable; each invocation can also be comma-separated.
                const v = next()
                if (v == null) fail("--paths requires a value (file or directory; comma-separated or repeated)")
                if (!args.paths) args.paths = []
                for (const p of v.split(",")) if (p.trim()) args.paths.push(p.trim())
                args.source = "paths"
                break
            }
            case "--intent":
                args.intent = next()
                break
            case "--reviewers":
                args.reviewers = next()
                break
            case "--json":
                args.json = next()
                break
            case "--max-diff-bytes":
                args.maxDiffBytes = Number(next())
                break
            case "--reviewer-timeout-ms":
                args.reviewerTimeoutMs = Number(next())
                break
            case "--self":
                args.self = next()
                break
            case "-h":
            case "--help":
                printHelp()
                process.exit(0)
                break
            default:
                if (a.startsWith("-")) fail(`unknown flag: ${a}`)
        }
    }
    return args
}

function printHelp() {
    console.log(
        [
            "adversarial-review — cross-harness code review",
            "",
            "Flags:",
            "  --source <auto|working-tree|staged|branch|pr|paths>  what to review (default: auto)",
            "                                            auto = branch commits + uncommitted/staged",
            "                                            paths = arbitrary file(s)/dir(s), see --paths",
            "  --base <ref>                              base for branch/auto mode (default: origin/main)",
            "  --paths <path[,path...]>                  review FULL CONTENT of these file(s)/dir(s)",
            "                                            (repeatable; also accepts comma-separated)",
            "                                            implies --source paths. Works for any content",
            "                                            — code, prose, RFCs, design docs.",
            "  --pr <number>                             review a GitHub PR (implies --source pr)",
            "  --intent <text>                           what the change does/why (inferred if omitted)",
            "  --reviewers <json>                        JSON array of reviewers, e.g.",
            '                                            \'["codex"]\' or',
            '                                            \'[{"harness":"claude","model":"opus","focus":"security"}]\'',
            "                                            (default: a single reviewer = the OTHER harness)",
            "  --json <path>                             also write the aggregated report as JSON",
            "  --max-diff-bytes <n>                      truncate diff above this size (default: 200000)",
            "  --reviewer-timeout-ms <n>                 kill a stuck reviewer after this long (default: 600000)",
            "  --self <claude|codex>                     override detected author harness (testing)",
        ].join("\n"),
    )
}

// ---------- subprocess ----------
// `timeoutMs` (optional): SIGTERM the child after this long, then SIGKILL 5s
// later if it ignores the term, and resolve with code 124. Without it one stuck
// reviewer (rate-limit retry loop, network stall, a hook awaiting a permission
// prompt in -p mode) would hang the whole Promise.all forever — and CLAUDE.md
// recommends this skill as a routine pre-PR check, so an engineer who runs it
// and steps away must not come back to a wedged process. code 124 flows through
// the no-output path → reviewer verdict "error" → forced overall "escalate".
function run(cmd, cmdArgs, { cwd, input, env, timeoutMs } = {}) {
    return new Promise((resolve, reject) => {
        const child = spawn(cmd, cmdArgs, {
            ...(cwd ? { cwd } : {}),
            env: env ?? process.env,
            stdio: ["pipe", "pipe", "pipe"],
        })
        let stdout = ""
        let stderr = ""
        let timedOut = false
        let termTimer = null
        let killTimer = null
        const clearTimers = () => {
            if (termTimer) clearTimeout(termTimer)
            if (killTimer) clearTimeout(killTimer)
        }
        if (timeoutMs && timeoutMs > 0) {
            termTimer = setTimeout(() => {
                timedOut = true
                child.kill("SIGTERM")
                killTimer = setTimeout(() => child.kill("SIGKILL"), 5_000)
            }, timeoutMs)
        }
        child.stdout.setEncoding("utf8")
        child.stderr.setEncoding("utf8")
        child.stdout.on("data", (c) => (stdout += c))
        child.stderr.on("data", (c) => (stderr += c))
        child.on("error", (err) => {
            clearTimers()
            reject(err)
        })
        child.on("close", (code) => {
            clearTimers()
            if (timedOut) {
                resolve({
                    code: 124,
                    stdout,
                    stderr: `${stderr}\n[adversarial-review: reviewer timed out after ${timeoutMs}ms; killed]`,
                })
            } else {
                resolve({ code: code ?? 1, stdout, stderr })
            }
        })
        // A reviewer that fails fast (binary mismatch, immediate exit) can close
        // its stdin before we finish writing the prompt → EPIPE on child.stdin.
        // With no listener that emits as an uncaughtException and kills the parent,
        // abandoning sibling reviewers in Promise.all. Swallow it — the close/error
        // handlers above already capture the real outcome.
        child.stdin.on("error", () => {})
        if (input != null) child.stdin.end(input)
        else child.stdin.end()
    })
}

async function git(cmdArgs) {
    const r = await run("git", cmdArgs)
    if (r.code !== 0) throw new Error(`git ${cmdArgs.join(" ")} failed: ${r.stderr.trim()}`)
    return r.stdout
}

async function hasBin(name) {
    const r = await run("which", [name])
    return r.code === 0 && r.stdout.trim() !== ""
}

// ---------- harness detection ----------
function detectHarness(override) {
    if (override) return normHarness(override)
    const lh = (process.env.LINDY_HARNESS || "").toLowerCase()
    if (lh.includes("codex")) return CODEX
    if (lh.includes("claude")) return CLAUDE
    // Active-session signals take precedence: CODEX_SANDBOX is set inside a
    // running `codex exec`, and CLAUDECODE/CLAUDE_CODE_ENTRYPOINT inside a running
    // Claude Code session. CODEX_HOME is exported merely by having Codex INSTALLED,
    // so it must be checked LAST — otherwise a Claude Code session on a machine
    // with Codex installed misdetects as codex, and the "other harness" reviewer
    // becomes claude-reviewing-claude while the report still claims cross-harness.
    if (process.env.CODEX_SANDBOX) return CODEX
    if (process.env.CLAUDECODE || process.env.CLAUDE_CODE_ENTRYPOINT) return CLAUDE
    if (process.env.CODEX_HOME) return CODEX // weak: installation marker, not active use
    return CLAUDE // best-effort default
}

function otherHarness(h) {
    return h === CLAUDE ? CODEX : CLAUDE
}

function normHarness(h) {
    const v = String(h).toLowerCase()
    if (v.startsWith("claude")) return CLAUDE
    if (v.startsWith("codex")) return CODEX
    fail(`unknown harness: ${h} (expected claude|codex)`) // exits
}

function resolveReviewers(args, current) {
    if (!args.reviewers) return [{ harness: otherHarness(current) }]
    let parsed
    try {
        parsed = JSON.parse(args.reviewers)
    } catch {
        fail(`--reviewers must be a JSON array; got: ${args.reviewers}`)
    }
    if (!Array.isArray(parsed) || parsed.length === 0) fail("--reviewers must be a non-empty JSON array")
    return parsed.map((r, idx) => {
        if (typeof r === "string") return { harness: normHarness(r) }
        if (r && typeof r === "object" && r.harness) {
            return {
                harness: normHarness(r.harness),
                ...(r.model ? { model: String(r.model) } : {}),
                ...(r.focus ? { focus: String(r.focus) } : {}),
            }
        }
        fail(`reviewer[${idx}] must be a harness string or {harness, model?, focus?}`) // exits
    })
}

// ---------- diff ----------
async function buildDiff(args) {
    if (args.source === "working-tree") {
        return {
            diff: await git(["diff", "HEAD"]),
            files: (await git(["diff", "--name-only", "HEAD"])).trim(),
            label: "working tree (uncommitted vs HEAD)",
        }
    }
    if (args.source === "staged") {
        return {
            diff: await git(["diff", "--cached"]),
            files: (await git(["diff", "--cached", "--name-only"])).trim(),
            label: "staged changes",
        }
    }
    if (args.source === "pr") {
        if (!args.pr) fail("--pr <number> required for source=pr")
        const d = await run("gh", ["pr", "diff", String(args.pr)])
        if (d.code !== 0) throw new Error(`gh pr diff ${args.pr} failed: ${d.stderr.trim()}`)
        const f = await run("gh", ["pr", "diff", String(args.pr), "--name-only"])
        return { diff: d.stdout, files: f.code === 0 ? f.stdout.trim() : "", label: `PR #${args.pr}` }
    }
    if (args.source === "branch") {
        return {
            diff: await git(["diff", `${args.base}...HEAD`]),
            files: (await git(["diff", `${args.base}...HEAD`, "--name-only"])).trim(),
            label: `branch vs merge-base(${args.base})`,
        }
    }
    if (args.source === "paths") {
        if (!args.paths || args.paths.length === 0) {
            fail("--paths requires at least one file or directory")
        }
        return readPaths(args.paths)
    }
    // auto (default): committed branch diff + uncommitted/staged working-tree diff.
    // That's what you actually want before committing or opening a PR — reviewing
    // only branch...HEAD would miss the change you haven't committed yet.
    const branchDiff = await git(["diff", `${args.base}...HEAD`])
    const wtDiff = await git(["diff", "HEAD"])
    const branchFiles = (await git(["diff", `${args.base}...HEAD`, "--name-only"])).trim()
    const wtFiles = (await git(["diff", "--name-only", "HEAD"])).trim()
    const allFiles = [
        ...new Set(
            [branchFiles, wtFiles]
                .filter(Boolean)
                .flatMap((s) => s.split("\n"))
                .filter(Boolean),
        ),
    ].join("\n")
    let combined = ""
    if (branchDiff.trim()) combined += `# branch commits vs ${args.base}\n${branchDiff}`
    if (wtDiff.trim())
        combined += `${combined ? "\n\n" : ""}# uncommitted/staged changes (vs HEAD)\n${wtDiff}`
    const haveBranch = !!branchDiff.trim()
    const haveWT = !!wtDiff.trim()
    const label =
        haveBranch && haveWT
            ? `branch vs ${args.base} + uncommitted/staged`
            : haveBranch
              ? `branch vs ${args.base}`
              : haveWT
                ? "uncommitted/staged vs HEAD"
                : "(empty)"
    return { diff: combined, files: allFiles, label }
}

// Read one or more files/dirs into a single content blob. Used by `paths` mode
// so the skill can adversarially review arbitrary content (specs, RFCs, design
// docs, configs) — not just diffs. Skips binaries, large files, and the usual
// build/dep directories.
async function readPaths(paths) {
    const SKIP_DIRS = new Set([
        ".git",
        "node_modules",
        "dist",
        "build",
        ".next",
        ".turbo",
        ".cache",
        ".pnpm-store",
    ])
    const BINARY_EXT = new Set([
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
        ".pdf", ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z",
        ".woff", ".woff2", ".ttf", ".otf", ".eot",
        ".mp3", ".mp4", ".mov", ".webm", ".wav",
        ".bin", ".exe", ".dll", ".so", ".dylib", ".class", ".jar",
    ])
    const MAX_BYTES_PER_FILE = 100_000
    const items = []
    // `seen` dedupes by textual `path.resolve()`, not `realpath`. Two distinct
    // symlinks to the same target won't be deduped, and a cycle outside
    // SKIP_DIRS could in theory recurse. The SKIP_DIRS list covers the
    // realistic cases (.git, node_modules, build dirs) so this is a theoretical
    // concern, not a practical one. Switch to fs.realpath if you ever pass
    // symlink-heavy paths.
    const seen = new Set()

    async function walk(p) {
        const abs = path.resolve(p)
        if (seen.has(abs)) return
        seen.add(abs)
        let st
        try {
            st = await stat(abs)
        } catch (e) {
            items.push({ path: abs, error: `stat: ${e?.code ?? e?.message ?? "unknown"}` })
            return
        }
        if (st.isDirectory()) {
            let entries
            try {
                entries = await readdir(abs)
            } catch (e) {
                items.push({ path: abs, error: `readdir: ${e?.code ?? e?.message ?? "unknown"}` })
                return
            }
            for (const name of entries) {
                if (SKIP_DIRS.has(name)) continue
                await walk(path.join(abs, name))
            }
            return
        }
        if (!st.isFile()) return
        const ext = path.extname(abs).toLowerCase()
        if (BINARY_EXT.has(ext)) {
            items.push({ path: abs, skipped: "binary extension" })
            return
        }
        if (st.size > MAX_BYTES_PER_FILE) {
            items.push({ path: abs, skipped: `too large (${st.size} > ${MAX_BYTES_PER_FILE})` })
            return
        }
        let buf
        try {
            buf = await readFile(abs)
        } catch (e) {
            items.push({ path: abs, error: `read: ${e?.code ?? e?.message ?? "unknown"}` })
            return
        }
        // Cheap binary detection: any null byte in the first ~4 KB.
        if (buf.slice(0, Math.min(4096, buf.length)).includes(0)) {
            items.push({ path: abs, skipped: "binary content (null byte)" })
            return
        }
        items.push({ path: abs, content: buf.toString("utf8") })
    }

    for (const p of paths) await walk(p)

    const cwd = process.cwd()
    const rel = (p) => path.relative(cwd, p) || p
    const contentParts = []
    const fileList = []
    const skipped = []
    for (const it of items) {
        if (it.content != null) {
            contentParts.push(`# === ${rel(it.path)} ===\n${it.content}`)
            fileList.push(rel(it.path))
        } else if (it.skipped) {
            skipped.push(`${rel(it.path)} (skipped: ${it.skipped})`)
        } else if (it.error) {
            skipped.push(`${rel(it.path)} (error: ${it.error})`)
        }
    }
    const files =
        fileList.join("\n") + (skipped.length ? `\n\n# not included:\n${skipped.join("\n")}` : "")
    // Surface the skipped count to stderr so a caller notices when files are
    // dropped — the `# not included:` block is in the reviewer's prompt but
    // easy to miss when scanning script output.
    if (skipped.length) {
        process.stderr.write(`adversarial-review: ${skipped.length} path(s) not included (binary/oversize/error) — see report\n`)
    }
    return {
        diff: contentParts.join("\n\n"),
        files,
        label: `paths: ${paths.join(", ")}`,
    }
}

async function inferIntent(args) {
    try {
        if (args.source === "pr") {
            const r = await run("gh", ["pr", "view", String(args.pr), "--json", "title", "-q", ".title"])
            if (r.code === 0 && r.stdout.trim()) return r.stdout.trim()
        }
        if (args.source === "paths") {
            return `Review of: ${(args.paths || []).join(", ")} (no intent supplied — review what is there on its own merits)`
        }
        const branch = (await git(["branch", "--show-current"])).trim()
        const includeLogs = args.source === "branch" || args.source === "auto"
        const logs = includeLogs ? (await git(["log", `${args.base}..HEAD`, "--format=%s"])).trim() : ""
        const bits = [branch && `branch: ${branch}`, logs && `commits:\n${logs}`].filter(Boolean).join("\n")
        return bits || "(intent not provided)"
    } catch {
        return "(intent not provided)"
    }
}

// ---------- prompt ----------
const SCHEMA_TEXT =
    '{ "verdict": "approve"|"request_changes"|"escalate", "findings": [ { "severity": "high"|"medium"|"low", "file": "path/to/file", "line": <integer or null>, "issue": "what is wrong", "suggestion": "what to do instead" } ], "summary": "one short paragraph" }'

function buildPrompt({ intent, files, diff, label, focus, mode }) {
    const isPaths = mode === "paths"
    const rubric = isPaths
        ? [
              "Review the FULL CONTENT below for:",
              "- Logical consistency and internal contradictions.",
              "- Gaps: missing cases, unstated assumptions, edges not considered, alternatives not addressed.",
              "- Scope clarity: what is in vs out; vague terms; hand-waving; weasel words.",
              "- Weak reasoning: claims that don't actually support the conclusion; non-sequiturs.",
              "- Factual or technical claims that look wrong; references that should be checked.",
              "- If any content is code (script/config/source): also flag correctness bugs, missing tests, scope creep, security, and reuse/simplicity.",
          ].join("\n")
        : [
              "Review for:",
              "- Correctness: logic errors, unhandled edge cases, weak/missing error handling, off-by-one, null/undefined, async races.",
              "- Root cause vs band-aid: fixes that paper over a symptom instead of the real invariant; a fix applied to one code path when the bug spans several.",
              "- Tests: missing tests, or tests that only assert the band-aid works rather than the underlying invariant.",
              "- Scope: unrelated changes, new unjustified surface area, scope creep.",
              "- Security: injection, authz/authn gaps, secret handling, unsafe input at trust boundaries.",
              "- Reuse & simplicity: duplicated logic, dead code, premature abstraction, needless complexity.",
          ].join("\n")
    const intro = isPaths
        ? "You are an ADVERSARIAL reviewer. You are deliberately a DIFFERENT model/harness than whoever wrote this. Your entire value is catching the blind spots that author would be overconfident about — be skeptical, and disagree where warranted. The content below may be code, prose, design docs, RFCs, configs — adapt the facets of the rubric that fit what you actually see."
        : "You are an ADVERSARIAL code reviewer. You are deliberately a DIFFERENT model/harness than the agent that wrote this change. Your entire value is catching the blind spots that author would be overconfident about — be skeptical, and disagree where warranted."
    return [
        intro,
        "",
        `Intent: ${intent}`,
        "",
        rubric,
        ...(focus ? ["", `PRIORITIZE THIS FOCUS above everything else: ${focus}`] : []),
        "",
        'Prefer a few high-signal findings over a pile of nits. If it is genuinely fine, return verdict "approve" with an empty findings array.',
        "",
        isPaths ? `Files reviewed:\n${files || "(none)"}` : `Changed files:\n${files || "(none reported)"}`,
        "",
        isPaths ? `Content (${label}):` : `Diff (${label}):`,
        diff,
        "",
        "You may read additional files in the repo (read-only) for context before deciding.",
        "",
        "For the `file` field in each finding, use the path the issue is in (one of the files listed above). Use `line` if you can identify a line number, otherwise null.",
        "",
        "Output ONLY a single JSON object — no prose, no markdown fences — matching:",
        SCHEMA_TEXT,
        'verdict: "approve" = ship it; "request_changes" = concrete fixable issues; "escalate" = needs a human/product decision.',
    ].join("\n")
}

function reviewJsonSchema() {
    return {
        type: "object",
        additionalProperties: false,
        required: ["verdict", "findings", "summary"],
        properties: {
            verdict: { type: "string", enum: VERDICTS },
            findings: {
                type: "array",
                items: {
                    type: "object",
                    additionalProperties: false,
                    required: ["severity", "file", "line", "issue", "suggestion"],
                    properties: {
                        severity: { type: "string", enum: ["high", "medium", "low"] },
                        file: { type: "string" },
                        line: { type: ["integer", "null"] },
                        issue: { type: "string" },
                        suggestion: { type: "string" },
                    },
                },
            },
            summary: { type: "string" },
        },
    }
}

// ---------- reviewers ----------
async function runReviewer(reviewer, ctx, repoRoot, timeoutMs) {
    const tag = `${reviewer.harness}${reviewer.model ? `:${reviewer.model}` : ""}${
        reviewer.focus ? ` (${reviewer.focus})` : ""
    }`
    const prompt = buildPrompt({ ...ctx, focus: reviewer.focus })
    const env = { ...process.env, ADVERSARIAL_REVIEW_ACTIVE: "1" }
    const base = { tag, harness: reviewer.harness, model: reviewer.model ?? "(default)", focus: reviewer.focus ?? null }
    try {
        const raw =
            reviewer.harness === CODEX
                ? await runCodexReviewer(reviewer, prompt, repoRoot, env, timeoutMs)
                : await runClaudeReviewer(reviewer, prompt, repoRoot, env, timeoutMs)
        return { ...base, ...validateReport(parseJsonObject(raw)) }
    } catch (err) {
        return { ...base, verdict: "error", findings: [], summary: "", error: String(err?.message ?? err) }
    }
}

async function runCodexReviewer(reviewer, prompt, repoRoot, env, timeoutMs) {
    const dir = await mkdtemp(path.join(tmpdir(), "advrev-codex-"))
    const schemaPath = path.join(dir, "schema.json")
    const outPath = path.join(dir, "out.json")
    try {
        await writeFile(schemaPath, JSON.stringify(reviewJsonSchema()))
        // cwd is set on the spawn options below; no need to pass -C as well
        // (it also affects relative --output-schema / --output-last-message
        // paths if those ever become relative).
        const cargs = [
            "exec",
            "--json",
            "--color",
            "never",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--output-schema",
            schemaPath,
            "--output-last-message",
            outPath,
        ]
        if (reviewer.model) cargs.push("-m", reviewer.model)
        cargs.push("-")
        const r = await run("codex", cargs, { cwd: repoRoot, input: prompt, env, timeoutMs })
        let raw = ""
        try {
            raw = await readFile(outPath, "utf8")
        } catch {
            // fall through to stdout scan
        }
        if (!raw.trim()) raw = extractCodexFinal(r.stdout)
        if (!raw.trim()) {
            throw new Error(`codex produced no output (exit ${r.code}): ${(r.stderr || r.stdout).slice(-400)}`)
        }
        return raw
    } finally {
        await rm(dir, { recursive: true, force: true })
    }
}

async function runClaudeReviewer(reviewer, prompt, repoRoot, env, timeoutMs) {
    // Default permission mode (no --dangerously-skip-permissions): that flag is
    // refused when running as root (e.g. inside the eng-agent sandbox). In -p
    // mode Claude auto-declines tools it lacks ambient permission for and still
    // returns a clean result event, so the reviewer answers from the inline
    // diff. --allowed-tools is a strict ALLOWLIST: only Read/Grep/Glob are
    // available, so Bash, Edit/Write, Task, and any MCP tool are out of reach
    // entirely — the reviewer is genuinely read-only.
    const cargs = ["-p", "--output-format", "stream-json", "--verbose"]
    if (reviewer.model) cargs.push("--model", reviewer.model)
    cargs.push("--allowed-tools", "Read", "Grep", "Glob")
    const r = await run("claude", cargs, { cwd: repoRoot, input: prompt, env, timeoutMs })
    const result = extractClaudeResult(r.stdout)
    if (!result) {
        throw new Error(`claude produced no result event (exit ${r.code}): ${(r.stderr || r.stdout).slice(-400)}`)
    }
    return result
}

// ---------- output parsing (defensive; mirrors what the harnesses emit) ----------
function extractCodexFinal(stdout) {
    const lines = stdout
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean)
    for (let i = lines.length - 1; i >= 0; i -= 1) {
        try {
            const event = JSON.parse(lines[i])
            const msg = readNestedString(event, ["msg", "message", "output", "response", "text"])
            if (msg) return msg
        } catch {
            // Fallback for codex stdout shapes that may not be strictly
            // newline-delimited JSON (the primary read path is the
            // --output-last-message file; this kicks in only when that fails).
            // parseJsonObject downstream does balanced-brace scanning, so a raw
            // non-JSON tail is still salvageable if it contains the JSON object.
            return lines[i]
        }
    }
    return ""
}

function extractClaudeResult(stdout) {
    const lines = stdout
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean)
    for (let i = lines.length - 1; i >= 0; i -= 1) {
        try {
            const event = JSON.parse(lines[i])
            if (event && event.type === "result" && typeof event.result === "string") return event.result
        } catch {
            // not JSON; skip
        }
    }
    return ""
}

function readNestedString(value, keys) {
    if (typeof value === "string") return value
    if (!value || typeof value !== "object") return undefined
    for (const key of keys) {
        const found = value[key]
        if (typeof found === "string") return found
        const nested = readNestedString(found, keys)
        if (nested) return nested
    }
    return undefined
}

function parseJsonObject(raw) {
    let s = String(raw).trim()
    const fence = /```(?:json)?\s*([\s\S]*?)```/i.exec(s)
    if (fence?.[1]) s = fence[1].trim()
    try {
        const parsed = JSON.parse(s)
        if (parsed && typeof parsed === "object") return parsed
    } catch {
        // fall through to balanced-brace scan
    }
    let fallback
    for (const candidate of balancedBraceObjects(s)) {
        try {
            const parsed = JSON.parse(candidate)
            if (parsed && typeof parsed === "object") {
                if ("verdict" in parsed) return parsed
                fallback ??= parsed
            }
        } catch {
            // keep scanning
        }
    }
    if (fallback !== undefined) return fallback
    throw new Error(`reviewer did not return parseable JSON. Raw (first 400): ${s.slice(0, 400)}`)
}

function* balancedBraceObjects(text) {
    for (let start = 0; start < text.length; start += 1) {
        if (text[start] !== "{") continue
        let depth = 0
        let inString = false
        let escaped = false
        for (let end = start; end < text.length; end += 1) {
            const ch = text[end]
            if (escaped) {
                escaped = false
                continue
            }
            if (ch === "\\") {
                escaped = true
                continue
            }
            if (ch === '"') {
                inString = !inString
                continue
            }
            if (inString) continue
            if (ch === "{") depth += 1
            else if (ch === "}") {
                depth -= 1
                if (depth === 0) {
                    yield text.slice(start, end + 1)
                    break
                }
            }
        }
    }
}

// ---------- normalize + aggregate ----------
function validateReport(obj) {
    const v = String(obj?.verdict ?? "").toLowerCase()
    // Consistent with "unparseable output forces escalate": a parseable object
    // with a verdict outside the documented enum is also broken reviewer output
    // and should not be quietly downgraded to request_changes.
    const verdict = VERDICTS.includes(v) ? v : "escalate"
    const findings = Array.isArray(obj?.findings) ? obj.findings.map(normFinding).filter(Boolean) : []
    const summary = typeof obj?.summary === "string" ? obj.summary : ""
    return { verdict, findings, summary }
}

function normFinding(f) {
    if (!f || typeof f !== "object") return null
    const sev = ["high", "medium", "low"].includes(String(f.severity).toLowerCase())
        ? String(f.severity).toLowerCase()
        : "medium"
    let line = null
    if (Number.isInteger(f.line)) line = f.line
    else if (f.line != null && Number.isFinite(Number(f.line))) line = Number(f.line)
    return {
        severity: sev,
        file: typeof f.file === "string" && f.file.trim() ? f.file.trim() : "(unspecified)",
        line,
        issue: typeof f.issue === "string" ? f.issue : String(f.issue ?? ""),
        suggestion: typeof f.suggestion === "string" ? f.suggestion : String(f.suggestion ?? ""),
    }
}

function overallVerdict(reports) {
    // A failed reviewer is a meaningful signal — treat any reviewer error as a
    // forced "escalate" so the aggregate stays inside the documented enum and a
    // crashed cross-harness check is never silently treated as approval.
    if (reports.some((r) => r.verdict === "error")) return "escalate"
    let worst = "approve"
    for (const r of reports) {
        if ((VERDICT_RANK[r.verdict] ?? 1) > (VERDICT_RANK[worst] ?? 0)) worst = r.verdict
    }
    return worst
}

function severityRank(s) {
    return s === "high" ? 0 : s === "medium" ? 1 : 2
}

function renderReport({ overall, reports, ctx, current }) {
    const lines = []
    lines.push("# Adversarial review")
    lines.push("")
    lines.push(`- Overall verdict: **${overall}**`)
    lines.push(`- Author harness: \`${current}\``)
    lines.push(`- Reviewers: ${reports.map((r) => `\`${r.tag}\``).join(", ")}`)
    lines.push(`- Source: ${ctx.label}`)
    lines.push(`- Intent: ${ctx.intent.replace(/\n/g, " ")}`)
    lines.push("")

    const errored = reports.filter((r) => r.verdict === "error")
    if (errored.length) {
        lines.push(
            `> ⚠️ ${errored.length} reviewer(s) failed: ${errored
                .map((r) => `\`${r.tag}\` (${r.error})`)
                .join("; ")}`,
        )
        lines.push("")
    }

    // merge identical findings across reviewers (key: file + issue prefix)
    const merged = new Map()
    for (const r of reports) {
        for (const f of r.findings) {
            const key = `${f.file}::${f.issue.trim().toLowerCase().slice(0, 120)}`
            if (!merged.has(key)) merged.set(key, { ...f, tags: new Set([r.tag]) })
            else merged.get(key).tags.add(r.tag)
        }
    }
    const all = [...merged.values()]
    if (all.length === 0) {
        lines.push("No findings. ✅")
    } else {
        lines.push(`## Findings (${all.length})`)
        const byFile = new Map()
        for (const f of all) {
            if (!byFile.has(f.file)) byFile.set(f.file, [])
            byFile.get(f.file).push(f)
        }
        for (const [file, fs] of [...byFile.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
            lines.push("")
            lines.push(`### \`${file}\``)
            fs.sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
            for (const f of fs) {
                const loc = f.line != null ? ` (line ${f.line})` : ""
                lines.push(`- **[${f.severity}]**${loc} ${f.issue}`)
                if (f.suggestion) lines.push(`  - ↳ ${f.suggestion}`)
                lines.push(`  - _raised by ${[...f.tags].map((t) => `\`${t}\``).join(", ")}_`)
            }
        }
    }
    lines.push("")
    lines.push("## Reviewer summaries")
    for (const r of reports) {
        lines.push("")
        // Keep the rendered verdict inside the documented enum. A failed reviewer
        // shows "escalate (failed)" — the per-reviewer error message is still
        // rendered below, and the `⚠️ N reviewer(s) failed` block above surfaces
        // the crash list.
        const renderedVerdict = r.verdict === "error" ? "escalate (failed)" : r.verdict
        lines.push(`### \`${r.tag}\` → ${renderedVerdict}`)
        lines.push(r.verdict === "error" ? `error: ${r.error}` : r.summary || "(no summary)")
    }
    return lines.join("\n")
}

// ---------- main ----------
async function main() {
    const args = parseArgs(process.argv.slice(2))

    if (process.env.ADVERSARIAL_REVIEW_ACTIVE === "1") {
        console.error(
            "adversarial-review: refusing to run inside a spawned reviewer (recursion guard). No-op.",
        )
        process.exit(0)
    }

    const repoRoot = (await git(["rev-parse", "--show-toplevel"])).trim()
    const current = detectHarness(args.self)
    const reviewers = resolveReviewers(args, current)

    for (const rv of reviewers) {
        if (!(await hasBin(rv.harness))) fail(`reviewer harness '${rv.harness}' binary not found on PATH`)
    }

    const { diff, files, label } = await buildDiff(args)
    if (!diff.trim()) {
        const ctxLabel =
            args.source === "branch"
                ? ` (base ${args.base})`
                : args.source === "paths"
                  ? ` (paths: ${(args.paths || []).join(", ")})`
                  : ""
        console.log(
            `# Adversarial review\n\nNothing to review for source=${args.source}${ctxLabel}.`,
        )
        process.exit(0)
    }

    let diffForReview = diff
    let truncated = false
    if (Buffer.byteLength(diff, "utf8") > args.maxDiffBytes) {
        diffForReview = `${diff.slice(0, args.maxDiffBytes)}\n\n[... diff truncated at ${args.maxDiffBytes} bytes; read files for the rest ...]`
        truncated = true
    }

    const intent = args.intent ?? (await inferIntent(args))
    const mode = args.source === "paths" ? "paths" : "diff"
    const ctx = {
        intent,
        files,
        diff: diffForReview,
        label: truncated ? `${label} (truncated)` : label,
        mode,
    }

    process.stderr.write(
        `adversarial-review: author=${current}, reviewers=[${reviewers
            .map((r) => r.harness + (r.model ? `:${r.model}` : ""))
            .join(", ")}], diff=${ctx.label}\n`,
    )

    const reports = await Promise.all(
        reviewers.map((rv) => runReviewer(rv, ctx, repoRoot, args.reviewerTimeoutMs)),
    )
    const overall = overallVerdict(reports)
    console.log(renderReport({ overall, reports, ctx, current }))

    if (args.json) {
        // JSON verdicts stay inside the documented enum. A reviewer that failed
        // gets verdict="escalate" + a populated `error` field, never an out-of-
        // contract "error" verdict — and the overall is already escalate (above).
        await writeFile(
            args.json,
            `${JSON.stringify(
                {
                    overall,
                    source: args.source,
                    base: args.base,
                    intent,
                    reviewers: reports.map(({ tag, harness, model, focus, verdict, summary, findings, error }) => ({
                        tag,
                        harness,
                        model,
                        focus,
                        verdict: verdict === "error" ? "escalate" : verdict,
                        failed: verdict === "error",
                        summary,
                        findings,
                        error: error ?? null,
                    })),
                },
                null,
                2,
            )}\n`,
        )
    }
}

main().catch((e) => {
    console.error(`adversarial-review failed: ${e?.stack ?? e}`)
    process.exit(2)
})
