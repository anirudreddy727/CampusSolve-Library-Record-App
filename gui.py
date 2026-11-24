"""Optional Tkinter window; imports Tk only when launched."""
def launch(library):
    import tkinter as tk
    from tkinter import ttk, messagebox
    root=tk.Tk(); root.title("CampusSolve Library Records"); root.geometry("900x560")
    tabs=ttk.Notebook(root); tabs.pack(fill="both",expand=True,padx=10,pady=10)
    def make_tab(title, headings, rows):
        frame=ttk.Frame(tabs); tabs.add(frame,text=title)
        tree=ttk.Treeview(frame,columns=headings,show="headings")
        for heading in headings: tree.heading(heading,text=heading); tree.column(heading,width=130)
        for row in rows: tree.insert("","end",values=row)
        tree.pack(fill="both",expand=True)
    make_tab("Books",("ID","Title","Author","Category","Available"),[(b.book_id,b.title,b.author,b.category,b.available_copies) for b in library.books])
    make_tab("Members",("ID","Name","Email","Type"),[(m.member_id,m.name,m.email,m.member_type) for m in library.members])
    make_tab("Issue / Return",("Issue","Book","Member","Due","Status"),[(i.issue_id,i.book_id,i.member_id,i.due_date,i.status) for i in library.issues])
    frame=ttk.Frame(tabs); tabs.add(frame,text="Reports"); text=tk.Text(frame,wrap="word"); text.pack(fill="both",expand=True)
    from reports import render
    text.insert("1.0",render(library)); root.mainloop()
