"""Library rules and operations."""
from datetime import date, timedelta
from models import Book, Member, IssueRecord

FINE_PER_DAY = 2.0
MAX_FINE = 200.0
UNPAID_FINE_LIMIT = 100.0
LOAN_DAYS = {"Student": 14, "Faculty": 30, "Staff": 21}


class LibraryError(ValueError):
    """A business rule prevented an operation."""


class Library:
    def __init__(self, storage):
        self.storage = storage
        self.books = storage.records["books"]
        self.members = storage.records["members"]
        self.issues = storage.records["issues"]

    def _save(self, group):
        self.storage.save(group)

    def add_book(self, book):
        if any(b.book_id.casefold() == book.book_id.casefold() for b in self.books): raise LibraryError("Book ID already exists.")
        if book.isbn and any(b.isbn == book.isbn for b in self.books): raise LibraryError("ISBN already exists.")
        if not 1 <= book.total_copies <= 100 or not 0 <= book.available_copies <= book.total_copies: raise LibraryError("Copy counts are invalid.")
        self.books.append(book); self._save("books")

    def update_book(self, book_id, **changes):
        book = self.find_book(book_id)
        for key, value in changes.items():
            if key in {"book_id", "isbn"} and value != getattr(book, key) and any(getattr(b, key) == value for b in self.books): raise LibraryError(f"Duplicate {key}.")
            if key == "total_copies" and value < book.total_copies - book.available_copies: raise LibraryError("Total copies cannot be below copies currently issued.")
            if key == "total_copies":
                book.available_copies += value - book.total_copies
            setattr(book, key, value)
        self._save("books"); return book

    def find_book(self, book_id):
        return next((b for b in self.books if b.book_id.casefold() == book_id.casefold()), None) or (_ for _ in ()).throw(LibraryError("Book not found."))

    def add_member(self, member):
        if any(m.member_id.casefold() == member.member_id.casefold() for m in self.members): raise LibraryError("Member ID already exists.")
        if member.member_type not in LOAN_DAYS: raise LibraryError("Invalid member type.")
        self.members.append(member); self._save("members")

    def find_member(self, member_id):
        return next((m for m in self.members if m.member_id.casefold() == member_id.casefold()), None) or (_ for _ in ()).throw(LibraryError("Member not found."))

    def update_member(self, member_id, **changes):
        member = self.find_member(member_id)
        if "member_id" in changes and any(m.member_id == changes["member_id"] for m in self.members): raise LibraryError("Member ID already exists.")
        for k, v in changes.items(): setattr(member, k, v)
        if "member_type" in changes: member.max_books = {"Student": 3, "Faculty": 5, "Staff": 4}[member.member_type]
        self._save("members"); return member

    def active_for(self, member_id):
        return [i for i in self.issues if i.member_id == member_id and i.return_date is None]

    def issue_book(self, book_id, member_id, today=None):
        today = today or date.today(); book = self.find_book(book_id); member = self.find_member(member_id)
        active = self.active_for(member_id)
        outstanding = sum(i.fine_amount for i in self.issues if i.member_id == member_id and i.return_date is not None)
        if book.available_copies <= 0: raise LibraryError("No copies are available.")
        if len(active) >= member.max_books: raise LibraryError("Member has reached their borrowing limit.")
        if outstanding > UNPAID_FINE_LIMIT: raise LibraryError("Member has unpaid fines above Rs. 100.")
        if any(i.book_id == book_id for i in active): raise LibraryError("Member already has this book issued.")
        number = max([int(i.issue_id[1:]) for i in self.issues if i.issue_id.startswith("I") and i.issue_id[1:].isdigit()] or [0]) + 1
        record = IssueRecord(f"I{number:04d}", book_id, member_id, today, today + timedelta(days=LOAN_DAYS[member.member_type]))
        book.available_copies -= 1; self.issues.append(record); self._save("books"); self._save("issues"); return record

    @staticmethod
    def calculate_fine(due_date, returned_on, cap=MAX_FINE):
        return min(max(0, (returned_on - due_date).days) * FINE_PER_DAY, cap)

    def return_book(self, issue_id, today=None):
        record = next((i for i in self.issues if i.issue_id.casefold() == issue_id.casefold()), None)
        if not record or record.return_date: raise LibraryError("Active issue record not found.")
        today = today or date.today()
        if today < record.issue_date: raise LibraryError("Return date cannot be before issue date.")
        book = self.find_book(record.book_id)
        record.return_date = today; record.fine_amount = self.calculate_fine(record.due_date, today, min(MAX_FINE, book.value)); record.status = "Returned"
        book.available_copies = min(book.total_copies, book.available_copies + 1)
        self._save("books"); self._save("issues"); return record

    def renew(self, issue_id, today=None):
        issue = next((i for i in self.issues if i.issue_id.casefold() == issue_id.casefold()), None)
        if not issue or issue.return_date: raise LibraryError("Active issue record not found.")
        today = today or date.today()
        if issue.due_date < today or issue.renewals >= 1: raise LibraryError("Overdue or already renewed; renewal unavailable.")
        member = self.find_member(issue.member_id); issue.due_date += timedelta(days=LOAN_DAYS[member.member_type]); issue.renewals += 1
        self._save("issues"); return issue

    def delete_book(self, book_id):
        book = self.find_book(book_id)
        if any(i.book_id == book.book_id and not i.return_date for i in self.issues): raise LibraryError("Book has active issues.")
        self.books.remove(book); self._save("books")

    def delete_member(self, member_id):
        member = self.find_member(member_id)
        if self.active_for(member_id): raise LibraryError("Member has active issues.")
        self.members.remove(member); self._save("members")
