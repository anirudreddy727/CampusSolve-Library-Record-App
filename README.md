# CampusSolve

CampusSolve is a dependency-free, menu-driven library record application for books, members, loans, returns, fines, search, reporting, CSV imports, and local JSON persistence. Python 3.10 or newer is required.

## Features

- Manage books and members with duplicate checks and active-loan deletion protection.
- Issue, return, and renew books; enforce member limits and calculate capped late fines.
- Search books, members, and issue records with paginated terminal tables.
- Recover missing or malformed JSON data safely; save changes atomically with rolling backups.
- Produce summary analytics and timestamped Markdown, text, and CSV reports.
- Import books, members, or issues from CSV with row-level rejection logs.
- Optional Tkinter GUI and optional Matplotlib category chart.

## Setup and run

No packages need installing. From this directory:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python main.py
```

The default command starts the local browser app and opens it at `http://127.0.0.1:8765`. On first launch, create an administrator account. Library members can then create a member login using their existing member ID and registered email. The server runs locally; keep its process running while using the page, and press Ctrl+C in its launch window to stop it. Use `python main.py --seed` to generate demo data into `data/`. The original terminal interface remains available with `python main.py --terminal`; `python main.py --gui` opens the optional Tkinter desktop window.

## Project structure

`main.py` launches the browser app by default and can also run the terminal or Tkinter interfaces. `webapp.py` serves the local web interface in `web/index.html`; `auth.py` stores salted password hashes and manages role sessions. `models.py`, `validators.py`, `storage.py`, and `library.py` define records, input rules, persistence, and business rules. `search.py`, `reports.py`, and `importer.py` implement queries, analytics/exports, and CSV import. `ui.py` contains terminal formatting, `gui.py` is optional, `seed_data.py` generates sample data, and `tests/` contains unit tests. Runtime records, accounts, logs, and exports are stored in `data/`, `logs/`, and `exports/`.

## Login roles

The first browser visit requires creation of the administrator account; there is no default password. Administrators can manage the full catalog, members, loans, imports, and reports. Members create their own login by matching their member ID and registered email, then can browse books and view or manage only their own loans. Account hashes are saved in `data/auth_users.json`; active sessions expire when the local server stops.

## Business rules

Student, Faculty, and Staff loans last 14, 30, and 21 days. Late fines are Rs. 2 per day, capped at the lower of Rs. 200 or the book value. Members have concurrent loan limits of 3, 5, and 4, and may not borrow when recorded returned fines exceed Rs. 100. Renewals are allowed once and only before the due date. A member cannot hold duplicate copies of one title concurrently.

## Sample data

`python main.py --seed` creates 40 books, 15 members, and 40 issue records in CSV and JSON, including varied categories, Unicode names, no-copy inventory, long titles, and overdue/on-time returns. `data/sample_invalid.csv` demonstrates invalid-date import rejection.

## Tests

Run the standard-library test suite with:

```powershell
python -m unittest discover
```

## Five-minute demo

1. Run `python main.py`; show the browser dashboard and attention panel.
2. Open Books → Add a book. Try an invalid copy count or an existing ID to show form and duplicate validation, then add a valid book.
3. Register a member, issue the book, and return it from the Loans page.
4. Open Reports & Import to show totals, fine metrics, category counts, and issue trend.
5. Stop and relaunch the app to show records persist, then export reports and open the timestamped files under `exports/`.
