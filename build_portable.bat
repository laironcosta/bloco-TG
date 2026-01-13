@echo off
echo Building bloco-TG Portable...
echo Ensure you have pyinstaller installed: pip install pyinstaller
echo.

if not exist "notepad.ico" (
    echo WARNING: notepad.ico not found. Using default icon.
    pyinstaller --noconsole --onefile --name "bloco-TG" --hidden-import "telethon" main.py
) else (
    pyinstaller --noconsole --onefile --name "bloco-TG" --icon "notepad.ico" --hidden-import "telethon" main.py
)

echo.
echo Build complete! Check the 'dist' folder for bloco-TG.exe
pause
