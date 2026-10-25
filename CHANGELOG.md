# Changelog

## Próxima — Topázio Repair Assistant

- nova aba Assistente com painel lateral recolhível e visualização de ROI;
- análise local de nitidez, bordas e possíveis descontinuidades geométricas;
- comparação com transparência ajustável e alinhamento opcional ORB/RANSAC;
- observações, hipóteses com incerteza, verificações sugeridas e resultados manuais;
- captura do melhor frame da ROI e histórico da sessão;
- exportação de imagem destacada e relatório JSON/Markdown;
- arquitetura separada em `vision`, `analysis`, `rules`, `models` e `reports`;
- testes com imagens sintéticas, interface headless e dispositivos simulados.

Limitação: o módulo não confirma rompimentos elétricos, não movimenta lentes e não executa reparos.

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

### Correções pós-revisão

- planejamento agora recebe o último frame, imagens da galeria ou arquivos importados;
- troca de imagem reinicia pontos e camadas do planejamento para preservar coordenadas coerentes;
- exportação do planejamento renderiza a imagem e suas marcações;
- gravação normaliza frames filtrados/zoom para o tamanho do `VideoRecorder`;
- falha ao abrir o gravador agora é informada ao usuário;
- ciclo de vida do worker captura exceções, libera a câmera em `finally` e aguarda a thread no fechamento;
- CI cobre interface v0.2, worker simulado, serialização, planejamento e dimensões de gravação.
