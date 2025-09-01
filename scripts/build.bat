
rmdir /s /q dist
rmdir /s /q build
@echo off
python -m PyInstaller main.py --contents-directory . --name "RFID Agent" --add-data="icon.ico;." --icon=icon.ico