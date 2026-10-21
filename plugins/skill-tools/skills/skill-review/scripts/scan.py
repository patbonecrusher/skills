#!/usr/bin/env python3
"""Static scanner for Claude Code skill / plugin repos.

Reads files only; never imports, sources or executes anything from the target.
Python is checked with compile() (parse only) and shell with `bash -n` (parse only).
Findings are leads for a human/Claude reviewer, not verdicts.

usage: scan.py <repo-dir> [--subpath DIR] [--text]
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build"}
TEXT_EXT = {".md", ".txt", ".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".json",
            ".yaml", ".yml", ".toml", ".swift", ".applescript", ".html", ".css", ".xml", ".plist", ".ps1",
            ".go", ".rs", ".lua", ".pl", ".php", ".cfg", ".ini", ".env", ""}
SCRIPT_EXT = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1"}
MAX_TEXT = 2_000_000

KNOWN_SKILL_KEYS = {"name", "description", "when_to_use", "user-invocable", "disable-model-invocation",
                    "argument-hint", "arguments", "allowed-tools", "model", "effort", "context", "agent",
                    "hooks", "paths", "shell", "license", "metadata", "version", "compatibility"}

# (id, severity, regex, message). Severity: high | medium | low | info
PATTERNS = [
    # remote code execution / installers
    ("pipe-to-shell", "high", r"\b(curl|wget)\s[^\n|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b",
     "downloads and pipes straight into a shell"),
    ("pipe-to-interp", "high", r"\b(curl|wget)\s[^\n|]*\|\s*(python3?|node|ruby|perl)\b",
     "downloads and pipes into an interpreter"),
    ("decode-exec", "high", r"base64\s+(-d|--decode|-D)\b[^\n]*\|\s*(ba|z)?sh\b", "decodes and executes hidden payload"),
    ("eval", "medium", r"\beval\s*\(|\beval\s+[\"$]", "eval of dynamic content"),
    ("exec-remote", "high", r"(exec|eval)\s*\(\s*(requests\.get|urllib|fetch)\b", "executes fetched code"),
    ("reverse-shell", "high", r"(/dev/tcp/|\bnc\b[^\n]*\s-e\s|\bncat\b[^\n]*--exec|socat\b[^\n]*exec:)",
     "reverse-shell style network command"),
    # destructive
    ("rm-rf", "medium", r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+(/|~|\$HOME|\*|\.\s|\"\$)", "recursive delete of a broad path"),
    ("sudo", "medium", r"\bsudo\b", "uses sudo"),
    ("chmod-777", "low", r"chmod\s+(-R\s+)?777", "world-writable permissions"),
    ("force-push", "medium", r"git\s+push\b[^\n]*(--force\b|-f\b)", "force push"),
    ("git-reset-hard", "low", r"git\s+(reset\s+--hard|clean\s+-[a-z]*f)", "discards local work"),
    ("no-verify", "medium", r"--no-verify\b", "skips git hooks / verification"),
    # credentials & private data
    ("ssh-keys", "high", r"~/\.ssh|\$HOME/\.ssh|id_rsa|id_ed25519", "touches SSH keys"),
    ("cloud-creds", "high", r"~/\.(aws|azure|kube|docker|gnupg|netrc)|\.config/gcloud|\$HOME/\.(aws|kube)",
     "touches cloud / credential stores"),
    ("keychain", "high", r"security\s+(find-(generic|internet)-password|dump-keychain)|secret-tool\s+lookup",
     "reads OS keychain"),
    ("gh-token", "high", r"gh\s+auth\s+token", "reads the user's GitHub token"),
    ("gh-token-env", "medium", r"\b(GITHUB_TOKEN|GH_TOKEN)\b", "uses a GitHub token variable"),
    ("browser-data", "high", r"(Cookies|Login Data|Local State)\b[^\n]*(Chrome|Chromium|Brave|Firefox)|"
     r"Library/Application Support/(Google/Chrome|BraveSoftware|Firefox)", "reads browser profile data"),
    ("dotenv-read", "medium", r"(cat|source|\.)\s+[^\n]*\.env\b|load_dotenv|printenv\b|\benv\s*\|", "reads environment / .env secrets"),
    ("anthropic-key", "medium", r"ANTHROPIC_API_KEY|OPENAI_API_KEY|CLAUDE_CODE_OAUTH", "references model API keys"),
    # exfiltration channels
    ("http-post", "medium", r"curl\b[^\n|]*(-d\b|--data|-F\b|--form|-T\b|--upload-file|-X\s*POST)|requests\.post|"
     r"fetch\([^\n]*method:\s*['\"]POST", "sends data to a remote host"),
    ("paste-sites", "high", r"(pastebin\.com|transfer\.sh|webhook\.site|requestbin|ngrok\.io|pipedream\.net|"
     r"discord(app)?\.com/api/webhooks|hooks\.slack\.com|0x0\.st|termbin)", "known exfiltration / paste endpoint"),
    ("raw-ip", "medium", r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "URL with a raw IP address"),
    ("dns-exfil", "medium", r"\b(dig|nslookup)\b[^\n]*\$", "DNS lookup built from variables"),
    # persistence / config tampering
    ("claude-config", "high", r"\.claude/settings(\.local)?\.json|--dangerously-skip-permissions|bypassPermissions|"
     r"skipDangerousModePermissionPrompt", "touches Claude settings or bypasses permissions"),
    ("claude-dir-write", "high", r"(>>?|\bcp|\bmv|\bln|\btee|\bmkdir|\binstall|\brsync)\b[^\n]*~?/?\.claude(/|\.json)",
     "writes into Claude's config directory (skills/agents/hooks/settings)"),
    ("shell-rc", "high", r"(>>?|tee\s+(-a\s+)?)\s*~?/?[^\n]*\.(zshrc|bashrc|bash_profile|profile|zprofile|zshenv)\b",
     "writes to a shell startup file"),
    ("persistence", "high", r"\bcrontab\b|launchctl\s+(load|bootstrap|submit)|LaunchAgents|systemctl\s+(--user\s+)?enable",
     "installs a persistent job"),
    ("git-config-global", "medium", r"git\s+config\s+--global", "changes global git config"),
    # unpinned supply chain
    ("npx-unpinned", "medium", r"\b(npx|bunx|pnpm\s+dlx)\s+(-y\s+|--yes\s+)?(@[\w.-]+/)?[\w.-]+(?![@\w.-]*@\d)(\s|$|['\"])",
     "runs an npm package without a pinned version"),
    ("latest-tag", "medium", r"@latest\b", "pulls @latest"),
    ("pip-unpinned", "low", r"\bpip3?\s+install\s+(?!-r\b)(?![^\n]*==)[^\n-][^\n]*", "pip install without a pinned version"),
    ("uvx", "low", r"\buvx\s+(?![^\s]*@)[\w.-]+", "uvx without a pinned version"),
    ("git-clone-run", "medium", r"git\s+clone\b[^\n]*&&[^\n]*(\./|bash|sh|make|npm\s+(i|install|run))",
     "clones then runs code from the clone"),
    # instruction-level red flags (prompt injection / deception)
    ("ignore-instructions", "high", r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier|system|user)\s+(instructions|prompts?|rules)",
     "tries to override other instructions"),
    ("conceal", "high", r"(do\s*n[o']t|never)\s+(tell|inform|mention|show|notify|alert|reveal)\s+(this\s+)?(to\s+)?(the\s+)?(user|human)s?"
     r"\s+(about|of|that you|what you|where|this)|without\s+(telling|informing|notifying|alerting)\s+(the\s+)?(user|human)|"
     r"(hide|conceal)\s+(this|it|these|the \w+)\s+from\s+(the\s+)?(user|human)", "asks Claude to hide things from the user"),
    ("silent", "medium", r"\b(silently|quietly|covertly|secretly)\s+(run|execute|send|upload|install|delete|remove|modify|write|add|copy|post|"
     r"fetch|download|exfiltrate|collect|read|change|commit|push)|without\s+(the\s+)?(user|them)\s+(knowing|noticing)", "asks for silent action"),
    ("no-confirm", "medium", r"(without|don'?t|do not|never)\s+(ask(ing)?|prompt(ing)?|confirm(ing|ation)?|wait(ing)?)\b[^\n]{0,40}"
     r"(permission|confirm|approv|user)", "tells Claude to skip confirmation"),
    ("roleplay-override", "medium", r"you are now\b|new system prompt|</?(system|instructions)>|\[\[?SYSTEM\]?\]",
     "fake system/role framing"),
    ("reviewer-targeting", "high", r"(if|when)\s+(you are|you're)\s+(reviewing|auditing|scanning|an? (ai|llm|reviewer))|"
     r"(reviewer|auditor|scanner)s?\s+(should|must)\s+(ignore|skip|approve|pass)", "text aimed at reviewers / scanners"),
]

SECRETS = [
    ("aws-key", r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("github-token", r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    ("anthropic-key", r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    ("openai-key", r"\bsk-(proj-)?[A-Za-z0-9]{32,}\b"),
    ("slack-token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("google-key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("stripe-key", r"\b(sk|rk)_live_[0-9a-zA-Z]{20,}"),
    ("private-key", r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY"),
    ("generic-secret", r"(?i)\b(api[_-]?key|secret|passw(or)?d|token)\b\s*[:=]\s*['\"]"
     r"(?![^'\"]*(your|example|xxx|placeholder|changeme|dummy|test|sample|\.\.\.|…))[^'\"\s$<{]{16,}['\"]"),
]

INVISIBLE = set(range(0x200B, 0x2010)) | set(range(0x202A, 0x202F)) | set(range(0x2060, 0x2065)) | \
            set(range(0x2066, 0x206A)) | {0x00AD, 0x180E, 0xFEFF, 0x034F, 0x115F, 0x1160, 0x3164} | \
            set(range(0xE0000, 0xE0080))

BOM = chr(0xFEFF)
COMPILED = [(i, s, re.compile(r, re.I), m) for i, s, r, m in PATTERNS]
COMPILED_SECRETS = [(i, re.compile(r)) for i, r in SECRETS]
B64 = re.compile(r"[A-Za-z0-9+/]{160,}={0,2}")
HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
ABS_HOME = re.compile(r"/Users/(?!Shared\b|you\b|me\b|username\b|USER\b|<)[A-Za-z][\w.-]+/|/home/(?!user\b|<)[a-z][\w.-]+/")

findings = []
GIT_LINKS = {}  # abs path -> abs target, for symlinks checked out as plain files (core.symlinks=false)


def load_git_links(repo):
    if not os.path.isdir(os.path.join(repo, ".git")):
        return
    r = subprocess.run(["git", "-C", repo, "ls-files", "-s", "-z"], capture_output=True, text=True, timeout=60)
    for entry in r.stdout.split("\0"):
        meta, _, path = entry.partition("\t")
        if meta.startswith("120000 "):
            full = os.path.join(repo, path)
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    target = f.read().strip()
            except OSError:
                continue
            GIT_LINKS[full] = os.path.normpath(os.path.join(os.path.dirname(full), target))


def resolve(path):
    """Resolve a path through git symlinks that were checked out as plain files."""
    parts = os.path.normpath(path).split(os.sep)
    for _ in range(40):
        for k in range(1, len(parts) + 1):
            prefix = os.sep.join(parts[:k])
            if prefix in GIT_LINKS:
                parts = GIT_LINKS[prefix].split(os.sep) + parts[k:]
                break
        else:
            return os.sep.join(parts)
    return os.sep.join(parts)


def add(sev, check, path, line, msg, excerpt=""):
    findings.append({"severity": sev, "check": check, "file": path, "line": line, "message": msg,
                     "excerpt": excerpt[:200]})


def read_text(full):
    try:
        with open(full, "rb") as f:
            data = f.read(MAX_TEXT + 1)
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def parse_frontmatter(text):
    """Minimal YAML-ish frontmatter parser: top-level scalars, block scalars, simple lists."""
    if not text.startswith("---"):
        return None, 0, ["no frontmatter (file must start with ---)"]
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, 0, ["frontmatter is not closed with ---"]
    fm, errors, i = {}, [], 1
    while i < end:
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if not m:
            errors.append(f"line {i + 1}: cannot parse `{raw.strip()[:60]}`")
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        i += 1
        if val in ("|", ">", "|-", ">-", "|+", ">+") or val == "":
            block = []
            while i < end and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            if val == "" and block and all(b.startswith("- ") or not b for b in block):
                fm[key] = [b[2:].strip().strip("'\"") for b in block if b]
            else:
                fm[key] = (" " if val.startswith(">") else "\n").join(b for b in block).strip()
        else:
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
                val = val[1:-1]
            fm[key] = val
    return fm, end + 1, errors


def plugin_root(path, repo):
    d = os.path.dirname(path)
    while d.startswith(repo):
        if os.path.isdir(os.path.join(d, ".claude-plugin")):
            return d
        if d == repo:
            break
        d = os.path.dirname(d)
    return None


def check_skill(full, rel, text, repo, inventory):
    skill_dir = os.path.dirname(full)
    dirname = os.path.basename(skill_dir)
    fm, body_start, errs = parse_frontmatter(text)
    for e in errs:
        add("high" if fm is None else "medium", "frontmatter", rel, 1, e)
    fm = fm or {}
    lines = text.split("\n")
    entry = {"path": rel, "name": fm.get("name"), "description": fm.get("description"),
             "allowed-tools": fm.get("allowed-tools"), "lines": len(lines),
             "disable-model-invocation": fm.get("disable-model-invocation")}
    inventory["skills"].append(entry)

    name = fm.get("name")
    if not name:
        add("medium", "name", rel, 1, "missing `name` (falls back to directory name)")
    else:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
            add("medium", "name", rel, 1, f"name `{name}` should be lowercase-kebab-case, <= 64 chars")
        if name != dirname:
            add("low", "name", rel, 1, f"name `{name}` differs from directory `{dirname}`")
        if re.search(r"anthropic|claude", name, re.I):
            add("medium", "name", rel, 1, f"name `{name}` uses a reserved word (anthropic/claude)")

    desc = fm.get("description")
    if not desc:
        add("high", "description", rel, 1, "missing `description`; the skill cannot be discovered/auto-invoked")
    else:
        if len(desc) > 1024:
            add("medium", "description", rel, 1, f"description is {len(desc)} chars (limit 1024)")
        if len(desc) < 40:
            add("medium", "description", rel, 1, "description is very short; unlikely to trigger reliably", desc)
        if not re.search(r"\b(use (it |this )?(when|for|whenever|if)|when the user|trigger|invoke)", desc, re.I):
            add("low", "description", rel, 1, "description does not say *when* to use the skill", desc)
        if re.search(r"<[a-zA-Z/][^>]*>", desc):
            add("low", "description", rel, 1, "description contains XML/HTML tags")

    for k in fm:
        if k not in KNOWN_SKILL_KEYS:
            add("low", "frontmatter", rel, 1, f"unknown frontmatter key `{k}`")

    tools = fm.get("allowed-tools")
    if tools:
        tl = tools if isinstance(tools, list) else re.split(r",\s*|\s+(?![^()]*\))", tools)
        for t in (x.strip() for x in tl if x.strip()):
            if t in ("Bash", "Bash(*)", "Bash(*:*)"):
                add("medium", "allowed-tools", rel, 1, "unscoped `Bash` pre-approved: every shell command runs without a prompt")
            elif re.fullmatch(r"Bash\((sudo|rm|curl|wget|sh|bash|python3?|node|eval)[: ]?\*?\)", t):
                add("medium", "allowed-tools", rel, 1, f"`{t}` pre-approves a powerful command family")
            elif t in ("WebFetch", "WebSearch") or t.startswith("mcp__"):
                add("info", "allowed-tools", rel, 1, f"`{t}` pre-approved (network/external access)")

    if len(lines) > 500:
        add("low", "size", rel, 0, f"SKILL.md is {len(lines)} lines; move detail into reference files (<500 suggested)")
    if len(text) - len("\n".join(lines[:body_start])) < 200:
        add("medium", "body", rel, body_start, "SKILL.md body is nearly empty")

    # referenced files
    proot = plugin_root(full, repo)
    refs = set()
    for m in re.finditer(r"\]\(([^)#\s]+)\)", text):
        t = m.group(1)
        if not re.match(r"^[a-z]+:|^/|^#", t):
            refs.add((t, skill_dir))
    for m in re.finditer(r"\$\{?CLAUDE_SKILL_DIR\}?/([^\s`'\")]+)", text):
        refs.add((m.group(1), skill_dir))
    for m in re.finditer(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/([^\s`'\")]+)", text):
        if proot:
            refs.add((m.group(1), proot))
    entries = set(os.listdir(skill_dir))
    for m in re.finditer(r"`([\w.-]+(?:/[\w.@-]+)*\.(?:md|py|sh|js|ts|json|txt|yaml|yml))`", text):
        t = m.group(1)
        first = t.split("/")[0]
        if "/" in t and (first in entries or first in {"scripts", "references", "reference", "templates", "assets", "examples"}):
            refs.add((t, skill_dir))
        elif "/" not in t and t not in ("SKILL.md", "README.md", "CLAUDE.md") and t.endswith(".md"):
            refs.add((t, skill_dir))
    skill_files = {f for _, _, fs in os.walk(skill_dir) for f in fs}
    for t, base in sorted(refs):
        t = t.rstrip(".,;:")
        if "/" not in t and "." not in t:
            continue
        if "/" not in t and t in skill_files:
            continue
        target = resolve(os.path.join(base, t))
        if not target.startswith(repo):
            add("medium", "reference", rel, 0, f"reference `{t}` points outside the repo")
        elif not os.path.exists(target):
            add("medium", "reference", rel, 0, f"referenced file `{t}` does not exist")

    # files in skill dir never mentioned by any markdown in it
    md_blob = text
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md") and f != "SKILL.md":
                md_blob += read_text(os.path.join(root, f)) or ""
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if f in ("SKILL.md", ".gitkeep", "LICENSE", "LICENSE.txt") or "templates" in root or ".claude-plugin" in root or \
                    not (ext in SCRIPT_EXT or ext in (".md", ".json", ".yaml", ".yml", ".html", ".txt")):
                continue
            relf = os.path.relpath(os.path.join(root, f), skill_dir)
            parts = relf.split(os.sep)
            if f in md_blob or relf in md_blob or \
                    any("/".join(parts[:k]) + "/" in md_blob for k in range(1, len(parts))):
                continue
            if True:
                add("low", "unreferenced", os.path.join(os.path.dirname(rel), relf), 0,
                    "file in the skill is never mentioned by its markdown (dead weight or hidden payload?)")


def check_agent_or_command(full, rel, text, kind, inventory):
    fm, _, errs = parse_frontmatter(text)
    inventory[kind].append({"path": rel, "name": (fm or {}).get("name"), "description": (fm or {}).get("description"),
                            "tools": (fm or {}).get("tools") or (fm or {}).get("allowed-tools")})
    if kind == "agents":
        for e in errs:
            add("medium", "frontmatter", rel, 1, e)
        if fm is not None and not fm.get("description"):
            add("medium", "description", rel, 1, "agent has no description; Claude cannot decide when to use it")


def check_json(full, rel, text, repo, inventory):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        add("high" if os.path.basename(full) in ("plugin.json", "marketplace.json", "hooks.json", ".mcp.json") else "low",
            "json", rel, e.lineno, f"invalid JSON: {e.msg}")
        return
    base = os.path.basename(full)
    if base == "plugin.json" and ".claude-plugin" in rel:
        inventory["plugins"].append({"path": rel, "name": data.get("name"), "version": data.get("version")})
        if not data.get("name"):
            add("high", "plugin", rel, 1, "plugin.json has no `name`")
        if not data.get("version"):
            add("low", "plugin", rel, 1, "plugin.json has no `version`")
        for k in ("hooks", "mcpServers"):
            if k in data:
                add("medium", k, rel, 1, f"plugin declares `{k}`: these run automatically once installed",
                    json.dumps(data[k])[:200])
    if base == "marketplace.json":
        mroot = os.path.dirname(os.path.dirname(full))
        for p in data.get("plugins", []):
            src = p.get("source")
            if isinstance(src, str) and src.startswith("."):
                if not os.path.isdir(os.path.normpath(os.path.join(mroot, src))):
                    add("high", "marketplace", rel, 1, f"plugin `{p.get('name')}` source `{src}` does not exist")
            elif src is not None:
                add("medium", "marketplace", rel, 1, f"plugin `{p.get('name')}` is pulled from an external source; "
                    "it was NOT scanned", json.dumps(src))
    if base == "hooks.json" or (base.startswith("settings") and isinstance(data, dict) and "hooks" in data):
        hooks = data.get("hooks", data)
        cmds = []
        if isinstance(hooks, dict):
            for event, arr in hooks.items():
                for h in arr if isinstance(arr, list) else []:
                    for hh in h.get("hooks", []) if isinstance(h, dict) else []:
                        cmds.append(f"{event}: {hh.get('command') or hh.get('url') or hh.get('prompt') or hh}")
        inventory["hooks"].append({"path": rel, "commands": cmds})
        for c in cmds:
            add("medium", "hooks", rel, 0, "hook runs automatically on Claude events; verify what it does", c)
    if base == ".mcp.json" or (isinstance(data, dict) and "mcpServers" in data and base != "plugin.json"):
        servers = data.get("mcpServers", {})
        for n, s in servers.items():
            desc = " ".join([str(s.get("command", "")), *map(str, s.get("args", []))]) or s.get("url", "")
            inventory["mcp"].append({"path": rel, "name": n, "run": desc})
            add("medium", "mcp", rel, 0, f"MCP server `{n}` starts automatically when enabled", desc)


def check_script(full, rel, text):
    ext = os.path.splitext(full)[1]
    first = text.split("\n", 1)[0]
    mode = os.lstat(full).st_mode
    if ext in (".sh", ".bash", ".zsh", ".py", ".rb", ".pl") or first.startswith("#!"):
        if not first.startswith("#!"):
            if ext in (".sh", ".bash", ".zsh"):
                add("low", "script", rel, 1, "shell script has no shebang")
        elif not mode & stat.S_IXUSR:
            add("info", "script", rel, 1, "script has a shebang but is not executable")
    if ext == ".py":
        try:
            compile(text, rel, "exec")
        except SyntaxError as e:
            add("medium", "syntax", rel, e.lineno or 0, f"Python syntax error: {e.msg}")
    if ext in (".sh", ".bash") or re.match(r"#!.*\b(ba)?sh\b", first):
        r = subprocess.run(["bash", "-n", full], capture_output=True, text=True, timeout=20)
        if r.returncode:
            add("medium", "syntax", rel, 0, "bash parse error", r.stderr.strip())
        if shutil.which("shellcheck"):
            r = subprocess.run(["shellcheck", "-f", "json", "-S", "warning", full], capture_output=True, text=True, timeout=60)
            try:
                for item in json.loads(r.stdout or "[]")[:15]:
                    add("low", "shellcheck", rel, item.get("line", 0), f"SC{item.get('code')}: {item.get('message')}")
            except json.JSONDecodeError:
                pass


def scan_text(rel, text, is_md):
    lines = text.split("\n")
    for n, line in enumerate(lines, 1):
        bad = sorted({f"U+{ord(c):04X}" for c in line if ord(c) in INVISIBLE and not (n == 1 and c == BOM and line.startswith(BOM))})
        if bad:
            sev = "high" if any(b.startswith("U+E00") or b in ("U+202E", "U+2066", "U+2067", "U+2068") for b in bad) else "medium"
            hidden = "".join(chr(ord(c) - 0xE0000) for c in line if 0xE0020 <= ord(c) <= 0xE007E)
            msg = f"invisible/bidi characters {', '.join(bad[:8])}" + (f"; tag chars spell: {hidden!r}" if hidden else "")
            add(sev, "invisible-unicode", rel, n, msg,
                "".join(c if ord(c) not in INVISIBLE else "␣" for c in line).strip())
        if len(line) > 4000 and is_md:
            add("low", "long-line", rel, n, f"{len(line)}-char line in markdown (content may hide off-screen)")
        for cid, sev, rx, msg in COMPILED:
            if rx.search(line):
                add(sev, cid, rel, n, msg, line.strip())
        for sid, rx in COMPILED_SECRETS:
            if rx.search(line):
                add("high", "secret", rel, n, f"possible {sid}", rx.sub(lambda m: m.group(0)[:6] + "…", line.strip()))
        if ABS_HOME.search(line):
            add("low", "abs-path", rel, n, "hardcoded user home path (machine-specific / personal info)", line.strip())
        for m in B64.finditer(line):
            add("medium", "base64-blob", rel, n, f"{len(m.group(0))}-char base64-like blob", m.group(0)[:80])
    if is_md:
        for m in HTML_COMMENT.finditer(text):
            body = m.group(1).strip()
            if body:
                add("medium", "html-comment", rel, text.count("\n", 0, m.start()) + 1,
                    "HTML comment (invisible when rendered, still read by Claude)", body)


def main():
    args = sys.argv[1:]
    as_text = "--text" in args
    args = [a for a in args if a != "--text"]
    subpath = ""
    if "--subpath" in args:
        i = args.index("--subpath")
        subpath = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    repo = os.path.realpath(args[0])
    top = os.path.realpath(os.path.join(repo, subpath)) if subpath else repo
    if not top.startswith(repo) or not os.path.isdir(top):
        print(f"not a directory inside the repo: {top}", file=sys.stderr)
        sys.exit(2)

    load_git_links(repo)
    inventory = {"skills": [], "commands": [], "agents": [], "plugins": [], "hooks": [], "mcp": [],
                 "scripts": [], "binaries": [], "files": 0}
    for root, dirs, files in os.walk(top, followlinks=False):
        for d in list(dirs):
            if d in SKIP_DIRS:
                dirs.remove(d)
                if d == "node_modules":
                    add("medium", "vendored", os.path.relpath(os.path.join(root, d), repo), 0,
                        "vendored node_modules (third-party code shipped with the skill; not scanned)")
            elif os.path.islink(os.path.join(root, d)):
                dirs.remove(d)
                files.append(d)
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, repo)
            inventory["files"] += 1
            if os.path.islink(full) or full in GIT_LINKS:
                target = GIT_LINKS.get(full) or os.path.realpath(full)
                shown = os.path.relpath(target, os.path.dirname(full)) if full in GIT_LINKS else os.readlink(full)
                inside = resolve(target).startswith(repo + os.sep)
                add("low" if inside else "high", "symlink", rel, 0,
                    f"symlink -> {shown}" + (" (inside repo; reviewed at its target)" if inside else " (points OUTSIDE the repo)"))
                continue
            size = os.path.getsize(full)
            ext = os.path.splitext(f)[1].lower()
            text = read_text(full) if size <= MAX_TEXT else None
            if text is None:
                with open(full, "rb") as fh:
                    magic = fh.read(4)
                is_exec = magic in (b"\x7fELF", b"MZ\x90\x00", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xfe\xed\xfa\xcf")
                if ext not in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".icns", ".webp", ".pdf", ".woff", ".woff2", ".ttf", ".otf"} or is_exec:
                    inventory["binaries"].append(rel)
                    add("high" if is_exec else "medium", "binary", rel, 0,
                        ("compiled executable" if is_exec else f"binary/oversized file ({size} bytes)") + " cannot be reviewed")
                continue
            is_md = ext == ".md"
            scan_text(rel, text, is_md)
            if f == "SKILL.md":
                check_skill(full, rel, text, repo, inventory)
            elif is_md and os.path.basename(root) == "agents":
                check_agent_or_command(full, rel, text, "agents", inventory)
            elif is_md and os.path.basename(root) == "commands":
                check_agent_or_command(full, rel, text, "commands", inventory)
            elif ext == ".json":
                check_json(full, rel, text, repo, inventory)
            if ext in SCRIPT_EXT or text.startswith("#!"):
                inventory["scripts"].append(rel)
                check_script(full, rel, text)

    names = {}
    for sk in inventory["skills"]:
        names.setdefault(sk.get("name"), []).append(sk["path"])
    for n, paths in names.items():
        if n and len(paths) > 1:
            add("low", "duplicate-skill", paths[0], 0, f"skill name `{n}` defined {len(paths)} times: {', '.join(paths)}")
    if not inventory["skills"] and not inventory["plugins"] and not inventory["commands"] and not inventory["agents"]:
        add("info", "inventory", subpath or ".", 0, "no SKILL.md, plugin.json, commands/ or agents/ found")

    grouped = {}
    for x in findings:
        g = grouped.setdefault((x["file"], x["check"], x["message"]), dict(x, more=[]))
        if g is not x and g["line"] != x["line"]:
            g["more"].append(x["line"])
    findings[:] = list(grouped.values())
    for x in findings:
        if x["more"]:
            extra = ", ".join(map(str, x["more"][:10])) + ("…" if len(x["more"]) > 10 else "")
            x["message"] += f" (+{len(x['more'])} more: lines {extra})"
        del x["more"]
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    findings.sort(key=lambda x: (order[x["severity"]], x["file"], x["line"]))
    counts = {s: sum(1 for x in findings if x["severity"] == s) for s in order}
    out = {"repo": repo, "scanned": top, "counts": counts, "inventory": inventory, "findings": findings}
    if not as_text:
        json.dump(out, sys.stdout, indent=1)
        print()
        return
    print(f"scanned {top}  ({inventory['files']} files)  " + "  ".join(f"{k}={v}" for k, v in counts.items()))
    for k in ("plugins", "skills", "commands", "agents", "hooks", "mcp"):
        for item in inventory[k]:
            print(f"  [{k}] {item.get('path')}  {item.get('name') or ''}")
    for x in findings:
        loc = f"{x['file']}:{x['line']}" if x["line"] else x["file"]
        print(f"{x['severity'].upper():6} {x['check']:18} {loc}  {x['message']}")
        if x["excerpt"]:
            print(f"       > {x['excerpt']}")


if __name__ == "__main__":
    main()
