# One row per order line (a product on an order), with its order, category and price info.
# Notes for the report:
# - Revenue is Quantity * UnitPrice, the price actually paid (after discounts), before refunds.
# - Cost uses Product.Cost, which has no history, so margins for older orders use today's cost.
# - Discounted = sold below the list price (ProductPrice) that applied on the order date.
# - Products belong to a subcategory (e.g. Jeans); Category is its parent (e.g. Byxor).
SALES_QUERY = """
SELECT l.Id AS LineId, o.Id AS OrderId, o.CreatedDate AS OrderDate,
       YEAR(o.CreatedDate) AS Year, MONTH(o.CreatedDate) AS Month, o.Source AS Channel,
       COALESCE(parent.Name, cat.Name) AS Category, cat.Name AS SubCategory, p.Name AS Product,
       l.Quantity, l.UnitPrice,
       l.Quantity * l.UnitPrice AS Revenue,
       l.Quantity * p.Cost AS Cost,
       l.UnitPrice < (SELECT pp.Price FROM ProductPrice pp
                      WHERE pp.ProductId = p.Id AND pp.StartDate <= o.CreatedDate
                      ORDER BY pp.StartDate DESC LIMIT 1) AS Discounted
FROM ProductToOrder l
JOIN COrder o                    ON o.Id = l.OrderId
JOIN Variant v                   ON v.Id = l.VariantId
JOIN Product p                   ON p.Id = v.ProductId
JOIN ProductCategory cat         ON cat.Id = p.CategoryId
LEFT JOIN ProductCategory parent ON parent.Id = cat.ParentCategoryId
"""
