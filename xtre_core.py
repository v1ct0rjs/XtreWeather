"""
xtre_core.py - Nucleo de XtreWeather (sin interfaz grafica) / XtreWeather core (no GUI).

Copyright (C) 2026 v1ct0r - Licencia GNU GPL v3 (ver LICENSE). Creado con asistencia de IA.

  * Acceso a rFactor2SharedMemoryMapPlugin64 (leer estado, enviar clima).
  * Proveedores meteorologicos: Open-Meteo (sin clave), OpenWeatherMap y WeatherAPI (con clave).
  * Conversion de datos reales a valores de rFactor 2.
  * Configuracion (xtreweather.json junto al ejecutable).
"""
import copy
import ctypes
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from xtre_i18n import t

IS_WIN = sys.platform == "win32"
APP_NAME = "XtreWeather"
APP_VERSION = "0.2.0"


# --------------------------------------------------------------------------- rutas / config
def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = base_dir() / "xtreweather.json"
LOG_PATH = base_dir() / "xtreweather.log"

PROVEEDORES = ("openmeteo", "openweathermap", "weatherapi")


def nombre_proveedor(clave):
    return t("prov_" + clave) if clave in PROVEEDORES else clave

SERVER_DEFAULT = {
    "modo": "real",              # real | manual | off
    "proveedor": "openmeteo",
    "coords": "auto",            # auto (segun circuito) | fijas
    "lat": 0.0,
    "lon": 0.0,
    "horas_adelanto": 0,         # solo Open-Meteo: usar el pronostico de dentro de N horas
    "ajuste_temp": 0.0,          # grados que se suman a la temperatura real
    "mult_lluvia": 1.0,          # multiplicador de la intensidad de lluvia
    "manual": {"lluvia": 0.0, "nubes": 0.3, "temp": 20.0, "viento": 2.0, "transicion_s": 20},
}

# Coordenadas aproximadas de circuitos habituales. "clave" se busca (sin mayusculas)
# dentro del nombre del circuito que reporta rFactor 2; gana la clave mas larga.
CIRCUITOS_DEFAULT = [
    {"clave": "longford", "nombre": "Longford (Tasmania)", "lat": -41.590, "lon": 147.120},
    {"clave": "spa", "nombre": "Spa-Francorchamps", "lat": 50.437, "lon": 5.971},
    {"clave": "monza", "nombre": "Monza", "lat": 45.620, "lon": 9.289},
    {"clave": "silverstone", "nombre": "Silverstone", "lat": 52.072, "lon": -1.017},
    {"clave": "nurburgring", "nombre": "Nurburgring", "lat": 50.335, "lon": 6.947},
    {"clave": "nordschleife", "nombre": "Nordschleife", "lat": 50.346, "lon": 6.966},
    {"clave": "le mans", "nombre": "Le Mans (Sarthe)", "lat": 47.950, "lon": 0.224},
    {"clave": "sarthe", "nombre": "Le Mans (Sarthe)", "lat": 47.950, "lon": 0.224},
    {"clave": "imola", "nombre": "Imola", "lat": 44.344, "lon": 11.717},
    {"clave": "mugello", "nombre": "Mugello", "lat": 43.998, "lon": 11.371},
    {"clave": "barcelona", "nombre": "Barcelona-Catalunya", "lat": 41.570, "lon": 2.261},
    {"clave": "portimao", "nombre": "Portimao", "lat": 37.227, "lon": -8.628},
    {"clave": "sebring", "nombre": "Sebring", "lat": 27.454, "lon": -81.348},
    {"clave": "daytona", "nombre": "Daytona", "lat": 29.185, "lon": -81.070},
    {"clave": "indianapolis", "nombre": "Indianapolis", "lat": 39.795, "lon": -86.235},
    {"clave": "road america", "nombre": "Road America", "lat": 43.798, "lon": -87.989},
    {"clave": "watkins", "nombre": "Watkins Glen", "lat": 42.337, "lon": -76.927},
    {"clave": "laguna", "nombre": "Laguna Seca", "lat": 36.584, "lon": -121.753},
    {"clave": "bathurst", "nombre": "Bathurst (Mount Panorama)", "lat": -33.447, "lon": 149.555},
    {"clave": "suzuka", "nombre": "Suzuka", "lat": 34.843, "lon": 136.541},
    {"clave": "interlagos", "nombre": "Interlagos", "lat": -23.701, "lon": -46.697},
]

DEFAULT_CONFIG = {
    "general": {
        "idioma": "auto",             # auto | es | en
        "intervalo_min": 15,          # cada cuanto se consulta el tiempo real
        "transicion_s": 300,          # segundos de sesion hasta alcanzar el clima real nuevo
        "instantaneo_al_cambiar_sesion": True,
        "minimizar_a_bandeja": True,
        "arrancar_minimizado": False,
    },
    "claves": {"openweathermap": "", "weatherapi": ""},
    "servidores": {},
    "circuitos": CIRCUITOS_DEFAULT,
}


def _merge(base, extra):
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict:
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            CONFIG_PATH.replace(CONFIG_PATH.with_suffix(".json.roto"))
    cfg = _merge(DEFAULT_CONFIG, data)
    if "circuitos" in data:               # la lista del usuario sustituye a la de serie
        cfg["circuitos"] = data["circuitos"]
    for n, s in list(cfg["servidores"].items()):
        cfg["servidores"][n] = _merge(SERVER_DEFAULT, s)
    return cfg


def save_config(cfg: dict):
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONFIG_PATH)


def server_cfg(cfg: dict, n: int) -> dict:
    key = str(n)
    if key not in cfg["servidores"]:
        cfg["servidores"][key] = copy.deepcopy(SERVER_DEFAULT)
    return cfg["servidores"][key]


def buscar_circuito(cfg: dict, nombre_pista: str):
    t = (nombre_pista or "").lower()
    mejores = [c for c in cfg["circuitos"] if c.get("clave") and c["clave"].lower() in t]
    return max(mejores, key=lambda c: len(c["clave"])) if mejores else None


# --------------------------------------------------------------------------- memoria compartida
FILE_MAP_WRITE = 0x0002
FILE_MAP_READ = 0x0004
L = ctypes.c_int32   # 'long' de Windows (4 bytes) tambien al probar en Linux


class VersionBlock(ctypes.Structure):
    _pack_ = 4
    _fields_ = [("begin", ctypes.c_uint32), ("end", ctypes.c_uint32)]


class WeatherInfo(ctypes.Structure):          # rF2WeatherControlInfo (616 bytes)
    _pack_ = 4
    _fields_ = [
        ("mET", ctypes.c_double),
        ("mRaining", (ctypes.c_double * 3) * 3),
        ("mCloudiness", ctypes.c_double),
        ("mAmbientTempK", ctypes.c_double),
        ("mWindMaxSpeed", ctypes.c_double),
        ("mApplyCloudinessInstantly", ctypes.c_bool),
        ("mUnused1", ctypes.c_bool), ("mUnused2", ctypes.c_bool), ("mUnused3", ctypes.c_bool),
        ("mExpansion", ctypes.c_ubyte * 508),
    ]


class WeatherControlMap(ctypes.Structure):
    _pack_ = 4
    _fields_ = [("ver", VersionBlock), ("mLayoutVersion", L), ("info", WeatherInfo)]


class WeatherMap(ctypes.Structure):
    _pack_ = 4
    _fields_ = [("ver", VersionBlock), ("mTrackNodeSize", ctypes.c_double), ("info", WeatherInfo)]


class ScoringHeadMap(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("ver", VersionBlock), ("mBytesUpdatedHint", ctypes.c_int32),
        ("mTrackName", ctypes.c_char * 64), ("mSession", L),
        ("mCurrentET", ctypes.c_double), ("mEndET", ctypes.c_double),
        ("mMaxLaps", L), ("mLapDist", ctypes.c_double), ("pointer1", ctypes.c_ubyte * 8),
        ("mNumVehicles", L), ("mGamePhase", ctypes.c_ubyte),
    ]


assert ctypes.sizeof(WeatherInfo) == 616
assert ctypes.sizeof(WeatherControlMap) == 628
assert ScoringHeadMap.mGamePhase.offset == 120

def nombre_fase(f: int) -> str:
    fases = t("phases")
    return fases[f] if 0 <= f < len(fases) else str(f)


def nombre_sesion(s: int) -> str:
    if s == 0:
        return t("ses_test")
    if 1 <= s <= 4:
        return t("ses_practice", i=s)
    if 5 <= s <= 8:
        return t("ses_qual", i=s - 4)
    if s == 9:
        return t("ses_warmup")
    if 10 <= s <= 13:
        return t("ses_race", i=s - 9)
    return str(s)


if IS_WIN:
    from ctypes import wintypes
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    _k32.OpenFileMappingW.restype = wintypes.HANDLE
    _k32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    _k32.MapViewOfFile.restype = wintypes.LPVOID
    _k32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
    _k32.UnmapViewOfFile.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL


class Mapped:
    """Abre un mapeo YA existente creado por el plugin."""

    def __init__(self, name, struct, write=False):
        self.name, self.struct, self.write = name, struct, write

    def __enter__(self):
        if not IS_WIN:
            raise FileNotFoundError(self.name)
        access = FILE_MAP_READ | (FILE_MAP_WRITE if self.write else 0)
        self.h = _k32.OpenFileMappingW(access, False, self.name)
        if not self.h:
            raise FileNotFoundError(self.name)
        self.ptr = _k32.MapViewOfFile(self.h, access, 0, 0, ctypes.sizeof(self.struct))
        if not self.ptr:
            _k32.CloseHandle(self.h)
            raise OSError(ctypes.get_last_error(), f"MapViewOfFile {self.name}")
        self.live = self.struct.from_address(self.ptr)
        return self

    def snapshot(self, tries=50):
        for _ in range(tries):
            copy_ = self.struct.from_buffer_copy(self.live)
            if copy_.ver.begin == copy_.ver.end:
                return copy_
            time.sleep(0.002)
        return copy_

    def __exit__(self, *exc):
        _k32.UnmapViewOfFile(self.ptr)
        _k32.CloseHandle(self.h)


def _map_name(buffer, pid):
    return f"$rFactor2SMMP_{buffer}${pid}"


def detectar_servidores():
    """[(numero_servidor, pid), ...] a partir de '+profile=playerN' en la linea de comandos."""
    if not IS_WIN:
        return []
    import psutil
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower() != "rfactor2 dedicated.exe":
                continue
            cmd = " ".join(p.info["cmdline"] or [])
            m = re.search(r'\+profile="?player(\d*)', cmd, re.I)
            n = int(m.group(1)) if m and m.group(1) else 1
            out.append((n, p.info["pid"]))
        except Exception:
            continue
    return sorted(out)


def leer_estado(pid) -> dict:
    est = {"pid": pid, "plugin": False, "control": False, "weather": False}
    try:
        with Mapped(_map_name("Scoring", pid), ScoringHeadMap) as m:
            s = m.snapshot()
        est.update(plugin=True, circuito=s.mTrackName.decode("latin-1", "replace").strip(),
                   sesion=s.mSession, et=s.mCurrentET, fase=s.mGamePhase,
                   coches=s.mNumVehicles, ver_scoring=s.ver.begin)
    except FileNotFoundError:
        return est
    try:
        with Mapped(_map_name("Weather", pid), WeatherMap) as m:
            w = m.snapshot()
        est.update(weather=w.mTrackNodeSize > 0, ver_weather=w.ver.begin,
                   lluvia=w.info.mRaining[1][1], nubes=w.info.mCloudiness,
                   temp=(w.info.mAmbientTempK - 273.15) if w.info.mAmbientTempK else None,
                   viento=w.info.mWindMaxSpeed)
    except FileNotFoundError:
        pass
    try:
        with Mapped(_map_name("WeatherControl", pid), WeatherControlMap):
            est["control"] = True
    except FileNotFoundError:
        pass
    return est


def enviar_clima(pid, clima: dict, et_objetivo: float, instantaneo: bool) -> int:
    """clima: {'lluvia','nubes','temp','viento'}  (temp en C, viento en m/s). Devuelve la version."""
    with Mapped(_map_name("WeatherControl", pid), WeatherControlMap, write=True) as m:
        b = m.live
        b.ver.begin = (b.ver.begin + 1) & 0xFFFFFFFF
        b.mLayoutVersion = 1
        b.info.mET = et_objetivo
        for i in range(3):
            for j in range(3):
                b.info.mRaining[i][j] = clima["lluvia"]
        b.info.mCloudiness = clima["nubes"]
        b.info.mAmbientTempK = clima["temp"] + 273.15
        b.info.mWindMaxSpeed = clima["viento"]
        b.info.mApplyCloudinessInstantly = bool(instantaneo)
        b.ver.end = b.ver.begin
        return b.ver.begin


# --------------------------------------------------------------------------- proveedores
class ProveedorError(Exception):
    pass


def _get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ProveedorError(t("err_key")) from e
        if e.code == 429:
            raise ProveedorError(t("err_limit")) from e
        raise ProveedorError(t("err_http", code=e.code)) from e
    except urllib.error.URLError as e:
        raise ProveedorError(t("err_conn", r=e.reason)) from e
    except TimeoutError as e:
        raise ProveedorError(t("err_timeout")) from e


def _openmeteo(lat, lon, _key, horas):
    base = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&wind_speed_unit=ms&timezone=auto"
    if horas <= 0:
        c = _get_json(base + "&current=temperature_2m,precipitation,rain,showers,cloud_cover,wind_speed_10m")["current"]
        mmh = max(c.get("precipitation") or 0.0, (c.get("rain") or 0.0) + (c.get("showers") or 0.0))
        return {"temp": c["temperature_2m"], "nubes_pct": c.get("cloud_cover") or 0,
                "precip_mmh": mmh, "viento_ms": c.get("wind_speed_10m") or 0.0, "hora": c.get("time")}
    h = _get_json(base + f"&hourly=temperature_2m,precipitation,cloud_cover,wind_speed_10m&forecast_hours={horas + 1}")["hourly"]
    i = min(horas, len(h["time"]) - 1)
    return {"temp": h["temperature_2m"][i], "nubes_pct": h["cloud_cover"][i] or 0,
            "precip_mmh": h["precipitation"][i] or 0.0, "viento_ms": h["wind_speed_10m"][i] or 0.0,
            "hora": f"{h['time'][i]} {t('forecast')}"}


def _openweathermap(lat, lon, key, _horas):
    if not key:
        raise ProveedorError(t("err_nokey", prov="OpenWeatherMap"))
    d = _get_json("https://api.openweathermap.org/data/2.5/weather"
                  f"?lat={lat}&lon={lon}&units=metric&appid={urllib.parse.quote(key)}")
    mmh = (d.get("rain") or {}).get("1h", 0.0) + (d.get("snow") or {}).get("1h", 0.0)
    return {"temp": d["main"]["temp"], "nubes_pct": (d.get("clouds") or {}).get("all", 0),
            "precip_mmh": mmh, "viento_ms": (d.get("wind") or {}).get("speed", 0.0),
            "hora": time.strftime("%Y-%m-%d %H:%M", time.localtime(d.get("dt", time.time())))}


def _weatherapi(lat, lon, key, _horas):
    if not key:
        raise ProveedorError(t("err_nokey", prov="WeatherAPI"))
    d = _get_json(f"https://api.weatherapi.com/v1/current.json?key={urllib.parse.quote(key)}&q={lat},{lon}")
    c = d["current"]
    return {"temp": c["temp_c"], "nubes_pct": c.get("cloud", 0), "precip_mmh": c.get("precip_mm", 0.0),
            "viento_ms": (c.get("wind_kph") or 0.0) / 3.6, "hora": c.get("last_updated")}


_PROV_FN = {"openmeteo": _openmeteo, "openweathermap": _openweathermap, "weatherapi": _weatherapi}


def consultar(proveedor, lat, lon, clave="", horas=0) -> dict:
    fn = _PROV_FN.get(proveedor)
    if fn is None:
        raise ProveedorError(t("err_unknown_prov", prov=proveedor))
    try:
        return fn(lat, lon, clave, int(horas))
    except (KeyError, TypeError, ValueError) as e:
        raise ProveedorError(t("err_unexpected", e=e)) from e


def geocodificar(texto, n=10, idioma="es"):
    """Busca lugares por nombre (Open-Meteo Geocoding, sin clave)."""
    q = urllib.parse.quote(texto)
    d = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count={n}&language={idioma}&format=json")
    res = []
    for r in d.get("results") or []:
        desc = ", ".join(x for x in (r.get("name"), r.get("admin1"), r.get("country")) if x)
        res.append({"nombre": desc, "lat": round(r["latitude"], 4), "lon": round(r["longitude"], 4)})
    return res


# --------------------------------------------------------------------------- conversion
def a_rf2(real: dict, scfg: dict) -> dict:
    """Datos reales normalizados -> valores rF2 (lluvia/nubes 0..1, temp C, viento m/s)."""
    mmh = max(0.0, real["precip_mmh"]) * float(scfg.get("mult_lluvia", 1.0))
    lluvia = min(1.0, math.sqrt(mmh) / 3.0) if mmh > 0.05 else 0.0
    nubes = max(0.0, min(1.0, real["nubes_pct"] / 100.0))
    if lluvia > 0:
        nubes = max(nubes, 0.6 + 0.4 * lluvia)
    return {"lluvia": round(lluvia, 3), "nubes": round(nubes, 3),
            "temp": round(real["temp"] + float(scfg.get("ajuste_temp", 0.0)), 1),
            "viento": round(max(0.0, real["viento_ms"]), 1)}


def describir(clima: dict) -> str:
    return t("weather_desc", r=clima["lluvia"], c=clima["nubes"], t=clima["temp"], w=clima["viento"])


def clima_servidor(est: dict):
    """Clima que tiene ahora el servidor (mismas claves que a_rf2) o None si no hay datos."""
    if est.get("weather") and est.get("temp") is not None:
        return {k: est[k] for k in ("lluvia", "nubes", "temp", "viento")}
    return None


def tipo_cielo(clima) -> str:
    """Estado del cielo para elegir icono: clear | partly | cloudy | rain | heavy_rain | nodata.

    Lluvia >= 0.5 equivale a unos 2,25 mm/h reales (ver a_rf2)."""
    if not clima:
        return "nodata"
    if clima["lluvia"] >= 0.5:
        return "heavy_rain"
    if clima["lluvia"] >= 0.01:
        return "rain"
    if clima["nubes"] >= 0.7:
        return "cloudy"
    if clima["nubes"] >= 0.3:
        return "partly"
    return "clear"
