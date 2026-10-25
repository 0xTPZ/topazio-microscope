from typing import Any, Protocol


class VisionModelProvider(Protocol):
    """Contrato futuro para um modelo local opcional, sem acoplamento ao UI."""

    name: str

    def analyze(self, frame) -> dict[str, Any]:
        ...


class OptionalONNXProvider:
    """Ponto de extensão seguro: não carrega ONNX nem baixa modelos automaticamente."""

    name = 'ONNX opcional'

    def __init__(self, model_path=None):
        self.model_path = model_path
        self.available = False

    def analyze(self, frame) -> dict[str, Any]:
        return {
            'available': False,
            'method': self.name,
            'message': 'Nenhum modelo ONNX foi configurado; análise clássica permanece ativa.',
        }
