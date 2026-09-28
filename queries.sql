-- 1. Последние 100 проверок с текстом письма и названием модели.
SELECT p.id AS "Номер проверки", p.created_at AS "Дата и время UTC",
 e.body AS "Текст письма",
 CASE p.label WHEN 1 THEN 'СПАМ' ELSE 'НЕ СПАМ' END AS "Результат",
 ROUND(p.spam_score * 100, 1) AS "Оценка спама, %", m.name AS "Модель"
FROM predictions p JOIN emails e ON e.id = p.email_id
JOIN models m ON m.id = p.model_id ORDER BY p.id DESC LIMIT 100;

-- 2. Только письма, отнесённые к спаму.
SELECT e.id AS "Номер письма", e.body AS "Текст письма",
 ROUND(p.spam_score * 100, 1) AS "Оценка спама, %"
FROM emails e JOIN predictions p ON p.email_id = e.id
WHERE p.label = 1 ORDER BY p.spam_score DESC;

-- 3. Количество проверок по результатам.
SELECT CASE label WHEN 1 THEN 'СПАМ' ELSE 'НЕ СПАМ' END AS "Результат",
 COUNT(*) AS "Количество" FROM predictions GROUP BY label;

-- 4. Количество проверок по дням (время UTC).
SELECT DATE(created_at) AS "Дата UTC", COUNT(*) AS "Количество"
FROM predictions GROUP BY DATE(created_at) ORDER BY "Дата UTC" DESC;

-- 5. Метрики и количество применений каждой модели.
SELECT m.id AS "Номер модели", m.name AS "Модель",
 ROUND(m.accuracy * 100, 2) AS "Верных ответов, %",
 ROUND(m.precision * 100, 2) AS "Точность для спама, %",
 ROUND(m.recall * 100, 2) AS "Полнота для спама, %",
 ROUND(m.f1, 4) AS "F1", COUNT(p.id) AS "Количество проверок"
FROM models m LEFT JOIN predictions p ON p.model_id = m.id GROUP BY m.id;
