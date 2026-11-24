"""Fault-tolerant JSON persistence for CampusSolve."""
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from models import Book, Member, IssueRecord

DATA_DIR = Path(__file__).parent / "data"
FILES = {"books": Book, "members": Member, "issues": IssueRecord}
Path(__file__).parent.joinpath("logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=Path(__file__).parent / "logs" / "audit.log", level=logging.INFO, format="%(asctime)s %(message)s")


class Storage:
    def __init__(self, directory=DATA_DIR):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.records = {name: [] for name in FILES}
        self.warnings = []
        for name in FILES:
            self.records[name] = self.load(name)

    def load(self, name):
        path = self.directory / f"{name}.json"
        cls = FILES[name]
        if not path.exists():
            self._write(name, [])
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("top-level JSON must be a list")
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            if path.exists():
                stamp = datetime.now().strftime("%Y%m%d%H%M%S")
                try:
                    path.replace(path.with_name(f"{name}.corrupt.{stamp}.json"))
                except OSError:
                    pass
            self.warnings.append(f"{name}.json was unreadable; started with an empty dataset ({exc}).")
            self._write(name, [])
            return []
        valid = []
        required = {"books": {"book_id", "title", "author", "category", "isbn", "total_copies", "available_copies", "added_on"}, "members": {"member_id", "name", "email", "phone", "member_type", "joined_on"}, "issues": {"issue_id", "book_id", "member_id", "issue_date", "due_date"}}[name]
        for index, row in enumerate(raw, 1):
            try:
                if not isinstance(row, dict) or not required.issubset(row):
                    raise ValueError("missing required fields")
                valid.append(cls.from_dict(row))
            except (KeyError, TypeError, ValueError) as exc:
                logging.warning("Skipped invalid %s row %s: %s", name, index, exc)
                self.warnings.append(f"Skipped invalid {name} row {index}.")
        if name == "issues":
            today = date.today()
            for issue in valid:
                if issue.return_date is None and issue.due_date < today:
                    issue.status = "Overdue"
        return valid

    def _write(self, name, rows):
        path = self.directory / f"{name}.json"
        temp = path.with_suffix(".json.tmp")
        try:
            if path.exists():
                backup = path.with_suffix(".json.bak")
                backup.write_bytes(path.read_bytes())
            temp.write_text(json.dumps([row.to_dict() for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:
            self.warnings.append(f"Could not save {name}: {exc}")
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def save(self, name):
        self._write(name, self.records[name])

    def save_all(self):
        for name in FILES:
            self.save(name)
