import os
import pathlib
import psycopg2

SQL_FILE = pathlib.Path(__file__).parent / "rls" / "init_rls.sql"


def apply_rls() -> None:
    url = os.environ["DATABASE_SYNC_URL"]
    sql = SQL_FILE.read_text()
    conn = psycopg2.connect(url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    print("✅  RLS policies applied.")


if __name__ == "__main__":
    apply_rls()
