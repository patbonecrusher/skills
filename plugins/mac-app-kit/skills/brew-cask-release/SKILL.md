---
name: brew-cask-release
description: Publish a macOS app as a Homebrew cask in a personal tap — notarized GitHub release, cask formula (sha256, livecheck, zap), tap update workflow, audit, and the per-release automation. Use for "add it to Homebrew", "brew cask", "tap", or cutting a new direct-download release.
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Homebrew cask release

The user's tap is `<GITHUB_USER>/homebrew-tap`, checked out at `$TAP_DIR` (from `~/.config/mac-app-kit/defaults.env`), installed as
`brew install --cask <GITHUB_USER>/tap/<cask>`. Casks live in `Casks/<cask>.rb`; formulas in `Formula/`.

## Prerequisites
- A notarized, stapled build people can download — a Developer ID zip on a GitHub release (see mac-app-signing). App Store
  builds cannot be used (they don't launch outside the store).
- `gh` logged in; the tap cloned locally.

## Per release (projects from new-mac-app)
```sh
# bump CFBundleShortVersionString in Resources/Info.plist, commit, then:
export ASC_KEY_ID=… ASC_ISSUER_ID=…     # notarization auth
Tools/release.sh                        # build --universal --sign devid --notarize → tag → gh release → cask sha/version → push tap
```
`Tools/release.sh` refuses a dirty tree or an existing tag. Asset name convention: `<Exec>-<version>.zip` (the cask URL depends on it).

## First-time cask
Copy `${CLAUDE_PLUGIN_ROOT}/templates/tap/cask.rb` to `Casks/<cask>.rb`, fill version/sha256/url/name/desc/homepage. Rules that
matter: `depends_on macos: :sonoma` (symbol form = "or later"; the `">= :sonoma"` string form is deprecated), `app "Name.app"`,
`zap trash:` listing the sandbox container `~/Library/Containers/<bundle-id>` and prefs plist, `livecheck` with
`strategy :github_latest`. Then:
```sh
ruby -c Casks/<cask>.rb
brew tap USER/tap && brew fetch --cask USER/tap/<cask>     # checks URL + sha256
brew audit --cask --online USER/tap/<cask>
ditto -x -k "$(brew --cache --cask USER/tap/<cask>)" /tmp/x && spctl --assess --type execute -v "/tmp/x/Name.app"   # notarized?
```
Don't `brew install` on the user's machine as a test if their packages are managed declaratively (e.g. chezmoi) — use that workflow instead.

## Tap automation
`.github/workflows/update-cask.yml` in the tap (template: `${CLAUDE_PLUGIN_ROOT}/templates/tap/update-cask.yml`) accepts
`repository_dispatch` `update-cask` with `client_payload.version` and `.cask`, downloads the asset, rewrites version + sha256,
commits. Triggering it from another repo's CI needs a PAT secret (`HOMEBREW_TAP_TOKEN`, repo scope on the tap); the local `release.sh`
path avoids the token entirely.

## Gotchas
- `sha256` must be of the exact uploaded asset; recompute after any re-upload (`shasum -a 256 file.zip`).
- `brew` caches downloads; after re-uploading an asset with the same name, `brew cleanup --prune=all` or the fetch will hit the stale sha.
- Casks are arch-agnostic if the binary is universal (`--universal` in build.sh); add `depends_on arch: :arm64` only for arm-only builds.
- Homebrew prints deprecation warnings from *your* tap to every user — fix them promptly (`brew audit` shows them).
