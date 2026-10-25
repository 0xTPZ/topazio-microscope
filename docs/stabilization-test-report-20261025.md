# Relatório de estabilização — 25/10/2026

## Versão

- Branch: `feature/repair-assistant`
- Commit validado: `630f8d24c843ecd5df5da74d09ba2f842563d830`
- Sistema: Windows 10 x64
- Python: 3.12.10 AMD64
- PySide6/Shiboken6: 6.8.2.1
- OpenCV: 4.10.0
- NumPy: 2.1.3
- PyInstaller: 6.11.1

## Testes aprovados

- `py_compile` dos módulos de captura, processamento, Repair Assistant e UI;
- testes headless do CI, incluindo ROI, ORB/RANSAC, relatórios, foco e regressões;
- inicialização da interface sem câmera física;
- layout em 1024×600, 1280×720, 1366×768, 1920×1080 e 2560×1440;
- rolagem do painel lateral em 1366×768;
- compilação PyInstaller e inicialização do executável sem erro de QtCore/DLL;
- presença de `Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, `cv2.pyd`, `opencv_videoio_ffmpeg4100_64.dll`, `shiboken6.abi3.dll`, `Shiboken.pyd` e runtimes MSVC;
- instalação em pasta separada e inicialização pelo atalho da área de trabalho.

## Recursos observados

O executável instalado permaneceu responsivo. O working set observado em repouso foi de aproximadamente 80,8 MiB. O valor de CPU medido foi acumulado desde a inicialização e não representa desempenho durante captura.

## USB físico

O Windows identificou:

- Nome: `USB 2.0 Camera`;
- VID/PID: `05E3:F12B`;
- Classe: Camera;
- Estado PnP: OK.

Nesta execução, a captura física do Repair Assistant ficou pendente. DirectShow não abriu o índice 0 e Media Foundation abriu o dispositivo, mas não entregou frames, com erro `-1072875772`. A causa operacional mais provável é que outra instância do aplicativo esteja usando o dispositivo ou que o estado do driver/câmera precise ser reinicializado.

Para repetir o teste, fechar primeiro as instâncias do Topázio que possam estar capturando vídeo, especialmente:

`C:\Users\User\Documents\TopazioLabs\Microscope\dist_repair_assistant_portable\TopazioRepairAssistant\TopazioRepairAssistant.exe`

e, se a câmera tiver sido iniciada nela:

`C:\Users\User\Documents\TopazioLabs\TopazioMicroscope-Daily-20251025\TopazioMicroscopeDaily.exe`

Depois abrir somente a instalação diária, iniciar a câmera, selecionar uma ROI na aba Assistente, analisar, capturar o melhor frame e exportar um relatório.

Nenhum processo foi encerrado automaticamente, nenhum driver foi alterado e nenhuma release estável foi publicada.
