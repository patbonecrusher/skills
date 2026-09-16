# mac-app-kit

Claude Code plugin for building and shipping native macOS apps, distilled from shipping SVG Viewer
(github.com/patbonecrusher/svg-viewer): scaffolding, signing, notarization, Mac App Store submission with
listing automation, Homebrew casks, GitHub Pages marketing sites.

| Skill | Use it for |
| --- | --- |
| `new-mac-app` | scaffold a Swift Package app with build/sign scripts, sandbox, icon, GitHub repo + Pages site |
| `mac-app-signing` | Developer ID + notarization for direct download; certificates; Gatekeeper checks |
| `app-store-submit` | certs → profile → pkg → upload → listing (`asc.py`) → submit → App Review replies |
| `brew-cask-release` | notarized release + Homebrew tap cask, per-release automation |

`scripts/` holds the reusable tools (`asc.py`, `new-mac-app.sh`, `record-demo.sh`, screenshot helpers);
`templates/` the project and tap templates with `__PLACEHOLDER__` substitution.

Install from the marketplace in this repo:
```
/plugin marketplace add patbonecrusher/skills
/plugin install mac-app-kit@patbonecrusher
```
