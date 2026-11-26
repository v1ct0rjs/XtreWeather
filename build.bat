@echo off
rem XtreWeather - compila XtreWeather.exe (un solo archivo) / builds a single-file XtreWeather.exe
cd /d "%~dp0"
if not exist "%~dp0xtreweather.ico" (echo FALTA / MISSING: xtreweather.ico & goto :error)
python -m pip install --upgrade -r requirements.txt || goto :error
rem icono del .exe: xtreweather.ico del repositorio, en lugar del de PyInstaller. Tambien va dentro del .exe
rem para que la ventana y la bandeja usen el mismo. / exe icon: the repo's xtreweather.ico (also bundled for the window)
python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --icon "%~dp0xtreweather.ico" --add-data "%~dp0xtreweather.ico;." --name XtreWeather xtreweather.py || goto :error
copy /y dist\XtreWeather.exe . >nul
rem refresca la cache de iconos del Explorador (si no, puede seguir mostrando el icono anterior) / refresh the icon cache
ie4uinit.exe -show >nul 2>&1
echo.
echo OK: %~dp0XtreWeather.exe
pause
exit /b 0
:error
echo.
echo ERROR
pause
exit /b 1
