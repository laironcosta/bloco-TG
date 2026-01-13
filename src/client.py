import os
from telethon import TelegramClient, events
from dotenv import load_dotenv
from telethon.errors import SessionPasswordNeededError

from src.constants import DEFAULT_API_ID, DEFAULT_API_HASH

class TelegramBackend:
    def __init__(self, api_id=None, api_hash=None, phone=None, session_path='bloco_tg'):
        # Load from arguments or defaults (constants/env)
        # Priority: Args > Constants > Env (Fallback)
        
        # If args not provided, try constants first (Standard for portable)
        self.api_id = api_id or DEFAULT_API_ID or os.getenv('TG_API_ID')
        self.api_hash = api_hash or DEFAULT_API_HASH or os.getenv('TG_API_HASH')
        self.phone = phone or os.getenv('TG_PHONE')
        
        if not self.api_id or not self.api_hash:
            raise ValueError("API Credentials missing.")

        # Ensure session is relative (portable)
        # If absolute path not provided, assume relative to execution base
        if not os.path.isabs(session_path):
             # We can't easily import utils here if circular, but client is low level. 
             # We'll rely on the caller to pass a good path, or default to current dir (which is fine for portable if cwd is correct)
             pass
             
        self.session_path = session_path
        self.client = TelegramClient(self.session_path, int(self.api_id), self.api_hash)
        self.listeners = [] # Callbacks for new messages

    async def connect(self):
        """
        Connects to Telegram.
        """
        await self.client.connect()

    async def is_user_authorized(self):
        """
        Checks if the user is already logged in.
        """
        return await self.client.is_user_authorized()

    async def send_code_request(self):
        """Sends login code request"""
        if not self.phone:
            raise ValueError("Phone number must be set for sending code request.")
        await self.client.send_code_request(self.phone)

    async def sign_in_with_code(self, code, password=None):
        """
        Signs in using the code (and password if needed).
        This is for GUI flow.
        """
        try:
            await self.client.sign_in(self.phone, code)
        except SessionPasswordNeededError:
            if password:
                await self.client.sign_in(password=password)
            else:
                raise SessionPasswordNeededError("2FA Password Required")
        
    async def start_interactive_login(self, phone=None, code_callback=None):
        """
        Starts the interactive login process. 
        If phone/callbacks are not provided, uses Telethon's default CLI.
        """
        if phone and code_callback:
            # GUI based auth could go here later
            await self.client.start(phone=phone, code_callback=code_callback)
        else:
            await self.client.start()
        
    async def get_me(self):
        """
        Returns the current user.
        """
        return await self.client.get_me()

    async def get_dialogs(self, limit=20, ignore_groups=True):
        """
        Fetches the recent conversations.
        If ignore_groups is True, only return User dialogs.
        """
        # Fetch more to allow filtering
        fetch_limit = 100 if ignore_groups else limit
        dialogs = await self.client.get_dialogs(limit=fetch_limit)
        
        if ignore_groups:
            # Filter: only users
            filtered = [d for d in dialogs if d.is_user]
            return filtered[:limit] # Return original limit count
        return dialogs

    async def get_messages(self, entity, limit=50):
        """
        Fetches history for a specific chat.
        """
        return await self.client.get_messages(entity, limit=limit)

    async def send_message(self, entity, text):
        """
        Sends a text message to the specified entity.
        """
        return await self.client.send_message(entity, text)

    async def download_media(self, message, path=None):
        """
        Downloads media from a message.
        """
        return await self.client.download_media(message, file=path)

    async def send_file(self, entity, path):
        """
        Sends a file to the specified entity.
        """
        return await self.client.send_file(entity, path)

    async def clear_history(self, entity):
        """
        Clears the message history for the entity (delete for everyone if possible).
        """
        # DeleteHistoryRequest is often cleaner for "Clear History" action
        from telethon.tl.functions.messages import DeleteHistoryRequest
        await self.client(DeleteHistoryRequest(
            peer=entity,
            max_id=0,
            just_clear=False,
            revoke=True
        ))

    async def mark_read(self, entity):
        """
        Marks the chat as read.
        """
        await self.client.send_read_acknowledge(entity)

    async def archive_chat(self, entity, archive=True):
        """
        Archives (folder=1) or Unarchives (folder=0) a chat.
        """
        await self.client.edit_folder(entity, folder=1 if archive else 0)

    async def toggle_mute(self, entity, active=True):
        """
        Mutes or unmutes a chat.
        """
        until = 2147483647 if not active else 0 
        await self.client.edit_notify_settings(entity, mute_until=until)

    async def delete_dialog_for_everyone(self, entity):
        """Deletes the dialog for everyone (revokes history)."""
        await self.client.delete_dialog(entity, revoke=True)

    async def get_all_contacts(self):
        """
        Retrieves all contacts using raw API request.
        """
        from telethon.tl.functions.contacts import GetContactsRequest
        # hash=0 forces full refresh
        result = await self.client(GetContactsRequest(hash=0))
        # result can be contacts.Contacts (which has .users) or contacts.ContactsNotModified
        if hasattr(result, 'users'):
            return result.users
        return []

    async def get_read_outbox_max_id(self, entity):
        """
        Returns the max ID of messages read by the peer (outbox).
        Used to determine [vv] status for history.
        """
        try:
            from telethon.tl.functions.messages import GetPeerDialogsRequest
            from telethon.tl.types import InputDialogPeer
            
            # Fetch specific dialog info for this peer
            # This is more accurate than iter_dialogs(limit=50) for random chats
            res = await self.client(GetPeerDialogsRequest(
                peers=[InputDialogPeer(peer=entity)]
            ))
            
            if res.dialogs:
                return res.dialogs[0].read_outbox_max_id
        except Exception as e:
            print(f"Error fetching read state: {e}")
        return 0

    def add_new_message_listener(self, callback):
        """
        Registers a callback that will be called when a new message arrives.
        Callback signature: callback(event)
        """
        @self.client.on(events.NewMessage)
        async def handler(event):
            try:
                # We can do some preprocessing here if needed
                callback(event)
            except Exception as e:
                print(f"Error in message handler: {e}")

    def add_read_listener(self, callback):
        """
        Registers a callback for MessageRead events.
        """
        @self.client.on(events.MessageRead)
        async def handler(event):
            try:
                callback(event)
            except Exception as e:
                print(f"Error in read handler: {e}")

    async def disconnect(self):
        await self.client.disconnect()
