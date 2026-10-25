from pathlib import Path

import cv2

from ..models.repair import RepairReport


def export_markdown(report: RepairReport, path: Path) -> None:
    lines = [
        '# Topázio Repair Assistant',
        '',
        f'- Fonte: {report.source or "não informada"}',
        f'- Criado em: {report.created_at}',
        f'- Métodos: {", ".join(report.methods)}',
        '',
        '## Observações',
        *[f'- {item}' for item in report.observations],
        '',
        '## Hipóteses',
    ]
    lines.extend(f'- {item.get("text", "")} (incerteza: {item.get("uncertainty", "não informada")}; base: {item.get("basis", "")})' for item in report.hypotheses)
    lines.extend(['', '## Verificações sugeridas', *[f'- {item}' for item in report.verifications], '', '## Resultados dos testes'])
    lines.extend(f'- {item.name}: {item.value} — {item.note}' for item in report.test_results)
    lines.extend(['', '## Planejamento', report.planning_notes or 'Nenhuma nota registrada.', '', '## Limitações e segurança', *[f'- {item}' for item in report.warnings]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def export_visual_result(image, path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(path), image))
