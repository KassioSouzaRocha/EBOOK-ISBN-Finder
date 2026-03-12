#!/usr/bin/env bash
# =============================================================================
# install.sh — ISBN Renamer: instalação para Linux e macOS
# =============================================================================
set -euo pipefail

VERDE="\033[0;32m"
AMARELO="\033[0;33m"
VERMELHO="\033[0;31m"
RESET="\033[0m"

ok()   { echo -e "${VERDE}✔ $*${RESET}"; }
aviso(){ echo -e "${AMARELO}⚠ $*${RESET}"; }
erro() { echo -e "${VERMELHO}✘ $*${RESET}"; exit 1; }
info() { echo -e "  $*"; }

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        ISBN Renamer — Instalação         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─── Detectar SO ──────────────────────────────────────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATAFORMA="macos"
elif [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    source /etc/os-release
    case "$ID" in
        ubuntu|debian|linuxmint) PLATAFORMA="apt" ;;
        fedora|rhel|centos)      PLATAFORMA="dnf" ;;
        arch|manjaro)            PLATAFORMA="pacman" ;;
        *)                       PLATAFORMA="desconhecido" ;;
    esac
else
    PLATAFORMA="desconhecido"
fi

info "Sistema detectado: $PLATAFORMA"
echo ""

# ─── Dependências do sistema ──────────────────────────────────────────────────
echo "▶ Instalando dependências do sistema..."

instalar_deps() {
    case "$PLATAFORMA" in
        macos)
            if ! command -v brew &>/dev/null; then
                aviso "Homebrew não encontrado. Instalando..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install tesseract poppler exiftool
            ;;
        apt)
            sudo apt-get update -qq
            sudo apt-get install -y tesseract-ocr poppler-utils libimage-exiftool-perl
            ;;
        dnf)
            sudo dnf install -y tesseract poppler-utils perl-Image-ExifTool
            ;;
        pacman)
            sudo pacman -Sy --noconfirm tesseract poppler perl-image-exiftool
            ;;
        *)
            aviso "Gerenciador de pacotes não reconhecido."
            aviso "Instale manualmente: tesseract-ocr, poppler-utils, exiftool"
            ;;
    esac
}

instalar_deps
ok "Dependências do sistema instaladas."
echo ""

# ─── Verificar ferramentas após instalação ────────────────────────────────────
echo "▶ Verificando ferramentas..."
for cmd in tesseract pdftoppm exiftool; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd → $(command -v "$cmd")"
    else
        aviso "$cmd não encontrado no PATH. Verifique a instalação."
    fi
done
echo ""

# ─── Instalar uv ──────────────────────────────────────────────────────────────
echo "▶ Verificando uv..."
if command -v uv &>/dev/null; then
    ok "uv já instalado: $(uv --version)"
else
    info "Instalando uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Recarregar PATH para a sessão atual
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if command -v uv &>/dev/null; then
        ok "uv instalado: $(uv --version)"
    else
        erro "uv não encontrado após instalação. Reinicie o terminal e rode 'uv sync' manualmente."
    fi
fi
echo ""

# ─── Instalar pacotes Python ──────────────────────────────────────────────────
echo "▶ Instalando pacotes Python com uv..."
uv sync
ok "Ambiente Python configurado."
echo ""

# ─── Conclusão ────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════╗"
echo "║         Instalação concluída! ✔          ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  Execute o script com:"
echo "    uv run isbn.py"
echo ""
