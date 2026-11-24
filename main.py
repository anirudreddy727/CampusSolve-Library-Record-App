"""CampusSolve terminal application."""
import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from storage import Storage
from library import Library, LibraryError
from models import Book, Member
from validators import CancelInput, get_choice, get_date, get_float, get_int, get_nonempty_string, get_regex_string
from search import search_books, search_members, search_issues
from reports import render, export_reports
from importer import import_csv
from ui import success, error, warning, paginate

VERSION = "1.0"

def book_menu(lib):
    while True:
        print("\nBooks: 1 List  2 Add  3 Update  4 Delete  0 Back")
        c=get_choice("Select",["0","1","2","3","4"])
        try:
            if c=="0": return
            if c=="1": paginate(["ID","Title","Author","Category","Copies","Available"],[[b.book_id,b.title,b.author,b.category,b.total_copies,b.available_copies] for b in lib.books])
            elif c=="2":
                item=Book(get_nonempty_string("Book ID: ",12).upper(),get_nonempty_string("Title: ",160),get_nonempty_string("Author: ",100),get_nonempty_string("Category: ",50),get_nonempty_string("ISBN: ",20),get_int("Total copies: ",1,100),0,date.today(),get_float("Book value Rs: ",0,100000)); item.available_copies=item.total_copies; lib.add_book(item); success("Book added.")
            elif c=="3":
                book=lib.find_book(get_nonempty_string("Book ID: ",12)); field=get_choice("Field to update",["title","author","category","isbn","copies"])
                if field=="copies": lib.update_book(book.book_id,total_copies=get_int("Total copies: ",1,100))
                else:
                    value=get_nonempty_string(f"New {field}: ",160 if field=="title" else 100)
                    lib.update_book(book.book_id,**{field:value})
                success("Book updated.")
            else:
                ident=get_nonempty_string("Book ID: ",12)
                if input("Delete this book? [y/N] ").strip().casefold()=="y": lib.delete_book(ident); success("Book deleted.")
        except CancelInput: print("Cancelled.")
        except (LibraryError, ValueError) as exc: error(str(exc))

def member_menu(lib):
    while True:
        print("\nMembers: 1 List  2 Add  3 Update  4 Delete  0 Back")
        c=get_choice("Select",["0","1","2","3","4"])
        try:
            if c=="0": return
            if c=="1": paginate(["ID","Name","Email","Type","Limit"],[[m.member_id,m.name,m.email,m.member_type,m.max_books] for m in lib.members])
            elif c=="2":
                member=Member(get_nonempty_string("Member ID: ",12).upper(),get_nonempty_string("Name: ",100),get_regex_string("Email: ",r"[^@\s]+@[^@\s]+\.[^@\s]+","Enter a valid email."),get_regex_string("Phone: ",r"[+0-9() -]{7,20}","Enter a valid phone."),get_choice("Type",["Student","Faculty","Staff"]),date.today()); lib.add_member(member); success("Member added.")
            elif c=="3":
                member=lib.find_member(get_nonempty_string("Member ID: ",12)); field=get_choice("Field to update",["name","email","phone","type"])
                if field=="type": value=get_choice("Type",["Student","Faculty","Staff"]); field="member_type"
                elif field=="email": value=get_regex_string("New email: ",r"[^@\s]+@[^@\s]+\.[^@\s]+","Enter a valid email.")
                elif field=="phone": value=get_regex_string("New phone: ",r"[+0-9() -]{7,20}","Enter a valid phone.")
                else: value=get_nonempty_string("New name: ",100)
                lib.update_member(member.member_id,**{field:value}); success("Member updated.")
            else:
                ident=get_nonempty_string("Member ID: ",12)
                if input("Delete this member? [y/N] ").strip().casefold()=="y": lib.delete_member(ident); success("Member deleted.")
        except CancelInput: print("Cancelled.")
        except (LibraryError, ValueError) as exc: error(str(exc))

def warnings_menu(lib):
    today=date.today()
    for issue in lib.issues:
        if not issue.return_date and issue.due_date < today: warning(f"Overdue: {issue.issue_id} {issue.book_id} for {issue.member_id}")
    for book in lib.books:
        if book.available_copies == 0: warning(f"No copies available: {book.book_id} {book.title}")
    for member in lib.members:
        count=len(lib.active_for(member.member_id))
        if count >= member.max_books: warning(f"At limit: {member.member_id} ({count}/{member.max_books})")
    if not lib.issues and not lib.books: print("No warnings.")
    for msg in lib.storage.warnings: warning(msg)

def run_gui(lib):
    try:
        import gui
        gui.launch(lib)
    except ImportError as exc: print(f"Tkinter GUI unavailable: {exc}")

def main(argv=None):
    parser=argparse.ArgumentParser(description="CampusSolve Library Records")
    parser.add_argument("--seed",action="store_true",help="load generated demo records")
    parser.add_argument("--gui",action="store_true",help="launch optional Tkinter interface")
    parser.add_argument("--terminal",action="store_true",help="use the original terminal interface")
    args=parser.parse_args(argv)
    if args.seed:
        from seed_data import generate
        print("Loaded demo dataset:",generate()); return 0
    storage=Storage(); lib=Library(storage)
    if args.gui: run_gui(lib); return 0
    if not args.terminal:
        from webapp import launch
        launch(lib)
        return 0
    print(f"\n{'='*56}\n  CampusSolve Library Record Application v{VERSION}\n  {date.today().isoformat()}\n{'='*56}")
    warnings_menu(lib)
    options=["1","2","3","4","5","6","7","8","9","10","0"]
    while True:
        print("\n1 Books  2 Members  3 Issue Book  4 Return Book  5 Renew Book  6 Search  7 Summary Report  8 Export Reports  9 Import CSV  10 Warnings  0 Exit")
        try:
            choice=get_choice("Choose",options)
            if choice=="0": storage.save_all(); print("Goodbye."); return 0
            if choice=="1": book_menu(lib)
            elif choice=="2": member_menu(lib)
            elif choice=="3":
                rec=lib.issue_book(get_nonempty_string("Book ID: ",12).upper(),get_nonempty_string("Member ID: ",12).upper()); success(f"Issued as {rec.issue_id}; due {rec.due_date}.")
            elif choice=="4":
                rec=lib.return_book(get_nonempty_string("Issue ID: ",12).upper()); success(f"Returned; fine Rs. {rec.fine_amount:.2f}.")
            elif choice=="5":
                rec=lib.renew(get_nonempty_string("Issue ID: ",12).upper()); success(f"Renewed through {rec.due_date}.")
            elif choice=="6":
                kind=get_choice("Search",["Books","Members","Issues"]); key=input("Keyword or ID (blank for all): ").strip()
                if kind=="Books": rows=search_books(lib.books,key); paginate(["ID","Title","Author","Category","Available"],[[b.book_id,b.title,b.author,b.category,b.available_copies] for b in rows])
                elif kind=="Members": rows=search_members(lib.members,key); paginate(["ID","Name","Email","Type"],[[m.member_id,m.name,m.email,m.member_type] for m in rows])
                else: rows=search_issues(lib.issues,member_id=key or None); paginate(["Issue","Book","Member","Due","Status"],[[i.issue_id,i.book_id,i.member_id,i.due_date,i.status] for i in rows])
            elif choice=="7": print(render(lib))
            elif choice=="8": print("Exported:", *export_reports(lib), sep="\n")
            elif choice=="9":
                kind=get_choice("Record type",["books","members","issues"]); filename=get_nonempty_string("CSV path: ",300); count,rejected=import_csv(lib,kind,filename); print(f"{count} imported, {rejected} rejected.")
            elif choice=="10": warnings_menu(lib)
        except CancelInput: print("\nReturning to menu.")
        except (LibraryError, ValueError, OSError, csv.Error) as exc: error(str(exc))
        except (KeyboardInterrupt, EOFError): print("\nReturning to menu.")

if __name__=="__main__": sys.exit(main())
