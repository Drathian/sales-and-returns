"""Creates the sales and returns report as a PDF. Run: python main.py

The data files each hold the SQL for one part of the database:
    sales.py     what was sold (one row per order line)
    customer.py  who placed each order
    returns.py   what was sent back
main.py joins them, works out the numbers and findings, and pdf_layout.py draws the pages.
"""
import calendar
import os
from collections import Counter
from datetime import date
from pathlib import Path

from reportlab.platypus import Spacer

from customer import CUSTOMER_QUERY
from db import fetch_all
from pdf_layout import (WIDTH, bar_chart, block, build_pdf, data_table, day, findings, kpi_tiles, line_chart,
                        pct, section, sek, sek_m, signed_pct, stacked_columns, text)
from returns import OUTCOME_SUMMARY_QUERY, REASON_SUMMARY_QUERY, RETURNS_QUERY, SIZE_REASONS
from sales import SALES_QUERY

TITLE = "Sales & Returns Report"
# Saved in the Downloads folder of whoever runs the script, like a normal download.
REPORT_FILE = Path.home() / "Downloads" / "Sales_and_Returns_Report.pdf"

# Every order line, with the customer who ordered it and its return (if it was returned).
ORDER_LINES = f"""
SELECT s.*, c.CustomerId, c.City, c.AgeGroup, c.CustomerOrderNo,
       COALESCE(r.QuantityReturned, 0) AS ItemsReturned,
       COALESCE(r.Refunded, 0) AS Refunded,
       r.IncomeDate AS ReturnDate
FROM ({SALES_QUERY}) s
JOIN ({CUSTOMER_QUERY}) c ON c.OrderId = s.OrderId
LEFT JOIN ({RETURNS_QUERY}) r ON r.PToOId = s.LineId
"""

# Everything the report measures. breakdown() calculates it for the whole period or per
# group (year, category, city...). The definitions are written out in notes_page().
MEASURES = """
    SUM(Revenue) AS Revenue,
    SUM(Refunded) AS Refunded,
    SUM(Revenue) - SUM(Refunded) AS NetRevenue,
    1 - SUM(Cost) / SUM(Revenue) AS GrossMargin,
    SUM(Discounted * Revenue) / SUM(Revenue) AS DiscountedShare,
    COUNT(DISTINCT OrderId) AS Orders,
    SUM(Revenue) / COUNT(DISTINCT OrderId) AS AvgOrderValue,
    SUM(Quantity) AS ItemsSold,
    SUM(ItemsReturned) / SUM(Quantity) AS ReturnRate,
    AVG(DATEDIFF(ReturnDate, OrderDate)) AS DaysToReturn,
    COUNT(DISTINCT CustomerId) AS Customers,
    COUNT(DISTINCT CASE WHEN CustomerOrderNo = 1 THEN CustomerId END) AS NewCustomers,
    COUNT(DISTINCT OrderId) / COUNT(DISTINCT CustomerId) AS OrdersPerCustomer,
    SUM(CASE WHEN CustomerOrderNo > 1 THEN Revenue ELSE 0 END) / SUM(Revenue) AS RepeatShare,
    MIN(OrderDate) AS FirstOrder,
    MAX(OrderDate) AS LastOrder
"""


def breakdown(by=None, where="TRUE", order="Revenue DESC"):
    """Return MEASURES with one row per value of `by`, or a single total row if `by` is None."""
    select = f"{by}, {MEASURES}" if by else MEASURES
    group = f"GROUP BY {by} ORDER BY {order}" if by else ""
    return fetch_all(f"SELECT {select} FROM ({ORDER_LINES}) order_lines WHERE {where} {group}")


def column(rows, key, scale=1):
    """One number per row, e.g. column(cities, "Revenue", 1e-6) for SEK millions."""
    return [row[key] * scale for row in rows]


def is_partial(year, latest):
    """True for the last year if the data stops before 31 December."""
    return year == latest.year and (latest.month, latest.day) != (12, 31)


def year_label(year, latest):
    return f"{year}*" if is_partial(year, latest) else str(year)


def partial_note(latest):
    return f"* {latest.year} runs to {day(latest)}." if is_partial(latest.year, latest) else ""


def summary_page(total, years, key_findings):
    """Title, headline numbers and the key findings."""
    latest = total["LastOrder"]
    return [
        text("CLOTHINGSHOP  ·  ANALYTICS REPORT", "overline"),
        text(TITLE, "title"),
        text(f"Orders, returns and customers from {day(total['FirstOrder'])} to {day(latest)}", "subtitle"),
        text(f"Generated {day(date.today())} from the clothingshop database", "meta"),
        Spacer(1, 18),
        kpi_tiles([
            ("Revenue", sek_m(total["Revenue"]), f"{sek_m(total['NetRevenue'])} after refunds"),
            (f"Revenue growth {latest.year}", signed_pct(years[-1]["Growth"]), f"vs the same dates in {latest.year - 1}"),
            ("Orders", f"{total['Orders']:,}", f"{sek(total['AvgOrderValue'])} per order on average"),
            ("Customers", f"{total['Customers']:,}", f"{total['OrdersPerCustomer']:.1f} orders per customer"),
            ("Return rate", pct(total["ReturnRate"]), f"of items sold, {sek_m(total['Refunded'])} refunded"),
            ("Gross margin", pct(total["GrossMargin"]), "at current product costs"),
        ]),
        Spacer(1, 14),
        *section("Key findings"),
        findings(key_findings),
    ]


def sales_section(total, years):
    """Revenue over time and by category, discount and channel."""
    latest = total["LastOrder"]
    months = breakdown("Year, Month", order="Year, Month")
    categories = breakdown("Category")
    discounts = {row["Discounted"]: row for row in breakdown("Discounted")}
    channels = breakdown("Channel")

    full_years = [row for row in years if not is_partial(row["Year"], latest)]
    first, last, this_year = full_years[0], full_years[-1], years[-1]
    growth = (
        f"Revenue {signed_pct(last['Revenue'] / first['Revenue'] - 1)} from {first['Year']} to {last['Year']}",
        f"Revenue went from {sek_m(first['Revenue'])} in {first['Year']} to {sek_m(last['Revenue'])} in "
        f"{last['Year']}. So far in {latest.year} it is {signed_pct(this_year['Growth'])} compared with the same "
        f"dates in {latest.year - 1} (orders {signed_pct(this_year['Orders'] / this_year['Previous']['Orders'] - 1)}, "
        f"average order value "
        f"{signed_pct(this_year['AvgOrderValue'] / this_year['Previous']['AvgOrderValue'] - 1)}).",
    )

    full_price, discounted = discounts[0], discounts[1]
    discounted_by_month = Counter()
    for row in months:
        discounted_by_month[row["Month"]] += row["Revenue"] * (row["DiscountedShare"] or 0)
    discount_month, discounted_revenue = discounted_by_month.most_common(1)[0]
    month_name = calendar.month_name[discount_month]
    discount = (
        f"Discounted items: {pct(discounted['ReturnRate'])} returned vs {pct(full_price['ReturnRate'])} at full price",
        f"{pct(discounted_revenue / discounted['Revenue'], 0)} of discounted sales happen in {month_name}. Items "
        f"sold below list price earn a gross margin of {pct(discounted['GrossMargin'])}, against "
        f"{pct(full_price['GrossMargin'])} at full price.",
    )

    most_returned = max(categories, key=lambda row: row["ReturnRate"])
    best_margin = max(categories, key=lambda row: row["GrossMargin"])
    by_new_customers = sorted(channels, key=lambda row: row["NewCustomers"], reverse=True)
    top, second, weakest = by_new_customers[0], by_new_customers[1], by_new_customers[-1]

    def year_cells(label, row, growth_text):
        return [label, f"{row['Revenue'] / 1e6:.1f}", growth_text, f"{row['Orders']:,}",
                f"{row['AvgOrderValue']:,.0f}", f"{row['ItemsSold']:,.0f}", pct(row["ReturnRate"]),
                f"{row['Refunded'] / 1e6:.1f}", f"{row['NetRevenue'] / 1e6:.1f}"]

    year_rows = [year_cells(year_label(row["Year"], latest), row,
                            signed_pct(row["Growth"]) if "Growth" in row else "–") for row in years]
    year_rows.append(year_cells("Total", total, ""))

    pages = [
        *section("Sales"),
        block(*growth,
              line_chart([date(row["Year"], row["Month"], 1) for row in months], column(months, "Revenue", 1e-6),
                         "Revenue per month, SEK M", [row["Month"] == discount_month for row in months],
                         f"{month_name}, the month with the most discounted sales"),
              caption=f"Revenue is what customers paid after discounts, before refunds. The last month runs to "
                      f"{day(latest)}."),
        block("Year by year", None,
              data_table(["Year", "Revenue, SEK M", "Growth", "Orders", "Avg order, SEK", "Items sold",
                          "Return rate", "Refunded, SEK M", "Net revenue, SEK M"],
                         year_rows, [WIDTH * 0.12] + [WIDTH * 0.11] * 8,
                         bold_cells=[(col, len(year_rows)) for col in range(9)]),
              caption=f"Growth is compared with the same dates the year before. {partial_note(latest)}"),
        block(f"{categories[0]['Category']} sells the most, {most_returned['Category']} is returned most often",
              f"{most_returned['Category']} has a return rate of {pct(most_returned['ReturnRate'])} against "
              f"{pct(total['ReturnRate'])} overall. {best_margin['Category']} has the highest gross margin "
              f"({pct(best_margin['GrossMargin'])}).",
              bar_chart([row["Category"] for row in categories], [
                  ("Revenue, SEK M", column(categories, "Revenue", 1e-6), "{:.1f}"),
                  ("Gross margin, %", column(categories, "GrossMargin", 100), "{:.1f}%"),
                  ("Return rate, % (line = average)", column(categories, "ReturnRate", 100), "{:.1f}%",
                   100 * total["ReturnRate"]),
              ]),
              caption="Gross margin uses today's product costs. Return rate = items returned ÷ items sold."),
        block(*discount,
              bar_chart(["Full price", "Discounted"], [
                  ("Share of revenue, %", column((full_price, discounted), "Revenue", 100 / total["Revenue"]),
                   "{:.1f}%"),
                  ("Gross margin, %", column((full_price, discounted), "GrossMargin", 100), "{:.1f}%"),
                  ("Return rate, %", column((full_price, discounted), "ReturnRate", 100), "{:.1f}%"),
              ]),
              caption="Discounted = sold below the list price that applied on the order date."),
        block(f"{top['Channel']} and {second['Channel']} bring in "
              f"{pct((top['NewCustomers'] + second['NewCustomers']) / total['NewCustomers'], 0)} of new customers",
              f"{weakest['Channel']} accounts for {pct(weakest['Revenue'] / total['Revenue'], 0)} of revenue but "
              f"{pct(weakest['NewCustomers'] / total['NewCustomers'], 0)} of new customers.",
              bar_chart([row["Channel"] for row in channels], [
                  ("Revenue, SEK M", column(channels, "Revenue", 1e-6), "{:.1f}"),
                  ("New customers won", column(channels, "NewCustomers"), "{:,.0f}"),
              ]),
              caption="Channel = where the order came from. A new customer counts for the channel of their "
                      "first order."),
    ]
    return [growth, discount], pages


def returns_section(total):
    """Why items are sent back, which items, and what happens to the returns."""
    reasons = fetch_all(REASON_SUMMARY_QUERY)
    outcomes = fetch_all(OUTCOME_SUMMARY_QUERY)
    subcategories = breakdown("Category, SubCategory", order="ReturnRate DESC")[:10]

    return_count = sum(row["Returns"] for row in reasons)
    size_returns = sum(row["Returns"] for row in reasons if row["ReturnReason"] in SIZE_REASONS)
    fit = (
        f"{pct(size_returns / return_count, 0)} of returns are about size",
        f"Items are most often sent back because they are too small, too large or the wrong size. The most "
        f"common single reason is “{reasons[0]['ReturnReason']}” ({pct(reasons[0]['Returns'] / return_count)}).",
    )

    per_outcome, rejections = Counter(), Counter()
    for row in outcomes:
        per_outcome[row["Outcome"]] += row["Returns"]
        if row["RejectReason"]:
            rejections[row["RejectReason"]] += row["Returns"]
    top_rejection, top_rejection_count = rejections.most_common(1)[0]
    handling = (
        f"{pct(per_outcome['Refunded'] / return_count, 0)} of returns are refunded",
        f"{pct(per_outcome['Rejected'] / return_count)} are rejected, most often because of “{top_rejection}” "
        f"({top_rejection_count:,} of {per_outcome['Rejected']:,}). Returns arrive "
        f"{total['DaysToReturn']:.0f} days after the order on average.",
    )

    worst = subcategories[0]
    pages = [
        *section("Returns"),
        block(*fit,
              bar_chart([row["ReturnReason"] for row in reasons],
                        [("Share of returns, %", column(reasons, "Returns", 100 / return_count), "{:.1f}%")],
                        highlight=SIZE_REASONS),
              caption=f"Blue = size-related reasons ({', '.join(SIZE_REASONS)})."),
        block(f"{worst['SubCategory']}, {subcategories[1]['SubCategory']} and {subcategories[2]['SubCategory']} "
              f"are returned most often",
              f"{worst['SubCategory']} ({worst['Category']}) has a return rate of {pct(worst['ReturnRate'])}, "
              f"{worst['ReturnRate'] / total['ReturnRate']:.1f} times the average of {pct(total['ReturnRate'])}.",
              bar_chart([f"{row['SubCategory']} ({row['Category']})" for row in subcategories],
                        [("Return rate, % (line = average)", column(subcategories, "ReturnRate", 100), "{:.1f}%",
                          100 * total["ReturnRate"])]),
              caption="The 10 subcategories with the highest return rate (items returned ÷ items sold)."),
        block(*handling,
              kpi_tiles([(outcome, f"{per_outcome[outcome]:,}", f"{pct(per_outcome[outcome] / return_count)} of returns")
                         for outcome in ("Refunded", "Rejected", "In progress")]),
              Spacer(1, 8),
              data_table(["Why returns were rejected", "Returns", "Share of rejections"],
                         [[reason, f"{count:,}", pct(count / per_outcome["Rejected"])]
                          for reason, count in rejections.most_common()],
                         [WIDTH * 0.6, WIDTH * 0.2, WIDTH * 0.2])),
    ]
    return [fit, handling], pages


def customers_section(total, years):
    """New and returning customers, cities and age groups."""
    latest = total["LastOrder"]
    cities = breakdown("City")
    city_categories = breakdown("City, Category")
    ages = breakdown("AgeGroup", order="AgeGroup")

    returning = [row["Customers"] - row["NewCustomers"] for row in years]
    repeat = (
        f"Repeat orders bring in {pct(total['RepeatShare'], 0)} of revenue",
        f"Customers place {total['OrdersPerCustomer']:.1f} orders on average. In {latest.year}, "
        f"{pct(returning[-1] / years[-1]['Customers'], 0)} of the customers who ordered had also ordered in an "
        f"earlier year.",
    )

    first, second = cities[0], cities[1]
    most_often = max(cities, key=lambda row: row["OrdersPerCustomer"])
    least_often = min(cities, key=lambda row: row["OrdersPerCustomer"])
    city_finding = (
        f"{first['City']} and {second['City']} account for "
        f"{pct((first['Revenue'] + second['Revenue']) / total['Revenue'], 0)} of revenue",
        f"Customers in {most_often['City']} order most often ({most_often['OrdersPerCustomer']:.1f} orders each), "
        f"customers in {least_often['City']} least often ({least_often['OrdersPerCustomer']:.1f}).",
    )

    # Each category's share of a city's revenue, and the category where cities differ the most
    city_names = [row["City"] for row in cities]
    city_revenue = {row["City"]: row["Revenue"] for row in cities}
    category_revenue = Counter()
    for row in city_categories:
        category_revenue[row["Category"]] += row["Revenue"]
    category_names = [name for name, _ in category_revenue.most_common()]
    share = Counter({(row["City"], row["Category"]): row["Revenue"] / city_revenue[row["City"]]
                     for row in city_categories})

    def spread(name):
        return max(share[city, name] for city in city_names) - min(share[city, name] for city in city_names)

    varies = max(category_names, key=spread)
    high = max(city_names, key=lambda city: share[city, varies])
    low = min(city_names, key=lambda city: share[city, varies])
    mix_rows = [[city] + [pct(share[city, name]) for name in category_names] + [f"{city_revenue[city] / 1e6:.1f}"]
                for city in city_names]
    mix_bold = [(col, city_names.index(max(city_names, key=lambda city: share[city, name])) + 1)
                for col, name in enumerate(category_names, start=1)]

    biggest = max(ages, key=lambda row: row["Revenue"])
    lowest_value = min(ages, key=lambda row: row["AvgOrderValue"])
    highest_value = max(ages, key=lambda row: row["AvgOrderValue"])

    pages = [
        *section("Customers"),
        block(*repeat,
              stacked_columns([year_label(row["Year"], latest) for row in years],
                              [("New customers", column(years, "NewCustomers")), ("Returning customers", returning)],
                              "Customers who ordered, per year"),
              caption=f"New = first order that year. Returning = had also ordered in an earlier year. "
                      f"{partial_note(latest)}"),
        block(*city_finding,
              bar_chart(city_names, [("Revenue, SEK M", column(cities, "Revenue", 1e-6), "{:.1f}"),
                                     ("Orders per customer", column(cities, "OrdersPerCustomer"), "{:.1f}")])),
        block(f"{varies} matters most in {high}: {pct(share[high, varies])} of revenue vs "
              f"{pct(share[low, varies])} in {low}", None,
              data_table(["City"] + category_names + ["Revenue, SEK M"], mix_rows,
                         [WIDTH * 0.13] + [WIDTH * 0.69 / len(category_names)] * len(category_names) + [WIDTH * 0.18],
                         bold_cells=mix_bold),
              caption="Each category's share of the city's revenue. Bold = the city where the category's share is "
                      "highest."),
        block(f"{biggest['AgeGroup']} year-olds bring in the most revenue",
              f"They account for {pct(biggest['Revenue'] / total['Revenue'], 0)} of revenue. Average order value "
              f"ranges from {sek(lowest_value['AvgOrderValue'])} ({lowest_value['AgeGroup']}) to "
              f"{sek(highest_value['AvgOrderValue'])} ({highest_value['AgeGroup']}).",
              bar_chart([row["AgeGroup"] for row in ages],
                        [("Revenue, SEK M", column(ages, "Revenue", 1e-6), "{:.1f}"),
                         ("Average order value, SEK", column(ages, "AvgOrderValue"), "{:,.0f}")]),
              caption="Age in the year of the order, worked out from the customer's birth year."),
    ]
    return [repeat, city_finding], pages


def notes_page(total):
    """How the numbers in the report are defined."""
    terms = [
        ("Period", f"All orders in the database, {day(total['FirstOrder'])} to {day(total['LastOrder'])}. "
                   f"A year that isn't over is compared with the same dates the year before."),
        ("Revenue", "Quantity × the price the customer paid (after discounts), before refunds."),
        ("Refunds", "Returns with status Återbetald (refunded), valued at the price paid. Rejected returns and "
                    "returns still being handled are not deducted."),
        ("Net revenue", "Revenue minus refunds."),
        ("Return rate", "Items returned ÷ items sold. A return counts towards the year and category of the "
                        "original order."),
        ("Gross margin", "(Revenue - product cost) ÷ revenue. Only today's product cost is stored, so margins "
                         "for earlier years are approximate."),
        ("Discounted", "Sold below the list price (ProductPrice) that applied on the order date."),
        ("Size-related returns", f"The return reasons {', '.join(SIZE_REASONS)}."),
        ("New and returning customers", "New: the customer's first order was that year. Returning: the customer "
                                        "had also ordered in an earlier year."),
        ("Repeat orders", "Every order after a customer's first one."),
        ("Age group", "The customer's age in the year of the order, from their birth year."),
        ("Source", "The clothingshop database (MariaDB): orders, order lines, products, categories, prices, "
                   "customers and returns."),
    ]
    return [*section("About the data"),
            data_table(["Term", "Definition"], [[text(term, "term"), text(definition)] for term, definition in terms],
                       [WIDTH * 0.26, WIDTH * 0.74], numbers=False)]


def main():
    print("Fetching data from the database, this takes about half a minute...")
    total = breakdown()[0]
    latest = total["LastOrder"]
    years = breakdown("Year", order="Year")
    same_dates = breakdown("Year", where=f"DATE_FORMAT(OrderDate, '%m-%d') <= '{latest:%m-%d}'", order="Year")
    # Compare each year with the year before. A year that isn't over yet is compared with
    # the same dates the year before.
    for i in range(1, len(years)):
        years[i]["Previous"] = same_dates[i - 1] if is_partial(years[i]["Year"], latest) else years[i - 1]
        years[i]["Growth"] = years[i]["Revenue"] / years[i]["Previous"]["Revenue"] - 1

    sales_findings, sales_pages = sales_section(total, years)
    returns_findings, returns_pages = returns_section(total)
    customer_findings, customer_pages = customers_section(total, years)

    print("Drawing the PDF...")
    story = (summary_page(total, years, sales_findings + returns_findings + customer_findings)
             + sales_pages + returns_pages + customer_pages + notes_page(total))
    try:
        build_pdf(str(REPORT_FILE), story, TITLE)
    except PermissionError:
        print(f"Couldn't save {REPORT_FILE}. Close the PDF if it's open and run again.")
        return
    print(f"Saved the report as {REPORT_FILE}")
    if hasattr(os, "startfile"):  # Windows: open it, like double-clicking the file
        os.startfile(REPORT_FILE)


if __name__ == "__main__":
    main()
