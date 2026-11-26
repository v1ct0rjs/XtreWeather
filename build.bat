@echo off
rem XtreWeather - compila XtreWeather.exe (un solo archivo) / builds a single-file XtreWeather.exe
cd /d "%~dp0"
python -m pip install --upgrade -r requirements.txt || goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --name XtreWeather xtreweather.py || goto :error
copy /y dist\XtreWeather.exe . >nul
echo.
echo OK: %~dp0XtreWeather.exe
pause
exit /b 0
:error
echo.
echo ERROR
pause
exit /b 1
