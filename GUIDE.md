# Extension Guide

## `skills/` — Slash Commands

Skills are custom commands invoked via `/skill-name` in Claude Code. Each skill is a directory with a `SKILL.md` entrypoint.

**Structure:**
```
skills/
└── my-skill/
    ├── SKILL.md           # Required — instructions + frontmatter
    ├── reference.md       # Optional — detailed docs Claude can read
    └── scripts/           # Optional — helper scripts
```

**SKILL.md format:**
```markdown
---
name: my-skill
description: Short description of what this skill does
user-invocable: true
argument-hint: [optional-args]
allowed-tools: Read, Grep, Bash
model: claude-sonnet-4-6
---

# Instructions for Claude

Detailed instructions go here...
```

**Key frontmatter fields:**
- `name` — Display name for `/slash-command` (defaults to directory name)
- `description` — When to use; Claude uses this to decide auto-invocation
- `user-invocable` — Set `false` to hide from `/` menu (Claude can still invoke it)
- `disable-model-invocation` — Set `true` to prevent Claude from auto-invoking
- `argument-hint` — Autocomplete hint, e.g. `[filename]` or `[issue-number]`
- `allowed-tools` — Tools Claude can use without prompting for permission
- `model` — Override model when skill is active
- `context: fork` — Run in a subagent context (isolated)
- `agent` — Subagent type: `Explore`, `Plan`, `general-purpose`, or custom

**Substitution variables:**
- `$ARGUMENTS` — All arguments passed to the skill
- `$0`, `$1`, etc. — Positional arguments
- `${CLAUDE_SKILL_DIR}` — Path to the skill's directory

---

## `agents/` — Custom Subagents

Agents are specialized workers that Claude can spawn for isolated tasks. Each agent is a single `.md` file.

**Structure:**
```
agents/
├── code-reviewer.md
└── test-writer.md
```

**File format:**
```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
model: claude-opus-4-6
tools: Read, Grep, Glob
skills:
  - detect-bugs
---

# Code Review Agent

You are a code reviewer. Analyze the provided code for:
1. Quality issues
2. Performance problems
3. Security vulnerabilities

Be concise and actionable.
```

**Key frontmatter fields:**
- `name` — Agent identifier
- `description` — What the agent does (Claude uses this to decide when to spawn it)
- `model` — Model to use
- `tools` — Comma-separated list of available tools
- `skills` — Skills preloaded into the agent
- `hooks` — Hooks scoped to this agent's lifecycle
- `memoryEnabled` — Enable auto memory for the agent

---

## `hooks/` — Automation Triggers

Hooks run shell commands in response to Claude Code lifecycle events. Each file is a JSON object mapping event names to hook arrays.

**Structure:**
```
hooks/
├── formatting.json
└── validation.json
```

**File format:**
```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "npx prettier --write $(jq -r '.tool_input.file_path')"
        }
      ]
    }
  ]
}
```

**Supported events:**
- `PreToolUse` / `PostToolUse` — Before/after a tool runs (matcher = tool name regex)
- `UserPromptSubmit` — When user sends a message
- `SessionStart` / `SessionEnd` — Session lifecycle
- `Notification` — When Claude needs attention
- `SubagentStart` / `SubagentStop` — Subagent lifecycle
- `Stop` — When Claude finishes responding

**Hook types:**
- `command` — Run a shell command (input on stdin as JSON, exit 2 to block)
- `http` — Call a webhook URL
- `prompt` — Ask Claude to evaluate a condition
- `agent` — Spawn an agent to verify something

**Note:** The install script merges these into the target `settings.json` under the `hooks` key.

---

## `rules/` — Context Rules

Rules are markdown files loaded into Claude's context. They can be global or scoped to specific file paths via frontmatter.

**Structure:**
```
rules/
├── code-style.md
├── testing.md
└── api-design.md
```

**File format (global rule):**
```markdown
# Code Style

- Use 2-space indentation
- Prefer const over let
- No default exports
```

**File format (path-scoped rule):**
```markdown
---
paths:
  - "src/api/**/*.ts"
  - "src/services/**/*.ts"
---

# API Development Rules

- All endpoints require input validation
- Use standard error response format
- Add OpenAPI annotations
```

Rules are loaded into `~/.claude/rules/` (global) or `.claude/rules/` (project). Path-scoped rules only activate when Claude works with matching files.

---

## `mcp/` — MCP Server Configs

MCP (Model Context Protocol) servers connect Claude to external tools, databases, and APIs. Each file defines one or more server configurations.

**Structure:**
```
mcp/
├── github.json
└── database.json
```

**File format:**
```json
{
  "server-name": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "${GITHUB_TOKEN}"
    }
  }
}
```

**Server types:**
- `stdio` — Local process communicating via stdin/stdout
- `http` — Remote HTTP server
- `sse` — Server-sent events (deprecated, use http)

**Common fields:**
- `command` + `args` — For stdio servers
- `url` — For http/sse servers
- `env` — Environment variables (supports `${VAR}` and `${VAR:-default}`)
- `headers` — HTTP headers for remote servers

**Note:** The install script merges these into `~/.claude.json` (global) or `.mcp.json` (project) under the `mcpServers` key.

---

## `plugins/` — Bundled Extensions

Plugins package multiple extension types together (skills, agents, hooks, MCP servers) for distribution.

**Structure:**
```
plugins/
└── my-plugin/
    ├── plugin.json        # Required — plugin manifest
    ├── skills/
    │   └── my-skill/
    │       └── SKILL.md
    ├── agents/
    │   └── my-agent.md
    ├── hooks/
    │   └── hooks.json
    └── .mcp.json          # Or mcpServers in plugin.json
```

**plugin.json format:**
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": "Your Name",
  "license": "MIT",
  "mcpServers": {}
}
```

**Installation:** Plugins are installed via `claude plugin add <path>`, not symlinked. The install script prints the commands to run.

**Namespacing:** Plugin skills are accessed as `plugin-name:skill-name` to avoid conflicts.
