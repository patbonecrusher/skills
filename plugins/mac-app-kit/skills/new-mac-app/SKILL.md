---
name: new-mac-app
description: Scaffold a new native macOS app (Swift Package + SwiftUI/AppKit, no Xcode project) with build/sign/notarize scripts, sandbox entitlements, generated icon, GitHub repo, and a GitHub Pages marketing site + privacy policy. Use when the user asks to create/start a new Mac app, "make me a macOS app", or set up the repo/site for one.
argument-hint: "<App Name>" [--bundle-id com.x.y] [--repo slug]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# New macOS app

Scaffolds a complete, shippable Mac app project the way SVG Viewer (github.com/patbonecrusher/svg-viewer) is built:
a Swift Package that `build.sh` turns into a signed `.app`, sandboxed from day one, with release tooling for
Developer ID, the Mac App Store and Homebrew already wired in.

## Gather inputs (ask only for what's missing; infer the rest)

| Input | Default |
| --- | --- |
| App name | from the request |
| Bundle ID | `com.<author-domain>.<ExecName>` — Pat uses `com.patlaplante.<ExecName>` |
| Repo slug | kebab-case of the name |
| GitHub user | `gh api user -q .login` |
| Author | `git config user.name` |
| Team ID | the team in `security find-identity -v -p codesigning` (parenthesized code on *Apple Distribution* / *Developer ID* certs — NOT the one on "Apple Development", that's a personal ID). Pat: `TEAMID`. |
| Category | `public.app-category.utilities` unless obvious |
| Tagline | one sentence; used for site, listing and repo description |

## Steps

1. Run the scaffolder (it copies `${CLAUDE_PLUGIN_ROOT}/templates/app`, substitutes placeholders, builds once, `git init`s,
   creates the GitHub repo and enables Pages from `main:/docs`):
   ```sh
   ${CLAUDE_PLUGIN_ROOT}/scripts/new-mac-app.sh --name "App Name" --bundle-id com.x.appname --repo app-name \
     --github-user USER --author "Name" --team-id TEAMID --category public.app-category.utilities --tagline "…" --dir /parent/dir
   ```
   Add `--no-github` if the user hasn't asked for a repo, `--private` for a private repo. Creating a public repo is
   outward-facing — confirm visibility if the user didn't say.
2. Replace `ContentView.swift` with the real app. Keep the patterns already in `App.swift`: `Settings` scene (⌘,),
   `Commands`, `AppDelegate` with `Prefs.registerDefaults()` and the `-preferRetina` / `-windowSize` debug hooks
   (needed later for screenshots). For a document-based app use `DocumentGroup(viewing:)` / `FileDocument`, add
   `CFBundleDocumentTypes` (+ `UTImportedTypeDeclarations` for custom extensions) to `Info.plist`, and expose
   per-window state to menu commands with `@FocusedValue`.
3. Icon: `Tools/MakeIcon/main.swift` draws a gradient tile with the app's initial at build time — replace `drawIcon()`
   with real artwork (CoreGraphics) or load a 1024 PNG. Keep the macOS icon grid (824 pt rounded square, radius 186, in 1024).
4. Marketing: rewrite `docs/index.html` copy (hero paragraph, feature cards, badges), `Marketing/listing.json`
   (App Store text; keys documented in app-store-submit), `README.md`. The privacy page already states "no data collected".
5. Verify: `./build.sh --sign dev --open` (Apple Development cert + real sandbox). Screenshot with
   `screencapture -x -o -l <windowID>` (get IDs by compiling `${CLAUDE_PLUGIN_ROOT}/scripts/window-ids.swift`). Read the
   screenshot — don't assume it rendered.
6. Commit and push. Tell the user the repo URL, site URL, and which skills come next (mac-app-signing, app-store-submit,
   brew-cask-release).

## Conventions baked into the template

- macOS 14 deployment target, Swift tools 5.9 (language mode 5 — avoids strict-concurrency friction).
- Sandbox entitlements: `app-sandbox`, `files.user-selected.read-write`, `network.client`. Keep `network.client` if the
  app uses WKWebView at all — WebKit's networking process needs it even for local HTML (otherwise: blank view, no error).
- Public API only. Never `setValue(_:forKey:)` on WebKit/AppKit private keys (e.g. `drawsBackground`) — App Review flags it.
- `ITSAppUsesNonExemptEncryption = NO` in Info.plist (skips export-compliance questions on every upload).
- `build.sh` modes: ad-hoc (default), `--sign dev`, `--sign devid [--notarize]`, `--sign appstore --pkg [--upload]`, `--universal`.
- Window restoration will reopen every previously open document on relaunch; when testing many files launch with
  `--args -ApplePersistenceIgnoreState YES`.

## Gotchas learned the hard way

- `ls` may be aliased (eza) in Pat's shell; use `/bin/ls` in scripts. `rm` is aliased to `trash` — use `/bin/rm`.
- SwiftUI `DocumentGroup(viewing:)` shows the Open panel on launch; `applicationShouldOpenUntitledFile` → false.
- `keyboardShortcut("+", modifiers: .command)` works for Zoom In (SwiftUI matches the shifted character).
- Menu `Picker` inside `Menu` with `.pickerStyle(.inline)` renders as radio items; put it in both the View menu and toolbar.
