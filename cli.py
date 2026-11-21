#!/usr/bin/env python3
"""
Engraver CLI — Preparação de Imagens para Gravação a Laser
Interface de linha de comando modular de alta performance.
"""

import argparse
import os
import sys
from core.pipeline import get_transform_entry, normalize_transforms_config
from core.presets_manager import DEFAULT_STARTUP_PRESET, PresetsManager
import engine


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Engraver CLI — Preparação Modular de Imagens para Gravação a Laser em Joias e Metais"
    )
    parser.add_argument("input", help="Caminho do arquivo de imagem de entrada")
    parser.add_argument(
        "-o", "--output", help="Caminho do arquivo de saída (padrão: processed_<nome>.bmp)"
    )
    parser.add_argument(
        "-p", "--preset", help="Nome do preset a ser aplicado (ex: 'Padrão', 'Minimalista', 'Fotorealista')"
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=["Atkinson", "Floyd-Steinberg", "Jarvis-Judice-Ninke", "Halftone (Clusters)"],
        default=None,
        help="Método de dithering (padrão do preset: Atkinson)",
    )
    parser.add_argument(
        "--halftone-cell",
        type=int,
        default=None,
        help="Tamanho da célula em pixels para 'Halftone (Clusters)' (3-12, padrão: 6)",
    )
    parser.add_argument(
        "--dpi", type=int, default=None, help="DPI alvo de saída (padrão do preset: 300)"
    )
    parser.add_argument(
        "--width", type=float, default=0.0, help="Largura física final em mm (opcional)"
    )
    parser.add_argument(
        "--height", type=float, default=0.0, help="Altura física final em mm (opcional)"
    )

    # Módulos de transformação (default=None para só sobrescrever o preset quando informados)
    parser.add_argument("--brightness", type=int, default=None, help="Brilho 0-100 (neutro: 50)")
    parser.add_argument("--contrast", type=int, default=None, help="Contraste 0-100 (neutro: 50)")
    parser.add_argument(
        "--channel-mixing",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Ativar/desativar mixagem de canais para pele (60/30/10)",
    )
    parser.add_argument(
        "--clahe",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Ativar/desativar contraste local CLAHE",
    )
    parser.add_argument("--clahe-clip", type=float, default=None, help="Limite CLAHE (0.5-6.0)")
    parser.add_argument("--clahe-tile", type=int, default=None, help="Tamanho da grade CLAHE (4-16)")
    parser.add_argument("--gamma", type=float, default=None, help="Valor da correção gama (0.4-2.5)")
    parser.add_argument("--no-gamma", action="store_true", help="Desativar correção gama")
    parser.add_argument("--density", type=int, default=None, help="Densidade 1-10")
    parser.add_argument("--sharpen", type=int, default=None, help="Nitidez Unsharp 0-100 (0 desativa)")
    parser.add_argument("--no-sharpen", action="store_true", help="Desativar nitidez completamente")
    parser.add_argument(
        "--high-pass",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Ativar/desativar filtro High Pass dentro da nitidez",
    )
    parser.add_argument(
        "--bilateral",
        type=int,
        default=None,
        help="Passagens de suavização bilateral preservadora de bordas (0-6)",
    )
    parser.add_argument(
        "--bilateral-sigma", type=int, default=None, help="Força sigma do bilateral (15-100)"
    )
    parser.add_argument(
        "--white-clamp", type=int, default=None, help="Trava de branco puro (180-255)"
    )
    parser.add_argument(
        "--black-clamp", type=int, default=None, help="Trava de preto puro (0-80)"
    )
    parser.add_argument(
        "--quantize",
        type=int,
        choices=[0, 2, 3, 4, 5, 6, 8],
        default=None,
        help="Níveis de quantização tonal (0 desativa; 2,3,4,5,6,8)",
    )
    parser.add_argument(
        "--quantize-softness",
        type=int,
        default=None,
        help="Suavização entre níveis da quantização 0-100%% (padrão: 35)",
    )
    parser.add_argument(
        "--quantize-mode",
        choices=["kmeans", "uniform"],
        default=None,
        help="Modo da quantização: kmeans (adaptativo) ou uniform",
    )
    parser.add_argument(
        "--cleanup",
        choices=["off", "morph", "median"],
        default=None,
        help="Limpeza de ilhas/ruído: off, morph (Close+Open) ou median (Filtro Mediano)",
    )
    parser.add_argument(
        "--cleanup-kernel",
        type=int,
        choices=[3, 5],
        default=None,
        help="Tamanho do kernel de limpeza: 3 ou 5",
    )

    parser.add_argument(
        "--bg",
        choices=["preto", "branco", "black", "white"],
        default=None,
        help="Fundo para imagens com transparência alpha (padrão: branco)",
    )
    parser.add_argument("--invert", action="store_true", help="Inverter cores (negativo)")
    parser.add_argument(
        "--no-dither", action="store_true", help="Exportar em escala de cinza pré-dithering (modo L)"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Modo silencioso (sem prints informativos)"
    )

    # Flags legadas para retrocompatibilidade
    parser.add_argument("--bg-black", action="store_true", help="[Legado] Define fundo preto")
    parser.add_argument("--bg-white", action="store_true", help="[Legado] Define fundo branco")

    return parser.parse_args(args)


def _apply_cli_overrides(settings, parsed):
    transforms = normalize_transforms_config(settings)
    settings["transforms"] = transforms

    if parsed.method is not None:
        settings["dither_method"] = parsed.method
    if parsed.halftone_cell is not None:
        settings["halftone_cell"] = parsed.halftone_cell
    if parsed.dpi is not None:
        settings["target_dpi"] = parsed.dpi
    if parsed.width > 0:
        settings["width_mm"] = parsed.width
    if parsed.height > 0:
        settings["height_mm"] = parsed.height
    if parsed.invert:
        settings["invert_colors"] = True

    if parsed.bg_black or parsed.bg in ("preto", "black"):
        settings["background"] = "Preto"
    elif parsed.bg_white or parsed.bg in ("branco", "white"):
        settings["background"] = "Branco"

    # Overrides nos módulos de transformação
    if parsed.brightness is not None or parsed.contrast is not None:
        e = get_transform_entry(transforms, "brightness_contrast")
        e["enabled"] = True
        if parsed.brightness is not None:
            e["params"]["brightness"] = parsed.brightness
        if parsed.contrast is not None:
            e["params"]["contrast"] = parsed.contrast

    if parsed.channel_mixing is not None:
        get_transform_entry(transforms, "channel_mixing")["enabled"] = parsed.channel_mixing

    if parsed.clahe is not None or parsed.clahe_clip is not None or parsed.clahe_tile is not None:
        e = get_transform_entry(transforms, "clahe")
        if parsed.clahe is not None:
            e["enabled"] = parsed.clahe
        else:
            e["enabled"] = True
        if parsed.clahe_clip is not None:
            e["params"]["clip_limit"] = parsed.clahe_clip
        if parsed.clahe_tile is not None:
            e["params"]["tile_size"] = parsed.clahe_tile

    if parsed.no_gamma:
        get_transform_entry(transforms, "gamma")["enabled"] = False
    elif parsed.gamma is not None:
        e = get_transform_entry(transforms, "gamma")
        e["enabled"] = True
        e["params"]["gamma"] = parsed.gamma

    if parsed.density is not None:
        e = get_transform_entry(transforms, "density")
        e["enabled"] = parsed.density > 1
        e["params"]["level"] = parsed.density

    if parsed.no_sharpen:
        e = get_transform_entry(transforms, "sharpen")
        e["enabled"] = False
        e["params"]["amount"] = 0
        e["params"]["high_pass"] = False
    else:
        e = get_transform_entry(transforms, "sharpen")
        if parsed.sharpen is not None:
            e["enabled"] = parsed.sharpen > 0
            e["params"]["amount"] = parsed.sharpen
        if parsed.high_pass is not None:
            e["params"]["high_pass"] = parsed.high_pass

    if parsed.bilateral is not None or parsed.bilateral_sigma is not None:
        e = get_transform_entry(transforms, "bilateral")
        if parsed.bilateral is not None:
            e["enabled"] = parsed.bilateral > 0
            if parsed.bilateral > 0:
                e["params"]["passes"] = parsed.bilateral
        else:
            e["enabled"] = True
        if parsed.bilateral_sigma is not None:
            e["params"]["sigma"] = parsed.bilateral_sigma

    if parsed.white_clamp is not None or parsed.black_clamp is not None:
        e = get_transform_entry(transforms, "tone_clamp")
        if parsed.white_clamp is not None:
            e["params"]["white_clamp"] = parsed.white_clamp
        if parsed.black_clamp is not None:
            e["params"]["black_clamp"] = parsed.black_clamp
        wc = e["params"]["white_clamp"]
        bc = e["params"]["black_clamp"]
        e["enabled"] = (bc > 0 or wc < 255)

    if (
        parsed.quantize is not None
        or parsed.quantize_softness is not None
        or parsed.quantize_mode is not None
    ):
        e = get_transform_entry(transforms, "quantize")
        if parsed.quantize is not None:
            e["enabled"] = parsed.quantize >= 2
            if parsed.quantize >= 2:
                e["params"]["levels"] = parsed.quantize
        else:
            e["enabled"] = True
        if parsed.quantize_softness is not None:
            e["params"]["softness"] = parsed.quantize_softness
        if parsed.quantize_mode is not None:
            e["params"]["mode"] = parsed.quantize_mode

    if parsed.cleanup is not None or parsed.cleanup_kernel is not None:
        e = get_transform_entry(transforms, "cleanup")
        if parsed.cleanup == "off":
            e["enabled"] = False
        elif parsed.cleanup in ("morph", "median"):
            e["enabled"] = True
            e["params"]["method"] = "median" if parsed.cleanup == "median" else "morph_close_open"
        else:
            e["enabled"] = True
        if parsed.cleanup_kernel is not None:
            e["params"]["kernel_size"] = parsed.cleanup_kernel

    return settings


def run_cli(args=None):
    parsed = parse_args(args)

    if not os.path.exists(parsed.input):
        print(f"[ERRO] Arquivo não encontrado: {parsed.input}", file=sys.stderr)
        return 1

    pm = PresetsManager()
    if parsed.preset:
        settings = pm.get_preset(parsed.preset)
        if not parsed.quiet:
            print(f"[Engraver] Carregando preset: '{parsed.preset}'")
    else:
        settings = pm.get_preset(DEFAULT_STARTUP_PRESET)

    settings = _apply_cli_overrides(settings, parsed)

    try:
        pil_img, dpi = engine.load_image_pillow(parsed.input)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar imagem: {e}", file=sys.stderr)
        return 1

    settings["current_dpi"] = dpi

    if not parsed.quiet:
        print(f"[Engraver] Imagem carregada: {parsed.input} (DPI: {dpi})")
        print(f"[Engraver] Método: {settings.get('dither_method')} | DPI Alvo: {settings.get('target_dpi')}")

    try:
        result = engine.process_live_preview(
            pil_img,
            settings,
            preview_mode=False,
            skip_dither=bool(parsed.no_dither),
        )

        if parsed.output:
            out_path = parsed.output
        else:
            base, _ = os.path.splitext(os.path.basename(parsed.input))
            suffix = "_grayscale" if parsed.no_dither else ""
            out_path = f"processed_{base}{suffix}.bmp"

        out_dpi = engine.resolve_output_dpi(settings)
        engine.save_engraving_image(result, out_path, dpi=out_dpi)

        if not parsed.quiet:
            w, h = result.size
            size_kb = os.path.getsize(out_path) / 1024
            print("[Engraver] Concluído com sucesso!")
            print(f"[Engraver] Saída: {out_path} ({w}x{h} px, {size_kb:.1f} KB)")

        return 0

    except Exception as e:
        print(f"[ERRO] Falha durante o processamento: {e}", file=sys.stderr)
        return 1


main = run_cli

if __name__ == "__main__":
    sys.exit(run_cli())
