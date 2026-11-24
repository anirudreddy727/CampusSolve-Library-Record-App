"""Row-validated CSV bulk import."""
import csv
from datetime import date
from pathlib import Path
from models import Book, Member, IssueRecord
from library import LibraryError

HEADERS = {"books": {"book_id", "title", "author", "category", "isbn", "total_copies", "available_copies", "added_on"}, "members": {"member_id", "name", "email", "phone", "member_type", "joined_on"}, "issues": {"issue_id", "book_id", "member_id", "issue_date", "due_date"}}


def import_csv(library, kind, filename, log_dir=None):
    if kind not in HEADERS: raise ValueError("kind must be books, members, or issues")
    errors = []; imported = 0
    with Path(filename).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not HEADERS[kind].issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV header must include: {', '.join(sorted(HEADERS[kind]))}")
        for rownum, row in enumerate(reader, 2):
            try:
                if kind == "books":
                    item = Book(row["book_id"].strip(), row["title"].strip(), row["author"].strip(), row["category"].strip(), row["isbn"].strip(), int(row["total_copies"]), int(row["available_copies"]), date.fromisoformat(row["added_on"]), float(row.get("value") or 200))
                    library.add_book(item)
                elif kind == "members":
                    item = Member(row["member_id"].strip(), row["name"].strip(), row["email"].strip(), row["phone"].strip(), row["member_type"].strip().title(), date.fromisoformat(row["joined_on"]))
                    library.add_member(item)
                else:
                    item = IssueRecord(row["issue_id"].strip(), row["book_id"].strip(), row["member_id"].strip(), date.fromisoformat(row["issue_date"]), date.fromisoformat(row["due_date"]), date.fromisoformat(row["return_date"]) if row.get("return_date") else None, float(row.get("fine_amount") or 0), row.get("status") or "Issued")
                    if any(i.issue_id == item.issue_id for i in library.issues): raise LibraryError("Duplicate issue ID")
                    library.issues.append(item); library.storage.save("issues")
                imported += 1
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f"row {rownum}, field record: {exc}")
    if errors:
        folder = Path(log_dir or Path(__file__).parent / "logs"); folder.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        path = folder / f"import_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        path.write_text("\n".join(errors) + "\n", encoding="utf-8")
    return imported, len(errors)
