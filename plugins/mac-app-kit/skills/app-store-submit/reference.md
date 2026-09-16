# App Store submission — reference

## Portal URLs
- Certificates: https://developer.apple.com/account/resources/certificates/add
- Identifiers: https://developer.apple.com/account/resources/identifiers/bundleId/add/bundle
- Profiles: https://developer.apple.com/account/resources/profiles/add
- App Store Connect apps: https://appstoreconnect.apple.com/apps
- API keys: https://appstoreconnect.apple.com/access/integrations/api
- App Privacy: https://appstoreconnect.apple.com/apps/<APP_ID>/distribution/privacy
- Review submissions: https://appstoreconnect.apple.com/apps/<APP_ID>/distribution/reviewsubmissions

## Certificate names vs portal labels
| Portal label | Identity name in keychain |
| --- | --- |
| Apple Distribution | `Apple Distribution: Name (TEAM)` |
| Mac App Distribution | `3rd Party Mac Developer Application: Name (TEAM)` |
| Mac Installer Distribution | `3rd Party Mac Developer Installer: Name (TEAM)` |
| Developer ID Application | `Developer ID Application: Name (TEAM)` |

A profile generated while selecting "Mac App Distribution" embeds the 3rd-Party cert, not Apple Distribution. Sign with whatever the profile contains.

## Errors seen and their fixes
| Message | Cause → fix |
| --- | --- |
| altool 90284 "must be signed with the certificate that is contained in the provisioning profile" | wrong signing cert → sign with the profile's embedded cert (build.sh does this by SHA-1) |
| Email ITMS-91109 "com.apple.quarantine extended file attribute" | downloaded file copied into bundle → `xattr -cr App.app` before signing |
| No build appears after upload | processing rejection email — check mail (`from:apple.com ITMS`) |
| `reviewSubmissionItems` 409 "not in valid state" | read `meta.associatedErrors`: `contentRightsDeclaration` missing → `PATCH /apps/{id}` `DOES_NOT_USE_THIRD_PARTY_CONTENT`; `APP_DATA_USAGES_REQUIRED` → user must click **Publish** on App Privacy |
| `ageRatingDeclarations` 409 "ageRatingOverride cannot be set when ageRatingOverrideV2 is set" | don't send override fields; send the full list of content descriptors (NONE) and booleans (false) |
| `/apps/{id}/builds` "parameter sort not allowed" | use `/builds?filter[app]={id}&sort=-uploadedDate` |
| appAvailabilities 409 "id must be a local id ${…}" | inline `included` ids need the literal `${TERRITORY}` form |
| Launch failed / "Launchd job spawn failed" | trying to run an App Store-signed build locally — expected; use `--sign dev` |
| Blank WKWebView in sandbox | add `com.apple.security.network.client` |

## Review-reply template (Guideline 2.1 – Information Needed)
1. Screen recording attached (device, OS version). Flow shown.
2. Purpose and audience — the problem, who it's for, the value.
3. Setup/access — no account; how to reach main features; sample files link.
4. External services — none / list them.
5. Regional differences — none; languages.
6. Regulated industry / third-party material — n/a; all original.
Also put the same text in App Review Information → Notes for future submissions.

## Timeline observed (Sept 2026)
Upload → processing 15–40 min → submit → "Information Needed" within ~12 h for a new account → reply with video → back to review.
