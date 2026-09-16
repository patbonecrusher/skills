import SwiftUI

@main
struct __EXEC_NAME__App: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .defaultSize(width: 900, height: 640)
        .commands { AppCommands() }

        Settings {
            SettingsView()
        }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    override init() {
        super.init()
        Prefs.registerDefaults()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Debug/screenshot hooks: `-preferRetina YES` moves new windows to the highest-density screen,
        // `-windowSize 1280x800` sets their size. Both are no-ops unless passed on the command line.
        let defaults = UserDefaults.standard
        guard defaults.bool(forKey: "preferRetina") || defaults.string(forKey: "windowSize") != nil else { return }
        NotificationCenter.default.addObserver(forName: NSWindow.didBecomeKeyNotification, object: nil, queue: .main) { note in
            guard let window = note.object as? NSWindow, window.isVisible else { return }
            var frame = window.frame
            if let spec = defaults.string(forKey: "windowSize") {
                let parts = spec.lowercased().split(separator: "x").compactMap { Double($0) }
                if parts.count == 2 { frame.size = NSSize(width: parts[0], height: parts[1]) }
            }
            if defaults.bool(forKey: "preferRetina"),
               let screen = NSScreen.screens.max(by: { $0.backingScaleFactor < $1.backingScaleFactor }) {
                let v = screen.visibleFrame
                frame.origin = NSPoint(x: v.midX - frame.width / 2, y: v.midY - frame.height / 2)
            }
            window.setFrame(frame, display: true)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}
