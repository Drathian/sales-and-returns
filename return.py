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


# One row per return, with the returned order line and the status/reason names joined on.
# Notes for the report:
# - Only ReturnStatusId 5 (Återbetald) is money refunded. 4 (Avslagen) was rejected and
#   sent back to the customer (only these have BackToCDate/RejectReasonId); 1-3 are
#   still being handled.
# - The column is Return.ReasonId (int, FK to ReturnReason), not a text column "Reason".
# - `Return` needs backticks since RETURN is a reserved word in MySQL.
RETURNS_QUERY = """
SELECT r.Id AS ReturnId, r.PToOId, r.QuantityReturned,
       r.IncomeDate, r.BackToCDate, r.BackToCMessage, r.HandlerNote,
       rs.Name AS ReturnStatus, rr.Name AS ReturnReason, rj.Name AS RejectReason,
       l.OrderId, l.VariantId, l.Name AS Product, l.Quantity AS QuantityOrdered, l.UnitPrice,
       r.QuantityReturned * l.UnitPrice AS ReturnedValue,
       CASE WHEN r.ReturnStatusId = 5 THEN r.QuantityReturned * l.UnitPrice ELSE 0 END AS Refunded
FROM `Return` r
JOIN ProductToOrder l     ON l.Id = r.PToOId
LEFT JOIN ReturnStatus rs ON rs.Id = r.ReturnStatusId
LEFT JOIN ReturnReason rr ON rr.Id = r.ReasonId
LEFT JOIN RejectReason rj ON rj.Id = r.RejectReasonId
"""

YEARLY_SUMMARY_QUERY = f"""
SELECT YEAR(IncomeDate) AS Year,
       COUNT(*) AS Returns,
       SUM(QuantityReturned) AS ItemsReturned,
       SUM(ReturnStatus = 'Återbetald') AS Refunded,
       SUM(ReturnStatus = 'Avslagen') AS Rejected,
       SUM(ReturnStatus NOT IN ('Återbetald', 'Avslagen')) AS Pending,
       SUM(Refunded) AS RefundedValue
FROM ({RETURNS_QUERY}) returns
GROUP BY Year
ORDER BY Year
"""

REASON_SUMMARY_QUERY = f"""
SELECT ReturnReason, COUNT(*) AS Returns, SUM(QuantityReturned) AS ItemsReturned,
       SUM(Refunded) AS RefundedValue
FROM ({RETURNS_QUERY}) returns
GROUP BY ReturnReason
ORDER BY Returns DESC
"""


def fetch_all(query):
    """Run a query and return the rows as a list of dicts."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query)
        return cur.fetchall()
    finally:
        conn.close()


def get_return_rows():
    """Return every return with its order line, status and reasons."""
    return fetch_all(RETURNS_QUERY)


def get_yearly_summary():
    """Return number of returns, outcome and refunded value per year (by IncomeDate)."""
    return fetch_all(YEARLY_SUMMARY_QUERY)


def get_reason_summary():
    """Return number of returns and refunded value per return reason."""
    return fetch_all(REASON_SUMMARY_QUERY)


if __name__ == "__main__":
    print(f"{'Year':<6}{'Returns':>9}{'Items':>8}{'Refunded':>10}{'Rejected':>10}{'Pending':>9}{'Refunded kr':>14}")
    for row in get_yearly_summary():
        print(f"{row['Year']:<6}{row['Returns']:>9}{row['ItemsReturned']:>8}{row['Refunded']:>10}"
              f"{row['Rejected']:>10}{row['Pending']:>9}{row['RefundedValue']:>14,.0f}")

    print()
    print(f"{'Reason':<28}{'Returns':>9}{'Items':>8}{'Refunded kr':>14}")
    for row in get_reason_summary():
        print(f"{row['ReturnReason']:<28}{row['Returns']:>9}{row['ItemsReturned']:>8}{row['RefundedValue']:>14,.0f}")
