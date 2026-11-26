# Changelog

## Unreleased
- Weather icons for each server (clear, partly cloudy, overcast, rain, heavy rain, no data) in the Overview table, on the server tabs and in each tab's Status block.
- `XtreWeather.exe` uses the repository's `xtreweather.ico` instead of PyInstaller's default icon; the window and tray load the same file, so they always match. Replace that file to change the icon everywhere.
- When run from source on Windows, the taskbar shows the XtreWeather icon instead of Python's.
- Fix: the state no longer flickers between *running* and *session idle* on an empty server, and the weather is no longer sent to a paused server. The state is now decided each time the plugin rewrites its data: *running* if the session clock (ET) advanced since the previous write, *session idle* if it didn't. Works for servers that pause when empty and for those that don't.

## 0.2.0
- English / Spanish interface (automatic from the Windows language, or chosen in Settings).
- Manual mode has its own transition (20 s by default) and applies clouds instantly.
- About dialog. New defaults: fetch every 15 min, 300 s real weather transition.
- Public release: README, user manual (EN/ES), GPL v3 licence.

## 0.1.0
- First version: multiple servers, real weather (Open-Meteo, OpenWeatherMap, WeatherAPI), manual and disabled modes, track coordinates table, tray, start with Windows.
