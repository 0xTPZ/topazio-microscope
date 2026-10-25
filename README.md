# Topázio Microscope

Aplicativo open source para inspeção de placas eletrônicas com microscópios USB/UVC no Windows.

Autor e mantenedor: **0xTPZ** · Topázio Labs / Topazioverse

![Ícone Topázio Microscope](assets/topazio-microscope-256.png)

## Recursos atuais

- captura por DirectShow ou Media Foundation;
- seleção de câmera, backend e resolução;
- zoom digital e nitidez local;
- brilho, contraste, saturação e gama;
- perfis normal, alto contraste, trilhas, solda, cinza e bordas;
- indicador local de qualidade de foco;
- congelamento, captura PNG, gravação AVI e tela cheia;
- ícone Topázio integrado ao aplicativo.

## v0.2

A branch `v0.2` adiciona layout responsivo para telas pequenas, controles em abas, captura assíncrona, resolução/FPS reais, galeria de sessão, anotações editáveis, planejamento visual de trilhas e foco assistido. O planejamento é apenas uma hipótese visual: qualquer reparo deve ser validado por esquema elétrico e multímetro.

O indicador de foco é heurístico. Ele não substitui o ajuste físico da lente e não apresenta medidas em milímetros sem calibração.

## Topázio Repair Assistant

A branch `feature/repair-assistant` adiciona a aba **Assistente**, com ROI em coordenadas da imagem, nitidez local, realce de bordas, candidatos geométricos visuais, comparação com overlay ajustável, alinhamento opcional por ORB/RANSAC, registro de medições e exportação de relatórios JSON/Markdown. O processamento é local e offline. Nenhuma análise visual confirma continuidade elétrica ou autoriza um reparo; valide a placa desenergizada com esquema e multímetro. Consulte [docs/repair-assistant.md](docs/repair-assistant.md).

## Instalação para desenvolvimento

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m topazio_microscope.diagnostics --json
.\.venv\Scripts\python.exe run_app.py
```

O diagnóstico testa DirectShow (`CAP_DSHOW`) e Media Foundation (`CAP_MSMF`), percorre MJPG/YUY2 e salva uma amostra em `captures/` quando há frame válido.

## Executável

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --icon assets\topazio-microscope.ico --add-data "assets;assets" --name TopazioMicroscope --paths . run_app.py
```

## Estrutura

`topazio_microscope/capture` contém a captura; `topazio_microscope/image` contém processamento e métricas; `topazio_microscope/ui` fica reservado para telas futuras; `docs` contém decisões técnicas.

## Roadmap

- anotações vetoriais e exportação com/sem anotações;
- comparação lado a lado e overlay;
- sessões de reparo com notas e histórico;
- grade e calibração de escala;
- detecção de diferenças;
- assistente de foco baseado em métricas locais;
- módulo opcional de IA somente quando houver benefício real.

## Licença

O projeto usa **Apache-2.0**: permite uso comercial e distribuição, inclui uma concessão explícita de patentes e mantém uma base permissiva para contribuições. MIT seria mais curta, mas não oferece a mesma proteção de patentes; GPL exigiria que derivados fossem distribuídos sob GPL, o que reduziria a flexibilidade de integração.

Veja [LICENSE](LICENSE), [CONTRIBUTING.md](CONTRIBUTING.md) e [docs/focus-analysis.md](docs/focus-analysis.md).
