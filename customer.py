# One row per order, with the customer who placed it.
# Notes for the report:
# - Customer is only linked to sales and returns through COrder, so join on OrderId.
# - AgeAtOrder is how old the customer was the year they ordered. Only BirthYear is
#   stored, so it can be off by one.
# - CustomerOrderNo is the customer's 1st, 2nd, 3rd... order. 1 = new customer.
# - Name, Address and Email are left out since the report only counts customers.
CUSTOMER_QUERY = """
SELECT OrderId, CustomerId, City, AgeAtOrder,
       CASE
           WHEN AgeAtOrder < 25 THEN '18-24'
           WHEN AgeAtOrder < 35 THEN '25-34'
           WHEN AgeAtOrder < 45 THEN '35-44'
           WHEN AgeAtOrder < 55 THEN '45-54'
           WHEN AgeAtOrder < 65 THEN '55-64'
           ELSE '65+'
       END AS AgeGroup,
       CustomerOrderNo
FROM (
    SELECT o.Id AS OrderId, c.Id AS CustomerId, c.City,
           YEAR(o.CreatedDate) - c.BirthYear AS AgeAtOrder,
           ROW_NUMBER() OVER (PARTITION BY c.Id ORDER BY o.CreatedDate, o.Id) AS CustomerOrderNo
    FROM COrder o
    JOIN Customer c ON c.Id = o.CustomerId
) orders
"""
