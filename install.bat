@echo off
echo ✦ Installing Pixel World dependencies...
echo.
pip install pywebview --break-system-packages 2>nul || pip install pywebview
echo.
echo Done! You can now run launch_app.bat
pause
