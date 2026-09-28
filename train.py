"""Русскоязычный антиспам: символьный TF-IDF + логистическая регрессия."""
from pathlib import Path
import csv
import hashlib
import json
import platform
import re
import unicodedata
import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

BASE = Path(__file__).resolve().parent
MODEL = BASE / 'model_ru.joblib'
METRICS = BASE / 'metrics_ru.json'
DATA = BASE / 'data' / 'russian_messages.csv'
MODEL_VERSION = 'ru-char-lr-v2'
MODEL_NAME = 'Символьный TF-IDF + логистическая регрессия'
DATASET_NAME = 'ZhiznMart — русскоязычные сообщения'


def clean_text(text):
    """Одинаковая обработка учебного текста и нового письма."""
    text = unicodedata.normalize('NFKC', text).lower().replace('ё', 'е')
    text = re.sub(r'https?://\S+|www\.\S+|<url>', ' ссылка ', text)
    text = re.sub(r'<(?:phone|email|handle|person|address)>', ' контакт ', text)
    text = re.sub(r'\d+', ' число ', text)
    return ' '.join(re.findall(r'[a-zа-я]+', text))


def read_dataset():
    unique = {}
    conflicts = set()
    raw_count = skipped_count = duplicate_count = 0
    with DATA.open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            raw_count += 1
            body, label = row['message'], int(row['label'])
            if label not in (0, 1):
                raise ValueError('В данных найдена неизвестная метка класса.')
            # Английские строки, числа и эмодзи без кириллицы исключаем.
            if not re.search(r'[а-яё]', body, re.I):
                skipped_count += 1
                continue
            text = clean_text(body)
            if text in unique:
                duplicate_count += 1
                if unique[text] != label:
                    conflicts.add(text)
            unique[text] = label
    for text in conflicts:
        del unique[text]
    texts = list(unique)
    labels = [unique[text] for text in texts]
    info = {'raw_count': raw_count, 'unique_count': len(texts),
            'skipped_count': skipped_count, 'duplicate_rows': duplicate_count,
            'conflicting_texts': len(conflicts),
            'ham_count': labels.count(0), 'spam_count': labels.count(1)}
    return texts, labels, info


def make_model():
    # Признаки — фрагменты длиной 3–5 символов в пределах слова.
    # Стоп-слова не удаляются: отрицания вроде «не» могут влиять на смысл.
    return Pipeline([
        ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5),
                                  min_df=2, max_features=50000, sublinear_tf=True)),
        ('classifier', LogisticRegression(C=3.0, class_weight='balanced',
                                           max_iter=1000, random_state=42)),
    ])


def train_model():
    texts, labels, info = read_dataset()
    # Дубликаты удалены до разделения. Словарь учится только на обучающей части.
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels)
    model = make_model()
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    metrics = {
        'model_version': MODEL_VERSION, 'model_name': MODEL_NAME,
        'dataset': DATASET_NAME, 'language': 'ru', **info,
        'train_count': len(x_train), 'test_count': len(x_test),
        'random_state': 42, 'test_size': 0.2,
        'accuracy': float(accuracy_score(y_test, predicted)),
        'precision': float(precision_score(y_test, predicted, zero_division=0)),
        'recall': float(recall_score(y_test, predicted, zero_division=0)),
        'f1': float(f1_score(y_test, predicted, zero_division=0)),
        'confusion_matrix': confusion_matrix(y_test, predicted, labels=[0, 1]).tolist(),
        'matrix_labels': ['не спам', 'спам'],
        'dataset_sha256': hashlib.sha256(DATA.read_bytes()).hexdigest(),
        'sklearn_version': sklearn.__version__, 'python_version': platform.python_version(),
        'evaluation_scope': 'Отложенные сообщения из одного чата; не почтовый корпус.',
    }
    # Сохраняется проверенная модель, без дообучения на тестовых данных.
    joblib.dump(model, MODEL)
    METRICS.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    return model, metrics


def load_model():
    if MODEL.exists() and METRICS.exists():
        try:
            metrics = json.loads(METRICS.read_text(encoding='utf-8'))
            if (metrics.get('model_version') == MODEL_VERSION
                    and metrics['sklearn_version'] == sklearn.__version__
                    and metrics['dataset_sha256'] == hashlib.sha256(DATA.read_bytes()).hexdigest()):
                return joblib.load(MODEL), metrics
        except (ValueError, KeyError, OSError, EOFError):
            pass
    return train_model()


def classify(model, text):
    if not text.strip():
        raise ValueError('Введите текст письма.')
    if len(text) > 100000:
        raise ValueError('Письмо слишком длинное. Максимум 100 000 символов.')
    # Иностранные названия внутри русского письма разрешены.
    if not re.search(r'[а-яё]{2}', text, re.I):
        raise ValueError('Введите письмо на русском языке. Одних чисел или английских слов недостаточно.')
    vector = model.named_steps['tfidf'].transform([clean_text(text)])
    if vector.nnz == 0:
        raise ValueError('Недостаточно знакомых модели фрагментов. Введите более полный текст письма.')
    classifier = model.named_steps['classifier']
    label = int(classifier.predict(vector)[0])
    spam_index = list(classifier.classes_).index(1)
    score = float(classifier.predict_proba(vector)[0][spam_index])
    return label, score


if __name__ == '__main__':
    _, result = train_model()
    print(json.dumps(result, ensure_ascii=False, indent=2))
