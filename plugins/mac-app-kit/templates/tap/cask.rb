cask "__CASK__" do
  version "__VERSION__"
  sha256 "__SHA256__"

  url "https://github.com/__GITHUB_USER__/__REPO__/releases/download/v#{version}/__EXEC_NAME__-#{version}.zip"
  name "__APP_NAME__"
  desc "__DESC__"
  homepage "https://__GITHUB_USER__.github.io/__REPO__/"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: :sonoma

  app "__APP_NAME__.app"

  zap trash: [
    "~/Library/Containers/__BUNDLE_ID__",
    "~/Library/Preferences/__BUNDLE_ID__.plist",
  ]
end
