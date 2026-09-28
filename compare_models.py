"""Сравнение моделей на валидации, не на окончательной тестовой выборке."""
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.naive_bayes import MultinomialNB
from train import BASE, read_dataset, make_model


def compare():
    texts, labels, _ = read_dataset()
    development, _, y_development, _ = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels)
    train, validation, y_train, y_validation = train_test_split(
        development, y_development, test_size=0.2, random_state=17,
        stratify=y_development)
    results = {'train_count': len(train), 'validation_count': len(validation), 'models': {}}
    for name in ['Наивный Байес', 'Логистическая регрессия']:
        model = make_model()
        if name == 'Наивный Байес':
            model.set_params(classifier=MultinomialNB(alpha=0.5))
        model.fit(train, y_train)
        predicted = model.predict(validation)
        results['models'][name] = {
            'accuracy': float(accuracy_score(y_validation, predicted)),
            'f1': float(f1_score(y_validation, predicted)),
        }
    (BASE / 'validation_comparison.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return results


if __name__ == '__main__':
    print(json.dumps(compare(), ensure_ascii=False, indent=2))
