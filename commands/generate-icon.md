---
description: Generate a macOS .icns icon from a square source image, producing all required iconset sizes
---
Generate a macOS app icon (`.icns`) from a square source image for the current project.

## Input

The user provides a path to a square image (PNG, JPEG, etc.), ideally 1024x1024 or larger. If no path is given, look for common candidates in the project: `icon.png`, `AppIcon.png`, `logo.png`, or ask the user.

## What to do

Write a `generate_icon.swift` script in the project root that:

1. Takes the source image path as input
2. Resizes it to all required macOS `.iconset` sizes using `NSImage` / `NSBitmapImageRep`
3. Outputs PNGs into a `<AppName>.iconset/` directory

### Required sizes

| File | Pixels |
|------|--------|
| `icon_16x16.png` | 16x16 |
| `icon_16x16@2x.png` | 32x32 |
| `icon_32x32.png` | 32x32 |
| `icon_32x32@2x.png` | 64x64 |
| `icon_128x128.png` | 128x128 |
| `icon_128x128@2x.png` | 256x256 |
| `icon_256x256.png` | 256x256 |
| `icon_256x256@2x.png` | 512x512 |
| `icon_512x512.png` | 512x512 |
| `icon_512x512@2x.png` | 1024x1024 |

### Script template

```swift
#!/usr/bin/env swift
import AppKit

let args = CommandLine.arguments
guard args.count > 1 else {
    print("Usage: swift generate_icon.swift <source-image> [iconset-name]")
    exit(1)
}

let sourcePath = args[1]
let iconsetName = args.count > 2 ? args[2] : "AppIcon"

guard let sourceImage = NSImage(contentsOfFile: sourcePath) else {
    print("Error: Could not load image at \(sourcePath)")
    exit(1)
}

let iconsetPath = "\(iconsetName).iconset"
let fm = FileManager.default
try? fm.removeItem(atPath: iconsetPath)
try! fm.createDirectory(atPath: iconsetPath, withIntermediateDirectories: true)

let sizes: [(name: String, pixels: Int)] = [
    ("icon_16x16", 16), ("icon_16x16@2x", 32),
    ("icon_32x32", 32), ("icon_32x32@2x", 64),
    ("icon_128x128", 128), ("icon_128x128@2x", 256),
    ("icon_256x256", 256), ("icon_256x256@2x", 512),
    ("icon_512x512", 512), ("icon_512x512@2x", 1024),
]

for entry in sizes {
    let s = entry.pixels
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil, pixelsWide: s, pixelsHigh: s,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
        isPlanar: false, colorSpaceName: .deviceRGB,
        bytesPerRow: 0, bitsPerPixel: 0)!
    rep.size = NSSize(width: s, height: s)

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    NSGraphicsContext.current?.imageInterpolation = .high
    sourceImage.draw(in: NSRect(x: 0, y: 0, width: s, height: s))
    NSGraphicsContext.restoreGraphicsState()

    let data = rep.representation(using: .png, properties: [:])!
    let path = "\(iconsetPath)/\(entry.name).png"
    try! data.write(to: URL(fileURLWithPath: path))
    print("Generated \(entry.name).png (\(s)x\(s))")
}

print("Done! Now run: iconutil -c icns \(iconsetPath) -o \(iconsetName).icns")
```

## After generating the script

Run it:

```bash
swift generate_icon.swift <source-image.png> <AppName>
iconutil -c icns <AppName>.iconset -o <AppName>.icns
```

Then place the `.icns` in the app bundle at `Contents/Resources/`.

If the project has a `bundle.sh` or build script, integrate the icon generation into it.

## Context: $@
