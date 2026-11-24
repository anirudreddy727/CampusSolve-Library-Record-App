"""Filter helpers for library records."""
def search_books(books, keyword="", category=None, available=None):
    key = keyword.casefold()
    return [b for b in books if (not key or key in b.title.casefold() or key in b.author.casefold() or key in b.isbn.casefold()) and (not category or b.category.casefold() == category.casefold()) and (available is None or (b.available_copies > 0) == available)]


def search_members(members, keyword="", member_type=None):
    key = keyword.casefold()
    return [m for m in members if (not key or key in m.name.casefold() or key in m.member_id.casefold()) and (not member_type or m.member_type.casefold() == member_type.casefold())]


def search_issues(issues, member_id=None, book_id=None, status=None, start=None, end=None):
    return [i for i in issues if (not member_id or i.member_id.casefold() == member_id.casefold()) and (not book_id or i.book_id.casefold() == book_id.casefold()) and (not status or i.status.casefold() == status.casefold()) and (not start or i.issue_date >= start) and (not end or i.issue_date <= end)]
