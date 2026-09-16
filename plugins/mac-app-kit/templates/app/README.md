# __APP_NAME__

__TAGLINE__

Native macOS app (Swift, SwiftUI/AppKit). Sandboxed, no accounts, no telemetry.

## Install

```sh
brew install --cask __GITHUB_USER__/tap/__CASK__
```

or the Mac App Store / the [releases page](https://github.com/__GITHUB_USER__/__REPO__/releases). Website: __SITE_URL__

## Build

```sh
./build.sh            # → build/__APP_NAME__.app (ad-hoc signed, sandboxed)
./build.sh --open
./build.sh --sign dev # Apple Development signing (tests the sandbox for real)
```

Requires Xcode 15+. No Xcode project — a Swift Package; `build.sh` assembles the `.app` bundle.
Signed / notarized / App Store builds: see [RELEASING.md](RELEASING.md).

## Layout

| Path | Purpose |
| --- | --- |
| `Sources/__EXEC_NAME__/` | App entry, views, settings |
| `Resources/Info.plist`, `Resources/__EXEC_NAME__.entitlements` | Bundle metadata, sandbox entitlements |
| `Tools/MakeIcon` | Generates the app icon at build time |
| `Tools/asc.py`, `Tools/release.sh` | App Store Connect listing automation, direct-download release |
| `Marketing/` | Screenshots, listing text, review notes |
| `docs/` | GitHub Pages site (landing page + privacy policy) |
