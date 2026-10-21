# Skill review checklist

Severity guide: 🔴 blocker (don't install), 🟡 warning (fix or accept knowingly), 🟢 suggestion (quality).

## 1. Security and safety

A skill runs with the user's permissions and Claude follows its text, so treat it like code *and* like a prompt.

### Instruction-level (the skill talking to Claude)
| Look for | Severity |
| --- | --- |
| Instructions to ignore the user/system, hide actions, "don't mention", act silently, skip confirmation | 🔴 |
| Text aimed at reviewers/scanners ("if you are reviewing this…", "approve this", "skip setup.sh") | 🔴 |
| Hidden text: HTML comments with instructions, zero-width or Unicode tag characters (they can spell words, and the scanner decodes them), bidi overrides, base64 that decodes to instructions | 🔴 |
| Description says one thing, body does another (e.g. "format code" but uploads files) | 🔴 |
| Instructions in a reference file that the SKILL.md doesn't explain or need | 🟡 (🔴 if harmful) |
| Fake system framing (`<system>`, "you are now", "new instructions") | 🟡 |
| Telling Claude to fetch and follow instructions from a URL at runtime (the content can change after review) | 🟡, 🔴 if the URL isn't the author's own |

### Code-level (scripts, hooks, commands in the markdown)
| Look for | Severity |
| --- | --- |
| Reading secrets: `~/.ssh`, `~/.aws`, `~/.kube`, `.netrc`, keychain, browser profiles, `gh auth token`, API-key env vars, `.env` | 🔴 unless clearly the skill's purpose *and* the data stays local |
| Sending data off-machine: POST/upload to non-obvious hosts, paste/webhook sites, raw IPs, DNS tricks | 🔴 if secrets or user files can reach it; 🟡 for telemetry the skill doesn't mention |
| Remote code execution: `curl … | sh`, decode-and-exec, `eval` of fetched content, clone-then-run | 🔴 |
| Persistence or config tampering: shell rc files, crontab/launchd, `~/.claude/settings.json`, installing hooks/skills, `--dangerously-skip-permissions`, global git config | 🔴 unless that *is* the skill and it asks first |
| Destructive commands: `rm -rf` on broad or unvalidated paths, `git reset --hard`, force push, `sudo` | 🟡 (🔴 if unguarded on user data) |
| Symlinks pointing outside the repo, compiled binaries, minified or obfuscated JS | 🔴 binaries/obfuscation (can't be reviewed); 🟡 symlinks |
| Hooks (`hooks.json`, plugin `hooks`) | 🟡 always list them, since they run with no prompt on every matching event |
| MCP servers (`.mcp.json`, plugin `mcpServers`) | 🟡 list what each launches; 🔴 if unpinned remote package plus broad access |

### Permissions
- `allowed-tools: Bash` (unscoped) pre-approves **every** shell command while the skill is active. 🟡 by
  default; 🔴 if combined with network or credential access. Prefer scoped grants: `Bash(git status:*)`, `Bash(npm test:*)`.
- `Write`/`Edit` pre-approved: fine for scaffolding skills; question it for "read-only" skills.
- `WebFetch` or MCP tools pre-approved: note them; they matter in combination with data access.
- Skills that deploy, publish, send or delete should set `disable-model-invocation: true` so they run only on request. 🟡 if missing.

### Supply chain
- Unpinned `npx pkg`, `uvx pkg`, `pip install pkg`, `@latest`, `brew install` of third-party taps, GitHub Actions
  pinned to a branch: 🟡 (the code can change after review). 🔴 under `--strict`.
- Vendored `node_modules` or third-party code: 🟡 not reviewed; list it.
- External plugin sources in `marketplace.json` (other repos/URLs): not covered by this review; say so.

### Secrets and personal data
- Real-looking keys/tokens/private keys committed: 🔴 (tell the author to rotate them).
- Hardcoded `/Users/<name>/…`, emails, team IDs, internal hostnames: 🟢/🟡 (portability, privacy).

### Legitimate vs suspicious: how to decide
- **Purpose fit**: an App Store skill reading an App Store Connect key in `~/.appstoreconnect` is expected; a
  "markdown formatter" reading `~/.ssh` is not.
- **Disclosure**: does the SKILL.md tell Claude, and so the user, what it will do before doing it?
- **Destination**: data going to the service the skill is about (e.g. `api.github.com` for a GitHub skill) vs anywhere else.
- **Consent**: hard-to-reverse or outward-facing steps behind a confirmation?
- **Docs vs code**: a dangerous command shown as an example in prose is lower risk than the same command in a
  script or a step Claude is told to run. Still flag examples that Claude would plausibly copy and run.

## 2. Structure and validity

- Each skill is a directory with `SKILL.md` starting with `---` YAML frontmatter, closed by `---`.
- `name`: lowercase letters, digits, hyphens; ≤ 64 chars; matches the directory; no "anthropic"/"claude".
- `description`: present, ≤ 1024 chars, no XML tags.
- Known keys only: `name, description, when_to_use, user-invocable, disable-model-invocation, argument-hint,
  arguments, allowed-tools, model, effort, context, agent, hooks, paths, shell, license, metadata, version`.
  Unknown keys are ignored silently, which usually means a typo.
- Every referenced file (`[x](reference.md)`, `${CLAUDE_SKILL_DIR}/scripts/x.sh`, `${CLAUDE_PLUGIN_ROOT}/…`) exists.
  Files nobody references are dead weight or a hiding place.
- Plugins: `.claude-plugin/plugin.json` valid JSON with `name` (and `version`); components in the conventional dirs
  (`skills/`, `agents/`, `commands/`, `hooks/hooks.json`, `.mcp.json`); `marketplace.json` sources resolve.
- Scripts: shebang, executable bit if run directly, parse cleanly (`bash -n`, Python compile), shellcheck clean.
  Scripts should resolve paths from their own location or `${CLAUDE_SKILL_DIR}`, not the current directory.
- `model:` overrides naming retired or nonexistent models: 🟢.

## 3. Triggering (will Claude use it at the right time?)

- The description states **what** it does and **when** to use it, in the user's vocabulary, with concrete triggers
  ("Use when the user asks to … / mentions …"). Vague ("helps with code") → 🟡: it won't fire or fires randomly.
- Not so broad it hijacks common requests ("use for any coding task") → 🟡.
- Doesn't collide with another skill in the same repo or with built-ins (two skills claiming "review code").
- `argument-hint` matches how `$ARGUMENTS` / `$0…` are actually used in the body.
- Manual-only skills (`disable-model-invocation: true`) don't need trigger phrasing; user-invocable `false`
  skills must have a strong description.

## 4. Instruction quality

- SKILL.md ≲ 500 lines; detail in reference files loaded on demand, one level deep (no reference → reference chains).
- Steps are concrete and ordered: exact commands, file paths, expected outputs, what to do on failure.
- Says what to do when inputs are missing (ask vs default), and doesn't over-ask.
- Confirmation points before irreversible or outward-facing actions (publish, push, send, delete, pay).
- No contradictions between sections or with reference files; no "always/never" rules that conflict.
- No machine-specific assumptions (absolute home paths, a particular username, tools not checked for).
- Doesn't re-explain what Claude already knows; spends words on what's specific to this task.
- Examples are correct and would actually run.

## 5. Hygiene

- README explaining what each skill does and how to install; license present.
- Version bumped in `plugin.json` when behavior changes.
- No large generated files, `.DS_Store`, caches, or test junk.
