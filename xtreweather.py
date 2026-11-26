"""
XtreWeather - clima en tiempo real para servidores dedicados de rFactor 2.
XtreWeather - real-time weather for rFactor 2 dedicated servers.

Copyright (C) 2026 v1ct0r
This program is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version. See LICENSE.
Creado con asistencia de IA (Claude, de Anthropic) / Created with AI assistance (Claude, by Anthropic).

Requiere rFactor2SharedMemoryMapPlugin64 en cada servidor con
"EnableWeatherControlInput": 1 y "UnsubscribedBuffersMask": 32. Ver docs/MANUAL.*.md
"""
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QLibraryInfo, QLocale, QObject, QSize, Qt, QTimer, QTranslator, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QSlider,
    QSpinBox, QSplitter, QSystemTrayIcon, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

import xtre_core as core
import xtre_i18n as i18n
import xtre_iconos as iconos
from xtre_i18n import t

TAREA = "XtreWeather"
COLOR_ESTADO = {"state_running": "green", "state_stopped": "gray"}
_pool_ui = ThreadPoolExecutor(max_workers=2)


# =========================================================================== motor
class Runtime:
    """Estado en memoria de un servidor."""

    def __init__(self, n):
        self.n = n
        self.pid = None
        self.est = {}
        self.prev_ver = None
        self.prev_sesion = None
        self.prev_et = None
        self.prev_circuito = None
        self.activo = False
        self.estado, self.estado_kw = "state_stopped", {}
        self.real = None            # datos reales normalizados del ultimo fetch
        self.real_info = ""
        self.coords = None          # (lat, lon, nombre) usadas en el ultimo fetch
        self.next_fetch = 0.0
        self.futuro = None
        self.pendiente = False
        self.pendiente_inst = False
        self.ultimo_envio = ""
        self.aviso_control = False

    def set_estado(self, clave, **kw):
        self.estado, self.estado_kw = clave, kw

    def texto_estado(self):
        txt = t(self.estado, **self.estado_kw) if self.estado_kw else t(self.estado)
        if self.estado == "state_idle" and self.pendiente:
            txt += t("state_pending")
        return txt


class Motor(QObject):
    log = Signal(str)
    actualizado = Signal()

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.rt = {}
        self.pool = ThreadPoolExecutor(max_workers=4)
        self._ultimo_scan = 0.0
        for k in cfg["servidores"]:
            self.rt[int(k)] = Runtime(int(k))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    # ------------------------------------------------------------ api para la interfaz
    def runtime(self, n):
        if n not in self.rt:
            self.rt[n] = Runtime(n)
            core.server_cfg(self.cfg, n)
            core.save_config(self.cfg)
        return self.rt[n]

    def quitar(self, n):
        self.rt.pop(n, None)
        self.cfg["servidores"].pop(str(n), None)
        core.save_config(self.cfg)

    def forzar_consulta(self, n):
        r = self.runtime(n)
        r.next_fetch = 0.0
        r.pendiente = True

    def forzar_envio(self, n):
        self.runtime(n).pendiente = True

    def objetivo(self, n):
        r, s = self.rt.get(n), core.server_cfg(self.cfg, n)
        if s["modo"] == "manual":
            m = s["manual"]
            return {k: m[k] for k in ("lluvia", "nubes", "temp", "viento")}
        if s["modo"] == "real" and r and r.real:
            return core.a_rf2(r.real, s)
        return None

    # ------------------------------------------------------------ bucle (1 s)
    def tick(self):
        try:
            self._tick()
        except Exception:
            self.log.emit(t("log_internal", tb=traceback.format_exc()))
        self.actualizado.emit()

    def _tick(self):
        ahora = time.time()
        if ahora - self._ultimo_scan >= 3:
            self._ultimo_scan = ahora
            vistos = dict(core.detectar_servidores())
            for n, pid in vistos.items():
                r = self.runtime(n)
                if r.pid != pid:
                    self.log.emit(t("log_detected", n=n, pid=pid))
                    r.pid, r.prev_ver, r.prev_sesion, r.prev_et = pid, None, None, None
                    r.pendiente, r.aviso_control = True, False
            for n, r in self.rt.items():
                if r.pid and n not in vistos:
                    self.log.emit(t("log_closed", n=n))
                    r.pid, r.activo, r.est = None, False, {}

        for n, r in self.rt.items():
            self._procesar(n, r, ahora)

    def _procesar(self, n, r, ahora):
        s = core.server_cfg(self.cfg, n)
        g = self.cfg["general"]

        # --- resultado de una consulta en curso
        if r.futuro and r.futuro.done():
            try:
                r.real = r.futuro.result()
                clima = core.a_rf2(r.real, s)
                r.real_info = t("real_info", place=r.coords[2], t=r.real["temp"], c=r.real["nubes_pct"],
                                mm=r.real["precip_mmh"], w=r.real["viento_ms"], hora=r.real.get("hora") or "")
                self.log.emit(t("log_real", n=n, info=r.real_info, clima=core.describir(clima)))
                r.pendiente = True
            except Exception as e:
                self.log.emit(t("log_fetch_error", n=n, prov=core.nombre_proveedor(s["proveedor"]), err=e))
                r.next_fetch = ahora + 60
            r.futuro = None

        if not r.pid:
            r.set_estado("state_stopped")
            return

        r.est = est = core.leer_estado(r.pid)
        if not est["plugin"]:
            r.set_estado("state_noplugin")
            return

        r.activo = r.prev_ver is not None and est["ver_scoring"] != r.prev_ver
        r.prev_ver = est["ver_scoring"]

        # --- cambio de sesion / reinicio / circuito
        if r.prev_sesion is not None and (est["sesion"] != r.prev_sesion or est["et"] + 5 < (r.prev_et or 0)):
            self.log.emit(t("log_new_session", n=n, ses=core.nombre_sesion(est["sesion"])))
            r.pendiente, r.pendiente_inst = True, bool(g["instantaneo_al_cambiar_sesion"])
        if est["circuito"] != r.prev_circuito:
            if r.prev_circuito is not None:
                self.log.emit(t("log_track_changed", n=n, track=est["circuito"]))
            r.next_fetch, r.real, r.real_info = 0.0, None, ""
            r.pendiente = True
        r.prev_sesion, r.prev_et, r.prev_circuito = est["sesion"], est["et"], est["circuito"]

        if not est["control"]:
            r.set_estado("state_nocontrol")
            if not r.aviso_control:
                self.log.emit(t("log_no_control", n=n))
                r.aviso_control = True
            return

        if s["modo"] == "off":
            r.set_estado("state_off")
            return

        # --- consulta del tiempo real
        if s["modo"] == "real":
            if s["coords"] == "auto":
                c = core.buscar_circuito(self.cfg, est["circuito"])
                if not c:
                    r.set_estado("state_nocoords", track=est["circuito"])
                    return
                coords = (c["lat"], c["lon"], c["nombre"])
            else:
                coords = (s["lat"], s["lon"], f"{s['lat']:.3f}, {s['lon']:.3f}")
            if r.coords is not None and r.coords[:2] != coords[:2] and r.futuro is None:
                r.next_fetch, r.real, r.real_info = 0.0, None, ""
            if r.futuro is None and ahora >= r.next_fetch:
                r.coords = coords
                r.next_fetch = ahora + max(1, int(g["intervalo_min"])) * 60
                clave = self.cfg["claves"].get(s["proveedor"], "")
                r.futuro = self.pool.submit(core.consultar, s["proveedor"], coords[0], coords[1],
                                            clave, s["horas_adelanto"])

        objetivo = self.objetivo(n)
        if objetivo is None:
            r.set_estado("state_waitdata")
            return
        if not r.activo:
            r.set_estado("state_idle")
            return

        r.set_estado("state_running")
        if r.pendiente:
            if s["modo"] == "manual":
                transicion, instantaneo = int(s["manual"].get("transicion_s", 20)), True
            elif r.pendiente_inst:
                transicion, instantaneo = min(10, g["transicion_s"]), True
            else:
                transicion, instantaneo = g["transicion_s"], False
            try:
                ver = core.enviar_clima(r.pid, objetivo, est["et"] + transicion, instantaneo)
                r.ultimo_envio = f"{time.strftime('%H:%M:%S')}  {core.describir(objetivo)}"
                self.log.emit(t("log_sent", n=n, clima=core.describir(objetivo), s=transicion, ver=ver))
            except Exception as e:
                self.log.emit(t("log_send_error", n=n, err=e))
            r.pendiente = r.pendiente_inst = False


# =========================================================================== utilidades UI
def comando_arranque():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimizado'
    pyw = sys.executable.replace("python.exe", "pythonw.exe")
    return f'"{pyw}" "{core.Path(__file__).resolve()}" --minimizado'


def autoarranque_activo():
    if not core.IS_WIN:
        return False
    return subprocess.run(["schtasks", "/Query", "/TN", TAREA], capture_output=True,
                          creationflags=0x08000000).returncode == 0


def autoarranque(activar: bool):
    if activar:
        args = ["schtasks", "/Create", "/TN", TAREA, "/TR", comando_arranque(),
                "/SC", "ONLOGON", "/RL", "HIGHEST", "/F"]
    else:
        args = ["schtasks", "/Delete", "/TN", TAREA, "/F"]
    r = subprocess.run(args, capture_output=True, text=True, creationflags=0x08000000)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip())


def ejecutar_en_hilo(parent, fn, *args, ok, error):
    """Lanza fn en segundo plano y llama ok(res)/error(exc) en el hilo de la interfaz."""
    fut = _pool_ui.submit(fn, *args)
    timer = QTimer(parent)

    def comprobar():
        if fut.done():
            timer.stop()
            timer.deleteLater()
            try:
                res = fut.result()
            except Exception as e:
                error(e)
                return
            ok(res)
    timer.timeout.connect(comprobar)
    timer.start(150)


def botones_dialogo(ok_txt, ok_cb, cancel_cb, guardar=False):
    tipo = QDialogButtonBox.Save if guardar else QDialogButtonBox.Ok
    b = QDialogButtonBox(tipo | QDialogButtonBox.Cancel)
    b.button(tipo).setText(ok_txt)
    b.button(QDialogButtonBox.Cancel).setText(t("btn_cancel"))
    b.accepted.connect(ok_cb)
    b.rejected.connect(cancel_cb)
    return b


def nota(texto):
    lb = QLabel(texto)
    lb.setWordWrap(True)
    lb.setStyleSheet("color: gray")
    return lb


class DialogoBuscar(QDialog):
    """Busca un lugar por nombre y devuelve {'nombre','lat','lon'}."""

    def __init__(self, parent, texto=""):
        super().__init__(parent)
        self.setWindowTitle(t("search_title"))
        self.resize(480, 340)
        self.resultado = None
        self.datos = []
        self.edit = QLineEdit(texto)
        self.edit.setPlaceholderText(t("search_ph"))
        bt = QPushButton(t("btn_search_go"))
        self.lista = QListWidget()
        self.info = QLabel("")
        fila = QHBoxLayout()
        fila.addWidget(self.edit)
        fila.addWidget(bt)
        lay = QVBoxLayout(self)
        lay.addLayout(fila)
        lay.addWidget(self.lista)
        lay.addWidget(self.info)
        lay.addWidget(botones_dialogo(t("btn_use"), self.aceptar, self.reject))
        bt.clicked.connect(self.buscar)
        self.edit.returnPressed.connect(self.buscar)
        self.lista.itemDoubleClicked.connect(lambda *_: self.aceptar())

    def buscar(self):
        texto = self.edit.text().strip()
        if not texto:
            return
        self.info.setText(t("searching"))
        self.lista.clear()

        def ok(res):
            self.datos = res
            for r in res:
                self.lista.addItem(f"{r['nombre']}   ({r['lat']}, {r['lon']})")
            self.info.setText(t("n_results", k=len(res)) if res else t("no_results"))

        ejecutar_en_hilo(self, core.geocodificar, texto, 10, i18n.lang(), ok=ok,
                         error=lambda e: self.info.setText(t("error", e=e)))

    def aceptar(self):
        i = self.lista.currentRow()
        if 0 <= i < len(self.datos):
            self.resultado = self.datos[i]
            self.accept()


# =========================================================================== ajustes
class DialogoAjustes(QDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle(t("settings_title"))
        self.resize(720, 500)
        tabs = QTabWidget()
        tabs.addTab(self._general(), t("tab_general"))
        tabs.addTab(self._claves(), t("tab_keys"))
        tabs.addTab(self._circuitos(), t("tab_tracks"))
        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        lay.addWidget(botones_dialogo(t("btn_save"), self.guardar, self.reject, guardar=True))

    def _general(self):
        g = self.cfg["general"]
        w = QWidget()
        f = QFormLayout(w)
        self.idioma = QComboBox()
        self.idioma.addItem(t("lang_auto"), "auto")
        for k, nombre in i18n.IDIOMAS.items():
            self.idioma.addItem(nombre, k)
        self.idioma.setCurrentIndex(max(0, self.idioma.findData(g.get("idioma", "auto"))))
        self.intervalo = QSpinBox(minimum=1, maximum=180, suffix=" min")
        self.intervalo.setValue(int(g["intervalo_min"]))
        self.transicion = QSpinBox(minimum=10, maximum=3600, suffix=" s")
        self.transicion.setValue(int(g["transicion_s"]))
        self.inst = QCheckBox(t("chk_instant"))
        self.inst.setChecked(bool(g["instantaneo_al_cambiar_sesion"]))
        self.bandeja = QCheckBox(t("chk_tray"))
        self.bandeja.setChecked(bool(g["minimizar_a_bandeja"]))
        self.minimizado = QCheckBox(t("chk_start_min"))
        self.minimizado.setChecked(bool(g["arrancar_minimizado"]))
        self.auto = QCheckBox(t("chk_autostart"))
        self.auto_inicial = autoarranque_activo()
        self.auto.setChecked(self.auto_inicial)
        self.auto.setEnabled(core.IS_WIN)
        f.addRow(t("lbl_language"), self.idioma)
        f.addRow("", nota(t("lang_restart")))
        f.addRow(t("lbl_interval"), self.intervalo)
        f.addRow(t("lbl_transition"), self.transicion)
        f.addRow(self.inst)
        f.addRow(self.bandeja)
        f.addRow(self.minimizado)
        f.addRow(self.auto)
        f.addRow(nota(t("note_calls")))
        return w

    def _claves(self):
        w = QWidget()
        f = QFormLayout(w)
        self.claves = {}
        for prov, url in (("openweathermap", "https://home.openweathermap.org/api_keys"),
                          ("weatherapi", "https://www.weatherapi.com/my/")):
            e = QLineEdit(self.cfg["claves"].get(prov, ""))
            e.setEchoMode(QLineEdit.Password)
            ver = QCheckBox(t("show"))
            ver.toggled.connect(lambda on, e=e: e.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
            probar = QPushButton(t("btn_test"))
            probar.clicked.connect(lambda _=False, p=prov, e=e: self.probar(p, e.text().strip()))
            fila = QHBoxLayout()
            fila.addWidget(e)
            fila.addWidget(ver)
            fila.addWidget(probar)
            f.addRow(core.nombre_proveedor(prov), fila)
            enlace = QLabel(t("get_key", url=url))
            enlace.setOpenExternalLinks(True)
            f.addRow("", enlace)
            self.claves[prov] = e
        f.addRow(nota(t("note_keys")))
        return w

    def probar(self, prov, clave):
        nombre = core.nombre_proveedor(prov)

        def ok(r):
            QMessageBox.information(self, t("key_ok_title"),
                                    t("key_ok", prov=nombre, t=r["temp"], c=r["nubes_pct"]))

        ejecutar_en_hilo(self, core.consultar, prov, 40.4168, -3.7038, clave, 0, ok=ok,
                         error=lambda e: QMessageBox.warning(self, "Error", f"{nombre}: {e}"))

    def _circuitos(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        ayuda = QLabel(t("tracks_help"))
        ayuda.setWordWrap(True)
        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText(t("filter"))
        self.filtro.textChanged.connect(self._filtrar)
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels([t("col_key"), t("col_name"), t("col_lat"), t("col_lon")])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        for c in sorted(self.cfg["circuitos"], key=lambda c: c["nombre"].lower()):
            self._fila(c)
        bts = QHBoxLayout()
        for txt, fn in ((t("btn_add"), self._anadir), (t("btn_find_coords"), self._buscar),
                        (t("btn_del"), self._quitar)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            bts.addWidget(b)
        bts.addStretch()
        lay.addWidget(ayuda)
        lay.addWidget(self.filtro)
        lay.addWidget(self.tabla)
        lay.addLayout(bts)
        return w

    def _fila(self, c):
        r = self.tabla.rowCount()
        self.tabla.insertRow(r)
        for col, v in enumerate((c.get("clave", ""), c.get("nombre", ""), c.get("lat", 0), c.get("lon", 0))):
            self.tabla.setItem(r, col, QTableWidgetItem(str(v)))
        return r

    def _filtrar(self, texto):
        texto = texto.lower()
        for r in range(self.tabla.rowCount()):
            txt = " ".join((self.tabla.item(r, c).text() if self.tabla.item(r, c) else "") for c in range(2))
            self.tabla.setRowHidden(r, texto not in txt.lower())

    def _anadir(self):
        r = self._fila({"clave": "", "nombre": "", "lat": 0.0, "lon": 0.0})
        self.tabla.setCurrentCell(r, 0)
        self.tabla.editItem(self.tabla.item(r, 0))

    def _buscar(self):
        r = self.tabla.currentRow()
        texto = self.tabla.item(r, 1).text() if r >= 0 and self.tabla.item(r, 1) else ""
        d = DialogoBuscar(self, texto)
        if d.exec() and d.resultado:
            if r < 0:
                r = self._fila({"clave": d.resultado["nombre"].split(",")[0].lower(),
                                "nombre": d.resultado["nombre"], "lat": 0, "lon": 0})
            self.tabla.item(r, 2).setText(str(d.resultado["lat"]))
            self.tabla.item(r, 3).setText(str(d.resultado["lon"]))
            if not self.tabla.item(r, 1).text():
                self.tabla.item(r, 1).setText(d.resultado["nombre"])

    def _quitar(self):
        for r in sorted({i.row() for i in self.tabla.selectedIndexes()}, reverse=True):
            self.tabla.removeRow(r)

    def guardar(self):
        circuitos = []
        for r in range(self.tabla.rowCount()):
            celdas = [self.tabla.item(r, c).text().strip() if self.tabla.item(r, c) else "" for c in range(4)]
            if not celdas[0]:
                continue
            try:
                lat, lon = float(celdas[2].replace(",", ".")), float(celdas[3].replace(",", "."))
            except ValueError:
                QMessageBox.warning(self, t("tab_tracks"), t("bad_coords", k=celdas[0]))
                return
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                QMessageBox.warning(self, t("tab_tracks"), t("range_coords", k=celdas[0]))
                return
            circuitos.append({"clave": celdas[0].lower(), "nombre": celdas[1] or celdas[0], "lat": lat, "lon": lon})
        if self.auto.isChecked() != self.auto_inicial:
            try:
                autoarranque(self.auto.isChecked())
            except Exception as e:
                QMessageBox.warning(self, t("autostart_title"), t("autostart_err", e=e))
        g = self.cfg["general"]
        g.update(idioma=self.idioma.currentData(), intervalo_min=self.intervalo.value(),
                 transicion_s=self.transicion.value(), instantaneo_al_cambiar_sesion=self.inst.isChecked(),
                 minimizar_a_bandeja=self.bandeja.isChecked(), arrancar_minimizado=self.minimizado.isChecked())
        for prov, e in self.claves.items():
            self.cfg["claves"][prov] = e.text().strip()
        self.cfg["circuitos"] = circuitos
        core.save_config(self.cfg)
        self.accept()


# =========================================================================== pestaña de servidor
class PestanaServidor(QWidget):
    def __init__(self, motor: Motor, n: int, quitar_cb):
        super().__init__()
        self.motor, self.n = motor, n
        self.s = core.server_cfg(motor.cfg, n)
        self._cargando = True

        # --- estado
        self.lb_estado, self.lb_servidor, self.lb_real, self.lb_objetivo, self.lb_envio = (QLabel() for _ in range(5))
        for lb in (self.lb_real, self.lb_objetivo, self.lb_servidor):
            lb.setWordWrap(True)
        g_estado = QGroupBox(t("grp_state"))
        fe = QFormLayout()
        fe.addRow(t("lbl_state"), self.lb_estado)
        fe.addRow(t("lbl_server_weather"), self.lb_servidor)
        fe.addRow(t("lbl_real"), self.lb_real)
        fe.addRow(t("lbl_target"), self.lb_objetivo)
        fe.addRow(t("lbl_last"), self.lb_envio)
        # icono grande con el cielo que tiene ahora el servidor
        self.lb_icono_cielo = QLabel()
        self.lb_icono_cielo.setFixedSize(64, 64)
        self.lb_cielo = QLabel()
        self.lb_cielo.setAlignment(Qt.AlignHCenter)
        self.lb_cielo.setStyleSheet("color: gray")
        self._cielo = None
        col_cielo = QVBoxLayout()
        col_cielo.addWidget(self.lb_icono_cielo, 0, Qt.AlignHCenter)
        col_cielo.addWidget(self.lb_cielo)
        col_cielo.addStretch()
        he = QHBoxLayout(g_estado)
        he.addLayout(fe, 1)
        he.addSpacing(12)
        he.addLayout(col_cielo)

        # --- modo
        self.rb = {"real": QRadioButton(t("mode_real")), "manual": QRadioButton(t("mode_manual")),
                   "off": QRadioButton(t("mode_off_long"))}
        grupo = QButtonGroup(self)
        g_modo = QGroupBox(t("grp_mode"))
        hm = QHBoxLayout(g_modo)
        for m, b in self.rb.items():
            grupo.addButton(b)
            hm.addWidget(b)
            b.toggled.connect(lambda on, m=m: on and self._set("modo", m, consulta=True))
        hm.addStretch()
        bt_quitar = QPushButton(t("btn_remove"))
        bt_quitar.clicked.connect(lambda: quitar_cb(n))
        hm.addWidget(bt_quitar)

        # --- tiempo real
        self.g_real = QGroupBox(t("grp_real"))
        fr = QFormLayout(self.g_real)
        self.cb_prov = QComboBox()
        for k in core.PROVEEDORES:
            self.cb_prov.addItem(core.nombre_proveedor(k), k)
        self.cb_prov.currentIndexChanged.connect(lambda _: self._set("proveedor", self.cb_prov.currentData(), True))
        self.rb_auto = QRadioButton(t("loc_auto"))
        self.rb_fijas = QRadioButton(t("loc_fixed"))
        gc = QButtonGroup(self)
        gc.addButton(self.rb_auto)
        gc.addButton(self.rb_fijas)
        self.rb_auto.toggled.connect(lambda on: self._set("coords", "auto" if on else "fijas", True))
        self.sp_lat = QDoubleSpinBox(minimum=-90, maximum=90, decimals=4, singleStep=0.01)
        self.sp_lon = QDoubleSpinBox(minimum=-180, maximum=180, decimals=4, singleStep=0.01)
        self.sp_lat.valueChanged.connect(lambda v: self._set("lat", v, True))
        self.sp_lon.valueChanged.connect(lambda v: self._set("lon", v, True))
        bt_buscar = QPushButton(t("btn_search"))
        bt_buscar.clicked.connect(self._buscar)
        fila_c = self._fila(self.rb_fijas, QLabel("lat"), self.sp_lat, QLabel("lon"), self.sp_lon, bt_buscar)
        fila_c.addStretch()
        self.sp_horas = QSpinBox(minimum=0, maximum=72, suffix=" h")
        self.sp_horas.setToolTip(t("tip_ahead"))
        self.sp_horas.valueChanged.connect(lambda v: self._set("horas_adelanto", v, True))
        self.sp_ajuste = QDoubleSpinBox(minimum=-20, maximum=20, decimals=1, suffix=" °C")
        self.sp_ajuste.valueChanged.connect(lambda v: self._set("ajuste_temp", v, envio=True))
        self.sp_mult = QDoubleSpinBox(minimum=0, maximum=5, decimals=2, singleStep=0.1)
        self.sp_mult.setToolTip(t("tip_rain_mult"))
        self.sp_mult.valueChanged.connect(lambda v: self._set("mult_lluvia", v, envio=True))
        bt_ahora = QPushButton(t("btn_fetch_now"))
        bt_ahora.clicked.connect(lambda: self.motor.forzar_consulta(self.n))
        fr.addRow(t("lbl_provider"), self.cb_prov)
        fr.addRow(t("lbl_location"), self.rb_auto)
        fr.addRow("", fila_c)
        fr.addRow(t("lbl_ahead"), self.sp_horas)
        fr.addRow(t("lbl_temp_adj"), self.sp_ajuste)
        fr.addRow(t("lbl_rain_mult"), self.sp_mult)
        fr.addRow("", bt_ahora)

        # --- manual
        self.g_man = QGroupBox(t("grp_manual"))
        fm = QFormLayout(self.g_man)
        self.sl_lluvia, self.lb_lluvia = self._slider("lluvia")
        self.sl_nubes, self.lb_nubes = self._slider("nubes")
        self.sp_temp = QDoubleSpinBox(minimum=-20, maximum=50, decimals=1, suffix=" °C")
        self.sp_temp.valueChanged.connect(lambda v: self._set_man("temp", v))
        self.sp_viento = QDoubleSpinBox(minimum=0, maximum=40, decimals=1, suffix=" m/s")
        self.sp_viento.valueChanged.connect(lambda v: self._set_man("viento", v))
        self.sp_mtrans = QSpinBox(minimum=5, maximum=1800, suffix=" s")
        self.sp_mtrans.setToolTip(t("tip_man_trans"))
        self.sp_mtrans.valueChanged.connect(lambda v: self._set_man("transicion_s", v))
        bt_aplicar = QPushButton(t("btn_send_now"))
        bt_aplicar.clicked.connect(lambda: self.motor.forzar_envio(self.n))
        fm.addRow(t("lbl_rain"), self._fila(self.sl_lluvia, self.lb_lluvia))
        fm.addRow(t("lbl_clouds"), self._fila(self.sl_nubes, self.lb_nubes))
        fm.addRow(t("lbl_temp"), self.sp_temp)
        fm.addRow(t("lbl_wind"), self.sp_viento)
        fm.addRow(t("lbl_man_trans"), self.sp_mtrans)
        fm.addRow("", bt_aplicar)

        lay = QVBoxLayout(self)
        lay.addWidget(g_modo)
        lay.addWidget(g_estado)
        lay.addWidget(self.g_real)
        lay.addWidget(self.g_man)
        lay.addStretch()
        self._cargar()

    @staticmethod
    def _fila(*ws):
        h = QHBoxLayout()
        for w in ws:
            h.addWidget(w)
        return h

    def _slider(self, campo):
        sl = QSlider(Qt.Horizontal, minimum=0, maximum=100)
        lb = QLabel("0.00")
        lb.setMinimumWidth(40)
        sl.valueChanged.connect(lambda v: (lb.setText(f"{v / 100:.2f}"), self._set_man(campo, v / 100)))
        return sl, lb

    def _cargar(self):
        s = self.s
        self._cargando = True
        self.rb.get(s["modo"], self.rb["real"]).setChecked(True)
        self.cb_prov.setCurrentIndex(max(0, self.cb_prov.findData(s["proveedor"])))
        (self.rb_auto if s["coords"] == "auto" else self.rb_fijas).setChecked(True)
        self.sp_lat.setValue(s["lat"])
        self.sp_lon.setValue(s["lon"])
        self.sp_horas.setValue(int(s["horas_adelanto"]))
        self.sp_ajuste.setValue(float(s["ajuste_temp"]))
        self.sp_mult.setValue(float(s["mult_lluvia"]))
        m = s["manual"]
        self.sl_lluvia.setValue(round(m["lluvia"] * 100))
        self.sl_nubes.setValue(round(m["nubes"] * 100))
        self.sp_temp.setValue(m["temp"])
        self.sp_viento.setValue(m["viento"])
        self.sp_mtrans.setValue(int(m.get("transicion_s", 20)))
        self._cargando = False
        self._visibilidad()

    def _visibilidad(self):
        self.g_real.setVisible(self.s["modo"] == "real")
        self.g_man.setVisible(self.s["modo"] == "manual")
        fijas = self.s["coords"] == "fijas"
        self.sp_lat.setEnabled(fijas)
        self.sp_lon.setEnabled(fijas)

    def _set(self, campo, valor, consulta=False, envio=False):
        if self._cargando or self.s.get(campo) == valor:
            return
        self.s[campo] = valor
        core.save_config(self.motor.cfg)
        self._visibilidad()
        if consulta:
            self.motor.forzar_consulta(self.n)
        elif envio:
            self.motor.forzar_envio(self.n)

    def _set_man(self, campo, valor):
        if self._cargando:
            return
        self.s["manual"][campo] = round(valor, 3)
        core.save_config(self.motor.cfg)

    def _buscar(self):
        d = DialogoBuscar(self)
        if d.exec() and d.resultado:
            self.rb_fijas.setChecked(True)
            self.sp_lat.setValue(d.resultado["lat"])
            self.sp_lon.setValue(d.resultado["lon"])

    def refrescar(self):
        r = self.motor.rt.get(self.n)
        if not r:
            return
        e = r.est
        color = COLOR_ESTADO.get(r.estado, "#c77700")
        extra = ""
        if e.get("plugin"):
            extra = t("session_line", track=e["circuito"], ses=core.nombre_sesion(e["sesion"]),
                      phase=core.nombre_fase(e["fase"]), et=e["et"], cars=e["coches"])
        self.lb_estado.setText(f'<span style="color:{color}"><b>{r.texto_estado()}</b></span>{extra}')
        clima = core.clima_servidor(e)
        self.lb_servidor.setText(core.describir(clima) if clima else "-")
        cielo = core.tipo_cielo(clima)
        if cielo != self._cielo:
            self._cielo = cielo
            self.lb_icono_cielo.setPixmap(iconos.icono_cielo(cielo).pixmap(QSize(64, 64),
                                                                          self.devicePixelRatioF()))
            self.lb_cielo.setText(t("sky_" + cielo))
        self.lb_real.setText(r.real_info if self.s["modo"] == "real" and r.real_info else "-")
        obj = self.motor.objetivo(self.n)
        self.lb_objetivo.setText(core.describir(obj) + (t("pending") if r.pendiente else "") if obj else "-")
        self.lb_envio.setText(r.ultimo_envio or "-")


# =========================================================================== ventana principal
class Ventana(QMainWindow):
    def __init__(self, cfg, minimizado=False):
        super().__init__()
        self.cfg = cfg
        self.salir_de_verdad = False
        self.setWindowTitle(t("win_title", app=core.APP_NAME, ver=core.APP_VERSION))
        self.setWindowIcon(iconos.icono_app())
        self.resize(980, 780)

        self.motor = Motor(cfg)
        self.pestanas = {}

        self.tabs = QTabWidget()
        self.tabs.addTab(self._resumen(), t("tab_summary"))
        bt_add = QPushButton(t("btn_add_server"))
        bt_add.clicked.connect(self._anadir)
        self.tabs.setCornerWidget(bt_add, Qt.TopRightCorner)

        self.log = QPlainTextEdit(readOnly=True)
        self.log.setMaximumBlockCount(2000)
        self.log.setFont(QFont("Consolas", 9))

        split = QSplitter(Qt.Vertical)
        split.addWidget(self.tabs)
        split.addWidget(self.log)
        split.setSizes([580, 200])

        barra = QHBoxLayout()
        for txt, fn in ((t("btn_settings"), self._ajustes), (t("btn_about"), self._acerca)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            barra.addWidget(b)
        barra.addStretch()
        atrib = QLabel(t("attribution"))
        atrib.setOpenExternalLinks(True)
        atrib.setStyleSheet("color: gray")
        barra.addWidget(atrib)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addWidget(split)
        lay.addLayout(barra)
        self.setCentralWidget(central)

        self.motor.log.connect(self._log)
        self.motor.actualizado.connect(self._refrescar)
        for n in sorted(self.motor.rt):
            self._pestana(n)

        self.tray = QSystemTrayIcon(iconos.icono_app(), self)
        menu = QMenu()
        a_mostrar = QAction(t("tray_show"), self)
        a_mostrar.triggered.connect(self._mostrar)
        a_salir = QAction(t("tray_quit"), self)
        a_salir.triggered.connect(self._salir)
        menu.addAction(a_mostrar)
        menu.addAction(a_salir)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(core.APP_NAME)
        self.tray.activated.connect(lambda motivo: motivo == QSystemTrayIcon.Trigger and self._mostrar())
        self.tray.show()

        self._log(t("log_started", app=core.APP_NAME, ver=core.APP_VERSION, path=core.CONFIG_PATH))
        if not core.IS_WIN:
            self._log(t("log_not_windows"))
        if not (minimizado or cfg["general"]["arrancar_minimizado"]) or not QSystemTrayIcon.isSystemTrayAvailable():
            self.show()

    # ---------------------------------------------------------------- resumen
    def _resumen(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels([t("col_srv"), t("col_state"), t("col_track"), t("col_session"),
                                              t("col_mode"), t("col_weather"), t("col_last")])
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeToContents)
        h.setStretchLastSection(True)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setIconSize(QSize(20, 20))
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.cellDoubleClicked.connect(lambda r, _c: self._ir_a(r))
        lay.addWidget(self.tabla)
        lay.addWidget(nota(t("summary_help")))
        return w

    def _ir_a(self, fila):
        item = self.tabla.item(fila, 0)
        if item and int(item.text()) in self.pestanas:
            self.tabs.setCurrentWidget(self.pestanas[int(item.text())])

    def _refrescar(self):
        for n in self.motor.rt:
            if n not in self.pestanas:
                self._pestana(n)
        filas = sorted(self.motor.rt)
        self.tabla.setRowCount(len(filas))
        modos = {"real": t("mode_real"), "manual": t("mode_manual"), "off": t("mode_off")}
        for i, n in enumerate(filas):
            r = self.motor.rt[n]
            e = r.est
            s = core.server_cfg(self.cfg, n)
            clima = core.clima_servidor(e)
            cielo = core.tipo_cielo(clima)
            vals = [str(n), r.texto_estado(), e.get("circuito", "-") if e.get("plugin") else "-",
                    core.nombre_sesion(e["sesion"]) if e.get("plugin") else "-", modos.get(s["modo"], s["modo"]),
                    core.describir(clima) if clima else "-", r.ultimo_envio or "-"]
            for c, v in enumerate(vals):
                it = self.tabla.item(i, c)
                if it is None:
                    it = QTableWidgetItem()
                    self.tabla.setItem(i, c, it)
                if it.text() != v:
                    it.setText(v)
                if c == 1:
                    it.setForeground(QBrush(QColor(COLOR_ESTADO.get(r.estado, "#c77700"))))
                elif c == 5 and it.data(Qt.UserRole) != cielo:
                    it.setData(Qt.UserRole, cielo)
                    it.setIcon(iconos.icono_cielo(cielo))
                    it.setToolTip(t("sky_" + cielo))
            p = self.pestanas[n]
            if p.property("cielo") != cielo:
                p.setProperty("cielo", cielo)
                self.tabs.setTabIcon(self.tabs.indexOf(p), iconos.icono_cielo(cielo))
                self.tabs.setTabToolTip(self.tabs.indexOf(p), t("sky_" + cielo))
        actual = self.tabs.currentWidget()
        if isinstance(actual, PestanaServidor):
            actual.refrescar()
        activos = sum(1 for r in self.motor.rt.values() if r.estado == "state_running")
        self.tray.setToolTip(t("tray_tooltip", app=core.APP_NAME, k=activos))

    # ---------------------------------------------------------------- pestañas
    def _pestana(self, n):
        p = PestanaServidor(self.motor, n, self._quitar)
        self.pestanas[n] = p
        orden = sorted(self.pestanas)
        self.tabs.insertTab(1 + orden.index(n), p, t("tab_server", n=n))

    def _anadir(self):
        n, ok = QInputDialog.getInt(self, t("add_title"), t("add_prompt"), 1, 1, 99)
        if not ok:
            return
        self.motor.runtime(n)
        if n not in self.pestanas:
            self._pestana(n)
        self.tabs.setCurrentWidget(self.pestanas[n])

    def _quitar(self, n):
        r = self.motor.rt.get(n)
        if r and r.pid:
            QMessageBox.information(self, t("remove_title"), t("remove_running"))
            return
        if QMessageBox.question(self, t("remove_title"), t("remove_confirm", n=n)) != QMessageBox.Yes:
            return
        p = self.pestanas.pop(n)
        self.tabs.removeTab(self.tabs.indexOf(p))
        p.deleteLater()
        self.motor.quitar(n)

    # ---------------------------------------------------------------- varios
    def _ajustes(self):
        if DialogoAjustes(self, self.cfg).exec():
            self._log(t("log_settings_saved"))
            for n in self.motor.rt:
                self.motor.forzar_consulta(n)

    def _acerca(self):
        caja = QMessageBox(self)
        caja.setWindowTitle(t("about_title", app=core.APP_NAME))
        caja.setTextFormat(Qt.RichText)
        caja.setText(t("about_text", app=core.APP_NAME, ver=core.APP_VERSION))
        caja.setIconPixmap(iconos.icono_app().pixmap(64, 64))
        caja.exec()

    def _log(self, texto):
        linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {texto}"
        self.log.appendPlainText(linea)
        try:
            if core.LOG_PATH.exists() and core.LOG_PATH.stat().st_size > 2_000_000:
                core.LOG_PATH.replace(core.LOG_PATH.with_suffix(".log.1"))
            with open(core.LOG_PATH, "a", encoding="utf-8") as f:
                f.write(linea + "\n")
        except OSError:
            pass

    def _mostrar(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def _salir(self):
        self.salir_de_verdad = True
        self.close()

    def closeEvent(self, ev):
        if (not self.salir_de_verdad and self.cfg["general"]["minimizar_a_bandeja"]
                and QSystemTrayIcon.isSystemTrayAvailable()):
            ev.ignore()
            self.hide()
            self.tray.showMessage(core.APP_NAME, t("tray_msg"), QSystemTrayIcon.Information, 3000)
            return
        self.motor.timer.stop()
        self.tray.hide()
        ev.accept()
        QApplication.quit()


def main():
    if core.IS_WIN and not getattr(sys, "frozen", False):
        # ejecutado con python(w).exe: id propio para que la barra de tareas use nuestro icono y no el de Python
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"Xtresimracing.{core.APP_NAME}")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(core.APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(iconos.icono_app())
    cfg = core.load_config()
    core.save_config(cfg)
    i18n.set_lang(cfg["general"].get("idioma", "auto"))
    tr = QTranslator(app)
    if tr.load(QLocale(i18n.lang()), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(tr)
    Ventana(cfg, minimizado="--minimizado" in sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
