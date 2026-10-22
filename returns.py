# One row per return, with its status and reasons as names.
# Notes for the report:
# - Outcome: 'Refunded' (status Återbetald) is money paid back, 'Rejected' (Avslagen) was
#   sent back to the customer, 'In progress' is everything still being handled.
# - Refunded is the value paid back: QuantityReturned * the price paid on the order line.
# - The column is Return.ReasonId (int, FK to ReturnReason), not a text column "Reason".
# - `Return` needs backticks since RETURN is a reserved word in MySQL.
RETURNS_QUERY = """
SELECT r.Id AS ReturnId, r.PToOId, l.OrderId, r.QuantityReturned, r.IncomeDate,
       rs.Name AS ReturnStatus,
       CASE r.ReturnStatusId WHEN 5 THEN 'Refunded' WHEN 4 THEN 'Rejected' ELSE 'In progress' END AS Outcome,
       rr.Name AS ReturnReason, rj.Name AS RejectReason,
       CASE WHEN r.ReturnStatusId = 5 THEN r.QuantityReturned * l.UnitPrice ELSE 0 END AS Refunded
FROM `Return` r
JOIN ProductToOrder l     ON l.Id = r.PToOId
LEFT JOIN ReturnStatus rs ON rs.Id = r.ReturnStatusId
LEFT JOIN ReturnReason rr ON rr.Id = r.ReasonId
LEFT JOIN RejectReason rj ON rj.Id = r.RejectReasonId
"""

# Return reasons that are about fit.
SIZE_REASONS = ("För liten", "För stor", "Fel storlek")

REASON_SUMMARY_QUERY = f"""
SELECT ReturnReason, COUNT(*) AS Returns
FROM ({RETURNS_QUERY}) returns
GROUP BY ReturnReason
ORDER BY Returns DESC
"""

OUTCOME_SUMMARY_QUERY = f"""
SELECT Outcome, RejectReason, COUNT(*) AS Returns
FROM ({RETURNS_QUERY}) returns
GROUP BY Outcome, RejectReason
"""
