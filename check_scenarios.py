"""Авторские сценарии писем. Не являются репрезентативным почтовым корпусом."""
import json
from train import BASE, load_model, classify


def check():
    model, _ = load_model()
    cases = json.loads((BASE / 'email_scenarios.json').read_text(encoding='utf-8'))
    for case in cases:
        label, score = classify(model, case['text'])
        case.update(predicted=label, spam_score=score, correct=label == case['expected'])
    report = {'note': 'Авторские сценарии. Не использовались для обучения. Это функциональная проверка, не оценка качества на реальной почте.',
              'total': len(cases), 'correct': sum(case['correct'] for case in cases), 'cases': cases}
    (BASE / 'scenario_results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False, indent=2))
