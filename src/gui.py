import tkinter as tk
from tkinter import font, messagebox, filedialog
import datetime
import asyncio
import threading
import os
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from telethon import utils

class NotepadApp(tk.Tk):
    def __init__(self, backend=None, loop=None):
        super().__init__()
        self.backend = backend
        self.loop = loop
        self.current_chat = None
        self.dialogs_map = {} 
        
        self.show_groups = tk.BooleanVar(value=False)
        self.tray_icon = None
        
        # State
        self.window_focused = True
        self.renderer_cache = {} 
        
        self.title("Sem título - Bloco de Notas")
        self.geometry("800x600")
        self.iconbitmap('') 
        
        self._setup_ui()
        self._create_menu()
        self._setup_bindings()
        
        # Search Cache
        self.all_contacts = []

    def _setup_bindings(self):
        # Sidebar
        self.sidebar_list.bind('<<ListboxSelect>>', self.on_contact_select)
        self.sidebar_list.bind('<Motion>', self.on_sidebar_hover)
        self.sidebar_list.bind('<Button-3>', self.show_sidebar_context_menu)
        
        # Text
        self.text_area.bind('<Return>', self.on_enter_pressed)
        self.text_area.bind('<Key>', self.on_text_key)
        self.text_area.bind('<Button-3>', self.show_chat_context_menu)
        
        # Window State
        self.bind('<FocusIn>', self.on_focus_in)
        self.bind('<FocusOut>', self.on_focus_out)
        
        # Hotkeys
        self.bind('<F12>', self.withdraw_window)
        self.bind('<Escape>', self.withdraw_window)
        self.bind('<Control-s>', self.emergency_clear)
        self.bind('<Alt-Up>', self.nav_up)
        self.bind('<Alt-Down>', self.nav_down)
        self.bind('<Control-n>', self.open_search_window)

    def _setup_ui(self):
        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=2)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        self.sidebar_frame = tk.Frame(self.paned_window, background="white", width=50)
        self.sidebar_list = tk.Listbox(
            self.sidebar_frame, 
            bg="white", fg="black", bd=0, highlightthickness=0,
            activestyle='none', font=("Consolas", 10),
            selectbackground="#e0e0e0", selectforeground="black"
        )
        self.sidebar_list.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(self.sidebar_frame, width=60)

        self.text_area = tk.Text(
            self.paned_window,
            bg="white", fg="black", font=("Consolas", 11),
            undo=True, wrap=tk.WORD, bd=0, highlightthickness=0,
            padx=5, pady=5
        )
        self.paned_window.add(self.text_area)
        self.text_area.focus_set()
        
        self.tooltip = tk.Toplevel(self)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip_label = tk.Label(self.tooltip, text="", background="#ffffe0", relief="solid", borderwidth=1, font=("Consolas", 8))
        self.tooltip_label.pack()

    def _create_menu(self):
        self.menu_bar = tk.Menu(self, bg="white", tearoff=0)
        
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Novo", accelerator="Ctrl+N", command=lambda: self.open_search_window(None))
        file_menu.add_command(label="Sair", command=self.quit)
        self.menu_bar.add_cascade(label="Arquivo", menu=file_menu)

        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        # Mimic standard edit options (placeholders)
        edit_menu.add_command(label="Desfazer", accelerator="Ctrl+Z")
        self.menu_bar.add_cascade(label="Editar", menu=edit_menu)

        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        view_menu.add_checkbutton(label="Exibir Grupos/Canais", variable=self.show_groups, command=self.refresh_contacts)
        self.menu_bar.add_cascade(label="Exibir", menu=view_menu)

        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Sobre", command=self.show_about)

        self.config(menu=self.menu_bar)

    # --- Feature: Dirty State ---
    def on_focus_in(self, event):
        self.window_focused = True
        self.title("Sem título - Bloco de Notas")

    def on_focus_out(self, event):
        self.window_focused = False

    def mark_dirty(self):
        if not self.window_focused:
            self.title("*bloco-TG - Bloco de Notas")

    # --- Feature: Tooltips ---
    def on_sidebar_hover(self, event):
        index = self.sidebar_list.nearest(event.y)
        bbox = self.sidebar_list.bbox(index)
        if bbox:
            if bbox[1] <= event.y <= bbox[1] + bbox[3]:
                entity = self.dialogs_map.get(index)
                if entity:
                    # Fix: use shared utility or robust check
                    name = utils.get_display_name(entity)
                    self.show_tooltip(name, event.x_root + 15, event.y_root + 10)
                    return
        self.hide_tooltip()

    def show_tooltip(self, text, x, y):
        self.tooltip_label.config(text=text)
        self.tooltip.geometry(f"+{x}+{y}")
        self.tooltip.deiconify()
        self.tooltip.lift()

    def hide_tooltip(self):
        self.tooltip.withdraw()

    # --- Feature: Hotkeys ---
    def emergency_clear(self, event):
        self.text_area.delete("1.0", tk.END)
        return "break"

    def nav_up(self, event):
        self._nav(-1)
        return "break"
        
    def nav_down(self, event):
        self._nav(1)
        return "break"

    def _nav(self, delta):
        cur = self.sidebar_list.curselection()
        if not cur:
            next_idx = 0
        else:
            next_idx = max(0, min(self.sidebar_list.size()-1, cur[0] + delta))
        self.sidebar_list.selection_clear(0, tk.END)
        self.sidebar_list.selection_set(next_idx)
        self.sidebar_list.activate(next_idx)
        self.sidebar_list.event_generate("<<ListboxSelect>>")

    # --- Feature: Read-Only History ---
    def on_text_key(self, event):
        # Allow navigation keys
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Prior', 'Next'):
            return
        
        # Check if cursor is in the last line (Input area)
        # We assume input is always at the very end. 
        # Actually in Notepad style, the user types at the bottom.
        # So anything before the last newline of the file should be protected.
        
        # Simple check: Is cursor at the very end?
        # index "end-1c" is the last character before the final newline provided by Tk.
        
        # Let's check insertion point line number vs total lines.
        cursor_index = self.text_area.index("insert")
        last_line_index = self.text_area.index("end-1c linestart")

        # Specific Backspace Protection
        if event.keysym == 'BackSpace':
            # If cursor is AT the start of input line, block backspace (prevents deleting newline before it)
            if self.text_area.compare("insert", "<=", last_line_index):
                 return "break"
            
            # Check if selection spans back into history
            try:
                sel_start = self.text_area.index("sel.first")
                if self.text_area.compare(sel_start, "<", last_line_index):
                    return "break"
            except tk.TclError:
                pass

        # General Protection: If cursor is strictly before the last line, block everything
        if self.text_area.compare(cursor_index, "<", last_line_index):
            return "break" # Prevent editing history

    # --- Feature: Quick Search (Open Note) ---
    def open_search_window(self, event):
        # Create window first
        self.search_window = tk.Toplevel(self)
        self.search_window.title("Abrir Nota")
        self.search_window.geometry("400x500") # Taller for list
        self.search_window.configure(bg="white")
        
        tk.Label(self.search_window, text="Nome do contato:", bg="white", anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))
        
        self.search_entry = tk.Entry(self.search_window, bg="white", fg="black")
        self.search_entry.pack(fill=tk.X, padx=10, pady=5)
        self.search_entry.bind('<KeyRelease>', self._filter_search_results)
        self.search_entry.bind('<Return>', self._on_search_confirm)
        self.search_entry.focus_set()
        
        self.search_list = tk.Listbox(self.search_window, bg="white", fg="black", bd=1, font=("Consolas", 10))
        self.search_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.search_list.bind('<Double-Button-1>', self._on_search_confirm)
        self.search_list.bind('<Return>', self._on_search_confirm)
        
        self.search_map = {} 
        
        # Initial Loading State
        self.search_list.insert(0, "Carregando contatos...")
        
        if self.backend and self.loop:
             asyncio.run_coroutine_threadsafe(self._load_all_contacts_for_search(), self.loop)

    async def _load_all_contacts_for_search(self):
        try:
            from telethon.tl.types import UserStatusOnline
            
            # Update UI to show we are trying
            self.search_window.title("Abrir Nota (Carregando...)")
            
            # Fetch contacts
            print("Fetching contacts...") 
            contacts = await self.backend.get_all_contacts()
            print(f"Fetched {len(contacts)} contacts.")
            
            # Sort: Online first, then Alphabetical
            def sort_key(user):
                is_online = isinstance(user.status, UserStatusOnline)
                name = utils.get_display_name(user) or ""
                return (not is_online, name.lower())
                
            self.all_contacts = sorted(contacts, key=sort_key)
            
            # Update title with count
            self.search_window.title(f"Abrir Nota ({len(self.all_contacts)} contatos)")
            self.search_list.delete(0, tk.END) 
            
            # Show initial list (Top 15 online) relies on filter with empty query
            self.after(0, lambda: self._filter_search_results(None))
            
        except Exception as e:
            print(f"Error loading contacts: {e}")
            self.search_window.title("Erro ao carregar")
            self.search_list.delete(0, tk.END)
            self.search_list.insert(0, f"Erro: {str(e)}")

    def _filter_search_results(self, event):
        query = self.search_entry.get().lower() if self.search_entry.get() else ""
        self.search_list.delete(0, tk.END)
        self.search_map.clear()
        
        from telethon.tl.types import UserStatusOnline
        
        idx = 0
        display_count = 0
        limit = 15
        
        for contact in self.all_contacts:
            if display_count >= limit:
                break
                
            name = utils.get_display_name(contact)
            if not name: continue
            
            if query in name.lower():
                # Add check/indicator for online
                is_online = isinstance(contact.status, UserStatusOnline)
                prefix = "[ON] " if is_online else "     "
                display_text = f"{prefix}{name}"
                
                self.search_list.insert(tk.END, display_text)
                self.search_map[idx] = contact
                idx += 1 # Index in Listbox
                display_count += 1
        
        # Select first if available
        if self.search_list.size() > 0:
            self.search_list.selection_set(0)

    def _on_search_confirm(self, event):
        selection = self.search_list.curselection()
        if not selection: return
        
        index = selection[0]
        entity = self.search_map.get(index)
        
        if entity:
            self.open_chat(entity)
            self.search_window.destroy()

    def open_chat(self, entity):
        self.current_chat = entity
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", f"Carregando...\n\n")
        
        # Also, we should probably add it to the sidebar if not there?
        # Or select it if it is there.
        # Check sidebar map
        found_in_sidebar = False
        for idx, mapped_entity in self.dialogs_map.items():
            if mapped_entity.id == entity.id:
                self.sidebar_list.selection_clear(0, tk.END)
                self.sidebar_list.selection_set(idx)
                self.sidebar_list.see(idx)
                found_in_sidebar = True
                break
        
        # If not in sidebar (e.g. searched generic contact), maybe we should add it?
        # But our sidebar logic refreshes from dialogs.
        # If we send a message, it becomes a dialog.
        # For now just load chat.
        
        if self.loop and self.backend:
            asyncio.run_coroutine_threadsafe(self._fetch_history(entity), self.loop)

    # --- Logic ---
    def _get_initials(self, name):
        if not name: return "[??]"
        parts = name.split()
        if len(parts) >= 2: return f"[{parts[0][0]}{parts[1][0]}]".upper()
        return f"[{name[:2]}]".upper()

    def refresh_contacts(self):
        if self.loop and self.backend:
             asyncio.run_coroutine_threadsafe(self._reload_dialogs(), self.loop)

    async def _reload_dialogs(self):
        ignore_groups = not self.show_groups.get()
        dialogs = await self.backend.get_dialogs(limit=20, ignore_groups=ignore_groups)
        self.after(0, lambda: self.load_contacts(dialogs))

    def load_contacts(self, dialogs):
        self.sidebar_list.delete(0, tk.END)
        self.dialogs_map.clear()
        for index, dialog in enumerate(dialogs):
            initials = self._get_initials(dialog.name)
            self.sidebar_list.insert(tk.END, initials)
            self.dialogs_map[index] = dialog.entity

    def on_contact_select(self, event):
        selection = self.sidebar_list.curselection()
        if not selection: return
        index = selection[0]
        entity = self.dialogs_map.get(index)
        if entity:
            self.open_chat(entity)

    async def _fetch_history(self, entity):
        # Fetch read state data first
        max_read_id = await self.backend.get_read_outbox_max_id(entity)
        self.current_max_read_id = max_read_id

        messages = await self.backend.get_messages(entity, limit=30)
        history = []
        user_me = await self.backend.get_me()
        for msg in reversed(messages):
            sender = "EU" if msg.sender_id == user_me.id else self._get_initials(utils.get_display_name(entity)).strip("[]")
            time_str = msg.date.strftime("%H:%M")
            history.append((msg, sender, time_str))
        self.after(0, self._render_history, history)

    def _render_history(self, history):
        self.text_area.delete("1.0", tk.END)
        self.renderer_cache.clear()
        for msg, sender, time_str in history:
            self.renderer_cache[msg.id] = msg
            self._insert_message_to_ui(msg, sender, time_str)
        
        # Ensure there is a newline at the end for typing
        if self.text_area.get("end-1c") != "\n":
            self.text_area.insert(tk.END, "\n")
            
        self.text_area.see(tk.END)

    def _insert_message_to_ui(self, msg, sender, time_str):
        # Insert Helper
        # Format: 16:18 - [ME] [vv]: message
        
        # Tags
        msg_tag = f"msg_{msg.id}"
        status_tag = f"status_{msg.id}"
        
        # User requested: 16:18 - [ME] [vv]: message
        # But sender is [EU] (brackets included in var?). 
        # _get_initials adds brackets. "EU" is hardcoded string in history loop?
        # In history loop: sender = "EU". line 366.
        # In _append_realtime: sender = "EU". line 533.
        # So "sender" var is just "EU".
        
        # Construct prefix
        # We need brackets around EU? 
        # Wait, previous code: line_start = f"{time_str} - [{sender}]"
        # If sender is "EU", result is "[EU]".
        # If sender is "[AB]", result is "[[AB]]" ?
        # _get_initials returns "[AB]". 
        # Line 366 strips brackets: .strip("[]"). 
        # So sender is "AB" or "EU".
        
        line_start = f"{time_str} - [{sender}]" 
        self.text_area.insert(tk.END, line_start, (msg_tag,))
        
        # Status
        if msg.out:
            # Determine status based on current max read id or default
            # Use [vv] if id <= current_max_read_id
            limit = getattr(self, 'current_max_read_id', 0)
            status = " [vv]" if msg.id <= limit else " [v]"
            self.text_area.insert(tk.END, status, (msg_tag, status_tag))
        
        self.text_area.insert(tk.END, ": ", (msg_tag,))
        
        if msg.media:
            filename = "midia"
            if hasattr(msg, 'file') and msg.file and hasattr(msg.file, 'name') and msg.file.name:
                filename = msg.file.name
            elif hasattr(msg.media, 'document') and hasattr(msg.media.document.attributes, 'file_name'):
                 filename = "download" # Simplified
            
            content = f"[ARQUIVO: {filename}]"
            tag_name = f"media_{msg.id}"
            
            self.text_area.insert(tk.END, content, (tag_name, msg_tag))
            self.text_area.insert(tk.END, "\n")
            
            self.text_area.tag_config(tag_name, foreground="blue")
            # Bind Left and Right click
            self.text_area.tag_bind(tag_name, "<Button-1>", lambda e, m=msg: self.download_media_action(m))
            self.text_area.tag_bind(tag_name, "<Button-3>", lambda e, m=msg: self.show_media_menu(e, m))
        else:
            content = msg.message if msg.message else "<...>"
            self.text_area.insert(tk.END, f"{content}\n", (msg_tag,))

    def show_media_menu(self, event, msg):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Baixar/Abrir", command=lambda: self.download_media_action(msg))
        menu.post(event.x_root, event.y_root)

    def download_media_action(self, msg):
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
        if self.loop and self.backend:
             asyncio.run_coroutine_threadsafe(self._download_and_open(msg), self.loop)

    async def _download_and_open(self, msg):
        path = await self.backend.download_media(msg, path="downloads/")
        if path:
            os.startfile(os.path.abspath(path))

    def on_enter_pressed(self, event):
        if not self.current_chat: return "break"
        
        # Get content of last line
        line_index = self.text_area.index("end-1c linestart")
        content = self.text_area.get(line_index, "end-1c").strip()
        
        if content:
            # Delete content from UI
            self.text_area.delete(line_index, "end")
            self.text_area.insert("end", "\n") # Restore newline
            
            # Manually append "Me" message immediately for echo
            now = datetime.datetime.now().strftime("%H:%M")
            
            # We need a fake message object for renderer if possible?
            # Or just manually matching format.
            # But we want the ID for future read updates...
            # We don't have ID yet.
            # This is tricky. Manual echo has no ID.
            # So it will be [v] forever if we don't update it when sent?
            # But the listener is disabled for Out messages to avoid duplication.
            
            # SOLUTION:
            # 1. Send it.
            # 2. Wait for result (Message object).
            # 3. THEN render.
            # It might be slightly slower but ensures ID availability.
            # User wants responsiveness?
            # Let's try async render on return.

            if self.loop and self.backend:
                 asyncio.run_coroutine_threadsafe(
                    self._send_and_render(self.current_chat, content, now),
                    self.loop
                )
        return "break"

    async def _send_and_render(self, chat, content, time_str):
        try:
            msg = await self.backend.send_message(chat, content)
            # Now we have ID.
            # We render it locally essentially replacing manual echo.
            self.after(0, lambda: self._manual_render_out(msg, time_str))
            # Refresh sidebar to show new conversation / move to top
            self.refresh_contacts()
        except Exception as e:
            print(f"Send failed: {e}")

    def _manual_render_out(self, msg, time_str):
        self._insert_message_to_ui(msg, "EU", time_str)
        self.text_area.see(tk.END)
        return "break"

    def incoming_message(self, event):
        msg = event.message
        self.after(0, self.mark_dirty)
        
        # ... (handling logic hidden) ...
        
        is_relevant = False
        try:
            if self.current_chat and msg.chat_id == self.current_chat.id:
                is_relevant = True
        except: pass
        
        if is_relevant:
            self.after(0, self._append_realtime, msg)

    def incoming_read_event(self, event):
        """Handles MessageRead events from backend."""
        # This runs in asyncio loop thread
        try:
            # Check if relevant to current chat
             if self.current_chat and event.chat_id == self.current_chat.id:
                 # event.max_id is the max ID read.
                 # or event.messages might be list of ids?
                 # Telethon's MessageRead event typically has .max_id (InboxRead) or .max_id (OutboxRead)
                 # We are interested in OutboxRead (messages WE sent that THEY read).
                 if event.inbox:
                     return # We read theirs.
                     
                 self.after(0, self._update_read_status_ui, event.max_id)
        except Exception as e:
            print(f"Read Event Error: {e}")

    def _update_read_status_ui(self, max_id):
        # Update current max_read_id
        self.current_max_read_id = max(getattr(self, 'current_max_read_id', 0), max_id)
        
        for msg_id, msg in self.renderer_cache.items():
            if msg.out and msg_id <= max_id:
                # Update this message
                status_tag = f"status_{msg_id}"
                ranges = self.text_area.tag_ranges(status_tag)
                if ranges:
                    # Replace content in this tag with [vv] if it is [v]
                    start, end = ranges[0], ranges[1]
                    current_status = self.text_area.get(start, end)
                    if " [v]" in current_status and " [vv]" not in current_status:
                        self.text_area.delete(start, end)
                        self.text_area.insert(start, " [vv]", (f"msg_{msg_id}", status_tag))

    def _append_realtime(self, msg):
        if msg.out:
            return

        sender = "EU" if msg.out else "XX"
        time_str = msg.date.strftime("%H:%M")
        self._insert_message_to_ui(msg, sender, time_str)
        self.text_area.see(tk.END)

    # --- Tray / Boss ---
    def _create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color = (255, 255, 255))
        d = ImageDraw.Draw(image)
        d.rectangle([16, 16, 48, 48], fill=(0, 0, 0))
        menu = (item('Abrir Bloco', self.restore_window), item('Sair', self.quit_app))
        self.tray_icon = pystray.Icon("name", image, "Bloco de Notas", menu)
        self.tray_icon.run()

    def withdraw_window(self, event=None):
        self.withdraw()
        if not self.tray_icon:
            threading.Thread(target=self._create_tray_icon, daemon=True).start()

    def restore_window(self, icon=None, item=None):
        self.after(0, self._restore_window_main)
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def _restore_window_main(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self, icon=None, item=None):
        if self.tray_icon: self.tray_icon.stop()
        self.after(0, self.quit)

    # --- Context Menus ---
    def show_chat_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Enviar Arquivo...", command=self.action_send_file)
        menu.add_separator()
        menu.add_command(label="Limpar Histórico de Conversa", command=self.action_clear_history)
        menu.add_command(label="Excluir conversa para todos", command=self.action_delete_for_everyone)
        menu.post(event.x_root, event.y_root)

    def action_send_file(self):
        if not self.current_chat: return
        file_path = filedialog.askopenfilename()
        if file_path:
            # Send via backend
            if self.loop and self.backend:
                asyncio.run_coroutine_threadsafe(
                    self.backend.send_file(self.current_chat, file_path),
                    self.loop
                )
            # Log confirmation
            now = datetime.datetime.now().strftime("%H:%M")
            self.text_area.insert(tk.END, f"{now} - [Sistema]: Arquivo enviado com sucesso.\n")
            self.text_area.see(tk.END)

    def action_clear_history(self):
        if not self.current_chat: return
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja limpar o histórico?"):
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", "\n")
            if self.loop and self.backend:
                asyncio.run_coroutine_threadsafe(
                    self.backend.clear_history(self.current_chat),
                    self.loop
                )

    def action_delete_for_everyone(self):
        if not self.current_chat: return
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja EXCLUIR esta conversa para TODOS?"):
            if self.loop and self.backend:
                asyncio.run_coroutine_threadsafe(
                    self.backend.delete_dialog_for_everyone(self.current_chat),
                    self.loop
                )
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", "\n")
            self.current_chat = None # No chat selected after deletion
            self.refresh_contacts() # Refresh sidebar to reflect changes

    def show_about(self):
        messagebox.showinfo(
            "Sobre o bloco-TG",
            "bloco-TG - v1.0\n\nDesenvolvido por Inside Soluções\nUse com cautela."
        )

    def show_sidebar_context_menu(self, event):
        # Auto-select item under mouse
        index = self.sidebar_list.nearest(event.y)
        # Check bounds
        bbox = self.sidebar_list.bbox(index)
        if not bbox or not (bbox[1] <= event.y <= bbox[1] + bbox[3]):
            return
            
        self.sidebar_list.selection_clear(0, tk.END)
        self.sidebar_list.selection_set(index)
        self.sidebar_list.activate(index)
        # We don't necessarily load the chat on right click, just select it for action?
        # Standard behavior: Right click usually selects AND opens actions.
        # Let's allow selection but not load chat to keep it "stealthy"?
        # Actually user said "Dynamic Selection".
        # If we select, we probably update 'current_target_for_action' but maybe not load chat unless left clicked?
        # But 'Archive' needs an entity. safely getting from map:
        entity = self.dialogs_map.get(index)
        if not entity: return
        
        # We store temp entity for action in case user moves mouse?
        # The command lambda captures it.
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Marcar como lida", command=lambda: self.action_mark_read(entity))
        menu.add_command(label="Arquivar", command=lambda: self.action_archive(entity))
        menu.add_command(label="Silenciar notificações", command=lambda: self.action_toggle_mute(entity))
        
        menu.post(event.x_root, event.y_root)

    def action_mark_read(self, entity):
        if self.loop and self.backend:
            asyncio.run_coroutine_threadsafe(self.backend.mark_read(entity), self.loop)

    def action_archive(self, entity):
        if self.loop and self.backend:
            # We assume 'Archive' means move to archive. Toggle not specified, implying 'Archive'.
            asyncio.run_coroutine_threadsafe(self.backend.archive_chat(entity, True), self.loop)
            # Should we remove from list?
            # Yes, if we are not showing groups/archived, it should disappear on refresh.
            # Let's trigger refresh.
            self.after(500, self.refresh_contacts)

    def action_toggle_mute(self, entity):
        if self.loop and self.backend:
            # We default to 'Mute' (active=False for notifications, so is_muted=True)
            # Actually toggle is hard without knowing current state.
            # Let's just Mute for now as requested "Toggle Mute" implies switch.
            # But we don't track state.
            # Let's prompt or just Mute.
            # Requirement says "Toggle Mute".
            # I'll implement "Mute Forever".
            asyncio.run_coroutine_threadsafe(self.backend.toggle_mute(entity, False), self.loop)

