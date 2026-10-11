# Guia de Contribuição e Desenvolvimento — Engraver

Este documento orienta desenvolvedores e agentes de IA sobre a arquitetura, convenções e execução da suíte de testes.

## 🛠️ Configuração do Ambiente

1. Clone o repositório e crie o ambiente virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   # ou .venv\Scripts\activate   # Windows
   ```

2. Instale as dependências de desenvolvimento:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Compilador C (para aceleração de dithering):**
   O Engraver compila sob demanda o acelerador nativo `core/dither_accel.c` via `gcc` ou `clang`.
   - **Linux (Debian/Ubuntu):** `sudo apt install build-essential gcc`
   - **Windows:** MinGW-w64 ou MSVC C++ Build Tools
   - **macOS:** `xcode-select --install`

## 🧪 Executando os Testes

A suíte de testes utiliza o **Pytest** e é configurada para rodar de forma completamente *headless* (offscreen), dispensando servidores de exibição gráfica.

Para executar todos os testes:
```bash
pytest
```

Para executar testes específicos com saída verbosa:
```bash
pytest tests/test_engine.py -vv
pytest tests/test_dither_backend.py -vv
pytest tests/test_ui_components.py -vv
pytest tests/test_integration.py -vv
```

## 🏗️ Estrutura do Projeto

- `core/`: Acelerador em C ANSI (`dither_accel.c`), carregador dinâmico (`dither_backend.py`) e gerenciador de presets JSON (`presets_manager.py`).
- `engine.py`: Pipeline principal de processamento de imagem OpenCV/PIL.
- `views/`: Componentes PySide6 (visualizador lado a lado com zoom/pan, sidebar com cartões, barra de status).
- `controllers/`: Gerenciador de eventos, threads em segundo plano (`QThreadPool`), diálogos nativos e timers de debounce.
- `packaging/`: Scripts de compilação nativa Nuitka (`build_dist.py`), instalador Windows Inno Setup (`inno_setup.iss`) e launchers CLI.
- `.github/workflows/`:
  - `ci.yml`: Roda a suíte de testes no Linux, Windows e macOS a cada commit/PR.
  - `build_releases.yml`: Compila e publica instaladores (`.exe`, `.AppImage`, `.dmg`) a cada tag `v*` criada via Nuitka.

## 📦 Gerando o Executável Localmente

Para compilar a aplicação de forma nativa com o Nuitka:
```bash
python packaging/build_dist.py
```
O pacote autônomo nativo será gerado no diretório `dist/Engraver/`.

## 📝 Convenções de Commits e Pull Requests

Para manter o histórico do repositório limpo e legível, adotamos a convenção de **Conventional Commits**:

- `feat:` Nova funcionalidade ou recurso para o usuário
- `fix:` Correção de bug ou regressão
- `refactor:` Alterações de código que não alteram a lógica externa nem corrigem bugs
- `perf:` Melhoria de performance ou renderização
- `test:` Adição ou correção de testes
- `docs:` Modificações apenas na documentação
- `ci:` Alterações nos workflows do GitHub Actions (`.github/workflows/`)

**Validação de Pull Requests:**
Todo Pull Request disparará automaticamente a matriz de 9 jobs no [CI](.github/workflows/ci.yml). O PR só poderá ser mesclado na branch `main` se todos os testes passarem sem falhas.
