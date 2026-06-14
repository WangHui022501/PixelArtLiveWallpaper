@echo off
set FILE=%~dp0healing-pixel-art.html

:: Try Microsoft Edge first (usually available on Windows 10/11)
set EDGE="%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
set EDGE2="%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

:: Try Chrome
set CHROME="%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set CHROME2="%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set CHROME3="%LocalAppData%\Google\Chrome\Application\chrome.exe"

if exist %EDGE% (
  %EDGE% --kiosk "file:///%FILE:\=/%"  --kiosk-printing --disable-pinch
  goto :eof
)
if exist %EDGE2% (
  %EDGE2% --kiosk "file:///%FILE:\=/%"  --disable-pinch
  goto :eof
)
if exist %CHROME% (
  %CHROME% --kiosk "file:///%FILE:\=/%"  --disable-pinch
  goto :eof
)
if exist %CHROME2% (
  %CHROME2% --kiosk "file:///%FILE:\=/%"  --disable-pinch
  goto :eof
)
if exist %CHROME3% (
  %CHROME3% --kiosk "file:///%FILE:\=/%"  --disable-pinch
  goto :eof
)

echo Neither Edge nor Chrome was found. Please open healing-pixel-art.html manually.
pause
