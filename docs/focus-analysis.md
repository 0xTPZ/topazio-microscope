# Foco e qualidade da imagem

O Topázio Microscope usa métricas locais e leves antes de considerar IA:

- variância do Laplaciano, sensível a detalhes de alta frequência;
- Tenengrad/Sobel, sensível a bordas e trilhas;
- indicador heurístico de 0–100 no painel.

O indicador não mede milímetros, não calibra a lente e não substitui o ajuste físico do anel de foco. IA pesada não é necessária para a primeira versão: ela adicionaria latência e dependências sem resolver foco óptico fora da profundidade de campo. Uma etapa futura pode usar essas métricas para busca automática do melhor ponto durante um ajuste manual assistido.
