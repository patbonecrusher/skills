on menuClick(m, i)
  tell application "System Events" to tell process "__APP_NAME__" to click menu item i of menu m of menu bar 1
end menuClick
on docCount()
  tell application "System Events" to tell process "__APP_NAME__"
    return count of (windows whose name ends with ".svg")
  end tell
end docCount
on openFile(p)
  set prevCount to docCount()
  tell application "System Events" to tell process "__APP_NAME__"
    keystroke "g" using {command down, shift down}
    delay 1.5
    keystroke p
    delay 1.0
    keystroke return
    delay 2.5
    keystroke return
  end tell
  repeat 8 times
    delay 1.0
    if docCount() > prevCount then exit repeat
    tell application "System Events" to tell process "__APP_NAME__"
      if exists (button "Open" of window 1) then click button "Open" of window 1
    end tell
  end repeat
end openFile

delay 2
tell application "__APP_NAME__" to activate
delay 4
menuClick("View", "Zoom In")
delay 1.2
menuClick("View", "Zoom In")
delay 1.2
menuClick("View", "Zoom Out")
delay 1.2
menuClick("View", "Actual Size")
delay 1.8
menuClick("View", "Zoom to Fit")
delay 1.8
tell application "System Events" to tell process "__APP_NAME__"
  click menu item "Light" of menu "Background" of menu item "Background" of menu "View" of menu bar 1
  delay 1.6
  click menu item "Dark" of menu "Background" of menu item "Background" of menu "View" of menu bar 1
  delay 1.6
  click menu item "Checkerboard" of menu "Background" of menu item "Background" of menu "View" of menu bar 1
end tell
delay 1.5
menuClick("View", "Show Source")
delay 3.5
menuClick("View", "Show Source")
delay 1.5
menuClick("File", "Open…")
delay 3
openFile("/path/to/second-file")
delay 3.5
tell application "System Events" to tell process "__APP_NAME__" to keystroke "," using command down
delay 2.5
tell application "System Events" to tell process "__APP_NAME__" to keystroke "w" using command down
delay 1.2
menuClick("File", "Export as PNG…")
delay 2.5
tell application "System Events" to tell process "__APP_NAME__" to keystroke return
delay 2.5
tell application "System Events" to tell process "__APP_NAME__" to keystroke "q" using command down
delay 1.5
