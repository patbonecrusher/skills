import AppKit
// usage: sheet out.png cols file1 file2 ...
let args = CommandLine.arguments
let out = args[1], cols = Int(args[2])!, files = Array(args[3...])
let cellW: CGFloat = 640, cellH: CGFloat = 480, label: CGFloat = 28
let rows = (files.count + cols - 1) / cols
let W = Int(cellW) * cols, H = (Int(cellH) + Int(label)) * rows
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: W, pixelsHigh: H, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .calibratedRGB, bytesPerRow: 0, bitsPerPixel: 0)!
rep.size = NSSize(width: W, height: H)
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSColor(white: 0.3, alpha: 1).setFill(); NSRect(x: 0, y: 0, width: W, height: H).fill()
let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 18, weight: .semibold), .foregroundColor: NSColor.white]
for (i, f) in files.enumerated() {
    let col = i % cols, row = i / cols
    let x = CGFloat(col) * cellW, y = CGFloat(H) - CGFloat(row + 1) * (cellH + label)
    if let img = NSImage(contentsOfFile: f) {
        let s = min(cellW / img.size.width, cellH / img.size.height)
        let sz = NSSize(width: img.size.width * s, height: img.size.height * s)
        img.draw(in: NSRect(x: x + (cellW - sz.width) / 2, y: y + label + (cellH - sz.height) / 2, width: sz.width, height: sz.height))
    }
    ((f as NSString).lastPathComponent as NSString).deletingPathExtension.draw(at: NSPoint(x: x + 8, y: y + 4), withAttributes: attrs)
}
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: out))
