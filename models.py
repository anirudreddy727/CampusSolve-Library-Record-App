"""Serializable records used by CampusSolve."""
from dataclasses import dataclass
from datetime import date


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    category: str
    isbn: str
    total_copies: int
    available_copies: int
    added_on: date
    value: float = 200.0

    def to_dict(self):
        return {**self.__dict__, "added_on": self.added_on.isoformat()}

    @classmethod
    def from_dict(cls, data):
        row = dict(data)
        row["added_on"] = date.fromisoformat(row["added_on"])
        return cls(**row)


@dataclass
class Member:
    member_id: str
    name: str
    email: str
    phone: str
    member_type: str
    joined_on: date
    max_books: int | None = None

    def __post_init__(self):
        limits = {"Student": 3, "Faculty": 5, "Staff": 4}
        if self.max_books is None:
            self.max_books = limits.get(self.member_type, 3)

    def to_dict(self):
        return {**self.__dict__, "joined_on": self.joined_on.isoformat()}

    @classmethod
    def from_dict(cls, data):
        row = dict(data)
        row["joined_on"] = date.fromisoformat(row["joined_on"])
        return cls(**row)


@dataclass
class IssueRecord:
    issue_id: str
    book_id: str
    member_id: str
    issue_date: date
    due_date: date
    return_date: date | None = None
    fine_amount: float = 0.0
    status: str = "Issued"
    renewals: int = 0

    def to_dict(self):
        return {**self.__dict__, "issue_date": self.issue_date.isoformat(), "due_date": self.due_date.isoformat(), "return_date": self.return_date.isoformat() if self.return_date else None}

    @classmethod
    def from_dict(cls, data):
        row = dict(data)
        for key in ("issue_date", "due_date", "return_date"):
            row[key] = date.fromisoformat(row[key]) if row.get(key) else None
        return cls(**row)
