"""
xtre_iconos.py - Iconos de XtreWeather dibujados con QPainter (sin archivos de imagen).
XtreWeather icons drawn with QPainter (no image files).

Copyright (C) 2026 v1ct0r - Licencia GNU GPL v3 (ver LICENSE). Creado con asistencia de IA.

  * Icono de la aplicacion (ventana, bandeja, "Acerca de" y ejecutable).
  * Iconos del estado del cielo de cada servidor (ver xtre_core.tipo_cielo).
  * Exporta el icono de la aplicacion a .ico para PyInstaller:
        python xtre_iconos.py [xtreweather.ico]
"""
import math
import struct
import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap, QTransform

# Tamaños que se pre-renderizan: cubren 100-200 % de escalado en tablas, pestañas, bandeja y ventana.
TAMANOS = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
TAMANOS_ICO = (16, 20, 24, 32, 40, 48, 64, 128, 256)

AZUL = "#1f6feb"
SOL = "#f2a900"


def _imagen(pintar, lado: int) -> QImage:
    """Dibuja sobre una rejilla de 64 x 64 escalada a 'lado' píxeles (nítido en cualquier tamaño)."""
    img = QImage(lado, lado, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(lado / 64, lado / 64)
    pintar(p)
    p.end()
    return img


def _icono(pintar) -> QIcon:
    ic = QIcon()
    for lado in TAMANOS:
        ic.addPixmap(QPixmap.fromImage(_imagen(pintar, lado)))
    return ic


# =========================================================================== icono de la aplicacion
def _logo(p: QPainter):
    """Mismo dibujo que el icono original: cuadro azul, nube blanca y gotas."""
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(AZUL))
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14)
    p.setBrush(QColor("white"))
    for x, y, d in ((12, 22, 22), (24, 14, 28), (38, 22, 20)):
        p.drawEllipse(QRectF(x, y, d, d))
    p.drawRect(QRectF(14, 32, 42, 10))
    p.setBrush(QColor("#9ecbff"))
    for x in (18, 30, 42):
        p.drawEllipse(QRectF(x, 46, 6, 10))


@lru_cache(maxsize=None)
def icono_app() -> QIcon:
    return _icono(_logo)


def guardar_ico(ruta, tamanos=TAMANOS_ICO):
    """Guarda el icono de la aplicacion como .ico con varios tamaños (entradas PNG, Windows Vista o posterior)."""
    pngs = []
    for lado in tamanos:
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        if not _imagen(_logo, lado).save(buf, "PNG"):
            raise RuntimeError(f"no se pudo generar el PNG de {lado} px")
        pngs.append((lado, bytes(buf.data())))
    cabecera = struct.pack("<HHH", 0, 1, len(pngs))
    inicio = 6 + 16 * len(pngs)
    entradas, datos = b"", b""
    for lado, png in pngs:
        # ancho/alto 0 = 256 px; 1 plano, 32 bits por píxel
        entradas += struct.pack("<BBBBHHII", lado % 256, lado % 256, 0, 0, 1, 32, len(png), inicio + len(datos))
        datos += png
    Path(ruta).write_bytes(cabecera + entradas + datos)


# =========================================================================== iconos del cielo
def _nube(x, y, escala=1.0) -> QPainterPath:
    """Silueta de nube de 44 x 28 (por escala) con la esquina superior izquierda en (x, y)."""
    c = QPainterPath()
    c.setFillRule(Qt.WindingFill)       # para que simplified() una las piezas en una sola silueta
    c.addEllipse(QRectF(0, 10, 18, 18))
    c.addEllipse(QRectF(9, 0, 24, 24))
    c.addEllipse(QRectF(25, 8, 19, 19))
    c.addRoundedRect(QRectF(2, 14, 40, 14), 7, 7)
    return QTransform().translate(x, y).scale(escala, escala).map(c.simplified())


def _pinta_nube(p, silueta, relleno, borde):
    p.setPen(QPen(QColor(borde), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(QColor(relleno))
    p.drawPath(silueta)


def _sol(p, cx, cy, radio, rayo_ini, rayo_fin, grosor):
    color = QColor(SOL)
    p.setPen(QPen(color, grosor, Qt.SolidLine, Qt.RoundCap))
    for i in range(8):
        a = math.radians(i * 45)
        p.drawLine(QPointF(cx + rayo_ini * math.cos(a), cy + rayo_ini * math.sin(a)),
                   QPointF(cx + rayo_fin * math.cos(a), cy + rayo_fin * math.sin(a)))
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(cx, cy), radio, radio)


def _gotas(p, xs, y0, largo, grosor=4.0):
    p.setPen(QPen(QColor(AZUL), grosor, Qt.SolidLine, Qt.RoundCap))
    for x in xs:
        p.drawLine(QPointF(x, y0), QPointF(x - largo * 0.35, y0 + largo))


def _despejado(p):
    _sol(p, 32, 32, 12, 18, 27, 5)


def _poco_nuboso(p):
    _sol(p, 23, 23, 10, 15, 21, 4)
    _pinta_nube(p, _nube(14, 28, 1.05), "#f6f8fa", "#8c959f")


def _nublado(p):
    _pinta_nube(p, _nube(18, 8, 0.9), "#afb8c1", "#6e7781")
    _pinta_nube(p, _nube(4, 24, 1.1), "#eaeef2", "#8c959f")


def _lluvia(p):
    _pinta_nube(p, _nube(9, 6, 1.05), "#d0d7de", "#6e7781")
    _gotas(p, (24, 35, 46), 41, 14)


def _lluvia_fuerte(p):
    _pinta_nube(p, _nube(9, 4, 1.05), "#6e7781", "#424a53")
    _gotas(p, (19, 29, 39, 49), 38, 19)


def _sin_datos(p):
    _pinta_nube(p, _nube(9, 18, 1.05), Qt.transparent, "#8c959f")     # solo el contorno: "sin datos"


_CIELOS = {"clear": _despejado, "partly": _poco_nuboso, "cloudy": _nublado,
           "rain": _lluvia, "heavy_rain": _lluvia_fuerte, "nodata": _sin_datos}


@lru_cache(maxsize=None)
def icono_cielo(tipo: str) -> QIcon:
    """tipo: clear | partly | cloudy | rain | heavy_rain | nodata (ver xtre_core.tipo_cielo)."""
    return _icono(_CIELOS.get(tipo, _sin_datos))


if __name__ == "__main__":
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "xtreweather.ico")
    guardar_ico(destino)
    print(f"OK: {destino.resolve()}")
