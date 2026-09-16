# Releasing __APP_NAME__

Team **__TEAM_ID__**. Bundle ID `__BUNDLE_ID__`. Everything is driven by `build.sh`; see `./build.sh --help`.

## Direct download (Developer ID + notarization) and Homebrew

```sh
export ASC_KEY_ID=… ASC_ISSUER_ID=…          # App Store Connect API key (~/.appstoreconnect/private_keys/AuthKey_<id>.p8)
Tools/release.sh                              # notarized universal zip → GitHub release → cask update in the tap
```

Needs a *Developer ID Application* certificate in the keychain and the tap checked out at `../mdview/homebrew-tap`
(override with `TAP_DIR`). Install: `brew install --cask __GITHUB_USER__/tap/__CASK__`.

## Mac App Store

One-time: *Apple Distribution* + *Mac Installer Distribution* certs, App ID, Mac App Store provisioning profile at
`Resources/__EXEC_NAME__.provisionprofile` (git-ignored), app record in App Store Connect, API key.

```sh
# bump CFBundleVersion (must strictly increase) in Resources/Info.plist, then:
./build.sh --universal --sign appstore --pkg --upload
Tools/asc.py all        # metadata (Marketing/listing.json), screenshots (Marketing/screenshot-*.png), price, review contact, build
Tools/asc.py submit
```

App Privacy has no public API: App Store Connect → App Privacy → Get Started → answer → **Publish** (the Publish button matters).

Notes: `build.sh` signs with the certificate embedded in the provisioning profile (App Store Connect rejects any other),
strips extended attributes before signing (ITMS-91109), and distribution-signed builds cannot be launched locally —
use `--sign dev` for local testing and screenshots.
