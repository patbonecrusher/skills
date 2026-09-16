// Prints "<windowID> <title>" for every on-screen window of the given app name (for screencapture -l).
// usage: swiftc -O -o window-ids window-ids.swift && ./window-ids "My App"
import CoreGraphics
let app = CommandLine.arguments.dropFirst().first ?? ""
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as! [[String: Any]]
for w in list where (w["kCGWindowOwnerName"] as? String) == app {
    guard let n = w["kCGWindowNumber"] as? Int, let title = w["kCGWindowName"] as? String, !title.isEmpty else { continue }
    print(n, title)
}
