#!/usr/bin/env bash
# ==============================================================================
# Script de Desinstalação do Engraver (Linux - Espaço de Usuário)
# ==============================================================================
set -e

echo "🗑️  Removendo atalhos do Engraver para o usuário atual (${USER})..."

APPS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
LOCAL_BIN="${HOME}/.local/bin"

rm -f "${APPS_DIR}/engraver.desktop"
rm -f "${ICONS_DIR}/engraver.png"
rm -f "${LOCAL_BIN}/engraver"
rm -f "${LOCAL_BIN}/engraver-cli"

if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database "${APPS_DIR}" 2>/dev/null || true
fi

echo "✅ Atalhos e comandos removidos com sucesso!"
