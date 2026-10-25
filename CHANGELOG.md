# Changelog

## 0.2.0 — responsividade e inspeção

- painel de captura reorganizado com `QSplitter` e `QScrollArea`;
- controles laterais separados em Câmera, Imagem, Inspeção e Captura;
- sliders com valor numérico, tooltip e restauração de padrões;
- estado do divisor persistido com `QSettings`;
- captura executada em worker Qt sem bloquear a interface;
- resolução entregue e FPS medido exibidos em tempo real;
- pasta de captura movida para `%LOCALAPPDATA%\TopazioLabs\TopazioMicroscope\captures`;
- base de anotações com camadas, ferramentas geométricas, texto, desenho livre, undo/redo e JSON;
- planejamento visual de trilhas com pontos, comprimento em pixels, notas e comparação antes/depois;
- foco assistido com histórico, melhor valor e tendência;
- distribuição Windows preparada na branch `v0.2`.
