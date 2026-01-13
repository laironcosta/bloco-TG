@echo off
echo Building bloco-TG (Notepad)...
pyinstaller --noconsole --onefile --name="Notepad" --add-data "src;src" --hidden-import="telethon.extensions.html" --hidden-import="telethon.extensions.markdown" main.py
echo Build complete! Check the 'dist' folder.
pause
