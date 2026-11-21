# Engraver — Preparação de Imagens para Gravação a Laser (v2.1)

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
| `core/` | **Core Backend** | Pipeline modular de transformações (`pipeline.py`), acelerador C para difusão de erro (`dither_accel.c`), retícula AM (`dither_backend.py`) e gerenciador de predefinições JSON (`presets_manager.py`). |

## Pipeline Modular de Processamento

Cada etapa pode ser ativada/desativada individualmente na barra lateral ou via CLI, com presets de fábrica prontos (**`Fotorealista`** selecionado por padrão, **`Minimalista`** para maior durabilidade em fiber laser e **`Padrão`** como base limpa):

1. **Redimensionamento Físico / Resolução Nativa** — Escala exata para `width_mm × height_mm @ DPI` (ou modo 1:1 preservando resolução original)
2. **Transparência (Alpha)** — Composição sobre fundo (padrão **Branco**, opcional Preto) + contorno limpo
3. **Módulos de Cor → Cinza** — `Brilho & Contraste` e `Mixagem de Canais` (pesos R/G/B configuráveis ou BT.601 padrão)
4. **Contraste & Tom** — `CLAHE` (clip/grade configuráveis), `Correção Gama` (`0.4–2.5`) e `Densidade` (`1–10`)
5. **Detalhe vs. Simplificação** — `Nitidez` (Unsharp + High Pass opcional com bypass real), `Suavização Bilateral` preservadora de bordas, `Trava de Extremos` (branco/preto puro), `Quantização Suave` (K-Means 1D / Uniforme com suavização *smoothstep* entre níveis) e `Limpeza` (`Morfologia Close+Open` ou `Filtro Mediano`)
6. **Dithering Acelerado** — `Atkinson` e `Jarvis-Judice-Ninke` (C nativo via `ctypes`), `Floyd-Steinberg` (PIL) e `Halftone (Clusters)` (retícula AM 45°)
7. **Inversão & Máscara Alfa** — Negativo opcional, máscara limpa e metadado de DPI físico embutido no arquivo exportado

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

- **Visualizador Lado a Lado 100% Fiel à Exportação:** Preview processado exatamente na resolução final de saída (com exportação instantânea reaproveitando o cache), mipmaps `INTER_AREA` sem Moiré em zoom reduzido e pixels 1-bit nítidos a partir de `1:1 Pixel`.
- **Inspeção Pré-Dithering (`👁 Pré-Dithering`):** Alternância instantânea entre tons de cinza pré-dithering e simulação 1-bit.
- **Presets Fixos no Topo:** Presets de fábrica (`Fotorealista`, `Minimalista`, `Padrão`) + perfis personalizados salvos em JSON.
- **Bloqueio de Proporção & Resolução Nativa:** Dimensões físicas em mm travadas com DPI embutido no arquivo exportado, ou modo original 1:1.
- **Diálogos Nativos & Tema Escuro Forçado:** Seletores nativos via `QFileDialog` e paleta escura consistente em qualquer tema do SO.

### 2. Modo Linha de Comando (CLI)

O CLI permite processar imagens de forma automatizada via terminal ou scripts externos:

```bash
# Processamento com preset padrão (Fotorealista)
python cli.py imagem.png

# Aplicando preset Minimalista (durabilidade em fiber laser)
python cli.py imagem.png --preset "Minimalista" -o gravacao.bmp

# Configuração modular detalhada
python cli.py imagem.png -o saida.bmp --no-clahe --no-sharpen --bilateral 3 --white-clamp 242 --black-clamp 62 --quantize 4 --quantize-softness 35

# Exportação em escala de cinza real (pré-dithering)
python cli.py imagem.png --preset "Minimalista" --no-dither -o cinza.bmp

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

