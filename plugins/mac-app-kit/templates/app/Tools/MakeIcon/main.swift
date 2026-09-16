// Generates the app icon (.iconset folder) with CoreGraphics: a rounded gradient tile with the app's
// initial. Replace drawIcon() with real artwork when you have it. Usage: MakeIcon <out.iconset>
import AppKit

let args = CommandLine.arguments
guard args.count > 1 else { FileHandle.standardError.write(Data("usage: MakeIcon <output.iconset>\n".utf8)); exit(1) }
let outDir = URL(fileURLWithPath: args[1])
try FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)

func rgb(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> CGColor { CGColor(srgbRed: r / 255, green: g / 255, blue: b / 255, alpha: a) }

func drawIcon(in ctx: CGContext, pixels: CGFloat) {
    ctx.scaleBy(x: pixels / 1024, y: pixels / 1024)
    let square = CGRect(x: 100, y: 100, width: 824, height: 824)          // macOS icon grid
    let shape = CGPath(roundedRect: square, cornerWidth: 186, cornerHeight: 186, transform: nil)
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -12), blur: 28, color: CGColor(gray: 0, alpha: 0.30))
    ctx.setFillColor(rgb(40, 40, 60)); ctx.addPath(shape); ctx.fillPath()
    ctx.restoreGState()
    ctx.saveGState(); ctx.addPath(shape); ctx.clip()
    let gradient = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!,
                              colors: [rgb(80, 160, 255), rgb(90, 70, 220)] as CFArray, locations: [0, 1])!
    ctx.drawLinearGradient(gradient, start: CGPoint(x: 160, y: 900), end: CGPoint(x: 880, y: 140), options: [])
    // Initial letter
    let letter = "__INITIAL__" as NSString
    let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 520, weight: .bold), .foregroundColor: NSColor.white]
    let size = letter.size(withAttributes: attrs)
    NSGraphicsContext.current?.cgContext.setShadow(offset: CGSize(width: 0, height: -8), blur: 20, color: CGColor(gray: 0, alpha: 0.25))
    letter.draw(at: NSPoint(x: 512 - size.width / 2, y: 512 - size.height / 2), withAttributes: attrs)
    ctx.restoreGState()
}

for (points, scale) in [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2), (256, 1), (256, 2), (512, 1), (512, 2)] {
    let px = points * scale
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8, samplesPerPixel: 4,
                                     hasAlpha: true, isPlanar: false, colorSpaceName: .calibratedRGB, bytesPerRow: 0, bitsPerPixel: 0),
          let gc = NSGraphicsContext(bitmapImageRep: rep) else { exit(2) }
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = gc
    drawIcon(in: gc.cgContext, pixels: CGFloat(px))
    gc.flushGraphics(); NSGraphicsContext.restoreGraphicsState()
    try rep.representation(using: .png, properties: [:])!.write(to: outDir.appendingPathComponent("icon_\(points)x\(points)\(scale == 2 ? "@2x" : "").png"))
}
