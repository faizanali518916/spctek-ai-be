import os
import sys
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()


def ping_db():
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print("❌ DATABASE_URL not set in environment")
        sys.exit(1)

    try:
        # Parse DB URL
        result = urlparse(db_url)

        conn = psycopg2.connect(
            dbname=result.path[1:],  # remove leading '/'
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode="require",  # important for Neon / cloud DBs
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()

        cursor.close()
        conn.close()

        print("✅ Database is ONLINE")

    except Exception as e:
        print("❌ Database is OFFLINE or unreachable")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    ping_db()
