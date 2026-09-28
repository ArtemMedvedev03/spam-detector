"""SQLite: три связанные таблицы и выполнение пяти запросов."""
from pathlib import Path
import hashlib
import json
import sqlite3
from contextlib import contextmanager

BASE = Path(__file__).resolve().parent
DB = BASE / 'spam_history_ru.db'


@contextmanager
def connect(path=DB):
    connection = sqlite3.connect(path)
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db(metrics, path=DB):
    # Хеш позволяет связать результат с конкретной версией модели и её метриками.
    key = hashlib.sha256(json.dumps(metrics, sort_keys=True).encode()).hexdigest()
    with connect(path) as db:
        db.executescript((BASE / 'schema.sql').read_text(encoding='utf-8'))
        db.execute('''INSERT OR IGNORE INTO models
            (model_key, name, accuracy, precision, recall, f1, test_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (key, metrics['model_name'], metrics['accuracy'],
             metrics['precision'], metrics['recall'], metrics['f1'], metrics['test_count']))
        return db.execute('SELECT id FROM models WHERE model_key = ?', (key,)).fetchone()[0]


def save_prediction(text, label, score, model_id, path=DB):
    # Обе записи сохраняются в одной транзакции: либо обе, либо ни одна.
    with connect(path) as db:
        cursor = db.execute('INSERT INTO emails (body) VALUES (?)', (text,))
        db.execute('''INSERT INTO predictions (email_id, model_id, label, spam_score)
                      VALUES (?, ?, ?, ?)''', (cursor.lastrowid, model_id, label, score))


def run_queries(path=DB):
    statements = (BASE / 'queries.sql').read_text(encoding='utf-8').split(';')
    results = []
    with connect(path) as db:
        for statement in statements:
            if statement.strip():
                cursor = db.execute(statement)
                results.append(([item[0] for item in cursor.description], cursor.fetchall()))
    return results


if __name__ == '__main__':
    for number, (columns, rows) in enumerate(run_queries(), start=1):
        print(f'\nЗапрос {number}:', ', '.join(columns))
        for row in rows:
            print(row)
