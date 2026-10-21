# sales-and-returns

## Get started (Windows)

You need [Python](https://www.python.org/downloads/) installed. Tick **"Add python.exe to PATH"** in the installer.

Open the project folder in VS Code, open a terminal (**Terminal → New Terminal**) and run these one at a time:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python return.py
```

You only need the first and third lines once. Next time, just run:

```
.venv\Scripts\activate
python return.py
```

**If activate gives a red error about "running scripts is disabled"**, run this once and try again:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
