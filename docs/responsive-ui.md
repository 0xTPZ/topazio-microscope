# Interface responsiva

O painel principal usa um `QSplitter` horizontal. A visualização fica no primeiro painel e os controles ficam em um `QScrollArea` recolhível no segundo painel. Os controles são organizados em abas e cada slider possui valor numérico e tooltip.

O divisor é salvo por `QSettings` em `TopazioLabs/TopazioMicroscope`. Se uma configuração antiga não couber, o Qt redistribui os painéis ao redimensionar a janela. A matriz validada inclui 1024×600, 1280×720, 1366×768, 1920×1080 e 2560×1440, com fatores Qt 1.25 e 1.5.

A imagem é escalada para preservar proporção. O zoom digital é independente do tamanho da janela; a tela de inspeção usa `QGraphicsView`, permitindo roda do mouse e pan com botão do meio ou ferramenta Pan.
