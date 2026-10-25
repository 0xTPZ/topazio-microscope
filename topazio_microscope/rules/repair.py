from ..analysis.assistant import AssistantAnalysis


def build_repair_guidance(result: AssistantAnalysis) -> dict:
    observations = [
        f'Nitidez local estimada: {result.sharpness:.1f} (métrica relativa à imagem analisada).',
        f'Densidade de bordas: {result.edge_density * 100:.1f}% na região selecionada ou no quadro.',
    ]
    hypotheses = []
    if result.sharpness < 35:
        hypotheses.append({
            'text': 'A região pode estar desfocada, com movimento ou com baixo contraste.',
            'uncertainty': 'média',
            'basis': 'métrica local de nitidez; não é diagnóstico óptico definitivo',
        })
    if result.suspicion_regions:
        observations.append(f'{len(result.suspicion_regions)} região(ões) com descontinuidade geométrica visual candidata.')
        hypotheses.append({
            'text': 'Pode haver uma interrupção visual, sujeira, máscara de solda ou alteração de iluminação.',
            'uncertainty': 'alta',
            'basis': 'bordas e morfologia; a imagem não prova interrupção elétrica',
        })
    else:
        observations.append('Nenhuma descontinuidade geométrica candidata foi destacada pela heurística atual.')
    if not hypotheses:
        hypotheses.append({
            'text': 'Não há hipótese visual forte com os dados atuais.',
            'uncertainty': 'alta',
            'basis': 'dados insuficientes para uma conclusão técnica',
        })
    verifications = [
        'Desenergizar a placa antes da inspeção física e limpar a região sem remover componentes.',
        'Comparar com uma fotografia de referência ou com a placa equivalente.',
        'Testar continuidade e resistência com multímetro nos dois extremos da região.',
        'Consultar o esquema elétrico ou boardview antes de planejar qualquer reparo.',
    ]
    return {
        'observations': observations,
        'hypotheses': hypotheses,
        'verifications': verifications,
        'warnings': result.warnings,
    }
