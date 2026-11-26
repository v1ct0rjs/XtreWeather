# Changelog

## Unreleased
- Weather icons for each server (clear, partly cloudy, overcast, rain, heavy rain, no data) in the Overview table, on the server tabs and in each tab's Status block.
- `XtreWeather.exe` now has the same icon as the app window: `build.bat` generates `xtreweather.ico` from the app's own drawing (`xtre_iconos.py`).
- When run from source on Windows, the taskbar shows the XtreWeather icon instead of Python's.

## 0.2.0
- English / Spanish interface (automatic from the Windows language, or chosen in Settings).
- Manual mode has its own transition (20 s by default) and applies clouds instantly.
- About dialog. New defaults: fetch every 15 min, 300 s real weather transition.
- Public release: README, user manual (EN/ES), GPL v3 licence.

## 0.1.0
- First version: multiple servers, real weather (Open-Meteo, OpenWeatherMap, WeatherAPI), manual and disabled modes, track coordinates table, tray, start with Windows.
