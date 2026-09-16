// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "__EXEC_NAME__",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(name: "__EXEC_NAME__", path: "Sources/__EXEC_NAME__"),
        .executableTarget(name: "MakeIcon", path: "Tools/MakeIcon"),
    ]
)
