-- Входящие и исходящие суммы клиента по месяцам (в KGS).
-- Параметры: :client_id, :date_from, :date_to (даты в формате YYYY-MM-DD).
WITH client_tx AS (
    -- Операции клиента за период, без переводов самому себе.
    SELECT payer_id, payee_id, amount_kgs, tx_datetime
    FROM transactions
    WHERE (payer_id = :client_id OR payee_id = :client_id)
      AND payer_id <> payee_id
      AND date(tx_datetime) BETWEEN :date_from AND :date_to
),
monthly AS (
    -- По каждому месяцу отдельно суммируем входящие и исходящие.
    SELECT
        strftime('%Y-%m', tx_datetime) AS month,
        ROUND(SUM(CASE WHEN payee_id = :client_id THEN amount_kgs ELSE 0 END), 2) AS incoming,
        ROUND(SUM(CASE WHEN payer_id = :client_id THEN amount_kgs ELSE 0 END), 2) AS outgoing
    FROM client_tx
    GROUP BY month
)
SELECT month, incoming, outgoing
FROM monthly
ORDER BY month;