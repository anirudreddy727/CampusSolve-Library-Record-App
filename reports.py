"""Summary metrics and timestamped report exports."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import csv


def summary(library):
    books, members, issues = library.books, library.members, library.issues
    active = [i for i in issues if not i.return_date]
    returned = [i for i in issues if i.return_date]
    overdue = [i for i in active if i.due_date < datetime.now().date()]
    duration = [(i.return_date - i.issue_date).days for i in returned]
    borrowed = Counter(i.book_id for i in issues)
    members_active = Counter(i.member_id for i in issues)
    return {
        "book_titles": len(books), "book_copies": sum(b.total_copies for b in books),
        "members_by_type": Counter(m.member_type for m in members), "active": len(active), "returned": len(returned), "overdue": len(overdue),
        "average_loan_days": sum(duration) / len(duration) if duration else 0,
        "average_overdue_fine": sum(i.fine_amount for i in returned if i.fine_amount) / sum(1 for i in returned if i.fine_amount) if any(i.fine_amount for i in returned) else 0,
        "average_books_per_member": len(issues) / len(members) if members else 0,
        "top_books": borrowed.most_common(5), "top_members": members_active.most_common(5),
        "categories": Counter(b.category for b in books), "fines_collected": sum(i.fine_amount for i in returned),
        "fines_outstanding": sum(i.fine_amount for i in active), "issues": issues
    }


def render(library):
    data = summary(library)
    lines = ["CampusSolve Library Summary", "=" * 30, f"Book titles: {data['book_titles']} ({data['book_copies']} copies)", f"Members: {dict(data['members_by_type'])}", f"Issues: {data['active']} active, {data['returned']} returned, {data['overdue']} overdue", f"Average loan: {data['average_loan_days']:.1f} days | Avg overdue fine: Rs. {data['average_overdue_fine']:.2f}", f"Average issues per member: {data['average_books_per_member']:.2f}", f"Fines collected: Rs. {data['fines_collected']:.2f} | Outstanding: Rs. {data['fines_outstanding']:.2f}", "", "Top borrowed books:"]
    names = {b.book_id: b.title for b in library.books}
    lines += [f"  {names.get(k,k)}: {v}" for k,v in data["top_books"]] or ["  None"]
    lines += ["", "Category distribution:"] + [f"  {cat}: {'#' * count} ({count})" for cat,count in sorted(data["categories"].items())]
    months = Counter(i.issue_date.strftime("%Y-%m") for i in data["issues"])
    lines += ["", "Monthly issue trend:"] + [f"  {month}: {'#' * count} ({count})" for month,count in sorted(months.items())]
    return "\n".join(lines)


def export_reports(library, directory=None):
    target = Path(directory or Path(__file__).parent / "exports"); target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = render(library)
    (target / f"summary_{stamp}.md").write_text("# " + report.replace("\n", "\n"), encoding="utf-8")
    (target / f"audit_{stamp}.txt").write_text(report + "\n", encoding="utf-8")
    with (target / f"summary_{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["metric", "value"])
        for line in report.splitlines(): writer.writerow([line])
    try:
        import matplotlib.pyplot as plt
        data = summary(library); plt.figure(figsize=(8, 4)); plt.bar(data["categories"].keys(), data["categories"].values()); plt.title("Books by category"); plt.tight_layout(); plt.savefig(target / f"categories_{stamp}.png"); plt.close()
    except ImportError:
        pass
    return [target / f"summary_{stamp}.md", target / f"audit_{stamp}.txt", target / f"summary_{stamp}.csv"]
