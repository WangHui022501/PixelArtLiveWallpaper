@echo off
cd /d "%~dp0"
python wallpaper_app.py
if errorlevel 1 (
  echo.
  echo Failed to launch. Try running install.bat first.
  pause
)
