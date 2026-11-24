import os
import io
import csv
import requests
import pandas as pd
import psycopg2

SHEET_ID = "1dI1y9wOWz6GzZ_jNvd9irO4fhKx45beI"
GID = "1776851451"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

DATABASE_URL = os.environ["NEON_DATABASE_URL"]

RAW_COLUMNS = [
    "id_da_fila", "id_do_pedido", "data_do_pedido", "data_de_envio",
    "modo_de_envio", "id_do_cliente", "nome_do_cliente", "segmento",
    "cidade", "estado_provincia", "pais_regiao", "regiao",
    "id_do_produto", "categoria", "sub_categoria", "nome_do_produto",
    "vendas", "quantidade", "desconto", "lucro", "cep"
]

TRANSFORM_SQL = """
BEGIN;

TRUNCATE TABLE analytics.fct_pedidos;

INSERT INTO analytics.fct_pedidos (
    id_fila, id_pedido, data_pedido, data_envio, dias_para_envio,
    modo_envio, id_cliente, nome_cliente, segmento,
    cidade, estado_provincia, pais_regiao, regiao, cep,
    id_produto, categoria, sub_categoria, nome_produto,
    vendas, quantidade, desconto, lucro, margem_lucro, _updated_at
)
SELECT DISTINCT ON (NULLIF(TRIM(id_da_fila), '')::INTEGER)
    NULLIF(TRIM(id_da_fila), '')::INTEGER                          AS id_fila,
    TRIM(id_do_pedido)                                             AS id_pedido,
    TO_DATE(TRIM(data_do_pedido), 'MM/DD/YYYY')                    AS data_pedido,
    TO_DATE(TRIM(data_de_envio), 'MM/DD/YYYY')                     AS data_envio,
    (TO_DATE(TRIM(data_de_envio), 'MM/DD/YYYY') 
     - TO_DATE(TRIM(data_do_pedido), 'MM/DD/YYYY'))                AS dias_para_envio,
    TRIM(modo_de_envio)                                            AS modo_envio,
    TRIM(id_do_cliente)                                            AS id_cliente,
    TRIM(nome_do_cliente)                                          AS nome_cliente,
    TRIM(segmento)                                                 AS segmento,
    TRIM(cidade)                                                   AS cidade,
    TRIM(estado_provincia)                                         AS estado_provincia,
    TRIM(pais_regiao)                                              AS pais_regiao,
    TRIM(regiao)                                                   AS regiao,
    NULLIF(TRIM(cep), '')                                          AS cep,
    TRIM(id_do_produto)                                            AS id_produto,
    TRIM(categoria)                                                AS categoria,
    TRIM(sub_categoria)                                            AS sub_categoria,
    TRIM(nome_do_produto)                                          AS nome_produto,
    REPLACE(NULLIF(TRIM(vendas), ''), ',', '.')::NUMERIC(12, 4)    AS vendas,
    NULLIF(TRIM(quantidade), '')::INTEGER                          AS quantidade,
    REPLACE(NULLIF(TRIM(desconto), ''), ',', '.')::NUMERIC(6, 4)   AS desconto,
    REPLACE(NULLIF(TRIM(lucro), ''), ',', '.')::NUMERIC(12, 4)     AS lucro,
    CASE 
        WHEN REPLACE(NULLIF(TRIM(vendas), ''), ',', '.')::NUMERIC > 0 
        THEN ROUND(
            (REPLACE(NULLIF(TRIM(lucro), ''), ',', '.')::NUMERIC / 
             REPLACE(NULLIF(TRIM(vendas), ''), ',', '.')::NUMERIC), 4
        )
        ELSE 0 
    END                                                            AS margem_lucro,
    CURRENT_TIMESTAMP                                              AS _updated_at
FROM raw.superloja_pedidos
WHERE NULLIF(TRIM(id_da_fila), '') IS NOT NULL
ORDER BY NULLIF(TRIM(id_da_fila), '')::INTEGER, _ingested_at DESC;

COMMIT;
"""

def extract_from_sheets() -> pd.DataFrame:
    response = requests.get(CSV_URL, timeout=60)
    response.raise_for_status()
    response.encoding = "utf-8"

    df = pd.read_csv(io.StringIO(response.text), dtype=str)
    # Garante exatamente as 21 colunas esperadas na ordem da tabela raw
    df = df.iloc[:, :len(RAW_COLUMNS)]
    df.columns = RAW_COLUMNS
    return df

def load_to_raw(conn, df: pd.DataFrame):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N", quoting=csv.QUOTE_MINIMAL)
    buffer.seek(0)

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw.superloja_pedidos;")
        sql = "COPY raw.superloja_pedidos FROM STDIN WITH (FORMAT CSV, DELIMITER ',', NULL '')"
        cur.copy_expert(sql, buffer)
    conn.commit()

def run_analytics_transform(conn):
    with conn.cursor() as cur:
        cur.execute(TRANSFORM_SQL)
    conn.commit()

def main():
    print("1. Extraindo dados do Google Sheets...")
    df = extract_from_sheets()
    print(f"   -> {len(df)} linhas extraídas.")

    print("2. Conectando ao Neon PostgreSQL...")
    with psycopg2.connect(DATABASE_URL) as conn:
        print("3. Carregando camada RAW (COPY)...")
        load_to_raw(conn, df)
        print("4. Executando transformação para camada ANALYTICS...")
        run_analytics_transform(conn)

    print("Pipeline concluído com sucesso!")

if __name__ == "__main__":
    main()