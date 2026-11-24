"""Generate reproducible demo JSON and CSV datasets."""
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from models import Book, Member, IssueRecord

ROOT = Path(__file__).parent

def generate():
    data = ROOT / "data"; data.mkdir(parents=True, exist_ok=True)
    categories = ["CS", "Fiction", "Science", "History", "Mathematics", "Biography", "Business", "Art"]
    books = [Book(f"B{i:03}", f"{['Practical','Modern','Complete','Foundations of'][i%4]} {categories[i%len(categories)]} {['Systems','Stories','Research','Guide'][i%4]}", f"Author {i%13+1}", categories[i%len(categories)], f"978000{i:07d}", 5 if i == 39 else 1 + i%5, 0 if i%11 == 0 else (5 if i == 39 else 1 + i%5), date.today()-timedelta(days=i)).to_dict() for i in range(1,41)]
    books[5]["title"] = "A Remarkably Long Reference Title for Pagination and Truncation Demonstrations"
    members = [Member(f"M{i:03}", ["Aarav Mehta", "Zoë García", "Mina Patel", "Noah Kim", "Fatima Noor"][i%5] + f" {i}", f"member{i}@campus.edu", f"+91-98765{i:05d}", ["Student","Faculty","Staff"][i%3], date.today()-timedelta(days=i*4)).to_dict() for i in range(1,16)]
    issues = []
    for i in range(1,41):
        issued = date.today()-timedelta(days=(i%32)+2); due=issued+timedelta(days=14)
        ret = due if i%9==0 else (date.today() if i%3==0 else None)
        issues.append(IssueRecord(f"I{i:04}", f"B{i:03}", f"M{i%15+1:03}", issued, due, ret, 0, "Returned" if ret else ("Overdue" if due < date.today() else "Issued")).to_dict())
    for name, records in (("books",books),("members",members),("issues",issues)):
        (data/f"{name}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        fields = list(records[0]);
        with (data/f"sample_{name}.csv").open("w", newline="", encoding="utf-8") as f:
            writer=csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(records)
        (data/f"sample_{name}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    with (data/"sample_invalid.csv").open("w", newline="", encoding="utf-8") as f:
        writer=csv.DictWriter(f, fieldnames=["book_id","title","author","category","isbn","total_copies","available_copies","added_on"]); writer.writeheader()
        writer.writerow({"book_id":"B999","title":"Invalid date demo","author":"Demo","category":"CS","isbn":"9999999999999","total_copies":2,"available_copies":2,"added_on":"not-a-date"})
        writer.writerow({"book_id":"B998","title":"Duplicate ISBN demo","author":"Demo","category":"CS","isbn":"9780000000001","total_copies":1,"available_copies":1,"added_on":date.today().isoformat()})
    return len(books),len(members),len(issues)

if __name__ == "__main__": print("Generated demo data:", generate())
