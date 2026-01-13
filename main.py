import asyncio
import os
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
from telethon.errors import SessionPasswordNeededError

from src.client import TelegramBackend
from src.gui import NotepadApp
from src.utils import load_config, get_session_path, save_config
from src.setup_wizard import SetupWizard, CodeRequestDialog, TwoFADialog

def run_backend_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def init_data(backend, app):
    """
    Fetches initial data (dialogs) and populates UI.
    """
    try:
        dialogs = await backend.get_dialogs(limit=20)
        app.after(0, lambda: app.load_contacts(dialogs))
        backend.add_new_message_listener(app.incoming_message)  
    except Exception as e:
        print(f"Data Init Error: {e}")

async def perform_login(backend, root_for_dialogs):
    """
    Orchestrates the login flow.
    Returns True if successful, False otherwise.
    """
    print("perform_login checked auth status...")
    if await backend.is_user_authorized():
        print("User already authorized.")
        return True
        
    print("User NOT authorized. Requesting code...")
    # Not authorized, need flow
    try:
        await backend.send_code_request()
        print("Code requested successfully.")
        
        # 1. Ask for Code
        loop = asyncio.get_running_loop()
        code_future = loop.create_future()
        
        def ask_code():
            print("UI: Opening CodeRequestDialog...")
            try:
                dlg = CodeRequestDialog(root_for_dialogs, backend.phone)
                if dlg.code:
                    print(f"UI: Code received ({len(dlg.code)} chars).")
                    loop.call_soon_threadsafe(code_future.set_result, dlg.code)
                else:
                    print("UI: Code dialog cancelled.")
                    loop.call_soon_threadsafe(code_future.set_exception, Exception("O código é obrigatório."))
            except Exception as e:
                print(f"UI Error: {e}")
                loop.call_soon_threadsafe(code_future.set_exception, e)

        root_for_dialogs.after(0, ask_code)
        
        print("Waiting for code input...")
        code = await code_future
        print("Code input received.")
        
        # 2. Try sign in
        try:
            print("Attempting sign_in...")
            await backend.sign_in_with_code(code)
            print("Sign in successful.")
            return True
        except SessionPasswordNeededError:
            print("2FA Password Required.")
            # 3. 2FA Required
            pwd_future = loop.create_future()
            def ask_pwd():
                print("UI: Opening TwoFADialog...")
                try:
                    dlg = TwoFADialog(root_for_dialogs)
                    if dlg.password:
                        print("UI: Password received.")
                        loop.call_soon_threadsafe(pwd_future.set_result, dlg.password)
                    else:
                        print("UI: 2FA dialog cancelled.")
                        loop.call_soon_threadsafe(pwd_future.set_exception, Exception("A senha 2FA é obrigatória."))
                except Exception as e:
                    loop.call_soon_threadsafe(pwd_future.set_exception, e)
            
            root_for_dialogs.after(0, ask_pwd)
            print("Waiting for password input...")
            password = await pwd_future
            print("Password input received. Verifying...")
            
            await backend.sign_in_with_code(code, password=password)
            print("2FA Sign in successful.")
            return True
            
    except Exception as e:
        print(f"Login Exception: {e}")
        # Show error
        root_for_dialogs.after(0, lambda: messagebox.showerror("Erro de Login", str(e), parent=root_for_dialogs))
        return False

def on_setup_complete(api_id, api_hash, phone):
    """Callback when setup is finished."""
    print("Setup finished. Config received.")
    # Config is saved by Wizard, so we just reload or use data
    # But init logic needs access to backend/app/loop which are in main scope
    # We can pass them or use a closure.
    pass 

def main():
    # FIX: Redirect stdout/stderr to file if running frozen (noconsole)
    if getattr(sys, 'frozen', False):
        try:
            log_path = os.path.join(os.path.dirname(sys.executable), 'debug.log')
            sys.stdout = open(log_path, 'w', encoding='utf-8', buffering=1)
            sys.stderr = sys.stdout
        except Exception as e:
            pass

    print("Launching bloco-TG (Final)...")
    try:
        # 1. Create Root Application (Hidden)
        print("Initializing Asyncio Loop...")
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=run_backend_loop, args=(loop,), daemon=True)
        t.start()
        
        print("Initializing NotepadApp...")
        app = NotepadApp(backend=None, loop=loop)
        app.withdraw() # Hide initially
        print("NotepadApp initialized.")
        
        # 2. Check/Load Config
        print("Loading Config...")
        initial_config = load_config()
        print(f"Config loaded: {bool(initial_config)}")
        
        # Internal function to continue startup after config is ready
        def continue_startup(config):
            print("Continuing startup with config...")
            # 3. Init Backend
            print("Initializing Backend...")
            if not config:
                print("CRITICAL: Config is still None!")
                app.quit()
                return

            try:
                session_file = get_session_path()
                backend = TelegramBackend(
                    api_id=config.get('api_id'),
                    api_hash=config.get('api_hash'),
                    phone=config.get('phone'),
                    session_path=session_file
                )
                app.backend = backend
                
                # Connect
                print("Connecting to Telegram...")
                asyncio.run_coroutine_threadsafe(connect_and_auth(backend, app, loop), loop)
            except Exception as e:
                print(f"Backend creation failed: {e}")
                messagebox.showerror("Erro Fatal", f"Erro no backend: {e}")
                app.quit()

        async def connect_and_auth(backend, app, loop):
            print("Async Connect started...")
            try:
                await backend.connect()
                print("Connected.")
                
                # Auth
                if not await backend.is_user_authorized():
                    print("User not authorized. Starting login flow...")
                    success = await perform_login(backend, app)
                    if not success:
                        print("Login failed or cancelled.")
                        app.quit()
                        return
                    print("Login successful.")
                
                # Init Data
                print("Fetching Dialogs...")
                await init_data(backend, app)
                
                # Show Main Window
                print("Showing Main Window...")
                app.after(0, app.deiconify)
                app.after(0, app.lift)
                
            except Exception as e:
                print(f"Startup Error: {e}")
                app.after(0, lambda: messagebox.showerror("Erro", f"Falha na conexão: {e}"))
                app.quit()

        def on_wizard_complete(api_id, api_hash, phone):
            # Callback from SetupWizard
            print("Wizard complete callback triggered.")
            new_config = {
                'api_id': api_id,
                'api_hash': api_hash,
                'phone': phone
            }
            # Continue startup
            app.after(0, lambda: continue_startup(new_config))

        def startup():
            print("Startup sequence begun...")
            # This runs inside the main loop
            if not initial_config:
                print("Config missing, showing wizard (Async)...")
                # Launch Wizard NON-BLOCKING
                SetupWizard(app, on_wizard_complete)
                # We return here. Mainloop continues running.
                # Wizard will call on_wizard_complete when done.
            else:
                continue_startup(initial_config)

        # Schedule startup and run loop
        app.after(100, startup)
        try:
            print("Starting Mainloop...")
            app.mainloop()
        except KeyboardInterrupt:
            pass
    except Exception as e:
        print(f"CRITICAL MAIN CRASH: {e}")
        import traceback
        traceback.print_exc()
        # input("Press Enter to exit...") # Removed for non-console

if __name__ == '__main__':
    main()
