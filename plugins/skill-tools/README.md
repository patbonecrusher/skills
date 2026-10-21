# skill-tools

Claude Code plugin for vetting skills and plugins before they run on your machine.

| Skill | Use it for |
| --- | --- |
| `skill-review` | read-only audit of a skill/plugin repo (GitHub URL, `owner/repo`, or local path): prompt injection and hidden text, risky scripts, credential access/exfiltration, hooks and MCP servers, over-broad `allowed-tools`, frontmatter/triggering, broken references, secrets. Produces a report with a verdict; never changes the target. |

```
/skill-review https://github.com/owner/repo
/skill-review owner/repo --ref v1.2.0 --path plugins/foo --strict
```

`skills/skill-review/scripts/scan.py` is the stdlib-only static scanner the skill runs first. It reads but never
executes the target, and its findings are leads that Claude then verifies in context. The checklist lives in
`skills/skill-review/reference.md`. You can also run the scanner on its own:

```
python3 -I skills/skill-review/scripts/scan.py <repo-dir> --text
```

It has no ignore/allowlist mechanism on purpose, since a suppression comment is exactly what a malicious skill would
add. Its own pattern list will match when it scans this repo.

Install from the marketplace in this repo:
```
/plugin marketplace add patbonecrusher/skills
/plugin install skill-tools@patbonecrusher
```
