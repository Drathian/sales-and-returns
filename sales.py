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
    SUM(pto.Quantity) AS AntalPlagg
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
        "Plagg:", row["AntalPlagg"]
    )

cursor.close()
db.close()