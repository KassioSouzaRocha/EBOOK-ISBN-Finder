#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Cria o Quick Action do macOS "Renomear com ISBN" via Automator
# Execute: bash create_macos_quickaction.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKFLOW_DIR="$HOME/Library/Services/Renomear com ISBN.workflow"
CONTENTS="$WORKFLOW_DIR/Contents"
INFO_PLIST="$CONTENTS/Info.plist"
DOCUMENT_WFLOW="$CONTENTS/document.wflow"

# Cria estrutura do .workflow
mkdir -p "$CONTENTS"

# Info.plist
cat > "$INFO_PLIST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSServices</key>
  <array>
    <dict>
      <key>NSMenuItem</key>
      <dict>
        <key>default</key>
        <string>Renomear com ISBN</string>
      </dict>
      <key>NSMessage</key>
      <string>runWorkflowAsService</string>
      <key>NSSendTypes</key>
      <array>
        <string>NSFilenamesPboardType</string>
      </array>
      <key>NSRequiredContext</key>
      <dict>
        <key>NSApplicationIdentifier</key>
        <string>com.apple.finder</string>
      </dict>
    </dict>
  </array>
</dict>
</plist>
PLIST

# document.wflow — workflow com um único passo: shell script
# Substitui INSTALL_DIR no comando
ESCAPED_DIR=$(printf '%s' "$INSTALL_DIR" | sed 's/[&/\]/\\&/g')

cat > "$DOCUMENT_WFLOW" <<WFLOW
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>AMApplicationBuild</key><string>523</string>
  <key>AMApplicationVersion</key><string>2.10</string>
  <key>AMDocumentSpecificationVersion</key><string>0.9</string>
  <key>actions</key>
  <array>
    <dict>
      <key>action</key>
      <dict>
        <key>AMAccepts</key>
        <dict>
          <key>Container</key><string>List</string>
          <key>Optional</key><true/>
          <key>Types</key><array><string>com.apple.cocoa.path</string></array>
        </dict>
        <key>AMActionVersion</key><string>2.0.3</string>
        <key>AMApplication</key><array><string>Automator</string></array>
        <key>AMParameterProperties</key><dict/>
        <key>AMProvides</key>
        <dict>
          <key>Container</key><string>List</string>
          <key>Types</key><array><string>com.apple.cocoa.path</string></array>
        </dict>
        <key>ActionBundlePath</key>
        <string>/System/Library/Automator/Run Shell Script.action</string>
        <key>ActionName</key><string>Run Shell Script</string>
        <key>ActionParameters</key>
        <dict>
          <key>COMMAND_STRING</key>
          <string>for f in "\$@"; do
  if [ -f "\$f" ]; then
    ARG="--arquivo"
    ALVO="\$f"
  elif [ -d "\$f" ]; then
    ARG="--pasta"
    ALVO="\$f"
  fi
  break
done
cd "${ESCAPED_DIR}"
# Abre Terminal com progresso
osascript -e "tell application \\"Terminal\\" to do script \\"cd '${ESCAPED_DIR}' &amp;&amp; uv run isbn.py \$ARG '\$ALVO'\\"" -e "tell application \\"Terminal\\" to activate"</string>
          <key>CheckedForUserDefaultShell</key><true/>
          <key>inputMethod</key><integer>1</integer>
          <key>shell</key><string>/bin/bash</string>
          <key>source</key><string></string>
        </dict>
        <key>BundleIdentifier</key>
        <string>com.apple.RunShellScript</string>
        <key>CFBundleVersion</key><string>2.0.3</string>
        <key>CanShowSelectedItemsWhenRun</key><false/>
        <key>CanShowWhenRun</key><true/>
        <key>Category</key><array><string>AMCategoryUtilities</string></array>
        <key>Class Name</key><string>RunShellScriptAction</string>
        <key>InputUUID</key><string>D1E36C26-C9D4-4B68-B62D-26D6E72E4D22</string>
        <key>Keywords</key><array><string>Shell</string><string>Script</string><string>Command</string></array>
        <key>OutputUUID</key><string>6DE58DE9-9218-4E33-9A37-55FF1EEE1E55</string>
        <key>UUID</key><string>A63E1E1B-EAA5-4EEB-8C45-0BBBBA3C3780</string>
        <key>UnlockActionForRun</key><false/>
        <key>arguments</key><dict/>
        <key>isViewVisible</key><true/>
        <key>location</key><string>309.000000:339.000000</string>
        <key>nibPath</key>
        <string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/English.lproj/main.nib</string>
      </dict>
      <key>isViewVisible</key><true/>
    </dict>
  </array>
  <key>connectors</key><dict/>
  <key>workflowMetaData</key>
  <dict>
    <key>serviceInputTypeIdentifier</key><string>com.apple.Automator.fileSystemObject</string>
    <key>serviceOutputTypeIdentifier</key><string>com.apple.Automator.nothing</string>
    <key>serviceProcessesInput</key><integer>0</integer>
    <key>workflowTypeIdentifier</key><string>com.apple.Automator.servicesMenu</string>
  </dict>
</dict>
</plist>
WFLOW

echo "✅ Quick Action criado em: $WORKFLOW_DIR"
echo "   Finder → clicar-direito → Renomear com ISBN"
echo "   (pode ser necessário reiniciar o Finder: killall Finder)"
