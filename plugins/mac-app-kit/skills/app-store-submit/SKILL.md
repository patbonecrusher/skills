---
name: app-store-submit
description: Submit a macOS app to the Mac App Store end to end — distribution certificates, App ID, provisioning profile, sandboxed pkg build, altool upload, App Store Connect listing automation (metadata, screenshots, price, review info, build attach, submit) via the ASC API, and handling App Review replies (Guideline 2.1 info requests, screen recordings). Use for "put it on the App Store", "submit for review", App Store Connect, altool/ITMS errors, or App Review responses.
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Mac App Store submission

Guided walkthrough — many steps are clicks in Apple's web UI that only the user can do. Do everything that can be
done from the terminal; for portal steps give the exact page (open it with `open <url>`) and exact clicks, one step
at a time, and verify each with a command before moving on. Read `reference.md` in this skill for the full detail.

## Order of operations

1. **Certificates** (developer.apple.com → Certificates → +, under *Software*): *Apple Distribution* (app) and
   *Mac Installer Distribution* (pkg). Verify: `security find-identity -v | grep -E "Distribution|Installer"`.
   One CSR (Keychain Access → Certificate Assistant) serves all certs. Team ID = the code in parentheses on these certs.
2. **App ID** (Identifiers → +, App IDs → App): explicit bundle ID, no capabilities. Platforms are just listed, nothing to tick.
3. **Provisioning profile** (Profiles → + → Distribution → *Mac App Store Connect* → Mac → App ID → a distribution cert):
   download to `Resources/<Exec>.provisionprofile` (git-ignored). **The app must be signed with the exact certificate embedded
   in the profile** — `build.sh --sign appstore` extracts the cert SHA-1 from the profile and signs with it; anything else
   fails validation with "must be signed with the certificate that is contained in the provisioning profile".
   Check: `security cms -D -i profile | plutil -p -` (TeamIdentifier, application-identifier, DeveloperCertificates).
4. **App record** (appstoreconnect.apple.com → My Apps → + → New App): macOS, name (may need a suffix if taken), bundle ID, SKU.
5. **API key** (Users and Access → Integrations → App Store Connect API → +, role App Manager): `.p8` downloadable once →
   `~/.appstoreconnect/private_keys/AuthKey_<KEYID>.p8`; note Key ID and Issuer ID. `export ASC_KEY_ID=… ASC_ISSUER_ID=…` (or keep them in `~/.config/mac-app-kit/defaults.env`).
6. **Build + upload**: `./build.sh --universal --sign appstore --pkg --upload` (validate → upload via `xcrun altool`).
   Delivery is accepted async — processing takes 10–40 min; a *rejection email* arrives instead of a build appearing.
   Check email if no build shows after ~30 min (`Tools/asc.py status`).
7. **Listing**: fill `Marketing/listing.json`, put 2560×1600 PNGs in `Marketing/screenshot-*.png`, then `Tools/asc.py all`
   (metadata, content rights, subtitle, categories, age rating, screenshots, price = free + all territories, review contact copied
   from another of the account's apps or `REVIEW_*` env vars, attach latest processed build). `Tools/asc.py status` to inspect.
8. **App Privacy** — no public API. User clicks: App Privacy → Get Started → "No, we do not collect data" → **Publish**
   (answers stay a draft until Publish is clicked; submission fails with "must have published answers to your app's data usages").
9. **Submit**: `Tools/asc.py submit`. On 409 "not in valid state", the `associatedErrors` in the response name the missing piece
   (content rights, privacy, build…). Confirm with the user before submitting — it's outward-facing.
10. **Wait**; poll `Tools/asc.py status`. Version states: PREPARE_FOR_SUBMISSION → WAITING_FOR_REVIEW → IN_REVIEW → …

## Build requirements (already in the template `build.sh`)

- Sandbox on; `network.client` if any WKWebView; `ITSAppUsesNonExemptEncryption=NO`; `LSApplicationCategoryType` set;
  `.icns` includes 1024 px (App Store Connect takes the macOS icon from the build — the grid placeholder on the page is normal until a build attaches).
- `xattr -cr` the bundle before signing — **ITMS-91109** rejects packages containing `com.apple.quarantine` (downloaded profile!).
- Entitlements for the store build add `com.apple.application-identifier = TEAM.bundleid` and `com.apple.developer.team-identifier`.
- `productbuild --component App.app /Applications --sign "3rd Party Mac Developer Installer: …" out.pkg`.
- `CFBundleVersion` must strictly increase per upload; a rejected delivery burns the number.
- Distribution-signed builds don't launch locally. Test/screenshot with `--sign dev`.

## Screenshots

macOS App Store: 16:10, 1280×800 / 1440×900 / 2560×1600 / 2880×1800, opaque PNG. Recipe: launch the dev-signed app with
`--args -ApplePersistenceIgnoreState YES -preferRetina YES -windowSize 1180x760`, capture with `screencapture -x -o -l <id>`
(IDs from `window-ids.swift`; must be on a 2× display or the capture is 1×), composite with
`${CLAUDE_PLUGIN_ROOT}/scripts/compose-screenshot.swift` (`swiftc -O` it; args: capture out.png [dark]). Show real UI, not splash art.
Per-app UI state for shots: launch flags such as `-showSource YES` read via `UserDefaults` are cheap to add.

## App Review "Guideline 2.1 – Information Needed" (new developer accounts get this)

They want: (1) a screen recording from launch through the main flow on a physical Mac, (2) purpose/audience, (3) setup
instructions, (4) external services (say "none, Apple frameworks only" if true), (5) regional differences ("none"),
(6) regulated content ("n/a"). Template: `${CLAUDE_PLUGIN_ROOT}/templates/app/Marketing/review-notes.md`. Put the text in
App Review Information → Notes (`Tools/asc.py review-info` does it) AND paste it as the Resolution Center reply with the video
attached — the reply thread has no public API, the user does that part.

Recording: `${CLAUDE_PLUGIN_ROOT}/scripts/record-demo.sh` drives the app with an AppleScript (`demo-example.applescript`) while
`screencapture -v` records. Needs the terminal app hosting Claude in System Settings → Privacy & Security → Accessibility; the user must stay hands-off (keystrokes go to
the frontmost app); hide other apps first; record the display the windows are on (`-D 1` main, `-D 2` built-in); make Open-panel
steps wait for a new document window; watch for leftover files causing "Replace?" sheets; trim the tail with ffmpeg; review frames.

## Tools in this plugin

- `${CLAUDE_PLUGIN_ROOT}/scripts/asc.py` — App Store Connect API client (PEP 723; runs with `uv run`). Copy into `Tools/` of the project.
  Commands: `status`, `metadata`, `screenshots [files]`, `build [version] [number]`, `price`, `review-info`, `submit`, `all`.
  Auth: `ASC_KEY_ID`, `ASC_ISSUER_ID`. Bundle ID from `Resources/Info.plist`. Text from `Marketing/listing.json`:
  `subtitle, description, promotionalText, keywords, supportUrl, marketingUrl, privacyPolicyUrl, primaryCategory (ASC enum e.g.
  GRAPHICS_AND_DESIGN, DEVELOPER_TOOLS, UTILITIES), secondaryCategory, copyright, reviewNotes`.
- The ASC API quirks it already handles: `/builds?filter[app]=` (not `/apps/{id}/builds` with sort); age rating needs *every*
  attribute sent explicitly; local IDs in inline `included` must be `${…}`; content rights on `/apps/{id}`; reuse an open
  `reviewSubmission` instead of creating duplicates.
