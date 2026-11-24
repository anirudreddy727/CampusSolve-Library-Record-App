import csv
import tempfile
import unittest
import json
import threading
from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError
from http.cookiejar import CookieJar
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from models import Book, Member
from storage import Storage
from library import Library, LibraryError
from search import search_books
from importer import import_csv
from validators import get_int, CancelInput
from webapp import make_handler
from http.server import ThreadingHTTPServer
from auth import AuthManager, AuthError


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent); self.storage=Storage(self.temp.name); self.lib=Library(self.storage)
        self.book=Book("B001","Python","A. Writer","CS","123",2,2,date.today(),100)
        self.member=Member("M001","Test User","t@example.com","1234567890","Student",date.today())
        self.lib.add_book(self.book); self.lib.add_member(self.member)
    def tearDown(self): self.temp.cleanup()

    def test_validator_retries(self):
        with patch("builtins.input",side_effect=["abc","99","2"]): self.assertEqual(get_int("n",1,3),2)
        with patch("builtins.input",side_effect=["c"]):
            with self.assertRaises(CancelInput): get_int("n",0,5)
    def test_fines(self):
        due=date(2025,1,1); self.assertEqual(self.lib.calculate_fine(due,due),0); self.assertEqual(self.lib.calculate_fine(due,due+timedelta(days=1)),2); self.assertEqual(self.lib.calculate_fine(due,due+timedelta(days=200)),200)
    def test_member_auth_is_linked_to_library_record(self):
        manager=AuthManager(self.temp.name)
        manager.register_member("M001","t@example.com","member-pass-123",self.lib.members)
        token,user=manager.login("m001","member-pass-123")
        self.assertEqual(user["role"],"member"); self.assertEqual(manager.get_session(token)["member_id"],"M001")
        with self.assertRaises(AuthError): manager.register_member("M001","wrong@example.com","member-pass-123",self.lib.members)
    def test_issue_return_limits_duplicate_and_copies(self):
        self.member.max_books=0
        with self.assertRaises(LibraryError): self.lib.issue_book("B001","M001",date.today())
        self.member.max_books=3
        issue=self.lib.issue_book("B001","M001",date.today()); self.assertEqual(self.book.available_copies,1)
        with self.assertRaises(LibraryError): self.lib.issue_book("B001","M001",date.today())
        self.lib.return_book(issue.issue_id,date.today()); self.assertEqual(self.book.available_copies,2)
        self.book.available_copies=0
        with self.assertRaises(LibraryError): self.lib.issue_book("B001","M001")
    def test_storage_missing_corrupt(self):
        path=Path(self.temp.name)/"books.json"; path.write_text("oops",encoding="utf-8"); store=Storage(self.temp.name)
        self.assertEqual(store.records["books"],[]); self.assertTrue(list(Path(self.temp.name).glob("books.corrupt.*.json")))
    def test_import_valid_bad(self):
        path=Path(self.temp.name)/"in.csv"
        with path.open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["book_id","title","author","category","isbn","total_copies","available_copies","added_on"]); w.writerow(["B002","Novel","Writer","Fiction","456",1,1,date.today()]); w.writerow(["B003","Broken","Writer","CS","789","no",1,date.today()])
        self.assertEqual(import_csv(self.lib,"books",path,Path(self.temp.name)/"logs"),(1,1))
    def test_search(self): self.assertEqual([b.book_id for b in search_books(self.lib.books,"yth")],["B001"])
    def test_browser_app_serves_dashboard_and_state(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(self.lib)); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            base=f"http://127.0.0.1:{server.server_port}"
            with urlopen(base) as response: self.assertIn(b"CampusSolve",response.read())
            opener=build_opener(HTTPCookieProcessor(CookieJar()))
            setup=Request(base+"/api/setup",data=json.dumps({"username":"admin1","password":"secure-pass-123"}).encode(),headers={"Content-Type":"application/json"})
            with opener.open(setup) as response: self.assertEqual(response.status,200)
            with opener.open(base+"/api/state") as response: state=json.loads(response.read())
            self.assertEqual(state["books"][0]["book_id"],"B001")
            member_opener=build_opener(HTTPCookieProcessor(CookieJar()))
            register=Request(base+"/api/register",data=json.dumps({"member_id":"M001","email":"t@example.com","password":"member-pass-123"}).encode(),headers={"Content-Type":"application/json"})
            with member_opener.open(register) as response: self.assertEqual(response.status,200)
            with member_opener.open(base+"/api/state") as response: member_state=json.loads(response.read())
            self.assertEqual(member_state["auth"]["user"]["role"],"member")
            denied=Request(base+"/api/members",data=b"{}",headers={"Content-Type":"application/json"})
            with self.assertRaises(HTTPError) as error: member_opener.open(denied)
            error.exception.close()
            self.assertEqual(error.exception.code,403)
        finally: server.shutdown(); server.server_close(); thread.join(timeout=2)

if __name__=="__main__": unittest.main()
