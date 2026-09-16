# Claude Code Extensions

A repository for developing and managing Claude Code skills, agents, hooks, rules, MCP servers, and plugins.

## Repository Structure

```
skills/          # Skill definitions (SKILL.md per skill)
agents/          # Custom subagent definitions (.md files)
hooks/           # Hook configurations (JSON files)
rules/           # CLAUDE.md rule files (.md with optional frontmatter)
mcp/             # MCP server configurations (.json files)
plugins/         # Full plugin packages (bundled extensions)
bin/             # Install/management scripts
```

## Plugins

| Plugin | What it does |
| --- | --- |
| [`mac-app-kit`](plugins/mac-app-kit) | Scaffold, sign, notarize and ship native macOS apps: GitHub repo + Pages site, Developer ID, Mac App Store submission with listing automation, Homebrew casks |

Install a plugin from this repo's marketplace inside Claude Code:

```
/plugin marketplace add patbonecrusher/skills
/plugin install mac-app-kit@patbonecrusher
```

## Installation

### Install everything globally (all projects)

```bash
./bin/install --global
```

### Install everything into a specific project

```bash
./bin/install --project /path/to/project
```

### Install specific items

```bash
./bin/install --global --only skills/my-skill
./bin/install --project /path/to/project --only agents/code-reviewer
```

### Uninstall

```bash
./bin/install --uninstall --global
./bin/install --uninstall --project /path/to/project
```

### List installed extensions

```bash
./bin/install --list --global
./bin/install --list --project /path/to/project
```

## Creating Extensions

### Skills

Create a directory under `skills/` with a `SKILL.md`:

```
skills/my-skill/
├── SKILL.md         # Required: instructions + frontmatter
└── ...              # Optional: supporting files
```

### Agents

Create a markdown file under `agents/`:

```
agents/my-agent.md   # Agent definition with frontmatter
```

### Hooks

Create a JSON file under `hooks/`:

```
hooks/my-hooks.json  # Hook event definitions
```

### Rules

Create markdown files under `rules/`:

```
rules/code-style.md  # Rule with optional path-scoped frontmatter
```

### MCP Servers

Create JSON config under `mcp/`:

```
mcp/my-server.json   # MCP server definition
```

### Plugins

Create a full plugin package under `plugins/`:

```
plugins/my-plugin/
├── plugin.json
├── skills/
├── agents/
├── hooks/
└── .mcp.json
```
