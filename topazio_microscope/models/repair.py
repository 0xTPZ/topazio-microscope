import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass
class TestResult:
    name: str
    value: str
    note: str = ''
    created_at: str = field(default_factory=utc_now)


@dataclass
class RepairReport:
    source: str = ''
    created_at: str = field(default_factory=utc_now)
    roi: dict | None = None
    observations: list[str] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    verifications: list[str] = field(default_factory=list)
    test_results: list[TestResult] = field(default_factory=list)
    planning_notes: str = ''
    analysis: dict = field(default_factory=dict)
    comparison: dict = field(default_factory=dict)
    methods: list[str] = field(default_factory=lambda: ['OpenCV/NumPy', 'regras explícitas'])
    warnings: list[str] = field(default_factory=lambda: [
        'Nenhuma conexão elétrica é confirmada por análise visual.',
        'Exija validação humana, esquema elétrico e medição antes do reparo.',
    ])

    def to_dict(self) -> dict:
        data = asdict(self)
        data['test_results'] = [asdict(item) for item in self.test_results]
        return data

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    @classmethod
    def load(cls, path: Path) -> 'RepairReport':
        data = json.loads(path.read_text(encoding='utf-8'))
        data['test_results'] = [TestResult(**item) for item in data.get('test_results', [])]
        return cls(**data)
