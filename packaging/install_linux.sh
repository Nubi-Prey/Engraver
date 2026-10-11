#!/usr/bin/env bash
# ==============================================================================
# Script de Instalação do Engraver (Linux - Espaço de Usuário)
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="${DIR}/Engraver"
CLI_PATH="${DIR}/engraver-cli"
ICON_PATH="${DIR}/resources/icon.png"

if [ ! -f "${BIN_PATH}" ]; then
    echo "❌ Erro: O executável 'Engraver' não foi encontrado em: ${DIR}"
    exit 1
fi

echo "🚀 Instalando o Engraver para o usuário atual (${USER})..."

# 1. Diretórios de destino no padrão XDG
APPS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
LOCAL_BIN="${HOME}/.local/bin"

mkdir -p "${APPS_DIR}"
mkdir -p "${ICONS_DIR}"
mkdir -p "${LOCAL_BIN}"

# 2. Instalação do ícone
if [ -f "${ICON_PATH}" ]; then
    cp "${ICON_PATH}" "${ICONS_DIR}/engraver.png"
    echo "  ✓ Ícone copiado para ${ICONS_DIR}/engraver.png"
fi

# 3. Criação do arquivo .desktop personalizado com caminhos absolutos
DESKTOP_FILE="${APPS_DIR}/engraver.desktop"
cat << EOF > "${DESKTOP_FILE}"
[Desktop Entry]
Version=1.0
Type=Application
Name=Engraver
GenericName=Laser Engraving Photo Editor
Comment=Preparação profissional de imagens para gravação a laser em joias e metais
Exec="${BIN_PATH}" %F
Icon=engraver
Terminal=false
Categories=Graphics;2DGraphics;RasterGraphics;Photography;
MimeType=image/png;image/jpeg;image/bmp;image/tiff;image/webp;
Keywords=laser;engraving;dither;photo;joias;gravação;
StartupNotify=true
StartupWMClass=Engraver
EOF

chmod +x "${DESKTOP_FILE}"
echo "  ✓ Atalho do sistema criado em ${DESKTOP_FILE}"

# 4. Criação de symlinks no terminal (~/.local/bin)
ln -sf "${BIN_PATH}" "${LOCAL_BIN}/engraver"
ln -sf "${CLI_PATH}" "${LOCAL_BIN}/engraver-cli"
echo "  ✓ Comandos 'engraver' e 'engraver-cli' vinculados em ${LOCAL_BIN}/"

# 5. Atualização da base de dados do desktop (GNOME/KDE/XFCE)
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database "${APPS_DIR}" 2>/dev/null || true
fi

echo ""
echo "✅ Instalação concluída com sucesso!"
echo "   - Você já pode abrir o 'Engraver' pelo Menu de Aplicativos do sistema."
echo "   - No terminal, você pode rodar 'engraver' (GUI) ou 'engraver-cli' (CLI)."
echo "   - Para desinstalar, basta rodar: ./uninstall_linux.sh"
echo ""
