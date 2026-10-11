================================================================================
  ENGRAVER — Preparação de Imagens para Gravação a Laser em Joias e Metais
  Versão 2.0.0 (Standalone Desktop & CLI)
================================================================================

O Engraver é uma ferramenta de alta precisão para tratamento e dithering de imagens
destinadas a máquinas de gravação a laser (fibras ópticas, MOPA, UV e CO2).

--------------------------------------------------------------------------------
1. COMO EXECUTAR A INTERFACE GRÁFICA (GUI)
--------------------------------------------------------------------------------
- No Windows:
  Dê dois cliques no executável:
    Engraver.exe

  [Nota Windows SmartScreen]: Caso o Windows exiba o aviso azul de proteção
  ("O Windows protegeu o seu computador"), clique em "Mais informações" e em
  seguida no botão "Executar assim mesmo". Alternativamente, clique com o botão
  direito no arquivo -> Propriedades -> Marque "Desbloquear" -> OK.

- No Linux:
  Abra um terminal na pasta e execute:
    ./Engraver

  Para integrar o Engraver ao menu de aplicativos e criar comandos no terminal:
    ./install_linux.sh
  (Para remover atalhos posteriormente: ./uninstall_linux.sh)

--------------------------------------------------------------------------------
2. COMO EXECUTAR A INTERFACE DE LINHA DE COMANDO (CLI)
--------------------------------------------------------------------------------
Você pode realizar conversões em lote ou automatizar tarefas diretamente pelo terminal:

- No Windows (Prompt de Comando ou PowerShell):
    engraver-cli.exe foto.png -o saida.bmp --dpi 300 -m Floyd-Steinberg

- No Linux (Bash / Zsh):
    ./engraver-cli foto.png -o saida.bmp --dpi 300 -m Floyd-Steinberg

Exemplos Úteis:
  # Usar um preset salvo:
    engraver-cli foto.png -p "Padrão" -o gravacao.bmp

  # Definir tamanho em mm (ex: medalha de 30mm de largura):
    engraver-cli medalha.png --width 30 --dpi 500 -m Atkinson -o medalha_laser.bmp

  # Imagem com transparência (fundo branco):
    engraver-cli logo.png --bg branco --sharpen 90 -o logo_laser.bmp

  # Ver todas as opções:
    engraver-cli --help

--------------------------------------------------------------------------------
3. ARQUIVOS E LICENÇA
--------------------------------------------------------------------------------
Distribuído sob a Licença MIT. Consulte o arquivo LICENSE incluído neste diretório.
Desenvolvido com foco em máxima precisão matemática e alta performance nativa.
================================================================================
