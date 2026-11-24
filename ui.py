"""Terminal display helpers."""
import os

COLOR = bool(os.getenv("TERM") or os.getenv("WT_SESSION"))
def color(text, code): return f"\033[{code}m{text}\033[0m" if COLOR else str(text)
def success(text): print(color(text, "32"))
def error(text): print(color(text, "31"))
def warning(text): print(color(text, "33"))

def table(headers, rows):
    values = [[str(v) for v in row] for row in rows]
    widths = [min(26, max(len(str(h)), *(min(26, len(row[i])) for row in values)) if values else len(str(h))) for i, h in enumerate(headers)]
    def line(row): return " | ".join(str(val)[:w-3] + "..." if len(str(val)) > w else str(val).ljust(w) for val, w in zip(row, widths))
    print(line(headers)); print("-+-".join("-" * w for w in widths))
    for row in values: print(line(row))

def paginate(headers, rows, page_size=10):
    for start in range(0, len(rows), page_size):
        table(headers, rows[start:start+page_size])
        if start + page_size < len(rows):
            try:
                choice = input("Next page? [Enter/ q]: ").strip().casefold()
            except (EOFError, KeyboardInterrupt): return
            if choice == "q": return
