#!/usr/bin/env python3
"""Run database migration to add the Current Portfolio feature's tables:
user_portfolios (named portfolios owned by a dashboard username) and
portfolio_holdings (ticker + shares rows within a portfolio, upserted on
(portfolio_id, ticker) so re-adding a ticker updates shares instead of
duplicating rows)."""

import psycopg2
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Parse DATABASE_URL
db_url = os.getenv('DATABASE_URL')
if not db_url:
    raise ValueError("DATABASE_URL environment variable not set")

result = urlparse(db_url)

# Database connection
conn = psycopg2.connect(
    host=result.hostname,
    database=result.path[1:],
    user=result.username,
    password=result.password,
    port=result.port or 5432
)

try:
    cursor = conn.cursor()

    print("Creating user_portfolios table...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_portfolios (
            id SERIAL PRIMARY KEY,
            owner_username VARCHAR(100) NOT NULL,
            name VARCHAR(200) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_user_portfolios_owner_name UNIQUE (owner_username, name)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_user_portfolios_owner_username
        ON user_portfolios (owner_username);
    """)

    print("Creating portfolio_holdings table...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES user_portfolios(id) ON DELETE CASCADE,
            ticker VARCHAR(20) NOT NULL,
            shares DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_portfolio_holdings_portfolio_ticker UNIQUE (portfolio_id, ticker)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_portfolio_holdings_portfolio_id
        ON portfolio_holdings (portfolio_id);
    """)

    conn.commit()

    # Verify
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name IN ('user_portfolios', 'portfolio_holdings')
        ORDER BY table_name;
    """)
    for (table_name,) in cursor.fetchall():
        print(f"✓ table {table_name} exists")

    cursor.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'portfolio_holdings' ORDER BY column_name;
    """)
    for column_name, data_type in cursor.fetchall():
        print(f"✓ portfolio_holdings.{column_name} ({data_type})")

    cursor.execute("""
        SELECT conname FROM pg_constraint
        WHERE conname IN ('uq_user_portfolios_owner_name', 'uq_portfolio_holdings_portfolio_ticker')
        ORDER BY conname;
    """)
    for (conname,) in cursor.fetchall():
        print(f"✓ constraint {conname} exists")

    cursor.close()

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
