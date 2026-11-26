"""
xtre_i18n.py - Textos de XtreWeather en varios idiomas / XtreWeather UI strings.

Para añadir un idioma: copia el bloque "en", cambia la clave (p. ej. "it") y traduce los valores.
To add a language: copy the "en" block, change its key (e.g. "it") and translate the values.
"""
import locale

IDIOMAS = {"es": "Español", "en": "English"}

TEXTOS = {
    "es": {
        # --- estados
        "state_stopped": "parado",
        "state_noplugin": "sin plugin de memoria compartida",
        "state_nocontrol": "sin control de clima (EnableWeatherControlInput)",
        "state_off": "desactivado",
        "state_nocoords": "'{track}' sin coordenadas (Ajustes > Circuitos)",
        "state_waitdata": "esperando datos meteorológicos",
        "state_idle": "sesión parada (esperando a que entre alguien)",
        "state_pending": " · envío pendiente",
        "state_running": "en marcha",
        # --- registro
        "log_started": "{app} {ver} iniciado. Configuración: {path}",
        "log_not_windows": "AVISO: no es Windows, no se detectarán servidores (modo prueba).",
        "log_detected": "Servidor {n}: detectado (PID {pid})",
        "log_closed": "Servidor {n}: se ha cerrado",
        "log_real": "Servidor {n}: tiempo real {info}  ->  {clima}",
        "log_fetch_error": "Servidor {n}: error consultando {prov}: {err}",
        "log_new_session": "Servidor {n}: nueva sesión ({ses})",
        "log_track_changed": "Servidor {n}: circuito cambiado a {track}",
        "log_no_control": "Servidor {n}: el plugin no tiene activado EnableWeatherControlInput",
        "log_sent": "Servidor {n}: enviado {clima} (en {s} s de sesión, v{ver})",
        "log_send_error": "Servidor {n}: error al enviar: {err}",
        "log_internal": "ERROR interno:\n{tb}",
        "log_settings_saved": "Ajustes guardados.",
        # --- clima
        "weather_desc": "lluvia {r:.2f} · nubes {c:.2f} · {t:.1f} °C · viento {w:.1f} m/s",
        "real_info": "{place}  ·  {t:.1f} °C, nubes {c:.0f} %, precip. {mm:.1f} mm/h, viento {w:.1f} m/s  ({hora})",
        "forecast": "pronóstico",
        "sky_clear": "Despejado", "sky_partly": "Poco nuboso", "sky_cloudy": "Nublado",
        "sky_rain": "Lluvia", "sky_heavy_rain": "Lluvia fuerte", "sky_nodata": "Sin datos",
        # --- sesiones y fases
        "ses_test": "Test day", "ses_practice": "Práctica {i}", "ses_qual": "Clasificación {i}",
        "ses_warmup": "Warmup", "ses_race": "Carrera {i}",
        "phases": ["antes de empezar", "reconocimiento", "parrilla", "formación", "semáforo",
                   "bandera verde", "safety car", "parada", "terminada", "pausa"],
        # --- proveedores y errores
        "prov_openmeteo": "Open-Meteo (gratis, sin clave)",
        "prov_openweathermap": "OpenWeatherMap (clave gratuita)",
        "prov_weatherapi": "WeatherAPI.com (clave gratuita)",
        "err_key": "clave API incorrecta o sin permiso",
        "err_limit": "límite de consultas alcanzado",
        "err_http": "HTTP {code}",
        "err_conn": "sin conexión ({r})",
        "err_timeout": "tiempo de espera agotado",
        "err_nokey": "falta la clave de {prov} (Ajustes > Claves API)",
        "err_unknown_prov": "proveedor desconocido: {prov}",
        "err_unexpected": "respuesta inesperada del proveedor ({e})",
        # --- ventana principal
        "win_title": "{app} {ver} - clima para rFactor 2",
        "tab_summary": "Resumen",
        "tab_server": "Servidor {n}",
        "btn_add_server": "+ Servidor",
        "btn_settings": "Ajustes...",
        "btn_about": "Acerca de...",
        "attribution": 'Datos meteorológicos: <a href="https://open-meteo.com/">Open-Meteo.com</a> (CC BY 4.0) '
                       '· OpenWeatherMap · WeatherAPI.com',
        "col_srv": "Srv", "col_state": "Estado", "col_track": "Circuito", "col_session": "Sesión",
        "col_mode": "Modo", "col_weather": "Clima en el servidor", "col_last": "Último envío",
        "summary_help": "Los servidores en marcha se detectan solos (por su perfil playerN). "
                        "Doble clic en una fila para configurar ese servidor. "
                        "El clima solo se aplica con la sesión corriendo (alguien conectado).",
        "mode_real": "Tiempo real", "mode_manual": "Manual", "mode_off": "Desactivado",
        "tray_show": "Mostrar", "tray_quit": "Salir",
        "tray_tooltip": "{app}: {k} servidor(es) con sesión en marcha",
        "tray_msg": "Sigue funcionando en la bandeja. Clic derecho > Salir para cerrar.",
        "add_title": "Añadir servidor", "add_prompt": "Número de servidor (perfil playerN):",
        "remove_title": "Quitar",
        "remove_running": "Ese servidor está en marcha; se volvería a añadir solo.\n"
                          "Si no quieres que se toque su clima, ponlo en 'Desactivado'.",
        "remove_confirm": "¿Quitar el servidor {n} y su configuración?",
        # --- pestaña servidor
        "grp_mode": "Modo", "grp_state": "Estado", "grp_real": "Tiempo real", "grp_manual": "Manual",
        "mode_off_long": "Desactivado (no tocar el clima)",
        "btn_remove": "Quitar de la lista",
        "lbl_state": "Estado:", "lbl_server_weather": "Clima en el servidor:", "lbl_real": "Tiempo real:",
        "lbl_target": "Objetivo:", "lbl_last": "Último envío:",
        "lbl_provider": "Proveedor:", "lbl_location": "Ubicación:",
        "loc_auto": "Según el circuito cargado (tabla de Ajustes > Circuitos)",
        "loc_fixed": "Coordenadas fijas:",
        "btn_search": "Buscar...",
        "lbl_ahead": "Adelantar pronóstico:",
        "tip_ahead": "0 = tiempo actual. Con N > 0 se usa el pronóstico de dentro de N horas "
                     "(solo Open-Meteo). Útil para que el evento tenga el clima de otra hora.",
        "lbl_temp_adj": "Ajuste de temperatura:",
        "lbl_rain_mult": "Multiplicador de lluvia:",
        "tip_rain_mult": "1 = lluvia real. 0 = nunca llueve. Más de 1 = la lluvia se nota más.",
        "btn_fetch_now": "Consultar y enviar ahora",
        "lbl_rain": "Lluvia:", "lbl_clouds": "Nubes:", "lbl_temp": "Temperatura:", "lbl_wind": "Viento máximo:",
        "lbl_man_trans": "Transición:",
        "tip_man_trans": "Segundos de sesión hasta alcanzar el clima manual. Las nubes cambian al instante.",
        "btn_send_now": "Enviar ahora",
        "pending": "  (envío pendiente)",
        "session_line": "  ·  {track}  ·  {ses}  ·  {phase}  ·  ET {et:.0f} s  ·  coches {cars}",
        # --- buscar
        "search_title": "Buscar coordenadas",
        "search_ph": "Pueblo o ciudad junto al circuito (p. ej. Longford, Stavelot, Monza)",
        "btn_search_go": "Buscar", "btn_use": "Usar este", "btn_cancel": "Cancelar", "btn_save": "Guardar",
        "searching": "Buscando...", "n_results": "{k} resultados", "no_results": "Sin resultados",
        "error": "Error: {e}",
        # --- ajustes
        "settings_title": "Ajustes",
        "tab_general": "General", "tab_keys": "Claves API", "tab_tracks": "Circuitos",
        "lbl_language": "Idioma:", "lang_auto": "Automático (idioma de Windows)",
        "lang_restart": "El cambio de idioma se aplica al reiniciar la aplicación.",
        "lbl_interval": "Consultar el tiempo real cada", "lbl_transition": "Transición en tiempo real",
        "chk_instant": "Al empezar una sesión nueva, aplicar el clima casi al instante",
        "chk_tray": "Al cerrar la ventana, seguir funcionando en la bandeja",
        "chk_start_min": "Arrancar minimizado en la bandeja",
        "chk_autostart": "Arrancar con Windows (tarea programada al iniciar sesión, con privilegios)",
        "note_calls": "Cada servidor en modo tiempo real hace 1 consulta por intervalo (15 min = 96/día). "
                      "Open-Meteo admite 10.000 consultas/día gratis; en los demás revisa el límite de tu plan.",
        "show": "ver", "btn_test": "Probar",
        "get_key": 'Consigue la clave en <a href="{url}">{url}</a>',
        "note_keys": "Open-Meteo no necesita clave. Las claves se guardan en xtreweather.json, "
                     "junto al ejecutable: no compartas ese archivo.",
        "key_ok_title": "Clave correcta",
        "key_ok": "{prov} responde.\nMadrid ahora: {t:.1f} °C, nubes {c:.0f} %",
        "tracks_help": "La <b>clave</b> se busca dentro del nombre de circuito que da rFactor 2 "
                       "(sin distinguir mayúsculas). Si varias coinciden, gana la más larga.",
        "filter": "Filtrar...",
        "col_key": "Clave", "col_name": "Nombre", "col_lat": "Latitud", "col_lon": "Longitud",
        "btn_add": "Añadir", "btn_find_coords": "Buscar coordenadas...", "btn_del": "Quitar",
        "bad_coords": "Coordenadas no válidas en la fila '{k}'",
        "range_coords": "Coordenadas fuera de rango en '{k}'",
        "autostart_title": "Arranque con Windows", "autostart_err": "No se pudo cambiar la tarea:\n{e}",
        # --- acerca de
        "about_title": "Acerca de {app}",
        "about_text": "<h3>{app} {ver}</h3>"
                      "<p>Clima en tiempo real para servidores dedicados de rFactor 2, "
                      "a través de rFactor2SharedMemoryMapPlugin64.</p>"
                      "<p>Creado por <b>v1ct0r</b> para la comunidad Xtresimracing, "
                      "<b>con asistencia de IA</b> (Claude, de Anthropic).</p>"
                      "<p>Licencia GNU GPL v3. Software sin garantía: úsalo bajo tu responsabilidad.</p>"
                      "<p>Datos meteorológicos: <a href='https://open-meteo.com/'>Open-Meteo.com</a> (CC BY 4.0), "
                      "OpenWeatherMap, WeatherAPI.com.</p>",
    },
    "en": {
        "state_stopped": "stopped",
        "state_noplugin": "shared memory plugin not loaded",
        "state_nocontrol": "weather control disabled (EnableWeatherControlInput)",
        "state_off": "disabled",
        "state_nocoords": "'{track}' has no coordinates (Settings > Tracks)",
        "state_waitdata": "waiting for weather data",
        "state_idle": "session idle (waiting for someone to join)",
        "state_pending": " · send pending",
        "state_running": "running",
        "log_started": "{app} {ver} started. Config: {path}",
        "log_not_windows": "WARNING: not running on Windows, no servers will be detected (test mode).",
        "log_detected": "Server {n}: detected (PID {pid})",
        "log_closed": "Server {n}: closed",
        "log_real": "Server {n}: real weather {info}  ->  {clima}",
        "log_fetch_error": "Server {n}: error querying {prov}: {err}",
        "log_new_session": "Server {n}: new session ({ses})",
        "log_track_changed": "Server {n}: track changed to {track}",
        "log_no_control": "Server {n}: the plugin does not have EnableWeatherControlInput enabled",
        "log_sent": "Server {n}: sent {clima} (in {s} s of session time, v{ver})",
        "log_send_error": "Server {n}: send error: {err}",
        "log_internal": "Internal ERROR:\n{tb}",
        "log_settings_saved": "Settings saved.",
        "weather_desc": "rain {r:.2f} · clouds {c:.2f} · {t:.1f} °C · wind {w:.1f} m/s",
        "real_info": "{place}  ·  {t:.1f} °C, clouds {c:.0f} %, precip. {mm:.1f} mm/h, wind {w:.1f} m/s  ({hora})",
        "forecast": "forecast",
        "sky_clear": "Clear", "sky_partly": "Partly cloudy", "sky_cloudy": "Overcast",
        "sky_rain": "Rain", "sky_heavy_rain": "Heavy rain", "sky_nodata": "No data",
        "ses_test": "Test day", "ses_practice": "Practice {i}", "ses_qual": "Qualifying {i}",
        "ses_warmup": "Warmup", "ses_race": "Race {i}",
        "phases": ["before start", "formation (recon)", "grid", "formation lap", "countdown",
                   "green flag", "full course yellow", "stopped", "over", "paused"],
        "prov_openmeteo": "Open-Meteo (free, no key)",
        "prov_openweathermap": "OpenWeatherMap (free key)",
        "prov_weatherapi": "WeatherAPI.com (free key)",
        "err_key": "invalid API key or not authorised",
        "err_limit": "request limit reached",
        "err_http": "HTTP {code}",
        "err_conn": "no connection ({r})",
        "err_timeout": "request timed out",
        "err_nokey": "{prov} API key missing (Settings > API keys)",
        "err_unknown_prov": "unknown provider: {prov}",
        "err_unexpected": "unexpected provider response ({e})",
        "win_title": "{app} {ver} - weather for rFactor 2",
        "tab_summary": "Overview",
        "tab_server": "Server {n}",
        "btn_add_server": "+ Server",
        "btn_settings": "Settings...",
        "btn_about": "About...",
        "attribution": 'Weather data: <a href="https://open-meteo.com/">Open-Meteo.com</a> (CC BY 4.0) '
                       '· OpenWeatherMap · WeatherAPI.com',
        "col_srv": "Srv", "col_state": "State", "col_track": "Track", "col_session": "Session",
        "col_mode": "Mode", "col_weather": "Server weather", "col_last": "Last sent",
        "summary_help": "Running servers are detected automatically (by their playerN profile). "
                        "Double-click a row to configure that server. "
                        "Weather is only applied while the session is running (someone connected).",
        "mode_real": "Real weather", "mode_manual": "Manual", "mode_off": "Disabled",
        "tray_show": "Show", "tray_quit": "Quit",
        "tray_tooltip": "{app}: {k} server(s) with a running session",
        "tray_msg": "Still running in the tray. Right-click > Quit to close.",
        "add_title": "Add server", "add_prompt": "Server number (playerN profile):",
        "remove_title": "Remove",
        "remove_running": "That server is running; it would be added again automatically.\n"
                          "If you don't want its weather touched, set it to 'Disabled'.",
        "remove_confirm": "Remove server {n} and its settings?",
        "grp_mode": "Mode", "grp_state": "Status", "grp_real": "Real weather", "grp_manual": "Manual",
        "mode_off_long": "Disabled (don't touch the weather)",
        "btn_remove": "Remove from list",
        "lbl_state": "State:", "lbl_server_weather": "Server weather:", "lbl_real": "Real weather:",
        "lbl_target": "Target:", "lbl_last": "Last sent:",
        "lbl_provider": "Provider:", "lbl_location": "Location:",
        "loc_auto": "From the loaded track (Settings > Tracks table)",
        "loc_fixed": "Fixed coordinates:",
        "btn_search": "Search...",
        "lbl_ahead": "Forecast offset:",
        "tip_ahead": "0 = current weather. With N > 0 the forecast for N hours ahead is used "
                     "(Open-Meteo only). Useful to match the event to another time of day.",
        "lbl_temp_adj": "Temperature offset:",
        "lbl_rain_mult": "Rain multiplier:",
        "tip_rain_mult": "1 = real rain. 0 = never rains. Above 1 = rain is more noticeable.",
        "btn_fetch_now": "Fetch and send now",
        "lbl_rain": "Rain:", "lbl_clouds": "Clouds:", "lbl_temp": "Temperature:", "lbl_wind": "Max wind:",
        "lbl_man_trans": "Transition:",
        "tip_man_trans": "Session seconds until the manual weather is reached. Clouds change instantly.",
        "btn_send_now": "Send now",
        "pending": "  (send pending)",
        "session_line": "  ·  {track}  ·  {ses}  ·  {phase}  ·  ET {et:.0f} s  ·  cars {cars}",
        "search_title": "Find coordinates",
        "search_ph": "Town or city next to the track (e.g. Longford, Stavelot, Monza)",
        "btn_search_go": "Search", "btn_use": "Use this one", "btn_cancel": "Cancel", "btn_save": "Save",
        "searching": "Searching...", "n_results": "{k} results", "no_results": "No results",
        "error": "Error: {e}",
        "settings_title": "Settings",
        "tab_general": "General", "tab_keys": "API keys", "tab_tracks": "Tracks",
        "lbl_language": "Language:", "lang_auto": "Automatic (Windows language)",
        "lang_restart": "Language changes apply after restarting the application.",
        "lbl_interval": "Fetch real weather every", "lbl_transition": "Real weather transition",
        "chk_instant": "When a new session starts, apply the weather almost instantly",
        "chk_tray": "When closing the window, keep running in the tray",
        "chk_start_min": "Start minimised to the tray",
        "chk_autostart": "Start with Windows (scheduled task at logon, elevated)",
        "note_calls": "Each server in real weather mode makes 1 request per interval (15 min = 96/day). "
                      "Open-Meteo allows 10,000 requests/day for free; check your plan's limit for the others.",
        "show": "show", "btn_test": "Test",
        "get_key": 'Get your key at <a href="{url}">{url}</a>',
        "note_keys": "Open-Meteo needs no key. Keys are stored in xtreweather.json next to the "
                     "executable: do not share that file.",
        "key_ok_title": "Key OK",
        "key_ok": "{prov} is responding.\nMadrid now: {t:.1f} °C, clouds {c:.0f} %",
        "tracks_help": "The <b>key</b> is searched inside the track name reported by rFactor 2 "
                       "(case-insensitive). If several match, the longest wins.",
        "filter": "Filter...",
        "col_key": "Key", "col_name": "Name", "col_lat": "Latitude", "col_lon": "Longitude",
        "btn_add": "Add", "btn_find_coords": "Find coordinates...", "btn_del": "Remove",
        "bad_coords": "Invalid coordinates in row '{k}'",
        "range_coords": "Coordinates out of range in '{k}'",
        "autostart_title": "Start with Windows", "autostart_err": "Could not change the task:\n{e}",
        "about_title": "About {app}",
        "about_text": "<h3>{app} {ver}</h3>"
                      "<p>Real-time weather for rFactor 2 dedicated servers, "
                      "via rFactor2SharedMemoryMapPlugin64.</p>"
                      "<p>Created by <b>v1ct0r</b> for the Xtresimracing community, "
                      "<b>with AI assistance</b> (Claude, by Anthropic).</p>"
                      "<p>Licensed under the GNU GPL v3. No warranty: use at your own risk.</p>"
                      "<p>Weather data: <a href='https://open-meteo.com/'>Open-Meteo.com</a> (CC BY 4.0), "
                      "OpenWeatherMap, WeatherAPI.com.</p>",
    },
}

_lang = "es"


def idioma_sistema() -> str:
    try:
        from PySide6.QtCore import QLocale
        codigo = QLocale.system().name()
    except Exception:
        codigo = (locale.getlocale()[0] or "")
    codigo = codigo[:2].lower()
    return codigo if codigo in TEXTOS else "en"


def set_lang(codigo: str):
    global _lang
    _lang = idioma_sistema() if codigo in (None, "", "auto") else (codigo if codigo in TEXTOS else "en")


def lang() -> str:
    return _lang


def t(clave: str, **kw):
    valor = TEXTOS[_lang].get(clave, TEXTOS["en"].get(clave, clave))
    return valor.format(**kw) if kw and isinstance(valor, str) else valor


assert set(TEXTOS["es"]) == set(TEXTOS["en"]), set(TEXTOS["es"]) ^ set(TEXTOS["en"])
