"""Проверка русской версии. Запуск: python test_project.py."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from main import EXAMPLES
from train import load_model, classify, read_dataset, clean_text, MODEL_VERSION
from database import init_db, save_prediction, run_queries, connect


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.metrics = load_model()

    def test_russian_examples(self):
        self.assertEqual(classify(self.model, EXAMPLES['Пример спама'])[0], 1)
        self.assertEqual(classify(self.model, EXAMPLES['Обычное письмо'])[0], 0)
        self.assertEqual(self.metrics['language'], 'ru')
        self.assertEqual(self.metrics['model_version'], MODEL_VERSION)
        self.assertEqual(classify(self.model, 'Здравствуйте! Отправляю отчёт по проекту Python.')[0], 0)

    def test_invalid_input(self):
        for text in ('', '   ', '12345 !!!!', 'Hello, meeting tomorrow',
                     'ъъъъъъъъъъ', 'а' * 100001):
            with self.subTest(text=text[:20]):
                with self.assertRaises(ValueError):
                    classify(self.model, text)

    def test_russian_normalization(self):
        self.assertEqual(clean_text('Отчёт готов!'), clean_text('ОТЧЕТ ГОТОВ'))
        self.assertEqual(clean_text('Цена 100 рублей'), clean_text('Цена 500 рублей'))
        self.assertEqual(clean_text('Откройте <URL>'), clean_text('Откройте https://example.org'))

    def test_unique_dataset_and_metrics(self):
        texts, labels, info = read_dataset()
        self.assertEqual(len(texts), len(set(texts)))
        self.assertEqual(len(texts), len(labels))
        m = self.metrics
        self.assertEqual(m['train_count'] + m['test_count'], info['unique_count'])
        self.assertEqual(sum(map(sum, m['confusion_matrix'])), m['test_count'])
        self.assertEqual(set(labels), {0, 1})
        self.assertEqual(info['raw_count'], info['unique_count'] + info['skipped_count']
                         + info['duplicate_rows'] + info['conflicting_texts'])

    def test_database_transactions_and_queries(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.db'
            model_id = init_db(self.metrics, path)
            self.assertEqual(model_id, init_db(self.metrics, path))
            for body in EXAMPLES.values():
                label, score = classify(self.model, body)
                save_prediction(body, label, score, model_id, path)
            quoted = "Здравствуйте, отчёт готов; DROP TABLE emails; --"
            label, score = classify(self.model, quoted)
            save_prediction(quoted, label, score, model_id, path)
            results = run_queries(path)
            self.assertEqual(len(results), 5)
            self.assertEqual(len(results[0][1]), 3)
            self.assertEqual(len(results[1][1]), 1 + label)
            self.assertEqual(sum(row[1] for row in results[2][1]), 3)
            self.assertIn('Текст письма', results[0][0])
            with self.assertRaises(sqlite3.IntegrityError):
                save_prediction('ошибка транзакции', 0, 0.1, -999, path)
            with connect(path) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM emails').fetchone()[0], 3)
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')


if __name__ == '__main__':
    unittest.main(verbosity=2)
