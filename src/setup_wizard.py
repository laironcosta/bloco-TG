import tkinter as tk
from tkinter import messagebox
import asyncio
from src.utils import save_config
from src.constants import DEFAULT_API_ID, DEFAULT_API_HASH

class SetupWizard(tk.Toplevel):
    def __init__(self, parent, on_complete_callback):
        super().__init__(parent)
        self.on_complete_callback = on_complete_callback
        self.title("Configuração de Fonte") # Stealth title
        self.geometry("400x250") # Smaller height since fields removed
        self.resizable(False, False)
        self.configure(bg="white")
        
        # Center window
        self._center_window()

        self.lift()
        self.focus_force()
        self.grab_set()
        
        self._setup_ui()
        
        # Force refresh
        self.update_idletasks()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def on_close(self):
        self.destroy()
        # Callback with None implies cancel
        # We rely on caller to handle if callback wasn't called with success
        
    def quit(self):
        self.destroy()
        
    def _setup_ui(self):
        # Font mimics Notepad dialogs
        font_label = ("Segoe UI", 9)
        font_entry = ("Consolas", 10)
        
        pad_x = 20
        pad_y = 5
        
        # Header (Looks like font selection but actually config)
        tk.Label(self, text="Inicialização do Sistema", bg="white", font=("Segoe UI", 12, "bold")).pack(pady=15)
        
        # Phone Only
        tk.Label(self, text="Telefone (ex: +5511999999999):", bg="white", font=font_label, anchor='w').pack(fill='x', padx=pad_x)
        self.entry_phone = tk.Entry(self, bg="white", font=font_entry, relief="solid", bd=1)
        self.entry_phone.pack(fill='x', padx=pad_x, pady=pad_y)
        self.entry_phone.bind('<Return>', lambda e: self.on_submit())
        self.entry_phone.focus_set()
        
        # Info
        tk.Label(self, text="Informe seu número para autenticar.", bg="white", fg="gray", font=("Segoe UI", 8)).pack(pady=15)
        
        # Buttons
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill='x', padx=pad_x, pady=10)
        
        tk.Button(btn_frame, text="Cancelar", command=self.quit, width=10).pack(side='right', padx=5)
        tk.Button(btn_frame, text="Entrar", command=self.on_submit, width=10).pack(side='right', padx=5)
        
    def on_submit(self):
        phone = self.entry_phone.get().strip()
        
        if not phone:
            messagebox.showerror("Erro", "O telefone é obrigatório.")
            return

        # Save with embedded constants
        try:
            save_config(DEFAULT_API_ID, DEFAULT_API_HASH, phone)
            
            # Show a pseudo-loading or just close
            self.destroy() 
            if self.on_complete_callback:
                self.on_complete_callback(DEFAULT_API_ID, DEFAULT_API_HASH, phone)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar configuração: {e}")

class CodeRequestDialog(tk.Toplevel):
    def __init__(self, parent, phone):
        super().__init__(parent)
        self.code = None
        self.title("Confirmação de Segurança")
        self.geometry("400x200")
        self.configure(bg="white")
        self.resizable(False, False)
        
        # Center
        # self.transient(parent) # REMOVED: Fix visibility on hidden parent
        self.lift()
        self.focus_force()
        self.grab_set()
        
        # UI
        font_label = ("Segoe UI", 10)
        font_entry = ("Consolas", 14)
        
        tk.Label(self, text="Verificação Telegram", bg="white", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))
        tk.Label(self, text=f"Insira o código enviado para {phone}", bg="white", font=font_label, fg="gray").pack()
        
        self.entry_code = tk.Entry(self, font=font_entry, justify='center', relief='solid', bd=1)
        self.entry_code.pack(pady=20, padx=50, fill='x')
        self.entry_code.bind('<Return>', lambda e: self.on_confirm())
        self.entry_code.focus_set()
        
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill='x', padx=50, pady=10)
        tk.Button(btn_frame, text="Confirmar", command=self.on_confirm, width=15, relief="flat", bg="#f0f0f0").pack()
        
        self.update_idletasks()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        parent.wait_window(self)
        
    def on_confirm(self):
        self.code = self.entry_code.get().strip()
        if self.code:
            self.destroy()

class TwoFADialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.password = None
        self.title("Autenticação de Dois Fatores")
        self.geometry("400x200")
        self.configure(bg="white")
        self.resizable(False, False)
        
        # Center
        # self.transient(parent) # REMOVED: Fix visibility on hidden parent
        self.lift()
        self.focus_force()
        self.grab_set()
        
        # UI
        font_label = ("Segoe UI", 10)
        font_entry = ("Consolas", 12)
        
        tk.Label(self, text="Proteção por Senha (2FA)", bg="white", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))
        tk.Label(self, text="Esta conta está protegida por uma senha adicional.", bg="white", font=font_label, fg="gray").pack()
        
        self.entry_pwd = tk.Entry(self, font=font_entry, justify='center', relief='solid', bd=1, show="•")
        self.entry_pwd.pack(pady=20, padx=50, fill='x')
        self.entry_pwd.bind('<Return>', lambda e: self.on_confirm())
        self.entry_pwd.focus_set()
        
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill='x', padx=50, pady=10)
        tk.Button(btn_frame, text="Desbloquear", command=self.on_confirm, width=15, relief="flat", bg="#f0f0f0").pack()
        
        self.update_idletasks()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        parent.wait_window(self)
        
    def on_confirm(self):
        self.password = self.entry_pwd.get().strip()
        if self.password:
            self.destroy()
