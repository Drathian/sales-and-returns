import mysql.connector
from getpass import getpass

db = mysql.connector.connect(
    host="comet-direct.usbx.me",
    port=17815,
    user="yhstudent",
    password=getpass("Databaslösenord: "),
    database="clothingshop",
    collation="utf8mb4_general_ci"
)

cursor = db.cursor(dictionary=True)
print("Ansluten till MySQL:", db.is_connected())

# HÄR börjar SQL-frågan
query = """
SELECT
    c.City AS Stad,
    pc.Name AS Kategori,
    COUNT(DISTINCT o.Id) AS AntalOrdrar,
    SUM(pto.Quantity) AS AntalPlagg,
SUM(pto.Quantity * pto.UnitPrice) AS Forsaljning
FROM COrder o
JOIN Customer c ON c.Id = o.CustomerId
JOIN ProductToOrder pto ON pto.OrderId = o.Id
JOIN Variant v ON v.Id = pto.VariantId
JOIN Product p ON p.Id = v.ProductId
JOIN ProductCategory pc ON pc.Id = p.CategoryId
WHERE o.CreatedDate >= '2022-01-06'
  AND o.CreatedDate < '2026-08-27'
GROUP BY c.City, pc.Id, pc.Name
ORDER BY Stad, AntalPlagg DESC;
"""

# Kör frågan
cursor.execute(query)

# Skriv ut resultatet
for row in cursor.fetchall():
    print(
        row["Stad"],
        row["Kategori"],
        "Ordrar:", row["AntalOrdrar"],
        "Plagg:", row["AntalPlagg"],
        "Försäljning:", f'{row["Forsaljning"]:,.2f}'
    )
# Total försäljning under perioden
query_total = """
SELECT
    COUNT(DISTINCT o.Id) AS AntalOrdrar,
    SUM(pto.Quantity) AS AntalPlagg,
    SUM(pto.Quantity * pto.UnitPrice) AS TotalForsaljning
FROM COrder o
JOIN ProductToOrder pto ON pto.OrderId = o.Id
WHERE o.CreatedDate >= '2022-01-06'
  AND o.CreatedDate < '2026-08-27';
"""

cursor.execute(query_total)
total = cursor.fetchone()

print("\nTOTALT FÖR PERIODEN")
print("Antal ordrar:", total["AntalOrdrar"])
print("Antal plagg:", total["AntalPlagg"])
print("Total försäljning:", total["TotalForsaljning"])

cursor.close()
db.close()