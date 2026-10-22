from decimal import Decimal

import mysql.connector

def get_connection():
    """Open a new connection to the clothingshop database."""
    return mysql.connector.connect(
        host="comet-direct.usbx.me",
        port=17815,
        user="yhstudent",
        password="darthvader123!",
        database="clothingshop",
        collation="utf8mb4_general_ci",
        ssl_disabled=True
    )


def fetch_all(query):
    """Run a query and return the rows as a list of dicts.
    Decimal numbers become floats so they work directly in charts and calculations."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query)
        return [{key: float(value) if isinstance(value, Decimal) else value for key, value in row.items()}
                for row in cur.fetchall()]
    finally:
        conn.close()
