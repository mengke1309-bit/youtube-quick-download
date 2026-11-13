@echo off
rem Start YouTube download bridge service (127.0.0.1:17890), silent background.
set "PYW=C:\Users\mengk\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
if exist "%PYW%" (
  start "" /min "%PYW%" "%~dp0yt_bridge.pyw"
) else (
  start "" /min pythonw "%~dp0yt_bridge.pyw"
)
exit /b 0
