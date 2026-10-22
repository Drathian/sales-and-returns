# sales-and-returns

Creates an analytics report (PDF) on sales, returns and customers from the clothingshop database.

## Files

| File | What it does |
|---|---|
| `main.py` | Joins the data, works out the numbers and findings, and saves the PDF |
| `sales.py` | SQL for what was sold (one row per order line) |
| `customer.py` | SQL for who placed each order |
| `returns.py` | SQL for what was returned |
| `db.py` | Database connection, used by every file |
| `pdf_layout.py` | How the PDF looks: colours, charts and tables |

## Get started (Windows)

You need [Python](https://www.python.org/downloads/) installed. Tick **"Add python.exe to PATH"** in the installer.

Open the project folder in VS Code, open a terminal (**Terminal → New Terminal**) and run these one at a time:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

`python main.py` takes about half a minute, saves the report as `Sales_and_Returns_Report.pdf` in your **Downloads** folder and opens it. Close the PDF before running it again, otherwise Windows won't let Python replace it.

You only need the first and third lines once. Next time, just run:

```
.venv\Scripts\activate
python main.py
```

**If activate gives a red error about "running scripts is disabled"**, run this once and try again:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
