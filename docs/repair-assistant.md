# Topázio Repair Assistant

O Repair Assistant é um módulo local e offline para apoiar a inspeção visual de placas. Ele usa OpenCV, NumPy e regras explícitas; não inclui um modelo genérico de IA e não aciona equipamentos externos.

## Fluxo

1. Abra a aba **Assistente**.
2. Use **Acompanhar câmera**, **Usar último frame** ou **Importar imagem**.
3. Arraste sobre a imagem para selecionar uma ROI. As coordenadas são mantidas na resolução original da imagem.
4. Clique em **Analisar** para obter nitidez, densidade de bordas e regiões visualmente suspeitas.
5. Use **Importar comparação** e **Mostrar overlay** para comparar fotografias. O alinhamento ORB/RANSAC é opcional e só é aplicado quando há pontos locais suficientes.
6. Registre medições em **Resultados** e notas em **Planejamento**.
7. Exporte uma imagem destacada e um relatório JSON ou Markdown.

## Interpretação segura

As regiões destacadas são candidatas geométricas visuais. Iluminação, foco, sujeira, máscara de solda, reflexos e perspectiva podem produzir falsos positivos. O programa nunca classifica uma trilha como rompida e nunca confirma uma conexão elétrica.

Antes de qualquer reparo:

- mantenha a placa desenergizada;
- consulte esquema elétrico ou boardview;
- confirme continuidade, resistência e possíveis curtos com multímetro;
- registre a medição e faça a decisão final manualmente.

O foco assistido mede a nitidez na ROI e memoriza o melhor frame observado. Ele não movimenta a lente e não promete autofoco físico.

## Arquitetura

- `vision/`: ROI, métricas, bordas, suspeitas geométricas, ORB/RANSAC e overlay;
- `analysis/`: pipeline de análise visual;
- `rules/`: observações, hipóteses e verificações com incerteza explícita;
- `models/`: relatório e resultados de testes;
- `reports/`: exportação JSON, Markdown e imagem;
- `ui/roi_canvas.py`: seleção visual da ROI em coordenadas da imagem.

Há um ponto de extensão para provedores de modelos futuros, mas nenhum modelo ONNX é distribuído nesta versão. Isso mantém o processamento offline, leve e auditável.

## Testes

Os testes usam imagens sintéticas, câmera/gravador simulados e inicialização Qt em modo headless. Não é necessário conectar uma câmera física no CI.
