@echo off
rem XtreWeather - compila XtreWeather.exe (un solo archivo) / builds a single-file XtreWeather.exe
cd /d "%~dp0"
python -m pip install --upgrade -r requirements.txt || goto :error
rem icono del .exe generado con el mismo dibujo que usa la aplicacion / exe icon drawn by the app itself
python xtre_iconos.py xtreweather.ico || goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --icon xtreweather.ico --name XtreWeather xtreweather.py || goto :error
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
