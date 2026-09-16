import SwiftUI

struct ContentView: View {
    @AppStorage(Prefs.showStatusBar) private var showStatusBar = true

    var body: some View {
        VStack(spacing: 0) {
            ContentUnavailableView("__APP_NAME__", systemImage: "app.dashed", description: Text("Replace ContentView with your UI."))
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            if showStatusBar {
                Divider()
                HStack {
                    Text("Ready").font(.callout).foregroundStyle(.secondary)
                    Spacer()
                }
                .padding(.horizontal, 12).padding(.vertical, 5)
                .background(.bar)
            }
        }
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Button { } label: { Label("Action", systemImage: "sparkles") }
            }
        }
    }
}

struct AppCommands: Commands {
    var body: some Commands {
        CommandGroup(replacing: .help) {
            Link("__APP_NAME__ Website", destination: URL(string: "__SITE_URL__")!)
        }
    }
}

struct SettingsView: View {
    @AppStorage(Prefs.showStatusBar) private var showStatusBar = true

    var body: some View {
        Form {
            Toggle("Show status bar", isOn: $showStatusBar)
        }
        .formStyle(.grouped)
        .frame(width: 440, height: 160)
    }
}

enum Prefs {
    static let showStatusBar = "showStatusBar"

    static func registerDefaults() {
        UserDefaults.standard.register(defaults: [showStatusBar: true])
    }
}
