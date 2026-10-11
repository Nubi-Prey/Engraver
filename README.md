# Engraver — Preparação de Imagens para Gravação a Laser (v2.0)

[![CI Test Suite](https://github.com/Nubi-Prey/Engraver/actions/workflows/ci.yml/badge.svg)](https://github.com/Nubi-Prey/Engraver/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/Nubi-Prey/Engraver?color=A855F7&label=Release)](https://github.com/Nubi-Prey/Engraver/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-6366F1.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)

Aplicação profissional de alta performance para pré-processamento e dithering de imagens destinadas a fotogravação a laser em joias e metais (fibras ópticas, MOPA, UV e CO₂). Possui arquitetura dual com **Interface Gráfica Desktop (PySide6 / Qt 6)** e **Interface de Linha de Comando (CLI)**.

---

## 📥 Download Rápido (Executáveis Prontos)

Não é necessário ter Python instalado para usar o Engraver! Baixe os executáveis autônomos na aba de **[Releases](https://github.com/Nubi-Prey/Engraver/releases)**:

* **Windows (64-bit):**
  - `Engraver-Windows-Setup-x64.exe` — Instalador completo (com atalhos no menu e integração CLI opcional ao PATH).
  - `Engraver-Windows-Portable-x64.zip` — Versão portátil (basta descompactar e rodar `Engraver.exe`).
* **Linux (x86_64):**
  - `Engraver-Linux-x86_64.AppImage` — Executável universal de 1 clique (dar permissão `chmod +x` e rodar).
  - `Engraver-Linux-x86_64.tar.xz` — Pacote portátil com scripts de integração ao sistema (`./install_linux.sh`).
* **macOS:**
  - `Engraver-macOS.dmg` — Imagem de disco padrão para macOS.

> [!NOTE]
> **Aviso do Windows Defender SmartScreen / Microsoft Edge:**
> Como o Engraver é um software de código aberto recém-lançado e distribuído de forma independente (sem certificado comercial pago de US$ 400/ano), o Windows SmartScreen pode exibir um aviso de "Fornecedor desconhecido" ao baixar ou executar:
> - **Na tela azul do SmartScreen:** Clique em **"Mais informações"** (*More info*) e depois no botão **"Executar assim mesmo"** (*Run anyway*).
> - **Na versão Portátil (`.zip`):** Antes ou após extrair, clique com o botão direito no arquivo → **Propriedades** → marque a caixa **"Desbloquear"** (*Unblock*) na parte inferior → **OK**.
> - Todos os binários são gerados diretamente nos servidores públicos do GitHub Actions a partir do código deste repositório, com hashes disponíveis no arquivo `SHA256SUMS.txt`.

---

## Arquitetura Modular (MVC)

| Módulo | Papel | Descrição |
|---|---|---|
| `views/` | **View (GUI)** | Interface gráfica em **PySide6 (Qt 6)** com tema *Dark Slate Purple & Neon Violet* (`resources/styles.qss`), visualizador sincronizado `SideBySideViewer` (`QGraphicsView`) e barra lateral de controles `SettingsSidebar`. |
| `controllers/` | **Controller** | `AppController` gerencia o fluxo de eventos, concorrência via `QThreadPool`/`QRunnable`, debounce com `QTimer`, diálogo nativo de arquivos e persistência de predefinições. |
| `cli.py` | **Interface CLI** | Interface de linha de comando com suporte a argumentos customizados, presets e automação em lote. |
| `engine.py` | **Model** | Pipeline de processamento de imagem de alta performance (OpenCV + PIL + extensões C nativas). |
| `core/` | **Core Backend** | Acelerador C para difusão de erro (`dither_accel.c`) e gerenciador de predefinições JSON (`presets_manager.py`). |

## Pipeline de Processamento

1. **Normalização de DPI** — Upscale via Lanczos se a imagem estiver abaixo do DPI alvo
2. **Processamento de Transparência** — Composição sobre fundo (preto/branco) + borda sólida de 1px
3. **Brilho e Contraste** — Ajuste fino via OpenCV (slider 0-100, 50=neutro)
4. **Mixagem de Canais** — `Gray = R×0.6 + G×0.3 + B×0.1` (realce de tons de pele para joias)
5. **CLAHE + Gamma** — Contraste adaptativo local + correção gamma para tons médios
6. **Densidade** — Escurecimento linear pré-dithering (mais pontos pretos)
7. **Nitidez** — High Pass Filter + Unsharp Mask proporcional
8. **Dithering Acelerado** — Floyd-Steinberg (PIL), Atkinson e Jarvis-Judice-Ninke (C puro via ctypes)
9. **Inversão** — Opção de inverter cores (negativo para matrizes escuras)
10. **Máscara de Fundo** — Limpeza de ruído fora do objeto para imagens com canal alfa

## Instalação e Execução

### Pré-requisitos
- Python 3.10+
- Linux, Windows ou macOS

```bash
# Ativar o ambiente virtual
source .venv/bin/activate    # Linux / macOS
# ou .venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 1. Modo Interface Gráfica (Desktop App)

```bash
python main.py
```

- **Visualizador Lado a Lado Sincronizado:** Zoom contínuo (5% a 3200%) e pan espelhado entre Imagem Original e Simulação.
- **Pixel Inspection:** Renderização nítida (*Nearest Neighbor*) em zoom alto para inspecionar pontos exatos de dithering.
- **Presets Customizados:** Salve, carregue e gerencie seus perfis de gravação personalizados.
- **Bloqueio de Proporção (Aspect Ratio):** Dimensões físicas em mm travadas com precisão.
- **Diálogos Nativos:** Seletores de arquivos nativos do OS via `QFileDialog`.

### 2. Modo Linha de Comando (CLI)

O CLI permite processar imagens de forma automatizada via terminal ou scripts externos:

```bash
# Processamento básico com configurações padrão
python cli.py imagem.png

# Processamento aplicando um preset salvo na interface gráfica
python cli.py imagem.png --preset "Padrão" -o gravacao.bmp

# Configuração detalhada por parâmetros
python cli.py imagem.png -o saida.bmp -m Atkinson --dpi 600 --sharpen 90 --bg preto

# Ajuda e listagem de todos os parâmetros
python cli.py --help
```

O comando CLI também pode ser invocado diretamente pelo executável principal via `python main.py cli ...` ou `engraver-cli`.

## Testes Automatizados

O projeto conta com suíte de testes com cobertura unitária e de integração em modo *headless*:

```bash
# Instalar dependências de teste
pip install -r requirements-dev.txt

# Executar a suíte de testes
pytest
```

## Distribuição e Empacotamento
 
Arquivos prontos para compilar executáveis nativos autônomos em C/C++ sem necessidade de Python instalado:

- **Orquestrador de Build Nativo (Nuitka):** `packaging/build_dist.py`
- **Instalador Windows (Inno Setup):** `packaging/inno_setup.iss`
- **Integração Desktop Linux (XDG):** `packaging/install_linux.sh` e `packaging/uninstall_linux.sh`
- **Workflow CI/CD Multi-OS:** `.github/workflows/build_releases.yml` (compila Windows `.exe`, Linux `.AppImage` e macOS `.dmg` via GitHub Actions).

## Licença

Este projeto é distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para obter detalhes completos.

