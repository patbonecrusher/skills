---
name: mac-app-signing
description: Sign and notarize a macOS app for distribution outside the App Store (Developer ID, hardened runtime, notarytool, stapling, Gatekeeper checks), including certificate setup, entitlements/sandbox pitfalls, CI keychain import, and verification. Use for "sign my app", "notarize", "Developer ID", "Gatekeeper says damaged", or preparing a direct-download build.
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Signing & notarizing for direct distribution

## Certificates (what exists, how to tell)

`security find-identity -v -p codesigning` lists usable identities (cert + private key). Names and what they're for:

| Identity name | Use |
| --- | --- |
| `Apple Development: Name (PERSONALID)` | local dev/testing. The parenthesized code is the *person's* ID, not the team — the team is the cert's OU (`openssl x509 -subject`). |
| `Developer ID Application: Name (TEAMID)` | outside-store distribution → this skill |
| `Developer ID Installer` | signed .pkg for outside-store (rarely needed) |
| `Apple Distribution` / `3rd Party Mac Developer Application` | Mac App Store app signing (see app-store-submit) |
| `3rd Party Mac Developer Installer` | Mac App Store .pkg |

Creating one (needs the Account Holder role): Keychain Access → Certificate Assistant → Request a Certificate From a
Certificate Authority (email, common name, *Saved to disk*) → developer.apple.com/account/resources/certificates/add →
**Software → Developer ID Application** → upload the CSR → Download → double-click. Same CSR works for every cert type.
Certs from another machine need a `.p12` export (private key travels with it); a `.cer` download alone won't sign.

## Build + sign

Projects scaffolded by `new-mac-app` have it all in `build.sh`:
```sh
./build.sh --universal --sign devid --notarize      # → build/<Exec>-<version>.zip, stapled
```
What it does, if you need to reproduce it by hand:
```sh
swift build -c release --arch arm64 --arch x86_64          # universal
xattr -cr "App.app"                                        # strip quarantine/xattrs BEFORE signing
codesign --force --timestamp --options runtime \
  --sign "Developer ID Application: Name (TEAM)" --entitlements App.entitlements --identifier com.x.app "App.app"
codesign --verify --strict --verbose=2 "App.app"
ditto -c -k --keepParent "App.app" App.zip
xcrun notarytool submit App.zip --key ~/.appstoreconnect/private_keys/AuthKey_KEYID.p8 --key-id KEYID --issuer ISSUER --wait
xcrun stapler staple "App.app" && ditto -c -k --keepParent "App.app" App.zip   # re-zip AFTER stapling
spctl --assess --type execute --verbose=2 "App.app"        # expect: accepted, source=Notarized Developer ID
```
- `--options runtime` (hardened runtime) is required for notarization. Sandbox is optional outside the store but keep it if the app already has it.
- Sign once at the bundle level; `--deep` is deprecated. Nested frameworks/helpers must be signed first (inside-out).
- Notarization auth: an **App Store Connect API key** works (`--key/--key-id/--issuer`, key file in `~/.appstoreconnect/private_keys/`), no
  app-specific password needed. Alternative: `xcrun notarytool store-credentials <profile> --apple-id … --team-id …` then `--keychain-profile`.
- If notarization is *Invalid*: `xcrun notarytool log <submission-id> --key … --key-id … --issuer …` shows per-file reasons (usually
  unsigned binary, missing hardened runtime, or a `get-task-allow` entitlement).

## Verify like a user would

Download the zip from wherever it's hosted (curl/brew fetch), unzip with `ditto -x -k`, then `spctl --assess` on the extracted
app. `codesign -dvv --entitlements -` shows what was actually signed. A "damaged and can't be opened" dialog on another Mac =
not notarized or ticket not stapled and offline.

## Entitlements pitfalls

- Sandboxed WKWebView needs `com.apple.security.network.client` even for `loadHTMLString` — without it the view is blank.
- `com.apple.application-identifier` / `team-identifier` entitlements need a provisioning profile; don't add them for Developer ID builds.
- `files.user-selected.read-write` covers Open/Save panels and drag-and-drop; the app can't read arbitrary paths.

## CI (GitHub Actions)

Import the `.p12` from secrets into a temp keychain (`security create-keychain`, `import -T /usr/bin/codesign`,
`set-key-partition-list -S apple-tool:,apple:,codesign:`), then run `build.sh --sign devid --notarize` with
`ASC_KEY_ID`/`ASC_ISSUER_ID` (+ the `.p8` written from a secret) or `APPLE_ID`/`APPLE_TEAM_ID`/`APPLE_APP_PASSWORD`. The
template workflow in `${CLAUDE_PLUGIN_ROOT}/templates/app/.github/workflows/build.yml` does exactly this on `v*` tags.

## Don'ts

- Don't copy a downloaded provisioning profile or asset into the bundle without `xattr -c` — quarantine xattrs break App Store uploads (ITMS-91109) and can trip notarization.
- Don't launch a distribution-signed (App Store) build locally to test — it won't start. Developer ID builds do run locally.
- Don't reuse a `.p12` from another project without checking the team ID inside the cert first.
