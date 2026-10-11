#!/usr/bin/env python3
"""Orquestrador Profissional de Build e Distribuição Nativa do Engraver via Nuitka.

Suporta empacotamento nativo completo para Linux, Windows e macOS:
- Compilação da extensão de aceleração em C (dither_accel)
- Geração de ícones multiplataforma (.ico / .png)
- Compilação nativa com Nuitka C Compiler (GUI standalone + poda Slim)
- Geração dos lançadores de terminal CLI (engraver-cli.exe / engraver-cli)
- Inclusão de scripts de instalação, atalhos .desktop e metadados
- Compactação otimizada (.tar.xz, .zip, .7z)
- Cálculo automatizado de checksums SHA-256
"""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PACKAGING_DIR = ROOT_DIR / "packaging"
RESOURCES_DIR = ROOT_DIR / "resources"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"


def log(msg: str):
    print(f"\033[1;34m[BUILD]\033[0m {msg}")


def log_success(msg: str):
    print(f"\033[1;32m[SUCESSO]\033[0m {msg}")


def log_warn(msg: str):
    print(f"\033[1;33m[AVISO]\033[0m {msg}")


def log_error(msg: str):
    print(f"\033[1;31m[ERRO]\033[0m {msg}")


def ensure_icons():
    """Gera icon.ico multi-resolução a partir de icon.png se necessário."""
    png_path = RESOURCES_DIR / "icon.png"
    ico_path = RESOURCES_DIR / "icon.ico"

    if not png_path.exists():
        log_warn("resources/icon.png não encontrado.")
        return

    if not ico_path.exists() or ico_path.stat().st_mtime < png_path.stat().st_mtime:
        try:
            from PIL import Image

            img = Image.open(png_path)
            img.save(
                ico_path,
                format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
            )
            log("resources/icon.ico multi-resolução gerado com sucesso.")
        except Exception as e:
            log_warn(f"Não foi possível gerar icon.ico: {e}")


def compile_c_accel():
    """Compila a biblioteca compartilhada C (dither_accel)."""
    c_source = ROOT_DIR / "core" / "dither_accel.c"
    if not c_source.exists():
        log_warn("core/dither_accel.c não encontrado.")
        return

    is_win = platform.system() == "Windows"
    is_mac = platform.system() == "Darwin"

    if is_win:
        out_name = "dither_accel.dll"
    elif is_mac:
        out_name = "dither_accel.dylib"
    else:
        out_name = "dither_accel.so"

    out_lib = ROOT_DIR / "core" / out_name

    cmd = ["gcc", "-O3", "-shared"]
    if not is_win:
        cmd += ["-fPIC"]
    cmd += ["-std=c99", "-Wall", "-Wextra", str(c_source), "-o", str(out_lib)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        log_success(f"Extensão C compilada com sucesso: {out_lib.name}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log_warn(f"Compilação C falhou (usará fallback NumPy/Python): {e}")


def run_nuitka(clean: bool = False, dry_run: bool = False):
    """Executa a compilação nativa em C com o Nuitka aplicando as podas Slim."""
    is_win = platform.system() == "Windows"
    is_mac = platform.system() == "Darwin"

    target_bundle = DIST_DIR / "Engraver"

    # Comando base Nuitka
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        # Otimizações Slim: Bloqueio estrito de módulos não utilizados
        "--nofollow-import-to=tkinter,customtkinter,unittest,test,pydoc,idlelib,email,html,http,xml,numba,llvmlite",
        "--noinclude-pytest-mode=nofollow",
        "--no-deployment-flag=self-execution",
        "--include-package=PIL",
        # Inclusão de dados e recursos estáticos
        f"--include-data-dir={RESOURCES_DIR}=resources",
        f"--include-data-dir={ROOT_DIR / 'core'}=core",
        f"--output-dir={DIST_DIR}",
        "--output-filename=Engraver",
    ]

    # Flags específicas por plataforma
    if is_win:
        cmd += [
            "--windows-console-mode=attach",
            f"--windows-icon-from-ico={RESOURCES_DIR / 'icon.ico'}",
            "--windows-company-name=Engraver",
            "--windows-product-name=Engraver",
            "--windows-file-version=2.0.0.0",
            "--windows-product-version=2.0.0.0",
            "--windows-file-description=Engraver - Photo Editor & Laser Dithering Studio",
        ]
    elif is_mac:
        cmd += [
            f"--macos-app-icon={RESOURCES_DIR / 'icon.png'}",
            "--macos-app-name=Engraver",
        ]
    else:
        cmd += [
            f"--linux-icon={RESOURCES_DIR / 'icon.png'}",
        ]

    cmd.append(str(ROOT_DIR / "main.py"))

    log(f"Comando Nuitka: {' '.join(cmd)}")

    if dry_run:
        log("Modo [dry-run]: Nuitka não foi executado.")
        return

    log("Iniciando compilação nativa C via Nuitka (pode levar alguns minutos)...")
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)

    # Padronização da pasta de saída para dist/Engraver
    default_nuitka_dir = DIST_DIR / "main.dist"
    if default_nuitka_dir.exists():
        if target_bundle.exists():
            shutil.rmtree(target_bundle)
        default_nuitka_dir.rename(target_bundle)

    log_success("Compilação nativa Nuitka concluída com sucesso.")

    # Compilação ou cópia do lançador CLI
    setup_cli_launcher(target_bundle, is_win)


def setup_cli_launcher(target_bundle: Path, is_win: bool):
    """Gera o executável/script CLI (engraver-cli) dentro do pacote compilado."""
    if not target_bundle.exists():
        return

    if is_win:
        c_launcher = PACKAGING_DIR / "engraver_cli.c"
        out_cli = target_bundle / "engraver-cli.exe"
        if c_launcher.exists():
            cmd = ["gcc", "-O2", str(c_launcher), "-o", str(out_cli)]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                log_success("Lançador nativo engraver-cli.exe compilado com sucesso.")
            except Exception as e:
                log_warn(f"Falha ao compilar engraver_cli.c: {e}")
    else:
        sh_launcher = PACKAGING_DIR / "engraver-cli"
        out_cli = target_bundle / "engraver-cli"
        if sh_launcher.exists():
            shutil.copy2(sh_launcher, out_cli)
            os.chmod(out_cli, 0o755)
            log_success("Lançador engraver-cli copiado para o pacote.")


def copy_bundle_metadata():
    """Copia documentação, scripts e atalhos para dentro do pacote final."""
    target_bundle = DIST_DIR / "Engraver"
    if not target_bundle.exists():
        log_error(f"Diretório alvo {target_bundle} não existe.")
        return

    # 1. Licença e README de distribuição
    license_src = ROOT_DIR / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, target_bundle / "LICENSE")

    readme_src = PACKAGING_DIR / "README_DIST.txt"
    if readme_src.exists():
        shutil.copy2(readme_src, target_bundle / "README.txt")

    # 2. Arquivos específicos do Linux
    if platform.system() != "Windows":
        for script_name in ["install_linux.sh", "uninstall_linux.sh", "engraver.desktop"]:
            src = PACKAGING_DIR / script_name
            if src.exists():
                dst = target_bundle / script_name
                shutil.copy2(src, dst)
                if script_name.endswith(".sh"):
                    os.chmod(dst, 0o755)

    log("Metadados, licença e scripts de instalação copiados para o pacote.")


def package_archives():
    """Gera arquivos compactados padrão e de alta compressão."""
    target_bundle = DIST_DIR / "Engraver"
    if not target_bundle.exists():
        return

    is_win = platform.system() == "Windows"

    if is_win:
        # ZIP padrão
        zip_path = DIST_DIR / "Engraver-Windows-Portable-x64.zip"
        log(f"Criando {zip_path.name}...")
        shutil.make_archive(str(DIST_DIR / "Engraver-Windows-Portable-x64"), "zip", str(DIST_DIR), "Engraver")

        # 7z ultra (se 7z estiver instalado)
        if shutil.which("7z"):
            z7_path = DIST_DIR / "Engraver-Windows-Portable-x64.7z"
            log(f"Criando {z7_path.name} com compressão LZMA2...")
            subprocess.run(["7z", "a", "-mx=9", str(z7_path), "Engraver"], cwd=str(DIST_DIR), check=True)
    else:
        # .tar.gz padrão
        tgz_path = DIST_DIR / "Engraver-Linux-x86_64.tar.gz"
        log(f"Criando {tgz_path.name}...")
        subprocess.run(["tar", "-czf", str(tgz_path), "-C", str(DIST_DIR), "Engraver"], check=True)

        # .tar.xz de alta compressão (multi-threaded com -T0)
        txz_path = DIST_DIR / "Engraver-Linux-x86_64.tar.xz"
        log(f"Criando {txz_path.name} (LZMA multithread)...")
        xz_env = {**os.environ, "XZ_OPT": "-T0"}
        subprocess.run(["tar", "-cJf", str(txz_path), "-C", str(DIST_DIR), "Engraver"], env=xz_env, check=True)


def generate_checksums():
    """Gera SHA256SUMS.txt com todos os pacotes em dist/."""
    checksums_file = DIST_DIR / "SHA256SUMS.txt"
    entries = []

    for item in sorted(DIST_DIR.iterdir()):
        if item.is_file() and item.name != "SHA256SUMS.txt" and not item.name.startswith("."):
            hasher = hashlib.sha256()
            with open(item, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            sha = hasher.hexdigest()
            entries.append(f"{sha}  {item.name}")

    if entries:
        with open(checksums_file, "w", encoding="utf-8") as f:
            f.write("\n".join(entries) + "\n")
        log_success(f"Checksums gerados em: {checksums_file.name}")


def print_summary():
    """Exibe o resumo dos pacotes gerados com seus tamanhos."""
    print("\n" + "=" * 80)
    print("  RESUMO DOS PACOTES DE DISTRIBUIÇÃO GERADOS (NUITKA)")
    print("=" * 80)
    print(f"{'Arquivo / Pasta':<45} | {'Tamanho':>12}")
    print("-" * 80)

    for item in sorted(DIST_DIR.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            size = sum(f.lstat().st_size for f in item.rglob("*") if not f.is_symlink() and f.is_file())
            size_str = f"{size / (1024 * 1024):.1f} MB (dir)"
        else:
            size = item.stat().st_size
            if size >= 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"

        print(f"{item.name:<45} | {size_str:>12}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Orquestrador de Build e Distribuição Nativa Nuitka do Engraver")
    parser.add_argument("--clean", action="store_true", help="Limpa diretórios build/ e dist/ antes do empacotamento")
    parser.add_argument("--dry-run", action="store_true", help="Exibe os passos e comandos sem executar a compilação")
    args = parser.parse_args()

    if args.clean:
        log("Limpando diretórios anteriores...")
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)

    log("Iniciando processo de build profissional com Nuitka...")
    ensure_icons()
    compile_c_accel()
    run_nuitka(clean=args.clean, dry_run=args.dry_run)
    if not args.dry_run:
        copy_bundle_metadata()
        package_archives()
        generate_checksums()
        print_summary()


if __name__ == "__main__":
    main()
