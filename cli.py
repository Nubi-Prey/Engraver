#!/usr/bin/env python3
"""
Engraver CLI — Preparação de Imagens para Gravação a Laser
Interface de linha de comando de alta performance.
"""

import argparse
import os
import sys
from core.presets_manager import PresetsManager
import engine


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Engraver CLI — Preparação de Imagens para Gravação a Laser em Joias e Metais"
    )
    parser.add_argument("input", help="Caminho do arquivo de imagem de entrada")
    parser.add_argument(
        "-o", "--output", help="Caminho do arquivo de saída (padrão: processed_<nome>.bmp)"
    )
    parser.add_argument(
        "-p", "--preset", help="Nome do preset salvo a ser aplicado (ex: 'Padrão')"
    )
    parser.add_argument(
        "-m", "--method",
        choices=["Atkinson", "Floyd-Steinberg", "Jarvis-Judice-Ninke"],
        help="Método de dithering (padrão: Atkinson)",
    )
    parser.add_argument(
        "--dpi", type=int, default=300, help="DPI alvo de saída (padrão: 300)"
    )
    parser.add_argument(
        "--width", type=float, default=0.0, help="Largura física final em mm (opcional)"
    )
    parser.add_argument(
        "--height", type=float, default=0.0, help="Altura física final em mm (opcional)"
    )
    parser.add_argument(
        "--brightness", type=int, default=50, help="Brilho 0-100 (padrão: 50)"
    )
    parser.add_argument(
        "--contrast", type=int, default=50, help="Contraste 0-100 (padrão: 50)"
    )
    parser.add_argument(
        "--sharpen", type=int, default=85, help="Nitidez Unsharp 0-100 (padrão: 85)"
    )
    parser.add_argument(
        "--density", type=int, default=1, help="Densidade 1-10 (padrão: 1)"
    )
    parser.add_argument(
        "--bg",
        choices=["preto", "branco", "black", "white"],
        default="preto",
        help="Fundo para imagens com transparência alpha (padrão: preto)",
    )
    parser.add_argument(
        "--invert", action="store_true", help="Inverter cores (negativo)"
    )
    parser.add_argument(
        "--no-gamma", action="store_true", help="Desativar correção gama"
    )
    parser.add_argument(
        "--no-dither", action="store_true", help="Exportar em escala de cinza sem dithering"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Modo silencioso (sem prints informativos)"
    )

    # Flags legadas para retrocompatibilidade
    parser.add_argument(
        "--bg-black", action="store_true", help="[Legado] Define fundo preto"
    )
    parser.add_argument(
        "--bg-white", action="store_true", help="[Legado] Define fundo branco"
    )

    return parser.parse_args(args)


def run_cli(args=None):
    parsed = parse_args(args)

    if not os.path.exists(parsed.input):
        print(f"[ERRO] Arquivo não encontrado: {parsed.input}", file=sys.stderr)
        return 1

    # Base settings: se preset for informado, carrega do gerenciador
    pm = PresetsManager()
    if parsed.preset:
        settings = pm.get_preset(parsed.preset)
        if not parsed.quiet:
            print(f"[Engraver] Carregando preset: '{parsed.preset}'")
    else:
        settings = pm.get_preset("Padrão")

    # Sobrescreve com argumentos explícitos da linha de comando
    if parsed.method:
        settings["dither_method"] = parsed.method
    if parsed.dpi:
        settings["target_dpi"] = parsed.dpi
    if parsed.width > 0:
        settings["width_mm"] = parsed.width
    if parsed.height > 0:
        settings["height_mm"] = parsed.height
    if parsed.brightness != 50:
        settings["brightness"] = parsed.brightness
    if parsed.contrast != 50:
        settings["contrast"] = parsed.contrast
    if parsed.sharpen != 85:
        settings["sharpen"] = parsed.sharpen
    if parsed.density != 1:
        settings["density"] = parsed.density
    if parsed.invert:
        settings["invert_colors"] = True
    if parsed.no_gamma:
        settings["gamma_active"] = False

    # Tratamento de background
    if parsed.bg_black or parsed.bg in ["preto", "black"]:
        settings["background"] = "Preto"
    elif parsed.bg_white or parsed.bg in ["branco", "white"]:
        settings["background"] = "Branco"

    # Carrega imagem original
    try:
        pil_img, dpi = engine.load_image_pillow(parsed.input)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar imagem: {e}", file=sys.stderr)
        return 1

    settings["current_dpi"] = dpi

    if not parsed.quiet:
        print(f"[Engraver] Imagem carregada: {parsed.input} (DPI: {dpi})")
        print(f"[Engraver] Método: {settings.get('dither_method')} | DPI Alvo: {settings.get('target_dpi')}")

    # Processamento através do motor C-acelerado
    try:
        result = engine.process_live_preview(pil_img, settings, preview_mode=False)

        # Se solicitado sem dithering (escala de cinza puro)
        if parsed.no_dither:
            result = result.convert("L")

        # Caminho de saída
        if parsed.output:
            out_path = parsed.output
        else:
            base, _ = os.path.splitext(os.path.basename(parsed.input))
            suffix = "_grayscale" if parsed.no_dither else ""
            out_path = f"processed_{base}{suffix}.bmp"

        result.save(out_path)

        if not parsed.quiet:
            w, h = result.size
            size_kb = os.path.getsize(out_path) / 1024
            print(f"[Engraver] Concluído com sucesso!")
            print(f"[Engraver] Saída: {out_path} ({w}x{h} px, {size_kb:.1f} KB)")

        return 0

    except Exception as e:
        print(f"[ERRO] Falha durante o processamento: {e}", file=sys.stderr)
        return 1


main = run_cli

if __name__ == "__main__":
    sys.exit(run_cli())
