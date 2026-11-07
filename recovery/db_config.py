# ============================================================
# FILE: db_config.py
# PURPOSE: Manages database connections for PostgreSQL and MongoDB.
#
# ADBMS CONCEPT — Polyglot Persistence:
#   Using two different databases in one system, each chosen
#   for what it does best:
#     PostgreSQL → structured banking data, ACID transactions
#     MongoDB    → flexible WAL log documents, fast inserts
#
# This file is imported by every other module.
# Change PG_PASSWORD to match your local PostgreSQL setup.
# ============================================================

import psycopg2
from pymongo ; MongoClient

# ── PostgreSQL settings ─────────────────────────────────────
PG_HOST     = "localhost"
PG_PORT     = 5432
PG_DATABASE = "bank_recovery_db"
PG_USER     = "postgres"
PG_PASSWORD = "12345678910"          # ← Change this

# ── MongoDB settings ────────────────────────────────────────
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB  = "bank_recovery_logs"


def get_pg_connection():
    """
    Returns a PostgreSQL connection with autocommit OFF.

    autocommit=False means we must call conn.commit() or
    conn.rollback() manually — this is essential for showing
    explicit transaction control in the ADBMS demo.
    """
    conn = psycopg2.connect(
        host     = PG_HOST,
        port     = PG_PORT,
        dbname   = PG_DATABASE,
        user     = PG_USER,
        password = PG_PASSWORD,
    )
    conn.autocommit = False    # Manual commit/rollback control
    return conn


def get_mongo_db():
    """
    Returns the MongoDB database object (bank_recovery_logs).

    MongoDB is used to store WAL logs.
    No authentication required for local development setup.
    """
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB]


def test_connections():
    """
    Tests both database connections and prints a status report.
    Call this at startup to ensure everything is reachable.
    """
    print("\n  Checking database connections...")

    # Test PostgreSQL
    try:
        conn = get_pg_connection()
        cur  = conn.cursor()
        cur.execute("SELECT current_database();")
        db = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"  [OK] PostgreSQL connected  → database: {db}")
    except Exception as e:
        print(f"  [FAIL] PostgreSQL error: {e}")
        raise

    # Test MongoDB
    try:
        db = get_mongo_db()
        db.command("ping")
        print(f"  [OK] MongoDB connected     → database: {MONGO_DB}")
    except Exception as e:
        print(f"  [FAIL] MongoDB error: {e}")
        raise

    print()
