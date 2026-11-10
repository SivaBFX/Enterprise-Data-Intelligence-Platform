import os
import pandas as pd

from databricks import sql
from databricks.sdk.core import Config


def get_connection():
    cfg = Config()

    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")

    if not warehouse_id:
        raise ValueError("SQL Warehouse resource is not configured.")

    server_hostname = cfg.host.replace("https://", "").replace("http://", "")

    return sql.connect(
        server_hostname=server_hostname,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
    )


def query_table(table_name, limit=10):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {table_name} LIMIT {int(limit)}"
            )

            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]

            return pd.DataFrame(rows, columns=columns)
