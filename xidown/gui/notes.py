import customtkinter as ctk
import os
import sys
import json
import time
from datetime import datetime

# NAVIGATION FIX
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 1. Get current file path (xidown/gui)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 2. Navigate back to package
    package_dir = os.path.dirname(current_dir)
    # 3. Navigate back to Root (xidown/)
    BASE_DIR = os.path.dirname(package_dir)

DATA_DIR = os.path.join(os.path.expanduser("~"), "Videos", "xidown")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Data storage files
NOTES_JSON = os.path.join(DATA_DIR, "notes_data.json")
OLD_NOTES_FILE = os.path.join(DATA_DIR, "user_notes.txt")

# CUSTOM WIDGET: NOTE CARD
class NoteCard(ctk.CTkFrame):
    def __init__(self, parent, note_id, data, is_selected, callback_select):
        self.default_bg = "#121212" if is_selected else "transparent"
        self.hover_bg = "#222222" if is_selected else "#1e1e1e"
        self.text_color = "#db2777" if is_selected else "#aaaaaa"
        
        super().__init__(parent, fg_color=self.default_bg, corner_radius=0, height=36)
        self.pack(fill="x", pady=1, padx=4)
        self.pack_propagate(False) 
        
        self.note_id = note_id
        self.callback_select = callback_select

        content = data.get("content", "").strip()
        original_title = data.get("title", "").strip()
        
        if original_title:
            display_text = original_title
        elif content:
            display_text = content.split('\n')[0].strip()
        else:
            display_text = "New Note"
            
        if len(display_text) > 25: 
            display_text = display_text[:22] + "..."

        # Left active indicator bar
        indicator_color = "#db2777" if is_selected else "transparent"
        self.indicator = ctk.CTkFrame(self, width=3, fg_color=indicator_color, corner_radius=0)
        self.indicator.pack(side="left", fill="y")

        self.lbl_title = ctk.CTkLabel(
            self, text=display_text, font=("Terminal", 11, "bold"), 
            text_color=self.text_color, anchor="w"
        )
        self.lbl_title.pack(side="left", fill="both", expand=True, padx=(8, 4))

        for w in [self, self.lbl_title, self.indicator]:
            w.bind("<Button-1>", self.on_click)
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)

    def on_enter(self, event):
        self.configure(fg_color=self.hover_bg)

    def on_leave(self, event):
        self.configure(fg_color=self.default_bg)

    def on_click(self, event):
        self.callback_select(self.note_id)


# MAIN WINDOW
class NotesWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        
        self.title("My Notes")
        self.parent = parent
        self.configure(fg_color="#121212")
        
        try:
            parent.update_idletasks()
            p_w = parent.winfo_width(); p_h = parent.winfo_height()
            p_x = parent.winfo_x(); p_y = parent.winfo_y()
            w = int(p_w * 0.65); h = int(p_h * 0.70)
            if w < 500: w = 500
            if h < 320: h = 320
            x = int(p_x + (p_w - w) / 2)
            y = int(p_y + (p_h - h) / 2)
        except:
            w, h = 550, 350
            ws = self.winfo_screenwidth(); hs = self.winfo_screenheight()
            x = (ws // 2) - (w // 2); y = (hs // 2) - (h // 2)

        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(True, True)
        self.transient(parent) 
        self.lift()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Load icon (Check assets, fallback to img)
        import xidown.core.utils as utils
        self.icon_path = utils.get_icon_path()
        def force_icon():
            try:
                if self.icon_path and os.path.exists(self.icon_path): self.iconbitmap(self.icon_path)
            except Exception: pass
        force_icon()
        self.after(200, force_icon)
        self.after(1000, force_icon)

        # Data Init
        self.notes_data = {} 
        self.current_note_id = None
        self.migrate_old_data() 
        self.load_database()
        self.initialize_order()

        # UI
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame_sidebar = ctk.CTkFrame(self, width=160, corner_radius=0, fg_color="#1a1a1a")
        self.frame_sidebar.grid(row=0, column=0, sticky="nsew")
        self.frame_sidebar.grid_propagate(False) 

        # Header Title in Sidebar (matches main window style)
        self.frame_sidebar_header = ctk.CTkFrame(self.frame_sidebar, fg_color="transparent", height=40)
        self.frame_sidebar_header.pack(side="top", fill="x", padx=10, pady=(12, 0))
        self.frame_sidebar_header.pack_propagate(False)
        
        self.lbl_sidebar_title = ctk.CTkLabel(self.frame_sidebar_header, text="NOTES", font=("Fixedsys", 16), text_color="#db2777")
        self.lbl_sidebar_title.pack(side="top", anchor="w", pady=(2, 0))

        self.btn_new = ctk.CTkButton(
            self.frame_sidebar, text="+ New Note", fg_color="#db2777", hover_color="#be185d",     
            text_color="white", font=("Terminal", 11, "bold"), height=28, corner_radius=0, command=self.action_add_note
        )
        self.btn_new.pack(fill="x", padx=10, pady=(5, 8))

        self.scroll_list = ctk.CTkScrollableFrame(
            self.frame_sidebar, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#333333", scrollbar_button_hover_color="#db2777"
        )
        self.scroll_list.pack(fill="both", expand=True, padx=2, pady=(0, 5))
        try:
            if hasattr(self.scroll_list, "_scrollbar"):
                self.scroll_list._scrollbar.configure(width=4, corner_radius=0)
        except: pass

        self.frame_editor = ctk.CTkFrame(self, corner_radius=0, fg_color="#121212")
        self.frame_editor.grid(row=0, column=1, sticky="nsew")
        self.editor_widgets_active = False
        
        self.frame_header_top = ctk.CTkFrame(self.frame_editor, fg_color="transparent", height=32)
        self.lbl_date = ctk.CTkLabel(self.frame_header_top, text="", font=("Consolas", 10, "italic"), text_color="#888888")
        self.lbl_date.pack(side="left", padx=5)
        
        try:
            ic_del = self.parent.ic_delete
            text_del = ""
        except:
            ic_del = None
            text_del = "Del"

        self.btn_delete = ctk.CTkButton(
            self.frame_header_top, text=text_del, image=ic_del, fg_color="#2b2b2b", hover_color="#8B0000", 
            text_color="#777777", font=("Terminal", 10, "bold"), width=28, height=28, corner_radius=0, command=self.action_delete_note
        )
        self.btn_delete.pack(side="right", padx=(5, 0))

        self.textbox_isi = ctk.CTkTextbox(
            self.frame_editor, font=("Consolas", 11), text_color="#eeeeee", 
            fg_color="#1a1a1a", border_width=1, border_color="#2c2c2c", corner_radius=0,
            scrollbar_button_color="#333333", scrollbar_button_hover_color="#db2777", undo=True
        )
        try:
            self.textbox_isi._y_scrollbar.configure(width=4, corner_radius=0)
        except: pass
        self.textbox_isi.bind("<KeyRelease>", self.action_save_content)

        self.refresh_sidebar_list()
        
        if self.notes_data:
            sorted_notes = sorted(self.notes_data.items(), key=lambda x: x[1].get('order', 9999))
            self.select_note(sorted_notes[0][0])
        else:
            self.action_add_note()

        self.after(50, self.deiconify)

    def initialize_order(self):
        if not self.notes_data: return
        notes_list = []
        needs_save = False
        for nid, data in self.notes_data.items():
            if 'order' not in data:
                data['order'] = 999999
                needs_save = True
            notes_list.append((nid, data))
        
        if needs_save:
            notes_list.sort(key=lambda x: x[1].get('updated', 0), reverse=True)
            for i, (nid, data) in enumerate(notes_list):
                self.notes_data[nid]['order'] = i
            self.save_database()

    def migrate_old_data(self):
        if os.path.exists(OLD_NOTES_FILE) and not os.path.exists(NOTES_JSON):
            try:
                with open(OLD_NOTES_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    new_id = str(int(time.time()))
                    self.notes_data[new_id] = {
                        "title": content.split('\n')[0][:30], "content": content, 
                        "updated": time.time(), "order": 0 
                    }
                    self.save_database()
            except: pass

    def load_database(self):
        if os.path.exists(NOTES_JSON):
            try:
                with open(NOTES_JSON, "r", encoding="utf-8") as f:
                    self.notes_data = json.load(f)
            except: self.notes_data = {}

    def save_database(self):
        try:
            with open(NOTES_JSON, "w", encoding="utf-8") as f:
                json.dump(self.notes_data, f, indent=4)
        except: pass

    def refresh_sidebar_list(self):
        for w in self.scroll_list.winfo_children(): w.destroy()
        sorted_notes = sorted(self.notes_data.items(), key=lambda x: x[1].get('order', 0))
        for n_id, data in sorted_notes:
            is_sel = (n_id == self.current_note_id)
            NoteCard(
                self.scroll_list, note_id=n_id, data=data, is_selected=is_sel, 
                callback_select=self.select_note
            )

    def select_note(self, note_id):
        if self.current_note_id == note_id: return
        self.current_note_id = note_id
        self.refresh_sidebar_list()
        self.show_editor(True)
        
        data = self.notes_data[note_id]
        ts = data.get("updated", time.time())
        self.lbl_date.configure(text=self.format_time(ts))
        
        self.textbox_isi.delete("0.0", "end")
        self.textbox_isi.insert("0.0", data.get("content", ""))

    def action_add_note(self):
        new_id = str(int(time.time()))
        ts = time.time()
        for nid in self.notes_data:
            self.notes_data[nid]['order'] += 1
        self.notes_data[new_id] = {
            "title": "", "content": "", "updated": ts, "order": 0 
        }
        self.save_database()
        self.select_note(new_id)

    def action_delete_note(self):
        if self.current_note_id and self.current_note_id in self.notes_data:
            del self.notes_data[self.current_note_id]
            self.save_database()
            self.current_note_id = None
            if self.notes_data:
                sorted_notes = sorted(self.notes_data.items(), key=lambda x: x[1].get('order', 0))
                self.select_note(sorted_notes[0][0])
            else:
                self.refresh_sidebar_list()
                self.action_add_note()

    def action_save_content(self, event=None):
        if self.current_note_id:
            content = self.textbox_isi.get("0.0", "end-1c")
            ts = time.time()
            lines = content.strip().split('\n')
            title = lines[0][:50] if lines else ""
            
            self.notes_data[self.current_note_id]["content"] = content
            self.notes_data[self.current_note_id]["title"] = title
            self.notes_data[self.current_note_id]["updated"] = ts
            
            self.save_database()
            self.lbl_date.configure(text=self.format_time(ts))
            self.update_sidebar_title_only(self.current_note_id, title)

    def update_sidebar_title_only(self, note_id, new_title):
        for card in self.scroll_list.winfo_children():
            if isinstance(card, NoteCard) and card.note_id == note_id:
                disp_title = new_title[:30] + "..." if len(new_title) > 30 else (new_title or "New Note")
                card.lbl_title.configure(text=disp_title)
                break

    def show_editor(self, show=True):
        if show:
            if not self.editor_widgets_active:
                self.frame_header_top.pack(fill="x", padx=15, pady=(15, 5))
                self.textbox_isi.pack(fill="both", expand=True, padx=15, pady=(0, 15))
                self.editor_widgets_active = True
        else:
            for w in self.frame_editor.winfo_children(): w.pack_forget()
            self.editor_widgets_active = False
    
    def format_time(self, ts):
        return datetime.fromtimestamp(ts).strftime("Edited: %d %b %H:%M")
    
    def on_closing(self):
        self.destroy()
        if self.parent: self.parent.notes_window = None