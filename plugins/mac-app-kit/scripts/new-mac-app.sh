#!/bin/zsh
# Scaffold a native macOS app project from the mac-app-kit templates.
#
#   new-mac-app.sh --name "My App" --bundle-id com.example.myapp --repo my-app --github-user me \
#                  --author "Full Name" --team-id TEAMID [--category public.app-category.utilities] \
#                  [--tagline "..."] [--dir /path/to/create] [--no-github]
#
# Creates the directory, substitutes placeholders, builds once, inits git, creates the GitHub repo
# (public, with GitHub Pages serving docs/), and pushes. Prints what to do next.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; TPL="$HERE/../templates/app"
NAME="" BUNDLE="" REPO="" USER_="" AUTHOR="" TEAM="" CATEGORY="public.app-category.utilities" TAGLINE="" DIR="" GITHUB=1 PRIVATE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME=$2; shift 2 ;; --bundle-id) BUNDLE=$2; shift 2 ;; --repo) REPO=$2; shift 2 ;;
    --github-user) USER_=$2; shift 2 ;; --author) AUTHOR=$2; shift 2 ;; --team-id) TEAM=$2; shift 2 ;;
    --category) CATEGORY=$2; shift 2 ;; --tagline) TAGLINE=$2; shift 2 ;; --dir) DIR=$2; shift 2 ;;
    --no-github) GITHUB=0; shift ;; --private) PRIVATE=1; shift ;;
    *) echo "unknown option $1" >&2; exit 1 ;;
  esac
done
for v in NAME BUNDLE REPO USER_ AUTHOR TEAM; do [[ -n ${(P)v} ]] || { echo "missing --${v:l}" >&2; exit 1; }; done
EXEC="${NAME//[^A-Za-z0-9]/}"; DIR="${DIR:-$PWD/$REPO}"; CASK="$REPO"
INITIAL="${NAME[1]:u}"; YEAR="$(date +%Y)"; DATE="$(date '+%B %-d, %Y')"; SITE="https://$USER_.github.io/$REPO/"
case "$CATEGORY" in
  *graphics-design) ASC=GRAPHICS_AND_DESIGN ;; *developer-tools) ASC=DEVELOPER_TOOLS ;; *productivity) ASC=PRODUCTIVITY ;;
  *photography) ASC=PHOTOGRAPHY ;; *education) ASC=EDUCATION ;; *music) ASC=MUSIC ;; *video) ASC=VIDEO ;;
  *reference) ASC=REFERENCE ;; *lifestyle) ASC=LIFESTYLE ;; *finance) ASC=FINANCE ;; *healthcare-fitness) ASC=HEALTH_AND_FITNESS ;;
  *) ASC=UTILITIES ;;
esac
[[ -e $DIR ]] && { echo "error: $DIR exists" >&2; exit 1; }
echo "==> Creating $DIR"
mkdir -p "$DIR"; cp -R "$TPL"/. "$DIR"/
mv "$DIR/Sources/__EXEC_NAME__" "$DIR/Sources/$EXEC"; mv "$DIR/Resources/__EXEC_NAME__.entitlements" "$DIR/Resources/$EXEC.entitlements"
cp "$HERE/asc.py" "$DIR/Tools/asc.py"; cp "$HERE/compose-screenshot.swift" "$DIR/Marketing/compose.swift"
esc() { printf '%s' "$1" | sed -e 's/[\/&|]/\\&/g'; }
find "$DIR" -type f \( -name "*.swift" -o -name "*.plist" -o -name "*.sh" -o -name "*.md" -o -name "*.html" -o -name "*.json" -o -name "*.yml" -o -name "*.entitlements" -o -name "*.rb" -o -name ".gitignore" \) -print0 |
  xargs -0 sed -i '' -e "s|__APP_NAME__|$(esc "$NAME")|g" -e "s|__EXEC_NAME__|$EXEC|g" -e "s|__BUNDLE_ID__|$BUNDLE|g" \
    -e "s|__TEAM_ID__|$TEAM|g" -e "s|__GITHUB_USER__|$USER_|g" -e "s|__REPO__|$REPO|g" -e "s|__CASK__|$CASK|g" \
    -e "s|__AUTHOR__|$(esc "$AUTHOR")|g" -e "s|__YEAR__|$YEAR|g" -e "s|__DATE__|$DATE|g" -e "s|__SITE_URL__|$SITE|g" \
    -e "s|__CATEGORY__|$CATEGORY|g" -e "s|__CATEGORY_ASC__|$ASC|g" -e "s|__INITIAL__|$INITIAL|g" \
    -e "s|__TAGLINE__|$(esc "${TAGLINE:-A native Mac app}")|g" -e "s|__DESCRIPTION__|$(esc "${TAGLINE:-$NAME for macOS.}")|g" \
    -e "s|__PROMO__|$(esc "${TAGLINE:-$NAME for macOS.}")|g" -e "s|__SUBTITLE__|$(esc "${TAGLINE:-}")|g" -e "s|__KEYWORDS__|mac,utility|g" -e "s|__DESC__|$(esc "${TAGLINE:-$NAME}")|g"
chmod +x "$DIR/build.sh" "$DIR/Tools/release.sh" "$DIR/Tools/asc.py"
echo "==> Building once"
( cd "$DIR" && ./build.sh >/dev/null && echo "    build ok: build/$NAME.app" )
( cd "$DIR" && git init -q -b main && git add -A && git commit -q -m "Scaffold $NAME (mac-app-kit)" )
if [[ $GITHUB == 1 ]]; then
  echo "==> Creating GitHub repo $USER_/$REPO"
  vis=--public; [[ $PRIVATE == 1 ]] && vis=--private
  ( cd "$DIR" && gh repo create "$USER_/$REPO" $vis --source . --remote origin --description "${TAGLINE:-$NAME for macOS}" --push >/dev/null )
  gh api -X POST "repos/$USER_/$REPO/pages" -f 'source[branch]=main' -f 'source[path]=/docs' >/dev/null 2>&1 && echo "    GitHub Pages: $SITE" || echo "    (enable Pages manually: Settings → Pages → main:/docs)"
fi
cat <<MSG

Done. Next:
  cd $DIR && ./build.sh --open            # run it
  edit Sources/$EXEC/ContentView.swift      # your UI
  edit docs/index.html, Marketing/listing.json, Tools/MakeIcon/main.swift   # marketing copy + icon
  Resources/Info.plist: CFBundleDocumentTypes if document-based
  Signing / App Store / Homebrew: see RELEASING.md (mac-app-kit skills: mac-app-signing, app-store-submit, brew-cask-release)
MSG
