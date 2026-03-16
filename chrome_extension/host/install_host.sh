#!/bin/bash

# Identifica o diretório onde este script está e o wrapper
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WRAPPER_PATH="$DIR/isbn_wrapper.sh"

chmod +x "$WRAPPER_PATH"
chmod +x "$DIR/isbn_native_host.py"

# Instalação dependente do ID da extensão - Deixado como placeholder para o usuário trocar depois
MANIFEST_CONTENT='{
  "name": "com.kassio.isbn_renamer",
  "description": "Host nativo para o ISBN Renamer",
  "path": "'"$WRAPPER_PATH"'",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://COLOQUE_AQUI_O_ID_DA_EXTENSAO/"
  ]
}'

# Lista de diretórios comuns no Linux para Native Messaging
DEST_DIRS=(
  "$HOME/.config/google-chrome/NativeMessagingHosts"
  "$HOME/.config/google-chrome-beta/NativeMessagingHosts"
  "$HOME/.config/google-chrome-unstable/NativeMessagingHosts"
  "$HOME/.config/chromium/NativeMessagingHosts"
  "$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
  "$HOME/.config/microsoft-edge/NativeMessagingHosts"
)

for DEST in "${DEST_DIRS[@]}"; do
  if [ -d "$(dirname "$DEST")" ]; then
    mkdir -p "$DEST"
    echo "$MANIFEST_CONTENT" > "$DEST/com.kassio.isbn_renamer.json"
    echo "Host manifest instalado em: $DEST"
  fi
done

echo ""
echo "==== IMPORTANTE ===="
echo "Após carregar a pasta chrome_extension no Chrome (via chrome://extensions habilitando modo do desenvolvedor),"
echo "copie o ID da extensão gerado e cole dentro do arquivo 'com.kassio.isbn_renamer.json' que foi instalado para o seu navegador."
echo "Normalmente em '~/.config/google-chrome/NativeMessagingHosts/com.kassio.isbn_renamer.json'."
echo "Substitua a string 'COLOQUE_AQUI_O_ID_DA_EXTENSAO' pelo ID real sem apagar a barra final."
