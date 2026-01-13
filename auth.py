import asyncio
import os
from src.client import TelegramBackend

async def run_auth():
    print("=== bloco-TG Authentication ===")
    
    if not os.path.exists('.env'):
        print("ERROR: .env file not found.")
        return

    try:
        backend = TelegramBackend()
        await backend.connect()
        
        if not await backend.is_user_authorized():
            print("Starting interactive login...")
            # This triggers Telethon's built-in console input for phone/code/password
            await backend.start_interactive_login()
            print("\nSuccessfully logged in!")
        else:
            print("Already logged in.")
            
        me = await backend.get_me()
        print(f"Session active for: {me.first_name} (ID: {me.id})")
        print("You can now run 'main.py'.")
        
        await backend.disconnect()

    except Exception as e:
        print(f"Auth Error: {e}")

if __name__ == '__main__':
    asyncio.run(run_auth())
