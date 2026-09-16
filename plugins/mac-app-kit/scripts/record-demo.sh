#!/bin/zsh
# Record a screen demo of an app for App Review (Guideline 2.1 "information needed" requests).
#   record-demo.sh "<App Name>" /path/to/App.app <steps.applescript> <out.mp4> [display=1] [seconds=70]
# Requirements: the terminal app has Accessibility permission (System Settings → Privacy & Security → Accessibility);
# the user keeps hands off during recording (keystrokes go to the frontmost app). ffmpeg for the final encode.
set -euo pipefail
NAME=$1 APP=$2 SCRIPT=$3 OUT=$4 DISPLAY_=${5:-1} SECS=${6:-70}
TMP=$(mktemp -d); pkill -x "$(basename "$APP" .app | tr -d ' ')" 2>/dev/null || true; sleep 1
osascript -e 'tell application "System Events" to set visible of every process whose visible is true to false' || true
( screencapture -v -V "$SECS" -D "$DISPLAY_" "$TMP/raw.mov" & ); sleep 2
open -a "$APP" --args -ApplePersistenceIgnoreState YES -windowSize 1280x820
osascript "$SCRIPT"
until [[ -f $TMP/raw.mov ]] && ! pgrep -x screencapture >/dev/null; do sleep 2; done
osascript -e 'tell application "System Events" to set visible of process "Finder" to true' || true
ffmpeg -v error -y -i "$TMP/raw.mov" -vf "scale=2048:-2" -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart -an "$OUT"
echo "wrote $OUT ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")s). Review it before sending: ffmpeg -i $OUT -vf fps=1/4,scale=800:-1 frames/f%02d.png"
