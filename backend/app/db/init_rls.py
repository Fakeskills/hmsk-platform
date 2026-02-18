import os
import pathlib
import psycopg2
from urllib.parse import urlparse

SQL_FILE = pathlib.Path(__file__).parent / "rls" / "init_rls.sql"


def apply_rls() -> None:
    raw_url = os.environ["DATABASE_SYNC_URL"]
    # Strip SQLAlchemy driver prefix so psycopg2 can parse it
    url = raw_url.replace("postgresql+psycopg2://", "postgresql://")

    sql = SQL_FILE.read_text()
    conn = psycopg2.connect(url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    print("✅  RLS policies applied.")


if __name__ == "__main__":
    apply_rls()
