import tkinter as tk
from tkinter import messagebox
import os, base64, json
from datetime import datetime
import random
import re

USER_FILE = "users.txt"
NOTES_FILE = "notes.json"

BG = "#FFE4F0"        
ENTRY_BG = "#FFF0F5"  
BTN_BG = "#FF6B81"    
TEXT_COLOR = "#900C3F"  
RIGHT_BG = "#FFDDE6" 
HEART_COLOR_VARIANTS = ["#FFC0CB", "#FFB6C1", "#FF69B4", "#FF1493"]  


class UserManager:
    def load_users(self):
        if not os.path.exists(USER_FILE):
            return []
        with open(USER_FILE, "rb") as f:
            data = base64.b64decode(f.read()).decode()
            return [line.split("|") for line in data.splitlines() if "|" in line]

    def save_users(self, users):
        with open(USER_FILE, "wb") as f:
            data = "\n".join(f"{u[0]}|{u[1]}" for u in users)
            f.write(base64.b64encode(data.encode()))

# ---------- NOTES STORAGE ----------
class NotesManager:
    def load_notes(self):
        if not os.path.exists(NOTES_FILE):
            return {}
        with open(NOTES_FILE, "r") as f:
            return json.load(f)

    def save_notes(self, notes):
        with open(NOTES_FILE, "w") as f:
            json.dump(notes, f)

# ---------- MAIN APP ----------
class NotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Anonymous Love Notes 💌")
        self.root.geometry("750x500")
        self.root.configure(bg=BG)

        self.um = UserManager()
        self.nm = NotesManager()

        self.users = []
        self.received_notes = {}  # {username: [{"content": note, "status": "UNREAD"}, ...]}
        self.timestamps = {}      # {username: [timestamp1, timestamp2,...]}

        self.current_user = "guest"
        self.selected_recipient = None
        self.selected_delete_accounts = set()  # for multi-delete

        self.login_frame = None
        self.register_frame = None
        self.delete_frame = None

        self.build_ui()
        self.load_users()
        self.load_notes()
        self.show_main_dashboard()
        self.auto_refresh()

        # Bind Enter globally
        self.root.bind("<Return>", self.global_enter_press)

    # ---------- UTILITY BUTTON ----------
    def gray_btn(self, parent, text, cmd, width=None):
        btn = tk.Button(parent, text=text, command=cmd,
                         bg=BTN_BG, fg="white",
                         activebackground="#FF8DAA",
                         width=width, relief="flat",
                         font=("Arial", 10, "bold"))
        return btn

    # ---------- GLOBAL ENTER HANDLER ----------
    def global_enter_press(self, event):
        widget = self.root.focus_get()

        if widget is None:
            if self.current_user == "guest" and self.users:
                if hasattr(self, "listbox"):
                    self.listbox.selection_clear(0, tk.END)
                    self.listbox.selection_set(0)
                    self.on_select(None)
            return

        # LOGIN
        if self.login_frame and self.login_frame.winfo_ismapped():
            username = self.login_frame.winfo_children()[1].get().strip()
            password = self.login_frame.winfo_children()[3].get().strip()
            self.do_login(username, password)
            return

        # REGISTER
        if self.register_frame and self.register_frame.winfo_ismapped():
            username = self.register_frame.winfo_children()[1].get().strip()
            password = self.register_frame.winfo_children()[3].get().strip()
            password2 = self.register_frame.winfo_children()[5].get().strip()
            self.do_register(username, password, password2)
            return

        # DELETE ACCOUNT
        if self.delete_frame and self.delete_frame.winfo_ismapped():
            self.delete_selected_accounts()
            return

        # NOTES TEXT
        if isinstance(widget, tk.Text):
            content = widget.get("1.0", "end").strip()
            if content:  # only send if not empty
                self.send_note()
            return

        # LISTBOX (Main dashboard)
        if hasattr(self, "listbox") and self.listbox.winfo_ismapped():
            sel = self.listbox.curselection()
            if not sel and self.listbox.size() > 0:
                self.listbox.selection_set(0)
                self.on_select(None)
            elif sel and self.current_user != "guest":
                self.on_double_click(None)
            return

    
        if hasattr(self, "listbox") and self.listbox.winfo_ismapped():
            sel = self.listbox.curselection()
        if not sel and self.listbox.size() > 0:
            self.listbox.selection_set(0)
            self.on_select(None)
        elif sel and self.current_user != "guest":
            self.on_double_click(None)  # open note
        return

    # ---------- USER & NOTES LOADING ----------
    def load_users(self):
        self.users = self.um.load_users()
        for u in self.users:
            if u[0] not in self.received_notes:
                self.received_notes[u[0]] = []
            if u[0] not in self.timestamps:
                self.timestamps[u[0]] = []

    def load_notes(self):
        data = self.nm.load_notes()
        self.received_notes = data.get("notes", {})
        self.timestamps = data.get("timestamps", {})
        # Ensure all users have entries
        for u in self.users:
            if u[0] not in self.received_notes:
                self.received_notes[u[0]] = []
            if u[0] not in self.timestamps:
                self.timestamps[u[0]] = []

    def save_notes(self):
        data = {
            "notes": self.received_notes,
            "timestamps": self.timestamps
        }
        self.nm.save_notes(data)

    # ---------- DASHBOARD ----------
    def show_main_dashboard(self):
        for w in self.left.winfo_children():
            w.destroy()

        # subtle heart pattern background
        canvas = tk.Canvas(self.left, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        for _ in range(30):
            x = random.randint(0, 700)
            y = random.randint(0, 500)
            size = random.randint(8, 18)
            color = random.choice(HEART_COLOR_VARIANTS)
            canvas.create_text(x, y, text="❤️", font=("Arial", size), fill=color)

        # Search
        top_frame = tk.Frame(canvas, bg=BG)
        top_frame.place(relx=0.5, rely=0.02, anchor="n")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.refresh_list)
        tk.Label(top_frame, text="Search:", bg=BG, fg=TEXT_COLOR, font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))
        tk.Entry(top_frame, textvariable=self.search_var,
                 bg=ENTRY_BG, fg=TEXT_COLOR, width=25).pack(side="left", padx=5)

        # Listbox with scrollbar
        list_frame = tk.Frame(canvas, bg=BG)
        list_frame.place(relx=0.5, rely=0.12, anchor="n", relwidth=0.9, relheight=0.7)
        self.scrollbar = tk.Scrollbar(list_frame)
        self.scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(list_frame, bg=ENTRY_BG, fg=TEXT_COLOR, yscrollcommand=self.scrollbar.set,
                                  font=("Arial", 11), selectbackground="#ADD8E6", selectmode="multiple")
        self.listbox.pack(fill="both", expand=True)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.listbox.bind("<Double-1>", self.on_double_click)

        # Bottom buttons
        self.bottom = tk.Frame(canvas, bg=BG)
        self.bottom.place(relx=0.5, rely=0.88, anchor="n")
        for w in self.bottom.winfo_children():
            w.destroy()

        if self.current_user == "guest":
            self.add_btn = self.gray_btn(self.bottom, "Add Note 💌", self.go_to_notes, 15)
            self.add_btn.pack(pady=5)
            self.add_btn.config(state="disabled")
        else:
            btn_frame = tk.Frame(self.bottom, bg=BG)
            btn_frame.pack()
            self.logout_btn = self.gray_btn(btn_frame, "Logout", self.logout, 12)
            self.logout_btn.pack(side="left", padx=5)
            self.delete_all_btn = self.gray_btn(btn_frame, "Delete All ❤️", self.delete_all_notes, 12)
            self.delete_all_btn.pack(side="left", padx=5)
            self.delete_selected_btn = self.gray_btn(btn_frame, "Delete Selected ❤️", self.delete_selected_note, 15)
            self.delete_selected_btn.pack(side="left", padx=5)

        self.refresh_list()

    # ---------- REFRESH LIST ----------
    def refresh_list(self, *args):
        self.load_notes()
        self.listbox.delete(0, tk.END)
        keyword = self.search_var.get().lower() if hasattr(self, "search_var") else ""

        if self.current_user == "guest":
            for u in self.users:
                username = u[0]
                notes = self.received_notes.get(username, [])
                msg_count = len(notes)
                if keyword in username.lower():
                    self.listbox.insert(tk.END, f"{username} ({msg_count} message{'s' if msg_count != 1 else ''})")
        else:
            notes = self.received_notes.get(self.current_user, [])
            timestamps = self.timestamps.get(self.current_user, [])
            for i, note in enumerate(notes):
                ts = timestamps[i] if i < len(timestamps) else ""
                ts_short = ts[:16] if ts else "No date"
                status_icon = "💌" if note.get("status") == "UNREAD" else "❤️"
                self.listbox.insert(tk.END, f"{status_icon} Anonymous - {ts_short}")

    # ---------- SELECT / DOUBLE CLICK ----------
    def on_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            if self.current_user == "guest":
                self.selected_recipient = self.listbox.get(sel[0]).split(" (")[0]
                self.add_btn.config(state="normal")
            else:
                clicked_user = self.listbox.get(sel[0])
                if clicked_user in self.selected_delete_accounts:
                    self.selected_delete_accounts.remove(clicked_user)
                else:
                    self.selected_delete_accounts.add(clicked_user)
                for i in range(self.listbox.size()):
                    if self.listbox.get(i) in self.selected_delete_accounts:
                        self.listbox.select_set(i)
                    else:
                        self.listbox.select_clear(i)

    def on_double_click(self, event):
        if self.current_user == "guest":
            return
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.received_notes[self.current_user][idx]["status"] = "READ"
            self.save_notes()
            self.show_view_note(idx)
            self.refresh_list()

    # ---------- DELETE ACCOUNT (MULTI-SELECT) ----------
    def delete_account_prompt(self):
    # Hide other frames first
        if self.login_frame:
            self.login_frame.destroy()
            self.login_frame = None
        if self.register_frame:
            self.register_frame.destroy()
            self.register_frame = None
    # Toggle: hide if already open
        if self.delete_frame:
            self.delete_frame.destroy()
            self.delete_frame = None
            return

    # Create delete frame
        self.delete_frame = tk.Frame(self.right_top, bg=RIGHT_BG)
        self.delete_frame.pack(pady=5, fill="both", expand=True)

        tk.Label(self.delete_frame, text="Select account(s) to delete 💔", bg=RIGHT_BG, fg=TEXT_COLOR).pack(pady=5)

        self.delete_listbox = tk.Listbox(self.delete_frame, selectmode="multiple", bg=ENTRY_BG, fg=TEXT_COLOR,
                                     font=("Arial", 11))
        for u in self.users:
            self.delete_listbox.insert(tk.END, u[0])
        self.delete_listbox.pack(padx=5, pady=5, fill="both", expand=True)

        tk.Label(self.delete_frame, text="Admin Password:", bg=RIGHT_BG, fg=TEXT_COLOR).pack(pady=5)
        self.admin_pwd_entry = tk.Entry(self.delete_frame, show="*", bg=ENTRY_BG, fg=TEXT_COLOR)
        self.admin_pwd_entry.pack(pady=5)

        confirm_btn = self.gray_btn(self.delete_frame, "Confirm Delete", self.delete_selected_accounts)
        confirm_btn.pack(pady=5)
        confirm_btn.focus_set()

    def delete_selected_accounts(self):
        selected_indices = self.delete_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "Select at least one account 💔")
            return

        admin_pass = self.admin_pwd_entry.get().strip()
        if admin_pass != "Peleno123":
            messagebox.showerror("Error", "Wrong admin password 💔")
            return

        selected_users = [self.delete_listbox.get(i) for i in selected_indices]
        for u in selected_users:
            self.users = [usr for usr in self.users if usr[0] != u]
            self.received_notes.pop(u, None)
            self.timestamps.pop(u, None)

        self.um.save_users(self.users)
        self.save_notes()
        messagebox.showinfo("Deleted", f"Deleted {len(selected_users)} account(s) 💌")

        self.delete_frame.destroy()
        self.delete_frame = None
        self.refresh_list()

    # ---------- NOTE ----------
    def go_to_notes(self):
        if not self.selected_recipient:
            messagebox.showerror("Error", "Select a user first")
            return
        self.show_notes_dashboard()

    def show_notes_dashboard(self):
        for w in self.left.winfo_children():
            w.destroy()
        self.right.pack_forget()
        tk.Label(self.left, text=f"Send to: {self.selected_recipient} 💖", bg=BG, fg=TEXT_COLOR,
                 font=("Arial", 12, "bold")).pack(pady=5)
        self.text = tk.Text(self.left, bg=ENTRY_BG, fg=TEXT_COLOR, font=("Arial", 12))
        self.text.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(self.left, bg=BG)
        btn_frame.pack(pady=5)
        send_btn = tk.Button(btn_frame, text="Done 💌", bg=BTN_BG, fg="white", command=self.send_note)
        send_btn.pack(side="left", padx=5)
        send_btn.focus_set()
        tk.Button(btn_frame, text="Back", bg=BTN_BG, fg="white", command=self.back_to_dashboard).pack(side="left", padx=5)

    def back_to_dashboard(self):
        self.right.pack(side="right", fill="y")
        self.show_main_dashboard()

    def send_note(self):
        content = self.text.get("1.0", "end").strip()
        if len(content) > 300:
            messagebox.showerror("Error", "Note too long! Max 300 characters 💔")
            return

        bad_words = [
            "fuck", "shit", "bitch", "asshole", "dumb", "stupid",
            "ugly", "idiot", "loser", "retard", "faggot", "cunt",
            "youre ugly", "you are ugly", "fuck you", "kill yourself"
        ]
        content_clean = re.sub(r'[^\w\s]', '', content.lower())
        for bad in bad_words:
            if bad in content_clean:
                messagebox.showerror("Error", f"This word or phrase '{bad}' is offensive. Cannot send 💔")
                return

        if not self.selected_recipient:
            messagebox.showerror("Error", "Select a user first 💔")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.received_notes.setdefault(self.selected_recipient, []).append({"content": content, "status": "UNREAD"})
        self.timestamps.setdefault(self.selected_recipient, []).append(timestamp)

        self.save_notes()  # Save immediately
        messagebox.showinfo("Sent", "Anonymous note sent! 💌")
        self.selected_recipient = None
        self.back_to_dashboard()

    def show_view_note(self, idx):
        for w in self.left.winfo_children():
            w.destroy()
        tk.Label(self.left, text="💌 Anonymous Message 💌", bg=BG, fg=TEXT_COLOR,
                 font=("Arial", 14, "bold")).pack(pady=5)
        text_area = tk.Text(self.left, bg=ENTRY_BG, fg=TEXT_COLOR, height=10, font=("Arial", 12))
        text_area.pack(fill="both", expand=True, padx=10, pady=10)
        text_area.insert("1.0", self.received_notes[self.current_user][idx]["content"])
        text_area.config(state="disabled")
        btn_frame = tk.Frame(self.left, bg=BG)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Back", bg=BTN_BG, fg="white", command=self.show_main_dashboard).pack(side="left", padx=5)

    # ---------- LOGIN / REGISTER ----------
    def login_inline(self):
        if self.register_frame:
            self.register_frame.destroy()
            self.register_frame = None
        if self.delete_frame:
            self.delete_frame.destroy()
            self.delete_frame = None
        if self.login_frame:
            self.login_frame.destroy()
            self.login_frame = None
            return

        self.login_frame = tk.Frame(self.right_top, bg=RIGHT_BG)
        self.login_frame.pack(pady=5)
        tk.Label(self.login_frame, text="Username", bg=RIGHT_BG, fg=TEXT_COLOR).pack()
        user = tk.Entry(self.login_frame, bg=ENTRY_BG, fg=TEXT_COLOR)
        user.pack()
        tk.Label(self.login_frame, text="Password", bg=RIGHT_BG, fg=TEXT_COLOR).pack()
        pwd = tk.Entry(self.login_frame, show="*", bg=ENTRY_BG, fg=TEXT_COLOR)
        pwd.pack()
        tk.Button(self.login_frame, text="Login", bg=BTN_BG, fg="white",
                  command=lambda: self.do_login(user.get().strip(), pwd.get().strip())).pack(pady=5)
        tk.Button(self.login_frame, text="Back", bg=BTN_BG, fg="white", command=self.back_to_dashboard).pack()

    def do_login(self, username, password):
        if not username or not password:
            messagebox.showerror("Error", "All fields required 💔")
            return
        for u in self.users:
            if u[0] == username and u[1] == password:
                self.current_user = username
                self.load_notes()  # <- LOAD NOTES ON LOGIN
                self.show_main_dashboard()
                return
        messagebox.showerror("Error", "Wrong login 💔")

    def register_inline(self):
    # Hide other frames first
        if self.login_frame:
            self.login_frame.destroy()
            self.login_frame = None
        if self.delete_frame:
           self.delete_frame.destroy()
           self.delete_frame = None
    # Toggle: hide if already open
        if self.register_frame:
           self.register_frame.destroy()
           self.register_frame = None
           return

    # Create register frame
        self.register_frame = tk.Frame(self.right_top, bg=RIGHT_BG)
        self.register_frame.pack(pady=5)
        tk.Label(self.register_frame, text="Username", bg=RIGHT_BG, fg=TEXT_COLOR).pack()
        user = tk.Entry(self.register_frame, bg=ENTRY_BG, fg=TEXT_COLOR)
        user.pack()
        tk.Label(self.register_frame, text="Password", bg=RIGHT_BG, fg=TEXT_COLOR).pack()
        pwd = tk.Entry(self.register_frame, show="*", bg=ENTRY_BG, fg=TEXT_COLOR)
        pwd.pack()
        tk.Label(self.register_frame, text="Confirm Password", bg=RIGHT_BG, fg=TEXT_COLOR).pack()
        pwd2 = tk.Entry(self.register_frame, show="*", bg=ENTRY_BG, fg=TEXT_COLOR)
        pwd2.pack()
        tk.Button(self.register_frame, text="Register", bg=BTN_BG, fg="white",
            command=lambda: self.do_register(user.get().strip(), pwd.get().strip(), pwd2.get().strip())).pack(pady=5)
        tk.Button(self.register_frame, text="Back", bg=BTN_BG, fg="white", command=self.back_to_dashboard).pack()

    def do_register(self, username, pwd, pwd2):
        if not username or not pwd or not pwd2:
            messagebox.showerror("Error", "All fields required 💔")
            return
        if pwd != pwd2:
            messagebox.showerror("Error", "Passwords do not match 💔")
            return
        if any(u[0] == username for u in self.users):
            messagebox.showerror("Error", "Username already exists 💔")
            return
        self.users.append([username, pwd])
        self.um.save_users(self.users)
        messagebox.showinfo(" Registered", f"Account {username} created 💌")
        self.current_user = username
        self.load_notes()
        self.show_main_dashboard()

    # ---------- DELETE NOTES ----------
    def delete_all_notes(self):
        if messagebox.askyesno("Confirm", "Delete all notes? 💔"):
            self.received_notes[self.current_user] = []
            self.timestamps[self.current_user] = []
            self.save_notes()
            self.refresh_list()

    def delete_selected_note(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showerror("Error", "Select a note first 💔")
            return
        for i in reversed(sel):
            self.received_notes[self.current_user].pop(i)
            self.timestamps[self.current_user].pop(i)
        self.save_notes()
        self.refresh_list()

    def logout(self):
        self.current_user = "guest"
        self.show_main_dashboard()
    
    def exit_app(self):
        self.root.quit()   # or self.root.destroy()

    # ---------- AUTO REFRESH ----------
    def auto_refresh(self):
        self.refresh_list()
        self.root.after(5000, self.auto_refresh)  # every 5 sec


    # ---------- LEFT / RIGHT FRAMES ----------
    def build_ui(self):
        self.left = tk.Frame(self.root, bg=BG)
        self.left.pack(side="left", fill="both", expand=True)

        self.right = tk.Frame(self.root, bg=RIGHT_BG, width=200)
        self.right.pack(side="right", fill="y")

    # ---------- TOP FRAME (buttons + forms dito) ----------
        self.right_top = tk.Frame(self.right, bg=RIGHT_BG)
        self.right_top.pack(side="top", fill="both", expand=True)

        tk.Label(self.right_top, text="Love 💖", bg=RIGHT_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(pady=10)

        self.gray_btn(self.right_top, "Login 🔑", self.login_inline).pack(pady=5, fill="x", padx=10)
        self.gray_btn(self.right_top, "Register ✍️", self.register_inline).pack(pady=5, fill="x", padx=10)
        self.gray_btn(self.right_top, "Delete Account ❌", self.delete_account_prompt).pack(pady=5, fill="x", padx=10)

    # ---------- BOTTOM FRAME (Exit dito lang) ----------
        self.right_bottom = tk.Frame(self.right, bg=RIGHT_BG)
        self.right_bottom.pack(side="bottom", fill="x")

        self.gray_btn(self.right_bottom, "Exit ❌", self.exit_app).pack(pady=10, fill="x", padx=10)
        
# ---------- RUN ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = NotesApp(root)
    root.mainloop()