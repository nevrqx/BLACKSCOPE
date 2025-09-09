from PySide6 import QtWidgets, QtGui, QtCore
import os, sys
from PySide6.QtCore import QFileSystemWatcher
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
import multiprocessing
import requests
import pymem
import pymem.process
import win32con
import win32gui
import json
import os
import sys
import time
import ctypes
from ctypes import wintypes
import random
import threading
import math
from datetime import date, datetime, timezone

# Удалено: таймер самоуничтожения и любые ограничения по дате

# Константы
CONFIG_DIR = os.path.join(os.environ['LOCALAPPDATA'], 'temp', 'PyIt')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
CONFIGS_DIR = os.path.join(CONFIG_DIR, 'configs')
DEFAULT_SETTINGS = {
    "esp_rendering": 1,
    "esp_mode": 1,
    "line_rendering": 1,
    "hp_bar_rendering": 1,
    "hp_bar_gradient": 1,        # 0/1 — градиентная заливка полосы HP
    "hp_bar_gradient_style": 0,  # стиль градиента HP: 0-красный→жёлтый, 1-зелёный→лайм, 2-синий→голубой
    "head_hitbox_rendering": 1,
    "bons": 1,
    "nickname": 1,
    "radius": 50,
    "weapon": 1,
    "bomb_esp": 1,
    "neon_outline": 0,
    "neon_outline_color": 0,
    "box_style": 0,              # 0-классический, 1-угловой, 2-капсула
    "box_thickness": 2,          # толщина линий бокса
    "box_opacity": 220,          # прозрачность (альфа) линий бокса 50..255
    "box_fill": 0,               # 0/1 заливка бокса
    "box_fill_alpha_pct": 25,    # прозрачность заливки 0..100 (в процентах)
    "box_fill_gradient": 1,      # 0/1 использовать градиентную заливку
    # Aimbot
    "aim_enabled": 0,
    "aim_hold_key": "RMB",      # клавиша удержания: RMB/LMB/ALT/SHIFT/CTRL/MOUSE4/MOUSE5
    "aim_fov": 80,               # радиус в пикселях
    "aim_snap": 1,               # моментальный перевод в цель
    "aim_snap_sticky": 1,        # удерживать прицел на цели пока зажата клавиша
    "aim_bone": 0,               # 0-глава, 1-грудь
    "aim_head_bone_id": 6,       # ID кости головы (по дамперу)
    "aim_head_mix": 0.15,        # 0..1 — доля шеи в целевой точке (стабильность на дальних)
    "aim_head_z_offset": 2,      # доп. сдвиг головы по Z (вверх) для точного попадания
    "aim_screen_offset_x": 0,    # тонкая экранная юстировка X (пикс)
    "aim_screen_offset_y": 4,    # тонкая экранная юстировка Y (пикс)
    "aim_dynamic_x_pct": 0.0,    # доп. экранная юстировка X в долях роста модели (на экране)
    "aim_dynamic_y_pct": 0.0,    # доп. экранная юстировка Y в долях роста модели (на экране)
    "aim_team": 0,               # 0-только враги, 1-все
    "aim_humanize": 1,           # человеческие микродребезги/рандомизация
    "aim_reaction_ms": 90,       # задержка реакции, 0..300
    "aimbot_speed": 1.6,          # множитель скорости шага (0.1..5.0)
    "aimbot_ease_out": 0.85,      # показатель ease-out (0.1..1.0)
    "aimbot_overshoot_chance": 0.3,   # вероятность небольшой «перестяжки» (0..1)
    "aimbot_overshoot_strength": 3.5, # сила «перестяжки» (пикс)
    "aim_stop_radius": 2,         # зона покоя у центра (px)
    # Trigger Bot
    "trigger_enabled": 0,
    "trigger_hold_key": "ALT",  # клавиша удержания: RMB/LMB/ALT/SHIFT/CTRL/MOUSE4/MOUSE5 или "Always"
    "trigger_radius": 10,        # радиус попадания в пикселях
    "trigger_delay_ms": 30,      # задержка клика
    # Hitmarker
    "hitmarker_enabled": 1,
    "hitmarker_duration_ms": 1700,
    "show_fps": 1,
    "overlay_fps_limit": 144,    # лимит FPS оверлея (40..300)
    "toggle_hotkey_mods": "",
    "toggle_hotkey_key": "F6",
    "accent": 0,
    # UI language: 'en' or 'ru'
    "language": "en"
}

# Курс для приблизительного пересчёта RUB→USD (для отображения в прайс-листе)
RUB_PER_USD_APPROX = 90.0

def _rub_to_usd_str(rub: int) -> str:
    try:
        usd = rub / float(RUB_PER_USD_APPROX)
        return f"≈ ${usd:.2f}"
    except Exception:
        return ""
# Лицензия/активация (по умолчанию выключено)
DEFAULT_SETTINGS.update({
    "license_active": 1,
    "license_key": "",
    "license_ip": "",
    "license_activated_at": "",
    "license_expires_at": ""
})

# --- Supabase отключен: автономный режим ---
SUPABASE_URL = ""
SUPABASE_REST_URL = ""
SUPABASE_ANON_KEY = ""

def _get_public_ip(timeout: float = 3.0) -> str:
    try:
        r = requests.get("https://api.ipify.org", timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text.strip()
    except Exception:
        pass
    try:
        r = requests.get("https://ifconfig.me/ip", timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text.strip()
    except Exception:
        pass
    try:
        r = requests.get("https://checkip.amazonaws.com", timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text.strip()
    except Exception:
        pass
    try:
        r = requests.get("https://ip.seeip.org", timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text.strip()
    except Exception:
        pass
    return ""

def _sb_headers():
    # Supabase отключен: пустые заголовки
    return {}

def _license_select_by_key(key: str):
    # Supabase отключен: не запрашиваем ничего из сети
    return None

def _license_mark_used(key: str, ip: str) -> bool:
    # Supabase отключен: всегда успех локально
    return True

def _license_delete_key(key: str) -> None:
    # Supabase отключен: ничего не делаем
    pass

def verify_license_settings(settings: dict) -> dict:
    # Автономный режим: лицензия всегда активна, без сетевых проверок
    try:
        settings["license_active"] = 1
        # Поля оставляем для совместимости UI
        if not settings.get("license_activated_at"):
            settings["license_activated_at"] = ""
        if not settings.get("license_expires_at"):
            settings["license_expires_at"] = ""
    except Exception:
        pass
    return settings
BombPlantedTime = 0
BombDefusedTime = 0

# Вспомогательные структуры эффекта урона
_LAST_HP_BY_ENTITY = {}
_DAMAGE_FLOATS = []  # [{"x":float,"y":float,"value":int,"t0":time}]
# События попаданий для HITMARKER
_HITMARKERS = []  # [{"t0": float}]

# Функции утилиты
def _apply_dpi_and_font_attributes():
    # В Qt6 AA_EnableHighDpiScaling/AA_UseHighDpiPixmaps включены по умолчанию и помечены как deprecated.
    # Не трогаем их, чтобы не спамить предупреждениями. Управляем только политикой округления.
    try:
        # Более ровное масштабирование на HiDPI дисплеях
        QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

def _apply_app_font(app: QtWidgets.QApplication) -> None:
    # Настраиваем читаемый шрифт и хинтинг
    try:
        font = QtGui.QFont("Segoe UI Variable Text", 10)
        if not QtGui.QFontInfo(font).family():
            font = QtGui.QFont("Segoe UI", 10)
        try:
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferFullHinting)
        except Exception:
            pass
        app.setFont(font)
    except Exception:
        pass

_apply_dpi_and_font_attributes()
def load_settings():
    # Обеспечиваем наличие каталога и файла
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIGS_DIR):
        os.makedirs(CONFIGS_DIR, exist_ok=True)
    # Попытки"мягкого" чтения (на случай, когда файл ещё пишется)
    attempts = 5
    delay = 0.05
    for attempt in range(attempts):
        try:
            if not os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_SETTINGS, f, indent=4, ensure_ascii=False)
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Минимальная валидация и слияние с дефолтом
                if not isinstance(data, dict):
                    raise ValueError("Config is not a dict")
                merged = {**DEFAULT_SETTINGS, **data}
                # Автономный режим: гарантия включенной лицензии и очистка полей
                changed = False
                if merged.get("license_active") != 1:
                    merged["license_active"] = 1
                    changed = True
                # чистим сетевые поля
                for k in ("license_key", "license_ip", "license_activated_at", "license_expires_at"):
                    if merged.get(k):
                        merged[k] = "" if k != "license_active" else 1
                        changed = True
                if changed:
                    # Сохраняем исправленные настройки, чтобы UI сразу работал без ограничений
                    try:
                        save_settings(merged)
                    except Exception:
                        pass
                return merged
        except Exception:
            # JSONDecodeError/временная пустота файла — ждём и пробуем снова
            time.sleep(delay)
    # Если всё плохо — пересоздаём
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_SETTINGS, f, indent=4, ensure_ascii=False)
    return dict(DEFAULT_SETTINGS)

def enforce_license_gating(settings: dict) -> dict:
    # Автономный режим: никаких ограничений по лицензии
    return settings

def save_settings(settings):
    # Пишем атомарно во временный файл и заменяем
    tmp_path = CONFIG_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(tmp_path, CONFIG_FILE)
    except Exception:
        # Фоллбек на прямую запись
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)

def get_offsets_and_client_dll():
    offsets = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json').json()
    client_dll = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json').json()
    return offsets, client_dll

def get_window_size(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:
        rect = win32gui.GetClientRect(hwnd)
        return rect[2], rect[3]
    return None, None

def w2s(mtx, posx, posy, posz, width, height):
    screenW = (mtx[12] * posx) + (mtx[13] * posy) + (mtx[14] * posz) + mtx[15]
    if screenW > 0.001:
        screenX = (mtx[0] * posx) + (mtx[1] * posy) + (mtx[2] * posz) + mtx[3]
        screenY = (mtx[4] * posx) + (mtx[5] * posy) + (mtx[6] * posz) + mtx[7]
        camX = width / 2
        camY = height / 2
        x = camX + (camX * screenX / screenW)
        y = camY - (camY * screenY / screenW)
        return [int(x), int(y)]
    return [-999, -999]

# Генерация простых векторных иконок под акцентный цвет
def generate_icon_pixmap(name: str, size: int, color: QtGui.QColor) -> QtGui.QPixmap:
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    pen = QtGui.QPen(color, max(1.5, size * 0.08), QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.NoBrush)

    c = size / 2.0
    r = size / 2.0

    if name == "esp":
        # Прицел: окружность + крест
        radius = r * 0.55
        painter.drawEllipse(QtCore.QPointF(c, c), radius, radius)
        gap = radius * 0.55
        # горизонталь
        painter.drawLine(QtCore.QPointF(c - radius, c), QtCore.QPointF(c - gap, c))
        painter.drawLine(QtCore.QPointF(c + gap, c), QtCore.QPointF(c + radius, c))
        # вертикаль
        painter.drawLine(QtCore.QPointF(c, c - radius), QtCore.QPointF(c, c - gap))
        painter.drawLine(QtCore.QPointF(c, c + gap), QtCore.QPointF(c, c + radius))

    elif name == "aim":
        # Буллсай: две окружности и точка в центре
        painter.drawEllipse(QtCore.QPointF(c, c), r * 0.55, r * 0.55)
        painter.drawEllipse(QtCore.QPointF(c, c), r * 0.30, r * 0.30)
        painter.setBrush(color)
        painter.drawEllipse(QtCore.QPointF(c, c), r * 0.08, r * 0.08)
        painter.setBrush(QtCore.Qt.NoBrush)

    elif name == "trigger":
        # Молния
        path = QtGui.QPainterPath()
        path.moveTo(c - r * 0.2, c - r * 0.6)
        path.lineTo(c + r * 0.15, c - r * 0.1)
        path.lineTo(c - r * 0.05, c - r * 0.1)
        path.lineTo(c + r * 0.2, c + r * 0.6)
        path.lineTo(c - r * 0.15, c + r * 0.05)
        path.lineTo(c + r * 0.05, c + r * 0.05)
        path.closeSubpath()
        painter.fillPath(path, color)

    elif name == "misc":
        # Слайдеры: три линии и кружки на разных позициях
        y1, y2, y3 = c - r * 0.45, c, c + r * 0.45
        margin = r * 0.2
        painter.drawLine(margin, y1, size - margin, y1)
        painter.drawLine(margin, y2, size - margin, y2)
        painter.drawLine(margin, y3, size - margin, y3)
        painter.setBrush(color)
        painter.drawEllipse(QtCore.QPointF(c + r * 0.25, y1), r * 0.12, r * 0.12)
        painter.drawEllipse(QtCore.QPointF(c - r * 0.15, y2), r * 0.12, r * 0.12)
        painter.drawEllipse(QtCore.QPointF(c + r * 0.05, y3), r * 0.12, r * 0.12)
        painter.setBrush(QtCore.Qt.NoBrush)

    elif name == "about":
        # Кружок + i
        painter.drawEllipse(QtCore.QPointF(c, c), r * 0.55, r * 0.55)
        # точка
        painter.setBrush(color)
        painter.drawEllipse(QtCore.QPointF(c, c - r * 0.18), r * 0.06, r * 0.06)
        painter.setBrush(QtCore.Qt.NoBrush)
        # палка
        painter.drawLine(QtCore.QPointF(c, c - r * 0.05), QtCore.QPointF(c, c + r * 0.22))

    elif name == "pricing":
        # Монета с символом доллара — более понятная иконка для прайса
        coin_r = r * 0.55
        painter.drawEllipse(QtCore.QPointF(c, c), coin_r, coin_r)
        # Внутренняя окружность
        painter.drawEllipse(QtCore.QPointF(c, c), coin_r * 0.78, coin_r * 0.78)
        # Символ $ как текст (толстый шрифт)
        font = QtGui.QFont("Segoe UI", int(size * 0.6))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QtCore.QRectF(c - coin_r, c - coin_r, coin_r * 2, coin_r * 2), QtCore.Qt.AlignCenter, "$")

    painter.end()
    return pixmap

# --- App icon helpers (ensure taskbar icon shows for all processes) ---
def _resource_path(rel: str) -> str:
    try:
        base = getattr(sys, "_MEIPASS")  # when bundled by PyInstaller
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, rel)

def _set_win_app_id(app_id: str) -> None:
    try:
        import ctypes  # type: ignore
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

def _apply_app_icon(app: QtWidgets.QApplication, window: QtWidgets.QWidget | None = None) -> None:
    try:
        icon_path = _resource_path("app.ico")
        if os.path.exists(icon_path):
            icon = QtGui.QIcon(icon_path)
            app.setWindowIcon(icon)
            if window is not None:
                window.setWindowIcon(icon)
    except Exception:
        pass
# UI Widgets
class ToggleSwitch(QtWidgets.QCheckBox):
    def __init__(self, label_text: str = "", parent=None):
        super().__init__(label_text, parent)
        self._offset = 0.0
        self._thumb_radius = 9
        self._track_radius = 11
        self._anim = QtCore.QPropertyAnimation(self, b"offset", self)  
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setDuration(200)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.toggled.connect(self._start_anim)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

    def sizeHint(self):
        return QtCore.QSize(48, 24)

    def _start_anim(self, checked: bool):
        self._anim.stop()
        end = 1.0 if checked else 0.0
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(end)
        self._anim.start()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        rect = self.rect()
        # Track - более компактный и ровный
        track_width = 40
        track_height = 20
        track_rect = QtCore.QRectF(2, (rect.height() - track_height) / 2, track_width, track_height)

        # Получаем акцентный цвет
        accent_idx = int(self.window().settings.get("accent", 0)) if hasattr(self.window(), "settings") else 0
        accents = [
            "#5a78ff",  # blue
            "#ff6b6b",  # red  
            "#36d399",  # green
            "#f3c969",  # yellow
            "#b072ff",  # purple
        ]
        accent_color = accents[accent_idx % len(accents)]

        # Рисуем трек
        painter.setPen(QtCore.Qt.NoPen)
        if self.isChecked():
            painter.setBrush(QtGui.QColor(accent_color))
        else:
            painter.setBrush(QtGui.QColor("#2a2e3a"))
        painter.drawRoundedRect(track_rect, self._track_radius, self._track_radius)

        # Thumb (ползунок) - более аккуратный
        thumb_size = 16
        thumb_margin = 2
        max_x = track_rect.width() - thumb_size - thumb_margin * 2
        x_pos = track_rect.left() + thumb_margin + max_x * self._offset
        y_pos = track_rect.top() + thumb_margin
        thumb_rect = QtCore.QRectF(x_pos, y_pos, thumb_size, thumb_size)
        
        # Тень для ползунка
        shadow_rect = thumb_rect.adjusted(0, 1, 0, 1)
        painter.setBrush(QtGui.QColor(0, 0, 0, 20))
        painter.drawEllipse(shadow_rect)
        
        # Сам ползунок
        painter.setBrush(QtGui.QColor("#ffffff"))
        painter.drawEllipse(thumb_rect)

        # Label
        if self.text():
            text_rect = QtCore.QRectF(track_rect.right() + 8, 0, rect.width() - track_rect.width() - 8, rect.height())
            painter.setPen(QtGui.QColor("#e1e5ff"))
            painter.drawText(text_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.text())

    @QtCore.Property(float)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value: float):
        self._offset = value
        self.update()

    # Make sure clicks always toggle the control, even if styles or layouts interfere
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.setChecked(not self.isChecked())
            event.accept()
            return
        super().mousePressEvent(event)

class HotkeyEdit(QtWidgets.QLineEdit):
    def __init__(self, initial_text: str = "F6", parent=None):
        super().__init__(initial_text, parent)
        self.setPlaceholderText("F6")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setClearButtonEnabled(True)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        # Function keys F1..F24
        if QtCore.Qt.Key_F1 <= key <= QtCore.Qt.Key_F24:
            n = key - QtCore.Qt.Key_F1 + 1
            self.setText(f"F{n}")
            event.accept()
            self.editingFinished.emit()
            return
        # Letters A..Z
        if QtCore.Qt.Key_A <= key <= QtCore.Qt.Key_Z:
            ch = chr(ord('A') + (key - QtCore.Qt.Key_A))
            self.setText(ch)
            event.accept()
            self.editingFinished.emit()
            return
        # Digits 0..9
        if QtCore.Qt.Key_0 <= key <= QtCore.Qt.Key_9:
            ch = chr(ord('0') + (key - QtCore.Qt.Key_0))
            self.setText(ch)
            event.accept()
            self.editingFinished.emit()
            return
        super().keyPressEvent(event)

class TitleBar(QtWidgets.QWidget):
    def __init__(self, parent=None, shutdown_event=None):
        super().__init__(parent)
        self._drag_pos = None
        self._shutdown_event = shutdown_event
        self.setObjectName("TitleBar")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        # Логотип
        logo_layout = QtWidgets.QHBoxLayout()
        logo_layout.setSpacing(8)
        
        # Добавляем иконку перед названием
        self.icon = QtWidgets.QLabel("●")
        self.icon.setObjectName("BrandIcon")
        logo_layout.addWidget(self.icon)
        
        self.title = QtWidgets.QLabel("BLACKSCOPE")
        self.title.setObjectName("Brand")
        logo_layout.addWidget(self.title)
        
        layout.addLayout(logo_layout)
        layout.addStretch(1)

        # Кнопки управления окном в контейнере
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Language selector (text): EN, RU, UA
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.setObjectName("LangCombo")
        self.lang_combo.setFixedHeight(32)
        self.lang_combo.setMinimumWidth(84)
        self.lang_combo.setFixedWidth(84)
        self.lang_combo.setMinimumContentsLength(2)
        self.lang_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.lang_combo.setEditable(False)
        self.lang_combo.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # Improve visual alignment of text and popup
        self.lang_combo.setView(QtWidgets.QListView())
        self.lang_combo.view().setSpacing(0)
        # Language combo will use the global ComboBox styling from apply_theme()
        self._lang_items = [("en", "EN"), ("ru", "RU"), ("uk", "UA")]
        for _, label in self._lang_items:
            self.lang_combo.addItem(label)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        buttons_layout.addWidget(self.lang_combo)

        self.min_btn = QtWidgets.QPushButton("–")
        self.min_btn.setObjectName("TbBtn")
        self.min_btn.setFixedSize(32, 32)
        self.min_btn.clicked.connect(self._minimize)
        buttons_layout.addWidget(self.min_btn)

        self.close_btn = QtWidgets.QPushButton("✕")
        self.close_btn.setObjectName("TbBtnClose")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.clicked.connect(self._close)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)

    def _minimize(self):
        # Для панели (shutdown_event отсутствует) скрываем окно, чтобы поднять по хоткею
        if self._shutdown_event is None:
            self.window().hide()
        else:
            self.window().showMinimized()

    def _close(self):
        # Если передан shutdown_event — закрываем всё приложение
        if self._shutdown_event is not None:
            try:
                self._shutdown_event.set()
                # Завершаем все процессы, связанные с оверлеем
                try:
                    # Находим и завершаем все процессы, связанные с нашей программой
                    import psutil
                    current_pid = os.getpid()
                    current_process = psutil.Process(current_pid)
                    parent_pid = current_process.ppid()
                    
                    # Завершаем все дочерние процессы и процессы с тем же родителем
                    for proc in psutil.process_iter(['pid', 'name', 'ppid']):
                        try:
                            # Если это дочерний процесс нашего процесса или процесс с тем же родителем
                            if proc.info['ppid'] == current_pid or proc.info['ppid'] == parent_pid:
                                if proc.pid != current_pid:  # Не завершаем текущий процесс
                                    proc.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            pass
                except Exception as e:
                    print(f"Ошибка при завершении процессов: {e}")
            finally:
                QtWidgets.QApplication.quit()
        else:
            # Иначе закрываем только это окно (панель)
            self.window().close()

    def _on_lang_changed(self, idx: int):
        code = self._lang_items[idx][0] if 0 <= idx < len(self._lang_items) else "en"
        win = self.window()
        if hasattr(win, "set_language"):
            win.set_language(code)

    def _sync_language_selector(self):
        # Select current language in the combobox
        lang = getattr(self.window(), "lang", "en")
        for i, (code, _) in enumerate(self._lang_items):
            if code == lang:
                try:
                    self.lang_combo.blockSignals(True)
                    self.lang_combo.setCurrentIndex(i)
                finally:
                    self.lang_combo.blockSignals(False)
                break

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = None

# Конфигуратор
class ConfigWindow(QtWidgets.QWidget):
    def __init__(self, shutdown_event=None):
        super().__init__()
        self._shutdown_event = shutdown_event
        # Автономный режим: грузим локальные настройки без сетевых проверок
        self.settings = load_settings()
        self.lang = self.settings.get("language", "en")
        self.initUI()
        self.is_dragging = False
        self.drag_start_position = None
        self.apply_theme()
        self.fade_in()

    # Simple translation helper (uk falls back to ru unless t3 is used)
    def t(self, en: str, ru: str) -> str:
        if (self.lang or "en") == "en":
            return en
        # ru or uk -> use Russian as default for Slavic locale until full UA translation provided
        return ru

    # List translation helper
    def tl(self, en_list, ru_list):
        return en_list if (self.lang or "en") == "en" else ru_list

    # Three-language helpers (EN/RU/UA)
    def t3(self, en: str, ru: str, uk: str) -> str:
        lang = (self.lang or "en")
        if lang == "en":
            return en
        if lang == "ru":
            return ru
        return uk

    def tl3(self, en_list, ru_list, uk_list):
        lang = (self.lang or "en")
        if lang == "en":
            return en_list
        if lang == "ru":
            return ru_list
        return uk_list

    # Translate short notifications/messages to current UI language
    def _tr(self, text: str) -> str:
        lang = (self.lang or "en")
        # Normalize dynamic prefixes
        if text.startswith("Конфиг сохранён:"):
            suffix = text.split(":", 1)[1].strip()
            if lang == "en":
                return f"Config saved: {suffix}"
            if lang == "uk":
                return f"Профіль збережено: {suffix}"
            return text
        mapping = {
            # RU base -> (EN, UA)
            "Настройки применены": ("Settings applied", "Налаштування застосовано"),
            "Ключ недействителен или уже активирован на другом IP": ("The key is invalid or already activated on another IP", "Ключ недійсний або вже активований на іншому IP"),
            "Произошла ошибка при запуске конфигуратора.\nПопробуйте перезапустить программу.": ("An error occurred while starting the configurator.\nTry restarting the application.", "Сталася помилка під час запуску конфігуратора.\nСпробуйте перезапустити програму."),
            "CS2 не запущен или не найден.\nЗапустите игру и перезапустите программу.": ("CS2 is not running or not found.\nStart the game and restart the application.", "CS2 не запущений або не знайдений.\nЗапустіть гру та перезапустіть програму."),
        }
        if text in mapping:
            en, uk = mapping[text]
            if lang == "en":
                return en
            if lang == "uk":
                return uk
        # Dynamic error prefixes
        if text.startswith("Ошибка активации:"):
            payload = text.split(":", 1)[1].strip()
            if lang == "en":
                return f"Activation error: {payload}"
            if lang == "uk":
                return f"Помилка активації: {payload}"
        return text

    def set_language(self, code: str):
        # Allowed: en, ru, uk
        if code not in ("en", "ru", "uk"):
            code = "en"
        if code == self.lang:
            return
        self.lang = code
        self.settings["language"] = self.lang
        save_settings(self.settings)
        # Rebuild UI to apply language across all widgets
        self.refresh_ui()

    def refresh_ui(self):
        # Keep current page index
        current_index = 0
        try:
            current_index = self.stack.currentIndex() if hasattr(self, "stack") else 0
        except Exception:
            pass
        # Recreate UI (initUI will clear existing layout safely)
        self.initUI()
        self.apply_theme()
        try:
            self.select_nav(current_index)
        except Exception:
            pass

    def _clear_layout(self, layout: QtWidgets.QLayout):
        try:
            while layout.count():
                item = layout.takeAt(0)
                if item is None:
                    continue
                w = item.widget()
                if w is not None:
                    w.deleteLater()
                else:
                    child_layout = item.layout()
                    if child_layout is not None:
                        self._clear_layout(child_layout)
        except Exception:
            pass

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowTitle("BLACKSCOPE")
        self.setFixedSize(980, 640)
        # Центрируем на доступном экране и не даём системе перекраивать высоту
        try:
            geo = QtGui.QGuiApplication.primaryScreen().availableGeometry()
            x = geo.x() + (geo.width() - 980) // 2
            y = geo.y() + (geo.height() - 640) // 2
            self.setGeometry(x, y, 980, 640)
        except Exception:
            pass

        # Reuse existing root layout if present; otherwise create it
        if self.layout() is None:
            root = QtWidgets.QVBoxLayout(self)
        else:
            root = self.layout()
            # Safely clear previous contents
            self._clear_layout(root)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(0)

        # Контейнер с тенью
        container = QtWidgets.QFrame()
        container.setObjectName("Container")
        shadow = QtWidgets.QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QtGui.QColor(0, 0, 0, 180))
        container.setGraphicsEffect(shadow)
        root.addWidget(container)

        chrome = QtWidgets.QVBoxLayout(container)
        chrome.setContentsMargins(0, 0, 0, 0)
        chrome.setSpacing(0)

        title = TitleBar(container, shutdown_event=self._shutdown_event)
        chrome.addWidget(title)
        # Sync language selector state
        try:
            title._sync_language_selector()
        except Exception:
            pass

        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        chrome.addLayout(body, 1)

        # Стек страниц контента (создаём до сайдбара, т.к. сайдбар может дергать select_nav)
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.create_esp_page())         # 0
        self.stack.addWidget(self.create_aim_page())         # 1
        self.stack.addWidget(self.create_trigger_page())     # 2
        self.stack.addWidget(self.create_misc_page())        # 3
        # Удалён раздел прайса/подписки для автономного режима
        self.stack.addWidget(self.create_about_page())       # 4

        sidebar = self.create_sidebar()

        body.addWidget(sidebar)
        body.addWidget(self.stack, 1)
        # По умолчанию активна первая вкладка
        self.select_nav(0)

    def apply_theme(self):
        accent_idx = int(self.settings.get("accent", 0))
        accents = [
            ("#5a78ff", "#3f5bdb"),  # blue
            ("#ff6b6b", "#d84e4e"),  # red
            ("#36d399", "#21b07f"),  # green
            ("#f3c969", "#d7a93a"),  # yellow
            ("#b072ff", "#8c52e6"),  # purple
        ]
        ac, ac_dark = accents[accent_idx % len(accents)]
        base_font = "'Segoe UI Variable Text', 'Segoe UI'"
        self.setStyleSheet(f"""
            QWidget {{ background-color: transparent; color: #eef0ff; font: 500 14px {base_font}; }}
            #Container {{ background-color: #0b0d15; border-radius: 20px; }}
            QLabel#Brand {{ font: 700 19px {base_font}; color: #ffffff; letter-spacing: 0.4px; }}
            QLabel#BrandIcon {{ font: 700 16px {base_font}; color: {ac}; }}
            QLabel#Header {{ font: 650 17px {base_font}; color: {ac}; margin: 14px 10px 6px 10px; letter-spacing: 0.3px; }}
            QLabel#AboutText {{ color: #f2f3ff; }}
            QLabel#AboutText a {{ color: {ac}; }}
            QLabel#AboutText a:hover {{ text-decoration: underline; }}
            #TitleBar {{ background: #0a0c12; border-bottom: 1px solid #1a1e28; border-top-left-radius: 20px; border-top-right-radius: 20px; }}
            QPushButton#TbBtn, QPushButton#TbBtnClose {{
                background: #121622; border: 1px solid #20263a; border-radius: 12px;
                color: #d4d9ef; font: 600 13px {base_font};
            }}
            QPushButton#TbBtn:hover {{ background: #182033; }}
            QPushButton#TbBtnClose:hover {{ background: #2a0f14; color: #ffd6db; }}
            QFrame#Sidebar {{ background: #090b10; border-right: 1px solid #1a1e28; border-bottom-left-radius: 20px; }}
            QPushButton#Nav {{
                background: transparent; color: #d7dbf6; text-align: left; padding: 10px 14px; 
                font: 600 14px {base_font}; border-radius: 14px; margin: 6px 8px; border: 1px solid transparent;
            }}
            QPushButton#Nav:hover {{ background: #121829; color: #ffffff; border-color: #202b45; }}
            QPushButton#Nav:pressed {{ background: #0f1526; }}
            QPushButton#Nav:checked {{
                color: #ffffff; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #141d33, stop:1 #10182b);
                border-color: #2a3a66;
            }}
            QFrame#Card {{ background: #0f1320; border: 1px solid #1a2140; border-radius: 16px; }}
            QGroupBox {{ border: none; margin-top: 0px; }}
            QLineEdit {{
                background: #0f1424; border: 1px solid #242b46; border-radius: 10px; padding: 8px 12px; color: #eef0ff;
                font: 500 14px {base_font};
            }}
            QLineEdit:hover {{ border-color: #2e3652; }}
            QLineEdit:focus {{ border-color: {ac}; }}
            
            /* Modern ComboBox styling */
            QComboBox {{
                background: #0f1424;
                border: 1px solid #242b46;
                border-radius: 10px;
                padding: 6px 10px;
                padding-right: 28px;
                color: #eef0ff;
                font: 500 14px {base_font};
                min-height: 16px;
            }}
            QComboBox:hover {{
                border-color: #2e3652;
                background: #111628;
            }}
            QComboBox:focus {{
                border-color: {ac};
                background: #121729;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #8892b0;
                width: 0;
                height: 0;
                margin-right: 6px;
            }}
            QComboBox::down-arrow:hover {{
                border-top-color: {ac};
            }}
            QComboBox QAbstractItemView {{
                background: #131722;
                border: 1px solid #242b46;
                border-radius: 8px;
                padding: 4px;
                color: #eef0ff;
                selection-background-color: {ac};
                selection-color: #ffffff;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
                border-radius: 4px;
                margin: 1px;
                min-height: 16px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: #1c2333;
                color: #ffffff;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: {ac};
                color: #ffffff;
                font-weight: 500;
            }}
            
            /* Language selector special styling */
            QComboBox#LangCombo {{
                background: #121622;
                border: 1px solid #20263a;
                border-radius: 12px;
                padding: 8px 12px;
                padding-right: 30px;
                color: #d4d9ef;
                font: 600 13px {base_font};
                min-height: 16px;
                text-align: center;
            }}
            QComboBox#LangCombo:hover {{
                background: #182033;
                border-color: #2a3248;
            }}
            QComboBox#LangCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
                background: transparent;
            }}
            QComboBox#LangCombo::down-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 4px solid #8892b0;
                width: 0;
                height: 0;
                margin-right: 4px;
            }}
            QComboBox#LangCombo::down-arrow:hover {{
                border-top-color: #d4d9ef;
            }}
            QComboBox#LangCombo QAbstractItemView {{
                background: #0f1320;
                border: 1px solid #20263a;
                border-radius: 8px;
                padding: 4px;
                color: #eef0ff;
                selection-background-color: #141d33;
                outline: none;
            }}
            QComboBox#LangCombo QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 1px;
                min-height: 16px;
                text-align: center;
            }}
            QComboBox#LangCombo QAbstractItemView::item:hover {{
                background: #1c2333;
                color: #ffffff;
            }}
            QComboBox#LangCombo QAbstractItemView::item:selected {{
                background: #141d33;
                color: #ffffff;
            }}
            QSlider::groove:horizontal {{ background: #1b233a; height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {ac}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}
            QSlider::handle:horizontal:hover {{ background: {ac_dark}; }}
            QLabel.rowLabel {{ color: #e1e5ff; font: 500 14px {base_font}; }}

            /* Clean scrollbars */
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px 2px 4px 2px; }}
            QScrollBar::handle:vertical {{ background: #272c3b; min-height: 32px; border-radius: 4px; }}
            QScrollBar::handle:vertical:hover {{ background: {ac_dark}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px 4px 2px 4px; }}
            QScrollBar::handle:horizontal {{ background: #272c3b; min-width: 32px; border-radius: 4px; }}
            QScrollBar::handle:horizontal:hover {{ background: {ac_dark}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
            
            /* Config buttons styling */
            QPushButton#ConfigBtn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2140, stop:1 #0f1320);
                border: 1px solid #242b46;
                border-radius: 10px;
                color: #eef0ff;
                font: 600 13px {base_font};
                padding: 8px 16px;
                min-height: 16px;
            }}
            QPushButton#ConfigBtn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e2548, stop:1 #131628);
                border-color: {ac};
                color: #ffffff;
            }}
            QPushButton#ConfigBtn:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f1320, stop:1 #0a0e18);
                border-color: {ac_dark};
            }}
            
            QPushButton#ConfigApplyBtn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {ac}, stop:1 {ac_dark});
                border: 1px solid {ac};
                border-radius: 10px;
                color: #ffffff;
                font: 600 13px {base_font};
                padding: 8px 16px;
                min-height: 16px;
            }}
            QPushButton#ConfigApplyBtn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6b8aff, stop:1 #4a6bef);
                border-color: #6b8aff;
                transform: translateY(-1px);
            }}
            QPushButton#ConfigApplyBtn:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {ac_dark}, stop:1 #2d4bc7);
                transform: translateY(0px);
            }}
            
            QPushButton#ConfigBrowseBtn {{
                background: #1a2140;
                border: 1px solid #242b46;
                border-radius: 8px;
                color: #d4d9ef;
                font: 600 12px {base_font};
                padding: 8px;
            }}
            QPushButton#ConfigBrowseBtn:hover {{
                background: #1e2548;
                border-color: {ac};
                color: #ffffff;
            }}
            QPushButton#ConfigBrowseBtn:pressed {{
                background: #0f1320;
            }}
            
            QLineEdit#ConfigEdit {{
                background: #0f1424;
                border: 1px solid #242b46;
                border-radius: 10px;
                padding: 8px 12px;
                color: #eef0ff;
                font: 500 14px {base_font};
            }}
            QLineEdit#ConfigEdit:hover {{
                border-color: #2e3652;
                background: #111628;
            }}
            QLineEdit#ConfigEdit:focus {{
                border-color: {ac};
                background: #121729;
            }}
        """)
        # Обновляем иконки сайдбара под новый акцент
        try:
            self._update_sidebar_icons(QtGui.QColor(ac))
        except Exception:
            pass

    def _update_sidebar_icons(self, accent_color: QtGui.QColor):
        # Векторные иконки для кнопок навигации
        if not hasattr(self, 'nav_buttons') or len(self.nav_buttons) < 5:
            return
        names = ["esp", "aim", "trigger", "misc", "about"]
        size = 18
        for btn, name in zip(self.nav_buttons, names):
            try:
                px = generate_icon_pixmap(name, size, accent_color)
                icon = QtGui.QIcon(px)
                btn.setIcon(icon)
                btn.setIconSize(QtCore.QSize(size, size))
            except Exception:
                continue

    def fade_in(self):
        # Use native window opacity animation to avoid nested QPainter from graphics effects
        self.setWindowOpacity(0.0)
        self._anim = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(220)
        self._anim.start()

    def create_sidebar(self):
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        # Отступ сверху
        layout.addSpacing(8)

        # Кнопки навигации
        self.nav_buttons = []

        def add_btn(title: str, index: int):
            btn = QtWidgets.QPushButton(title)
            btn.setObjectName("Nav")
            btn.setCheckable(True)
            btn.clicked.connect(lambda: self.select_nav(index))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        add_btn("ESP", 0)
        add_btn(self.t3("Aimbot", "Аимбот", "Еймбот"), 1)
        add_btn(self.t3("Trigger", "Триггер", "Тригер"), 2)
        add_btn(self.t3("Misc", "Другие функции", "Інше"), 3)
        add_btn(self.t3("About", "О программе", "Про програму"), 4)

        layout.addStretch(1)

        return sidebar

    def select_nav(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)

    def create_esp_page(self) -> QtWidgets.QWidget:
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

        header = QtWidgets.QLabel(self.t3("Globals • ESP", "Глобальные • ESP", "Глобальні • ESP"))
        header.setObjectName("Header")
        content_layout.addWidget(header)

        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setSpacing(18)
        inner_layout.addWidget(self.create_esp_card())
        inner_layout.addStretch(1)
        scroll.setWidget(inner)

        content_layout.addWidget(scroll)
        return content

    def create_misc_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page_layout = QtWidgets.QVBoxLayout(page)
        page_layout.setContentsMargins(24, 20, 24, 20)
        page_layout.setSpacing(16)
        header = QtWidgets.QLabel(self.t3("Miscellaneous", "Другие функции", "Інші налаштування"))
        header.setObjectName("Header")
        page_layout.addWidget(header)

        # Обёртка со скроллом для всего содержимого страницы
        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(18)

        # Карточка глобальных опций
        card, card_layout = self.create_card(self.t3("Global options", "Глобальные опции", "Глобальні опції"))
        grid = QtWidgets.QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(20)

        self.show_fps_cb = ToggleSwitch("")
        self.show_fps_cb.setChecked(self.settings.get("show_fps", 1) == 1)
        self.show_fps_cb.toggled.connect(self.save_settings)
        self._add_row(grid, 0, self.t3("Show overlay FPS", "Показывать FPS оверлея", "Показувати FPS оверлею"), self.show_fps_cb)

        self.overlay_fps_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.overlay_fps_slider.setRange(40, 300)
        self.overlay_fps_slider.setValue(int(self.settings.get("overlay_fps_limit", 144)))
        self.overlay_fps_slider.sliderReleased.connect(self.save_settings)
        self.overlay_fps_slider.valueChanged.connect(lambda _: self.overlay_fps_value_lbl.setText(str(self.overlay_fps_slider.value())))
        self.overlay_fps_value_lbl = QtWidgets.QLabel(str(self.overlay_fps_slider.value()))
        ofps_container = QtWidgets.QWidget()
        ofps_layout = QtWidgets.QVBoxLayout(ofps_container)
        ofps_layout.setContentsMargins(0, 0, 0, 0)
        ofps_layout.setSpacing(6)
        ofps_layout.addWidget(self.overlay_fps_slider)
        ofps_layout.addWidget(self.overlay_fps_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 1, self.t3("Overlay FPS limit", "Лимит FPS оверлея", "Ліміт FPS оверлею"), ofps_container)

        self.hotkey_key_edit = HotkeyEdit(self.settings.get("toggle_hotkey_key", "F6"))
        self.hotkey_key_edit.editingFinished.connect(self.save_settings)
        self._add_row(grid, 2, self.t3("Panel hotkey (e.g., F6)", "Горячая клавиша панели (например, F6)", "Гаряча клавіша панелі (наприклад, F6)"), self.hotkey_key_edit)

        card_layout.addLayout(grid)
        inner_layout.addWidget(card)

        # Карточка темы
        theme_card, theme_layout = self.create_card(self.t3("Interface theme", "Тема интерфейса", "Тема інтерфейсу"))
        theme_row = QtWidgets.QHBoxLayout()
        theme_row.setSpacing(8)
        self.accent_combo = QtWidgets.QComboBox()
        self.accent_combo.clear()
        self.accent_combo.addItems(self.tl3(
            ["Blue", "Red", "Green", "Yellow", "Purple"],
            ["Синий", "Красный", "Зелёный", "Жёлтый", "Фиолетовый"],
            ["Синій", "Червоний", "Зелений", "Жовтий", "Фіолетовий"]
        ))
        self.accent_combo.setCurrentIndex(int(self.settings.get("accent", 0)))
        self.accent_combo.currentIndexChanged.connect(self._change_accent)
        theme_row.addWidget(QtWidgets.QLabel(self.t3("Accent color:", "Акцентный цвет:", "Акцентний колір:")))
        theme_row.addWidget(self.accent_combo, 1)
        theme_layout.addLayout(theme_row)
        inner_layout.addWidget(theme_card)

        # Карточка конфигов настроек
        cfg_card, cfg_layout = self.create_card(self.t3("Settings profiles", "Конфиги настроек", "Профілі налаштувань"))
        cfg_grid = QtWidgets.QGridLayout()
        cfg_grid.setVerticalSpacing(12)
        cfg_grid.setHorizontalSpacing(20)

        # 1) Создать конфиг
        create_container = QtWidgets.QWidget()
        cc_layout = QtWidgets.QHBoxLayout(create_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(8)
        self.cfg_name_edit = QtWidgets.QLineEdit()
        self.cfg_name_edit.setObjectName("ConfigEdit")
        self.cfg_name_edit.setPlaceholderText(self.t3("Profile name (without extension)", "Имя конфига (без расширения)", "Назва профілю (без розширення)"))
        save_btn = QtWidgets.QPushButton(self.t3("Create profile", "Создать конфиг", "Створити профіль"))
        save_btn.setObjectName("ConfigBtn")
        save_btn.clicked.connect(self._on_save_config)
        cc_layout.addWidget(self.cfg_name_edit, 1)
        cc_layout.addWidget(save_btn)
        self._add_row(cfg_grid, 0, self.t3("Create profile", "Создать конфиг", "Створити профіль"), create_container)

        # 2) Открыть папку конфигов
        open_dir_btn = QtWidgets.QPushButton(self.t3("Open profiles folder", "Открыть папку конфигов", "Відкрити теку профілів"))
        open_dir_btn.setObjectName("ConfigBtn")
        open_dir_btn.clicked.connect(self._on_open_configs_dir)
        self._add_row(cfg_grid, 1, self.t3("Folder", "Папка", "Тека"), open_dir_btn)

        # 3) Применить конфиг из файла
        manual_container = QtWidgets.QWidget()
        man_layout = QtWidgets.QHBoxLayout(manual_container)
        man_layout.setContentsMargins(0, 0, 0, 0)
        man_layout.setSpacing(8)
        self.apply_path_edit = QtWidgets.QLineEdit()
        self.apply_path_edit.setObjectName("ConfigEdit")
        self.apply_path_edit.setPlaceholderText(self.t3("Path to .json profile", "Путь к .json конфигу", ".json шлях до профілю"))
        browse_btn = QtWidgets.QPushButton("...")
        browse_btn.setObjectName("ConfigBrowseBtn")
        browse_btn.setFixedWidth(34)
        browse_btn.clicked.connect(self._on_browse_config)
        apply_btn = QtWidgets.QPushButton(self.t3("Apply", "Применить", "Застосувати"))
        apply_btn.setObjectName("ConfigApplyBtn")
        apply_btn.clicked.connect(self._on_apply_config)
        man_layout.addWidget(self.apply_path_edit, 1)
        man_layout.addWidget(browse_btn)
        man_layout.addWidget(apply_btn)
        self._add_row(cfg_grid, 2, self.t3("Apply from file", "Применить из файла", "Застосувати з файлу"), manual_container)

        cfg_layout.addLayout(cfg_grid)
        inner_layout.addWidget(cfg_card)

        # Автономный режим: секция активации удалена

        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        page_layout.addWidget(scroll)
        return page

    def create_in_progress_page(self, title: str) -> QtWidgets.QWidget:
        # Удалено: больше не используется
        return QtWidgets.QWidget()

    def create_pricing_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QtWidgets.QLabel(self.t3("Pricing and subscription", "Прайс-лист и покупка подписки", "Тарифи та підписка"))
        header.setObjectName("Header")
        layout.addWidget(header)

        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)

        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setSpacing(18)

        # Автономный режим: предупреждения о подписке удалены

        # Тарифы / Plans
        plans_card, plans_layout = self.create_card(self.t("BLACKSCOPE plans (USD)", "Тарифы BLACKSCOPE (USD)"))
        plans_grid = QtWidgets.QGridLayout()
        plans_grid.setVerticalSpacing(12)
        plans_grid.setHorizontalSpacing(16)

        def plan_row(row_index: int, title: str, usd_price: float):
            title_lbl = QtWidgets.QLabel(title)
            price_lbl = QtWidgets.QLabel(f"${usd_price:.2f}")
            price_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            buy_btn = QtWidgets.QPushButton(self.t("Buy from @aunex", "Купить у @aunex"))
            buy_btn.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://t.me/aunex")))
            row_box = QtWidgets.QHBoxLayout()
            row_box.setContentsMargins(0, 0, 0, 0)
            row_box.setSpacing(8)
            row_box.addWidget(price_lbl, 1)
            row_box.addWidget(buy_btn)
            plans_grid.addWidget(title_lbl, row_index, 0, alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            plans_grid.addLayout(row_box, row_index, 1)

        plan_row(0, self.t("15 days access", "15 дней доступа"), 1.10)
        plan_row(1, self.t("30 days (1 month)", "30 дней (месяц)"), 2.00)
        plan_row(2, self.t("90 days (3 months)", "90 дней (3 месяца)"), 5.50)
        plan_row(3, self.t("365 days (1 year)", "365 дней (год)"), 18.90)

        plans_layout.addLayout(plans_grid)
        inner_layout.addWidget(plans_card)

        # Что включено / What's included
        incl_card, incl_layout = self.create_card(self.t("What's included", "Что входит в подписку"))
        incl_html = self.t(
            "<ul>"
            "<li>Full access to Aimbot and Trigger sections</li>"
            "<li>Access to ESP (overlay)</li>"
            "<li>Advanced ESP settings (boxes, fill, gradients, hitmarker)</li>"
            "<li>Updates during the paid period</li>"
            "</ul>",
            "<ul>"
            "<li>Полный доступ к разделам Aimbot и Trigger</li>"
            "<li>Доступ к ESP (оверлей)</li>"
            "<li>Расширенные настройки ESP (боксы, заливка, градиенты, hitmarker)</li>"
            "<li>Обновления в течение оплаченного срока</li>"
            "</ul>"
        )
        incl_lbl = QtWidgets.QLabel(incl_html)
        incl_lbl.setTextFormat(QtCore.Qt.RichText)
        incl_lbl.setWordWrap(True)
        incl_layout.addWidget(incl_lbl)
        inner_layout.addWidget(incl_card)

        # Как купить / How to buy
        contact_card, contact_layout = self.create_card(self.t("How to buy", "Как купить"))
        contact_html = self.t(
            'To purchase a key, message the admin: '
            '<a href="https://t.me/aunex" target="_blank">@aunex</a><br/>'
            'Payments in USD. Bank cards from various regions may be accepted (online payment).<br/>'
            'Specify the desired plan. The key is bound to your IP on activation.',
            'Для покупки ключа напишите администратору: '
            '<a href="https://t.me/aunex" target="_blank">@aunex</a><br/>'
            'Оплата в долларах США. Принимаются карты России, Украины, Казахстана, Беларуси '
            'и других постсоветских стран (онлайн-платёж).<br/>'
            'Укажите желаемый тариф. Ключ привязывается к вашему IP при активации.'
        )
        contact_text = QtWidgets.QLabel(contact_html)
        contact_text.setTextFormat(QtCore.Qt.RichText)
        contact_text.setOpenExternalLinks(True)
        contact_text.setWordWrap(True)
        contact_layout.addWidget(contact_text)

        # Кнопки действий
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(8)
        copy_btn = QtWidgets.QPushButton(self.t("Copy @aunex", "Скопировать @aunex"))
        copy_btn.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText("@aunex"))
        open_btn = QtWidgets.QPushButton(self.t("Open Telegram chat", "Открыть чат в Telegram"))
        open_btn.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://t.me/aunex")))
        actions_row.addStretch(1)
        actions_row.addWidget(copy_btn)
        actions_row.addWidget(open_btn)
        contact_layout.addLayout(actions_row)
        inner_layout.addWidget(contact_card)

        # Правила/примечания / Notes
        rules_card, rules_layout = self.create_card(self.t("Important notes", "Важно знать"))
        rules_html = self.t(
            "<ul>"
            "<li>Subscription is activated when you enter the key and is bound to your IP.</li>"
            "<li>Access time is counted from the moment of activation.</li>"
            "<li>When the term ends, Aimbot/Trigger and advanced ESP options are disabled automatically.</li>"
            "</ul>",
            "<ul>"
            "<li>Подписка активируется при вводе ключа и привязывается к вашему IP.</li>"
            "<li>Срок доступа отсчитывается с момента активации ключа.</li>"
            "<li>При окончании срока Aimbot/Trigger и расширенные опции ESP автоматически отключаются.</li>"
            "</ul>"
        )
        rules_lbl = QtWidgets.QLabel(rules_html)
        rules_lbl.setTextFormat(QtCore.Qt.RichText)
        rules_lbl.setWordWrap(True)
        rules_layout.addWidget(rules_lbl)
        inner_layout.addWidget(rules_card)

        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return page

    def create_aim_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        header = QtWidgets.QLabel(self.t3("Aimbot", "Аимбот", "Еймбот"))
        header.setObjectName("Header")
        layout.addWidget(header)

        # Прокрутка как во вкладке ESP
        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setSpacing(18)

        # Автономный режим: предупреждение о подписке удалено

        card, card_layout = self.create_card(self.t3("Aimbot parameters", "Параметры Aimbot", "Параметри Aimbot"))
        grid = QtWidgets.QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(20)

        self.aim_enabled_cb = ToggleSwitch("")
        self.aim_enabled_cb.setChecked(int(self.settings.get("aim_enabled", 0)) == 1)
        self.aim_enabled_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 0, self.t3("Enable Aimbot", "Включить Aimbot", "Увімкнути Aimbot"), self.aim_enabled_cb)

        self.aim_hold_key = QtWidgets.QComboBox()
        self.aim_hold_key.addItems(["RMB", "LMB", "ALT", "SHIFT", "CTRL", "MOUSE4", "MOUSE5"])
        idx = max(0, self.aim_hold_key.findText(self.settings.get("aim_hold_key", "RMB")))
        self.aim_hold_key.setCurrentIndex(idx)
        self.aim_hold_key.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 1, self.t3("Hold key", "Клавиша удержания", "Клавіша утримання"), self.aim_hold_key)

        self.aim_fov_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.aim_fov_slider.setRange(10, 300)
        self.aim_fov_slider.setValue(int(self.settings.get("aim_fov", 80)))
        self.aim_fov_slider.sliderReleased.connect(self._save_settings_flush)
        self.aim_fov_slider.valueChanged.connect(lambda _: self.aim_fov_value_lbl.setText(str(self.aim_fov_slider.value())))
        self.aim_fov_value_lbl = QtWidgets.QLabel(str(self.aim_fov_slider.value()))
        aim_fov_container = QtWidgets.QWidget()
        af_layout = QtWidgets.QVBoxLayout(aim_fov_container)
        af_layout.setContentsMargins(0, 0, 0, 0)
        af_layout.setSpacing(6)
        af_layout.addWidget(self.aim_fov_slider)
        af_layout.addWidget(self.aim_fov_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 2, self.t3("FOV (radius, px)", "FOV (радиус, px)", "FOV (радіус, px)"), aim_fov_container)

        # Обычное сглаживание убрано — ряды уплотняем без пустых мест

        # Сглаживание цели (борьба с тряской)
        self.aim_target_smooth_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.aim_target_smooth_slider.setRange(0, 90)
        self.aim_target_smooth_slider.setValue(int(self.settings.get("aim_target_smooth_pct", 35)))
        self.aim_target_smooth_slider.sliderReleased.connect(self._save_settings_flush)
        self.aim_target_smooth_slider.valueChanged.connect(lambda _: self.aim_target_smooth_value_lbl.setText(str(self.aim_target_smooth_slider.value())))
        self.aim_target_smooth_value_lbl = QtWidgets.QLabel(str(self.aim_target_smooth_slider.value()))
        aim_tsm_container = QtWidgets.QWidget()
        tsm_layout = QtWidgets.QVBoxLayout(aim_tsm_container)
        tsm_layout.setContentsMargins(0, 0, 0, 0)
        tsm_layout.setSpacing(6)
        tsm_layout.addWidget(self.aim_target_smooth_slider)
        tsm_layout.addWidget(self.aim_target_smooth_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 3, self.t3("Target smoothing (%, lower = smoother)", "Сглаживание цели (%, меньше — плавнее)", "Згладжування цілі (%, менше — плавніше)"), aim_tsm_container)

        # Сглаживание при зажатой ЛКМ (компенсация отдачи)
        self.aim_fire_smooth_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.aim_fire_smooth_slider.setRange(0, 95)
        self.aim_fire_smooth_slider.setValue(int(self.settings.get("aim_fire_smooth_pct", 20)))
        self.aim_fire_smooth_slider.sliderReleased.connect(self._save_settings_flush)
        self.aim_fire_smooth_slider.valueChanged.connect(lambda _: self.aim_fire_smooth_value_lbl.setText(str(self.aim_fire_smooth_slider.value())))
        self.aim_fire_smooth_value_lbl = QtWidgets.QLabel(str(self.aim_fire_smooth_slider.value()))
        aim_fsm_container = QtWidgets.QWidget()
        fsm_layout = QtWidgets.QVBoxLayout(aim_fsm_container)
        fsm_layout.setContentsMargins(0, 0, 0, 0)
        fsm_layout.setSpacing(6)
        fsm_layout.addWidget(self.aim_fire_smooth_slider)
        fsm_layout.addWidget(self.aim_fire_smooth_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 4, self.t3("Fire smoothing (%, higher = flatter)", "Сглаживание при стрельбе (%, сильнее — ровнее)", "Згладжування під час стрільби (%, вище — рівніше)"), aim_fsm_container)

        self.aim_bone_cb = QtWidgets.QComboBox()
        self.aim_bone_cb.addItems(self.tl3(["Head", "Chest"], ["Голова", "Грудь"], ["Голова", "Груди"])) 
        self.aim_bone_cb.setCurrentIndex(int(self.settings.get("aim_bone", 0)))
        self.aim_bone_cb.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 5, self.t3("Target bone", "Приоритет кости", "Пріоритет кістки"), self.aim_bone_cb)

        self.aim_team_cb = QtWidgets.QComboBox()
        self.aim_team_cb.addItems(self.tl3(["Enemies only", "All players"], ["Только враги", "Все игроки"], ["Лише вороги", "Всі гравці"])) 
        self.aim_team_cb.setCurrentIndex(int(self.settings.get("aim_team", 0)))
        self.aim_team_cb.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 6, self.t3("Targets", "Цели", "Цілі"), self.aim_team_cb)

        self.aim_humanize_cb = ToggleSwitch("")
        self.aim_humanize_cb.setChecked(int(self.settings.get("aim_humanize", 1)) == 1)
        self.aim_humanize_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 7, self.t3("Humanize aiming", "Humanize наведения", "Людиноподібне наведення"), self.aim_humanize_cb)

        self.aim_react_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.aim_react_slider.setRange(0, 300)
        self.aim_react_slider.setValue(int(self.settings.get("aim_reaction_ms", 90)))
        self.aim_react_slider.sliderReleased.connect(self._save_settings_flush)
        self.aim_react_slider.valueChanged.connect(lambda _: self.aim_react_value_lbl.setText(str(self.aim_react_slider.value())))
        self.aim_react_value_lbl = QtWidgets.QLabel(str(self.aim_react_slider.value()))
        aim_react_container = QtWidgets.QWidget()
        ar_layout = QtWidgets.QVBoxLayout(aim_react_container)
        ar_layout.setContentsMargins(0, 0, 0, 0)
        ar_layout.setSpacing(6)
        ar_layout.addWidget(self.aim_react_slider)
        ar_layout.addWidget(self.aim_react_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 8, self.t3("Reaction (ms)", "Реакция (мс)", "Реакція (мс)"), aim_react_container)

        self.aim_pause_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.aim_pause_slider.setRange(0, 50)
        self.aim_pause_slider.setValue(int(self.settings.get("aim_pause_ms", 12)))
        self.aim_pause_slider.sliderReleased.connect(self._save_settings_flush)
        self.aim_pause_slider.valueChanged.connect(lambda _: self.aim_pause_value_lbl.setText(str(self.aim_pause_slider.value())))
        self.aim_pause_value_lbl = QtWidgets.QLabel(str(self.aim_pause_slider.value()))
        aim_pause_container = QtWidgets.QWidget()
        ap_layout = QtWidgets.QVBoxLayout(aim_pause_container)
        ap_layout.setContentsMargins(0, 0, 0, 0)
        ap_layout.setSpacing(6)
        ap_layout.addWidget(self.aim_pause_slider)
        ap_layout.addWidget(self.aim_pause_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 9, self.t3("Micro‑pause (ms)", "Микропаузa (мс)", "Мікропаузa (мс)"), aim_pause_container)

        # Опция «не целиться через стены» удалена — без лишних пустых рядов

        card_layout.addLayout(grid)
        # Добавляем карточку в контейнер прокрутки
        inner_layout.addWidget(card)
        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return page

    def create_trigger_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        header = QtWidgets.QLabel(self.t3("Trigger Bot", "Триггер-бот", "Тригер-бот"))
        header.setObjectName("Header")
        layout.addWidget(header)

        # Прокрутка
        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setSpacing(18)

        card, card_layout = self.create_card(self.t3("Trigger parameters", "Параметры Trigger Bot", "Параметри Trigger Bot"))
        grid = QtWidgets.QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(20)

        # Автономный режим: предупреждение о подписке удалено

        self.trigger_enabled_cb = ToggleSwitch("")
        self.trigger_enabled_cb.setChecked(int(self.settings.get("trigger_enabled", 0)) == 1)
        self.trigger_enabled_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 0, self.t3("Enable Trigger", "Включить Trigger", "Увімкнути Trigger"), self.trigger_enabled_cb)

        self.trigger_hold_key = QtWidgets.QComboBox()
        self.trigger_hold_key.addItems(["Always", "RMB", "LMB", "ALT", "SHIFT", "CTRL", "MOUSE4", "MOUSE5"])
        idx = max(0, self.trigger_hold_key.findText(self.settings.get("trigger_hold_key", "ALT")))
        self.trigger_hold_key.setCurrentIndex(idx)
        self.trigger_hold_key.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 1, self.t3("Activation mode", "Режим активации", "Режим активації"), self.trigger_hold_key)

        self.trigger_radius_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.trigger_radius_slider.setRange(2, 40)
        self.trigger_radius_slider.setValue(int(self.settings.get("trigger_radius", 10)))
        self.trigger_radius_slider.sliderReleased.connect(self._save_settings_flush)
        self.trigger_radius_slider.valueChanged.connect(lambda _: self.trigger_radius_value_lbl.setText(str(self.trigger_radius_slider.value())))
        self.trigger_radius_value_lbl = QtWidgets.QLabel(str(self.trigger_radius_slider.value()))
        tr_r_container = QtWidgets.QWidget()
        trr_layout = QtWidgets.QVBoxLayout(tr_r_container)
        trr_layout.setContentsMargins(0, 0, 0, 0)
        trr_layout.setSpacing(6)
        trr_layout.addWidget(self.trigger_radius_slider)
        trr_layout.addWidget(self.trigger_radius_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 2, self.t3("Radius (px)", "Радиус (px)", "Радіус (px)"), tr_r_container)

        self.trigger_delay_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.trigger_delay_slider.setRange(0, 200)
        self.trigger_delay_slider.setValue(int(self.settings.get("trigger_delay_ms", 30)))
        self.trigger_delay_slider.sliderReleased.connect(self._save_settings_flush)
        self.trigger_delay_slider.valueChanged.connect(lambda _: self.trigger_delay_value_lbl.setText(str(self.trigger_delay_slider.value())))
        self.trigger_delay_value_lbl = QtWidgets.QLabel(str(self.trigger_delay_slider.value()))
        tr_d_container = QtWidgets.QWidget()
        trd_layout = QtWidgets.QVBoxLayout(tr_d_container)
        trd_layout.setContentsMargins(0, 0, 0, 0)
        trd_layout.setSpacing(6)
        trd_layout.addWidget(self.trigger_delay_slider)
        trd_layout.addWidget(self.trigger_delay_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 3, self.t3("Delay (ms)", "Задержка (мс)", "Затримка (мс)"), tr_d_container)

        card_layout.addLayout(grid)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def create_about_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        header = QtWidgets.QLabel(self.t3("About", "О программе", "Про програму"))
        header.setObjectName("Header")
        layout.addWidget(header)

        card, card_layout = self.create_card(self.t3("BLACKSCOPE • guide & safety • author @aunex", "BLACKSCOPE • руководство и безопасность • разработчик @aunex", "BLACKSCOPE • керівництво та безпека • розробник @aunex"))
        about = QtWidgets.QLabel()
        about.setObjectName("AboutText")
        about.setWordWrap(True)
        about.setTextFormat(QtCore.Qt.RichText)
        about.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        about.setOpenExternalLinks(True)
        about.setText(self.t3(
            """
            <h3>Overview</h3>
            <p>BLACKSCOPE is a configurable ESP/assist overlay for CS2. It is for educational purposes only. You assume all risks when using it.</p>

            <h3>Display compatibility</h3>
            <ul>
              <li><b>Window mode</b>: Run the game in <b>Windowed</b> or <b>Borderless Windowed</b>. Exclusive fullscreen will not render the overlay.</li>
              <li><b>Resolution</b>: Avoid changing resolution while running—the overlay may flicker briefly.</li>
            </ul>

            <h3>"Legit" play recommendations</h3>
            <ul>
              <li><b>ESP</b>: keep boxes/line/HP only; avoid skeleton/neon outline in ranked modes.</li>
              <li><b>Aimbot</b>:
                <ul>
                  <li>Smoothing 6–12, FOV 50–90, target <b>Chest</b> looks more natural.</li>
                  <li>Disable instant snap and keep reaction 60–120 ms.</li>
                  <li>Use hold on RMB/ALT, not auto‑lock.</li>
                </ul>
              </li>
              <li><b>Trigger</b>: radius ≤ 10, delay 20–60 ms, hold mode.</li>
              <li><b>General</b>: vary your playstyle, don't track enemies through walls with camera, avoid robotic micro‑movements.</li>
            </ul>

            <h3>What not to enable</h3>
            <ul>
              <li>Instant snap with high FOV—it's obvious.</li>
              <li>Too bright/thick boxes and skeletons (especially on streams/demos).</li>
              <li>Any smoothing below 3 and 0 ms delays.</li>
            </ul>

            <h3>Useful settings</h3>
            <ul>
              <li><b>Overlay FPS cap</b>—match your monitor (e.g., 144) to reduce load.</li>
              <li><b>Panel hotkey</b>—quick access to settings above the game.</li>
              <li><b>Configs</b>—save/share presets and apply quickly.</li>
            </ul>

            <h3>Technical notes</h3>
            <ul>
              <li>If the game isn't found—start CS2 and relaunch the overlay from the panel.</li>
              <li>If FPS drops, disable extra ESP elements, lower the overlay FPS cap.</li>
              <li>If the game window loses focus, rendering may pause until focus returns.</li>
            </ul>

            <h3>Important</h3>
            <p><b>Anti‑cheat resistance does not equal invisibility.</b> Use wisely and at your own risk. The author/community are not responsible for bans or consequences.</p>

            <p class="muted">Contact/feedback: author Telegram — <a href="https://t.me/aunex" target="_blank">@aunex</a>.</p>
            """,
            """
            <h3>Общие сведения</h3>
            <p>BLACKSCOPE — настраиваемый ESP/Assist‑оверлей для CS2. Проект создан для ознакомительных целей. Используя программу, вы берёте на себя все риски.</p>

            <h3>Совместимость экрана</h3>
            <ul>
              <li><b>Режим окна</b>: Игра должна быть запущена в режиме «<b>Оконный</b>» или «<b>Полноэкранный в окне</b>». В «эксклюзивном фуллскрине» оверлей не отрисуется.</li>
              <li><b>Разрешение</b>: Старайтесь не менять разрешение во время работы — при смене размера окна оверлей может кратко мигать.</li>
            </ul>

            <h3>Рекомендации по «легитной» игре</h3>
            <ul>
              <li><b>ESP</b>: оставьте только боксы/линию/HP, не включайте «скелеты» и неоновую обводку в соревновательных режимах.</li>
              <li><b>Aimbot</b>:
                <ul>
                  <li>Сглаживание 6–12, FOV 50–90, приоритет «Грудь» — выглядит естественнее.</li>
                  <li>Отключите моментальный «snap» и держите реакцию 60–120 мс.</li>
                  <li>Используйте удержание на RMB/ALT, а не автопривязку.</li>
                </ul>
              </li>
              <li><b>Trigger</b>: радиус ≤ 10, задержка 20–60 мс, режим «по удержанию».</li>
              <li><b>Общее</b>: периодически меняйте стиль игры, не отслеживайте врагов через стены взглядом, избегайте «роботных» микродвижений.</li>
            </ul>

            <h3>Что лучше не включать</h3>
            <ul>
              <li>Мгновенный снэп (snap) на высоких FOV — выглядит очевидно.</li>
              <li>Слишком яркие/толстые боксы и «скелет» (особенно на трансляциях/демках).</li>
              <li>Любые значения сглаживания ниже 3 и задержек 0 мс.</li>
            </ul>

            <h3>Полезные настройки</h3>
            <ul>
              <li><b>Ограничение FPS оверлея</b> — ставьте около вашего монитора (например, 144), чтобы снизить нагрузку.</li>
              <li><b>Горячая клавиша панели</b> — быстрый доступ к настройкам поверх игры.</li>
              <li><b>Конфиги</b> — можно сохранить свой пресет и быстро применять/делиться.</li>
            </ul>

            <h3>Технические замечания</h3>
            <ul>
              <li>Если игра не найдена — запустите CS2 и перезапустите оверлей из панели.</li>
              <li>При резких падениях FPS отключите лишние элементы ESP, понизьте FPS‑лимит оверлея.</li>
              <li>Если окно игры теряет фокус, отрисовка может приостанавливаться до возврата фокуса.</li>
            </ul>

            <h3>Важное</h3>
            <p><b>Наличие защиты от античита не означает невидимость.</b> Используйте с умом и на свой риск. Автор и сообщество не несут ответственности за блокировки и последствия.</p>

            <p class="muted">Контакты/обратная связь: Telegram автора — <a href="https://t.me/aunex" target="_blank">@aunex</a>.</p>
            """,
            """
            <h3>Загальні відомості</h3>
            <p>BLACKSCOPE — налаштовуваний ESP/Assist‑оверлей для CS2. Проект створено для ознайомчих цілей. Використовуючи програму, ви берете на себе всі ризики.</p>

            <h3>Сумісність екрану</h3>
            <ul>
              <li><b>Режим вікна</b>: Гра повинна бути запущена в режимі «<b>Віконний</b>» або «<b>Повноекранний у вікні</b>». В «ексклюзивному фулскріні» оверлей не відображатиметься.</li>
              <li><b>Роздільна здатність</b>: Намагайтеся не змінювати роздільну здатність під час роботи — при зміні розміру вікна оверлей може коротко блимати.</li>
            </ul>

            <h3>Рекомендації з «легітної» гри</h3>
            <ul>
              <li><b>ESP</b>: залиште тільки бокси/лінію/HP, не вмикайте «скелети» та неонову обводку в змагальних режимах.</li>
              <li><b>Aimbot</b>:
                <ul>
                  <li>Згладжування 6–12, FOV 50–90, пріоритет «Груди» — виглядає природніше.</li>
                  <li>Відключіть миттєвий «snap» та тримайте реакцію 60–120 мс.</li>
                  <li>Використовуйте утримання на RMB/ALT, а не автоприв'язку.</li>
                </ul>
              </li>
              <li><b>Trigger</b>: радіус ≤ 10, затримка 20–60 мс, режим «по утриманню».</li>
              <li><b>Загальне</b>: періодично змінюйте стиль гри, не відстежуйте ворогів через стіни поглядом, уникайте «роботних» мікрорухів.</li>
            </ul>

            <h3>Що краще не вмикати</h3>
            <ul>
              <li>Миттєвий снеп (snap) на високих FOV — виглядає очевидно.</li>
              <li>Занадто яскраві/товсті бокси та «скелет» (особливо на трансляціях/демках).</li>
              <li>Будь-які значення згладжування нижче 3 та затримок 0 мс.</li>
            </ul>

            <h3>Корисні налаштування</h3>
            <ul>
              <li><b>Обмеження FPS оверлею</b> — ставте близько вашого монітора (наприклад, 144), щоб знизити навантаження.</li>
              <li><b>Гаряча клавіша панелі</b> — швидкий доступ до налаштувань поверх гри.</li>
              <li><b>Конфіги</b> — можна зберегти свій пресет та швидко застосовувати/ділитися.</li>
            </ul>

            <h3>Технічні зауваження</h3>
            <ul>
              <li>Якщо гра не знайдена — запустіть CS2 та перезапустіть оверлей з панелі.</li>
              <li>При різких падіннях FPS відключіть зайві елементи ESP, знизьте FPS‑ліміт оверлею.</li>
              <li>Якщо вікно гри втрачає фокус, відрисовка може призупинятися до повернення фокусу.</li>
            </ul>

            <h3>Важливе</h3>
            <p><b>Наявність захисту від античіту не означає невидимість.</b> Використовуйте з розумом та на свій ризик. Автор та спільнота не несуть відповідальності за блокування та наслідки.</p>

            <p class="muted">Контакти/зворотний зв'язок: Telegram автора — <a href="https://t.me/aunex" target="_blank">@aunex</a>.</p>
            """
        ))
        card_layout.addWidget(about)

        # Оборачиваем карточку скроллом, как на других страницах
        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(18)
        inner_layout.addWidget(card)
        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return page

    def create_card(self, title: str):
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        
        # Добавляем эффект тени для карточки
        shadow = QtWidgets.QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QtGui.QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)
        
    def create_card(self, title: str):
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(16)
        
        # Заголовок с иконкой
        header_row = QtWidgets.QHBoxLayout()
        header_row.setSpacing(8)
        
        # Получаем акцентный цвет
        accent_idx = int(self.settings.get("accent", 0))
        accents = [
            ("#5a78ff", "#3f5bdb"),  # blue
            ("#ff6b6b", "#d84e4e"),  # red
            ("#36d399", "#21b07f"),  # green
            ("#f3c969", "#d7a93a"),  # yellow
            ("#b072ff", "#8c52e6"),  # purple
        ]
        ac, _ = accents[accent_idx % len(accents)]
        
        # Иконка заголовка с акцентным цветом
        header_icon = QtWidgets.QLabel("●")
        header_icon.setStyleSheet(f"color: {ac}; font: 700 14px 'Segoe UI';")
        
        # Заголовок карточки
        header = QtWidgets.QLabel(title)
        header.setStyleSheet("font: 700 14px 'Segoe UI'; color: #ffffff;")
        
        header_row.addStretch(1)
        header_row.addWidget(header_icon)
        header_row.addWidget(header)
        header_row.addStretch(1)
        
        card_layout.addLayout(header_row)
        return card, card_layout

    def _add_row(self, grid: QtWidgets.QGridLayout, row: int, label_text: str, widget: QtWidgets.QWidget):
        label = QtWidgets.QLabel(label_text)
        label.setObjectName("rowLabel")
        label.setMinimumWidth(160)
        grid.addWidget(label, row, 0, alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        grid.addWidget(widget, row, 1, alignment=QtCore.Qt.AlignRight)

    def create_esp_card(self):
        card, layout = self.create_card(self.t3("ESP settings", "Настройки ESP", "Налаштування ESP"))
        grid = QtWidgets.QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(20)

        self.esp_rendering_cb = ToggleSwitch("")
        self.esp_rendering_cb.setChecked(self.settings["esp_rendering"] == 1)
        self.esp_rendering_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 0, self.t3("Enable ESP", "Включить ESP", "Увімкнути ESP"), self.esp_rendering_cb)

        self.esp_mode_cb = QtWidgets.QComboBox()
        self.esp_mode_cb.addItems(self.tl3(["Enemies only", "All players"], ["Только враги", "Все игроки"], ["Лише вороги", "Всі гравці"]))
        self.esp_mode_cb.setCurrentIndex(self.settings["esp_mode"])
        self.esp_mode_cb.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 1, self.t3("ESP mode", "Режим ESP", "Режим ESP"), self.esp_mode_cb)

        self.line_rendering_cb = ToggleSwitch("")
        self.line_rendering_cb.setChecked(self.settings["line_rendering"] == 1)
        self.line_rendering_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 2, self.t3("Draw lines", "Рисовать линии", "Малювати лінії"), self.line_rendering_cb)

        self.hp_bar_rendering_cb = ToggleSwitch("")
        self.hp_bar_rendering_cb.setChecked(self.settings["hp_bar_rendering"] == 1)
        self.hp_bar_rendering_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 3, self.t3("Show HP/Armor", "Показывать HP/Броню", "Показувати HP/Броню"), self.hp_bar_rendering_cb)

        # Градиент HP
        self.hp_bar_gradient_cb = ToggleSwitch("")
        self.hp_bar_gradient_cb.setChecked(int(self.settings.get("hp_bar_gradient", 1)) == 1)
        self.hp_bar_gradient_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 4, self.t3("HP bar gradient", "Градиентная полоса HP", "Градієнтна смуга HP"), self.hp_bar_gradient_cb)

        self.hp_bar_grad_style_cb = QtWidgets.QComboBox()
        self.hp_bar_grad_style_cb.addItems(self.tl3(["Red→Yellow", "Green→Lime", "Blue→Cyan"], ["Красный→Жёлтый", "Зелёный→Лайм", "Синий→Голубой"], ["Червоний→Жовтий", "Зелений→Лайм", "Синій→Бірюзовий"]))
        self.hp_bar_grad_style_cb.setCurrentIndex(int(self.settings.get("hp_bar_gradient_style", 0)))
        self.hp_bar_grad_style_cb.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 5, self.t3("HP gradient style", "Стиль градиента HP", "Стиль градієнта HP"), self.hp_bar_grad_style_cb)

        self.head_hitbox_rendering_cb = ToggleSwitch("")
        self.head_hitbox_rendering_cb.setChecked(self.settings["head_hitbox_rendering"] == 1)
        self.head_hitbox_rendering_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 6, self.t3("Head hitbox", "Хитбокс головы", "Хітбокс голови"), self.head_hitbox_rendering_cb)

        self.bons_cb = ToggleSwitch("")
        self.bons_cb.setChecked(self.settings["bons"] == 1)
        self.bons_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 7, self.t3("Show skeleton", "Показывать скелет", "Показувати скелет"), self.bons_cb)

        self.nickname_cb = ToggleSwitch("")
        self.nickname_cb.setChecked(self.settings["nickname"] == 1)
        self.nickname_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 8, self.t3("Show nickname", "Показывать никнейм", "Показувати нікнейм"), self.nickname_cb)

        self.weapon_cb = ToggleSwitch("")
        self.weapon_cb.setChecked(self.settings["weapon"] == 1)
        self.weapon_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 9, self.t3("Show weapon", "Показывать оружие", "Показувати зброю"), self.weapon_cb)

        self.bomb_esp_cb = ToggleSwitch("")
        self.bomb_esp_cb.setChecked(self.settings["bomb_esp"] == 1)
        self.bomb_esp_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 10, self.t("Bomb ESP", "ESP бомбы"), self.bomb_esp_cb)

        self.radius_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.radius_slider.setMinimum(0)
        self.radius_slider.setMaximum(100)
        self.radius_slider.setValue(self.settings.get("radius", 50))
        self.radius_slider.sliderReleased.connect(self._save_settings_flush)
        self.radius_slider.valueChanged.connect(lambda _: self.radius_value_lbl.setText(str(self.radius_slider.value())))
        self.radius_value_lbl = QtWidgets.QLabel(str(self.radius_slider.value()))
        radius_container = QtWidgets.QWidget()
        rc_layout = QtWidgets.QVBoxLayout(radius_container)
        rc_layout.setContentsMargins(0, 0, 0, 0)
        rc_layout.setSpacing(6)
        rc_layout.addWidget(self.radius_slider)
        rc_layout.addWidget(self.radius_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 11, self.t("Circle radius", "Радиус круга"), radius_container)

        # Neon outline
        self.neon_outline_cb = ToggleSwitch("")
        self.neon_outline_cb.setChecked(self.settings.get("neon_outline", 0) == 1)
        self.neon_outline_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 12, self.t("Neon outline", "Неоновая обводка"), self.neon_outline_cb)

        self.neon_color_cb = QtWidgets.QComboBox()
        self.neon_color_cb.addItems(self.tl3(["Blue", "Purple", "Yellow"], ["Синий", "Фиолетовый", "Жёлтый"], ["Синій", "Фіолетовий", "Жовтий"]))
        self.neon_color_cb.setCurrentIndex(self.settings.get("neon_outline_color", 0))
        self.neon_color_cb.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 13, self.t3("Outline color", "Цвет обводки", "Колір обводки"), self.neon_color_cb)

        # (удалено) опция видимости

        # Доп. настройки боксов: стиль/толщина/прозрачность/заливка
        self.box_style_cb = QtWidgets.QComboBox()
        self.box_style_cb.addItems(self.tl3(["Classic", "Corner", "Capsule"], ["Классический", "Угловой", "Капсула"], ["Класичний", "Кутовий", "Капсула"]))
        self.box_style_cb.setCurrentIndex(int(self.settings.get("box_style", 0)))
        self.box_style_cb.currentIndexChanged.connect(self._save_settings_flush)
        self._add_row(grid, 14, self.t3("Box style", "Стиль бокса", "Стиль боксу"), self.box_style_cb)

        # Толщина линий (слайдер + лейбл значения)
        self.box_thickness_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.box_thickness_slider.setRange(1, 6)
        self.box_thickness_slider.setValue(int(self.settings.get("box_thickness", 2)))
        self.box_thickness_slider.sliderReleased.connect(self._save_settings_flush)
        self.box_thickness_slider.valueChanged.connect(lambda _: self.box_thickness_value_lbl.setText(str(self.box_thickness_slider.value())))
        self.box_thickness_value_lbl = QtWidgets.QLabel(str(self.box_thickness_slider.value()))
        box_thickness_container = QtWidgets.QWidget()
        bts_layout = QtWidgets.QVBoxLayout(box_thickness_container)
        bts_layout.setContentsMargins(0, 0, 0, 0)
        bts_layout.setSpacing(6)
        bts_layout.addWidget(self.box_thickness_slider)
        bts_layout.addWidget(self.box_thickness_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 15, self.t3("Line thickness", "Толщина линий", "Товщина ліній"), box_thickness_container)

        # Прозрачность (слайдер + лейбл значения)
        self.box_opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.box_opacity_slider.setRange(50, 255)
        self.box_opacity_slider.setValue(int(self.settings.get("box_opacity", 220)))
        self.box_opacity_slider.sliderReleased.connect(self._save_settings_flush)
        self.box_opacity_slider.valueChanged.connect(lambda _: self.box_opacity_value_lbl.setText(str(self.box_opacity_slider.value())))
        self.box_opacity_value_lbl = QtWidgets.QLabel(str(self.box_opacity_slider.value()))
        box_opacity_container = QtWidgets.QWidget()
        bos_layout = QtWidgets.QVBoxLayout(box_opacity_container)
        bos_layout.setContentsMargins(0, 0, 0, 0)
        bos_layout.setSpacing(6)
        bos_layout.addWidget(self.box_opacity_slider)
        bos_layout.addWidget(self.box_opacity_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 16, self.t3("Opacity (alpha)", "Прозрачность (альфа)", "Прозорість (альфа)"), box_opacity_container)

        self.box_fill_cb = ToggleSwitch("")
        self.box_fill_cb.setChecked(int(self.settings.get("box_fill", 0)) == 1)
        self.box_fill_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 17, self.t3("Box fill", "Заливка бокса", "Заливка боксу"), self.box_fill_cb)

        # Прозрачность заливки (%)
        self.box_fill_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.box_fill_alpha_slider.setRange(0, 100)
        self.box_fill_alpha_slider.setValue(int(self.settings.get("box_fill_alpha_pct", 25)))
        self.box_fill_alpha_slider.sliderReleased.connect(self._save_settings_flush)
        self.box_fill_alpha_slider.valueChanged.connect(lambda _: self.box_fill_alpha_value_lbl.setText(str(self.box_fill_alpha_slider.value())))
        self.box_fill_alpha_value_lbl = QtWidgets.QLabel(str(self.box_fill_alpha_slider.value()))
        box_fill_alpha_container = QtWidgets.QWidget()
        bfa_layout = QtWidgets.QVBoxLayout(box_fill_alpha_container)
        bfa_layout.setContentsMargins(0, 0, 0, 0)
        bfa_layout.setSpacing(6)
        bfa_layout.addWidget(self.box_fill_alpha_slider)
        bfa_layout.addWidget(self.box_fill_alpha_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 18, self.t3("Fill opacity (%)", "Прозрачность заливки (%)", "Прозорість заливки (%)"), box_fill_alpha_container)

        # Градиентная заливка
        self.box_fill_gradient_cb = ToggleSwitch("")
        self.box_fill_gradient_cb.setChecked(int(self.settings.get("box_fill_gradient", 1)) == 1)
        self.box_fill_gradient_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 19, self.t3("Gradient fill", "Градиентная заливка", "Градієнтна заливка"), self.box_fill_gradient_cb)

        # Hitmarker
        self.hitmarker_cb = ToggleSwitch("")
        self.hitmarker_cb.setChecked(int(self.settings.get("hitmarker_enabled", 1)) == 1)
        self.hitmarker_cb.toggled.connect(self._schedule_save_settings)
        self._add_row(grid, 20, self.t3("Hitmarker", "Хитмаркер", "Хітмаркер"), self.hitmarker_cb)

        self.hitmarker_dur_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.hitmarker_dur_slider.setRange(300, 3000)
        self.hitmarker_dur_slider.setSingleStep(50)
        self.hitmarker_dur_slider.setValue(int(self.settings.get("hitmarker_duration_ms", 1700)))
        self.hitmarker_dur_slider.sliderReleased.connect(self._save_settings_flush)
        self.hitmarker_dur_slider.valueChanged.connect(lambda _: self.hitmarker_dur_value_lbl.setText(str(self.hitmarker_dur_slider.value())))
        self.hitmarker_dur_value_lbl = QtWidgets.QLabel(str(self.hitmarker_dur_slider.value()))
        hm_dur_container = QtWidgets.QWidget()
        hm_layout = QtWidgets.QVBoxLayout(hm_dur_container)
        hm_layout.setContentsMargins(0, 0, 0, 0)
        hm_layout.setSpacing(6)
        hm_layout.addWidget(self.hitmarker_dur_slider)
        hm_layout.addWidget(self.hitmarker_dur_value_lbl, 0, QtCore.Qt.AlignRight)
        self._add_row(grid, 21, self.t("Duration (ms)", "Длительность (мс)"), hm_dur_container)

        # (удалено) Предупреждение наблюдателей

        layout.addLayout(grid)
        
        # Автономный режим — ничего не блокируем
        # Если лицензия не активна — оставляем доступным только тумблер ESP,
        # остальные элементы выключаем и блокируем (значения — минимальные)
        try:
            license_active = int(self.settings.get("license_active", 0)) == 1
        except Exception:
            license_active = False

        if not license_active:
            widgets_to_disable = [
                getattr(self, "esp_rendering_cb", None),
                getattr(self, "esp_mode_cb", None),
                getattr(self, "line_rendering_cb", None),
                getattr(self, "hp_bar_rendering_cb", None),
                getattr(self, "hp_bar_gradient_cb", None),
                getattr(self, "hp_bar_grad_style_cb", None),
                getattr(self, "head_hitbox_rendering_cb", None),
                getattr(self, "bons_cb", None),
                getattr(self, "nickname_cb", None),
                getattr(self, "weapon_cb", None),
                getattr(self, "bomb_esp_cb", None),
                getattr(self, "radius_slider", None),
                getattr(self, "neon_outline_cb", None),
                getattr(self, "neon_color_cb", None),
                getattr(self, "box_style_cb", None),
                getattr(self, "box_thickness_slider", None),
                getattr(self, "box_opacity_slider", None),
                getattr(self, "box_fill_cb", None),
                getattr(self, "box_fill_alpha_slider", None),
                getattr(self, "box_fill_gradient_cb", None),
                getattr(self, "hitmarker_cb", None),
                getattr(self, "hitmarker_dur_slider", None),
            ]

            for w in widgets_to_disable:
                if w is None:
                    continue
                try:
                    if isinstance(w, ToggleSwitch):
                        w.setChecked(False)
                        w.setEnabled(False)
                    elif isinstance(w, QtWidgets.QComboBox):
                        w.setCurrentIndex(0)
                        w.setEnabled(False)
                    elif isinstance(w, QtWidgets.QSlider):
                        w.setValue(w.minimum())
                        w.setEnabled(False)
                    else:
                        w.setEnabled(False)
                except Exception:
                    pass

            # Обновим лейблы значений у слайдеров
            try:
                if hasattr(self, "radius_value_lbl"):
                    self.radius_value_lbl.setText(str(self.radius_slider.value()))
            except Exception:
                pass
            try:
                if hasattr(self, "box_thickness_value_lbl"):
                    self.box_thickness_value_lbl.setText(str(self.box_thickness_slider.value()))
            except Exception:
                pass
            try:
                if hasattr(self, "box_opacity_value_lbl"):
                    self.box_opacity_value_lbl.setText(str(self.box_opacity_slider.value()))
            except Exception:
                pass
            try:
                if hasattr(self, "box_fill_alpha_value_lbl"):
                    self.box_fill_alpha_value_lbl.setText(str(self.box_fill_alpha_slider.value()))
            except Exception:
                pass
            try:
                if hasattr(self, "hitmarker_dur_value_lbl"):
                    self.hitmarker_dur_value_lbl.setText(str(self.hitmarker_dur_slider.value()))
            except Exception:
                pass

        return card

    # legacy container creators removed

    def _schedule_save_settings(self):
        # Debounce сохранение, чтобы убрать лаги от частых вызовов
        try:
            if not hasattr(self, "_save_timer"):
                self._save_timer = QtCore.QTimer(self)
                self._save_timer.setSingleShot(True)
                self._save_timer.timeout.connect(self._save_settings_flush)
            # 120 мс после последнего переключения
            self._save_timer.start(120)
        except Exception:
            # fallback на немедленное сохранение
            self._save_settings_flush()

    def _save_settings_flush(self):
        self.save_settings()

    def save_settings(self):
        # Автономный режим — лицензия считается активной
        license_active = True
        self.settings["esp_rendering"] = 1 if self.esp_rendering_cb.isChecked() else 0
        self.settings["esp_mode"] = self.esp_mode_cb.currentIndex()
        self.settings["line_rendering"] = 1 if self.line_rendering_cb.isChecked() else 0
        self.settings["hp_bar_rendering"] = 1 if self.hp_bar_rendering_cb.isChecked() else 0
        self.settings["hp_bar_gradient"] = 1 if self.hp_bar_gradient_cb.isChecked() else 0
        self.settings["head_hitbox_rendering"] = 1 if self.head_hitbox_rendering_cb.isChecked() else 0
        self.settings["bons"] = 1 if self.bons_cb.isChecked() else 0
        self.settings["nickname"] = 1 if self.nickname_cb.isChecked() else 0
        self.settings["weapon"] = 1 if self.weapon_cb.isChecked() else 0
        self.settings["bomb_esp"] = 1 if self.bomb_esp_cb.isChecked() else 0
        self.settings["radius"] = self.radius_slider.value()
        self.settings["neon_outline"] = 1 if self.neon_outline_cb.isChecked() else 0
        self.settings["neon_outline_color"] = self.neon_color_cb.currentIndex()
        # Новые опции боксов
        if hasattr(self, "box_style_cb"):
            self.settings["box_style"] = int(self.box_style_cb.currentIndex())
        if hasattr(self, "box_thickness_slider"):
            self.settings["box_thickness"] = int(self.box_thickness_slider.value())
            if hasattr(self, "box_thickness_value_lbl"):
                self.box_thickness_value_lbl.setText(str(self.settings["box_thickness"]))
        if hasattr(self, "box_opacity_slider"):
            self.settings["box_opacity"] = int(self.box_opacity_slider.value())
            if hasattr(self, "box_opacity_value_lbl"):
                self.box_opacity_value_lbl.setText(str(self.settings["box_opacity"]))
        if hasattr(self, "box_fill_cb"):
            self.settings["box_fill"] = 1 if self.box_fill_cb.isChecked() else 0
        if hasattr(self, "box_fill_alpha_slider"):
            self.settings["box_fill_alpha_pct"] = int(self.box_fill_alpha_slider.value())
            if hasattr(self, "box_fill_alpha_value_lbl"):
                self.box_fill_alpha_value_lbl.setText(str(self.settings["box_fill_alpha_pct"]))
        if hasattr(self, "box_fill_gradient_cb"):
            self.settings["box_fill_gradient"] = 1 if self.box_fill_gradient_cb.isChecked() else 0
        # Hitmarker
        if hasattr(self, "hitmarker_cb"):
            self.settings["hitmarker_enabled"] = 1 if self.hitmarker_cb.isChecked() else 0
        if hasattr(self, "hitmarker_dur_slider"):
            self.settings["hitmarker_duration_ms"] = int(self.hitmarker_dur_slider.value())
            if hasattr(self, "hitmarker_dur_value_lbl"):
                self.hitmarker_dur_value_lbl.setText(str(self.settings["hitmarker_duration_ms"]))
        # misc
        if hasattr(self, "show_fps_cb"):
            self.settings["show_fps"] = 1 if self.show_fps_cb.isChecked() else 0
        if hasattr(self, "overlay_fps_slider"):
            self.settings["overlay_fps_limit"] = int(self.overlay_fps_slider.value())
            if hasattr(self, "overlay_fps_value_lbl"):
                self.overlay_fps_value_lbl.setText(str(self.settings["overlay_fps_limit"]))
        if hasattr(self, "hotkey_key_edit"):
            self.settings["toggle_hotkey_key"] = self.hotkey_key_edit.text().strip() or "F6"
        # Aimbot
        if hasattr(self, "aim_enabled_cb"):
            self.settings["aim_enabled"] = 1 if self.aim_enabled_cb.isChecked() else 0
        if hasattr(self, "aim_hold_key"):
            self.settings["aim_hold_key"] = self.aim_hold_key.currentText()
        if hasattr(self, "aim_fov_slider"):
            self.settings["aim_fov"] = int(self.aim_fov_slider.value())
            if hasattr(self, "aim_fov_value_lbl"):
                self.aim_fov_value_lbl.setText(str(self.settings["aim_fov"]))
        # Обычное сглаживание убрано
        if hasattr(self, "aim_target_smooth_slider"):
            self.settings["aim_target_smooth_pct"] = int(self.aim_target_smooth_slider.value())
            if hasattr(self, "aim_target_smooth_value_lbl"):
                self.aim_target_smooth_value_lbl.setText(str(self.settings["aim_target_smooth_pct"]))
        if hasattr(self, "aim_fire_smooth_slider"):
            self.settings["aim_fire_smooth_pct"] = int(self.aim_fire_smooth_slider.value())
            if hasattr(self, "aim_fire_smooth_value_lbl"):
                self.aim_fire_smooth_value_lbl.setText(str(self.settings["aim_fire_smooth_pct"]))
        if hasattr(self, "aim_bone_cb"):
            self.settings["aim_bone"] = int(self.aim_bone_cb.currentIndex())
        if hasattr(self, "aim_team_cb"):
            self.settings["aim_team"] = int(self.aim_team_cb.currentIndex())
        if hasattr(self, "aim_humanize_cb"):
            self.settings["aim_humanize"] = 1 if self.aim_humanize_cb.isChecked() else 0
        if hasattr(self, "aim_react_slider"):
            self.settings["aim_reaction_ms"] = int(self.aim_react_slider.value())
            if hasattr(self, "aim_react_value_lbl"):
                self.aim_react_value_lbl.setText(str(self.settings["aim_reaction_ms"]))
        if hasattr(self, "aim_pause_slider"):
            self.settings["aim_pause_ms"] = int(self.aim_pause_slider.value())
            if hasattr(self, "aim_pause_value_lbl"):
                self.aim_pause_value_lbl.setText(str(self.settings["aim_pause_ms"]))
        if hasattr(self, "aim_no_wall_cb"):
            self.settings["aim_no_through_walls"] = 1 if self.aim_no_wall_cb.isChecked() else 0
        # Trigger
        if hasattr(self, "trigger_enabled_cb"):
            self.settings["trigger_enabled"] = 1 if self.trigger_enabled_cb.isChecked() else 0
        if hasattr(self, "trigger_hold_key"):
            self.settings["trigger_hold_key"] = self.trigger_hold_key.currentText()
        if hasattr(self, "trigger_radius_slider"):
            self.settings["trigger_radius"] = int(self.trigger_radius_slider.value())
            if hasattr(self, "trigger_radius_value_lbl"):
                self.trigger_radius_value_lbl.setText(str(self.settings["trigger_radius"]))
        if hasattr(self, "trigger_delay_slider"):
            self.settings["trigger_delay_ms"] = int(self.trigger_delay_slider.value())
            if hasattr(self, "trigger_delay_value_lbl"):
                self.trigger_delay_value_lbl.setText(str(self.settings["trigger_delay_ms"]))
        self.radius_value_lbl.setText(str(self.settings["radius"]))
        save_settings(self.settings)

    def _change_accent(self):
        self.settings["accent"] = int(self.accent_combo.currentIndex())
        save_settings(self.settings)
        self.apply_theme()

    # --- Работа с конфигами ---
    def _on_save_config(self):
        try:
            name = (self.cfg_name_edit.text() or "").strip()
            if not name:
                name = f"config_{int(time.time())}"
            # Безопасное имя
            safe = "".join(ch for ch in name if ch.isalnum() or ch in ("_","-")) or "config"
            path = os.path.join(CONFIGS_DIR, f"{safe}.json")
            os.makedirs(CONFIGS_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self._show_info(f"Конфиг сохранён: {safe}.json")
        except Exception as e:
            print(f"Ошибка сохранения конфига: {e}")

    def _on_open_configs_dir(self):
        try:
            os.makedirs(CONFIGS_DIR, exist_ok=True)
            os.startfile(CONFIGS_DIR)
        except Exception as e:
            print(f"Ошибка открытия папки конфигов: {e}")

    def _on_browse_config(self):
        try:
            from PySide6.QtWidgets import QFileDialog
            file, _ = QFileDialog.getOpenFileName(self, "Выберите конфиг", CONFIGS_DIR, "JSON (*.json)")
            if file:
                self.apply_path_edit.setText(file)
        except Exception as e:
            print(f"Ошибка выбора файла: {e}")

    def _on_apply_config(self):
        try:
            path = (self.apply_path_edit.text() or "").strip()
            if not path or not os.path.isfile(path):
                print("Укажите корректный путь к .json конфигу")
                self._show_info("Укажите корректный путь к .json конфигу")
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                print("Некорректный формат файла конфига")
                self._show_info("Некорректный формат файла конфига")
                return
            # Сливаем настройки с дефолтом и применяем
            self.settings = {**DEFAULT_SETTINGS, **data}
            save_settings(self.settings)
            # Обновляем UI полностью (пересоздаём страницы), чтобы все контролы приняли новые значения
            self._reload_ui_pages()
        except Exception as e:
            print(f"Ошибка применения конфига: {e}")

    def closeEvent(self, event):
        # Сохраняем настройки при закрытии
        save_settings(self.settings)
        if hasattr(self, '_shutdown_event'):
            self._shutdown_event.set()
        # Принудительно завершаем все процессы
        QtWidgets.QApplication.quit()
        event.accept()

    def _reload_ui_pages(self):
        try:
            # Перечитываем настройки с диска
            self.settings = load_settings()
            # Обновим тему
            self.apply_theme()
            current = 3 if self.stack.currentIndex() is None else int(self.stack.currentIndex())
            # Полностью пересоберём
            while self.stack.count() > 0:
                w = self.stack.widget(0)
                self.stack.removeWidget(w)
                w.deleteLater()
            # Пересоздаём страницы
            self.stack.addWidget(self.create_esp_page())         # 0
            self.stack.addWidget(self.create_aim_page())          # 1
            self.stack.addWidget(self.create_trigger_page())      # 2
            self.stack.addWidget(self.create_misc_page())         # 3
            # Прайс/подписка удалены в автономном режиме
            self.stack.addWidget(self.create_about_page())        # 4
            # Вернёмся на прежнюю вкладку, если в пределах
            if 0 <= current < self.stack.count():
                self.select_nav(current)
            else:
                self.select_nav(3)
        except Exception as e:
            print(f"Ошибка обновления UI: {e}")

    def _show_info(self, text: str):
        try:
            QtWidgets.QMessageBox.information(
                self,
                self.t3("BLACKSCOPE", "BLACKSCOPE", "BLACKSCOPE"),
                self._tr(text)
            )
        except Exception:
            print(text)

    def _license_status_text(self) -> str:
        if int(self.settings.get("license_active", 0)) == 1:
            ip = self.settings.get("license_ip", "")
            exp = self.settings.get("license_expires_at", "")
            if exp:
                return f"Активна (IP: {ip}) • до {exp}"
            return f"Активна (IP: {ip})"
        return "Не активирована"

    def _on_activate_license(self):
        key = (self.lic_input.text() or "").strip()
        if not key:
            self._show_info("Введите ключ активации")
            return
        try:
            ip = _get_public_ip() or ""
            if not ip:
                self._show_info("Не удалось определить публичный IP. Проверьте интернет/VPN и попробуйте снова.")
                return
            try:
                ok = _license_mark_used(key, ip)
            except ConnectionError:
                self._show_info("Вы пока не можете войти в аккаунт, потому что сервер временно отключен. Это временно — скоро всё восстановят.")
                return

            if ok:
                self.settings["license_active"] = 1
                self.settings["license_key"] = key
                self.settings["license_ip"] = ip
                # Обновим статусы c сервера, чтобы подтянуть expires_at
                refreshed = verify_license_settings(self.settings)
                self.settings.update(refreshed)
                save_settings(self.settings)
                self.lic_status_lbl.setText(self._license_status_text())
                self._show_info("Активация успешна")
                # Перепостроить страницы, чтобы применить блокировки
                self._reload_ui_pages()
            else:
                # Уточним причину: занятый ключ на другом IP
                try:
                    row = _license_select_by_key(key)
                except ConnectionError:
                    self._show_info("Вы пока не можете войти в аккаунт, потому что сервер временно отключен. Это временно — скоро всё восстановят.")
                    return
                if row and row.get("used") and str(row.get("ip") or "") != ip:
                    self._show_info("Ключ уже активирован на другом IP. Отключите VPN/прокси и попробуйте снова. Для переноса — свяжитесь с администратором.")
                else:
                    self._show_info("Ключ недействителен или уже активирован на другом IP")
        except Exception as e:
            self._show_info(f"Ошибка активации: {e}")

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.is_dragging = True
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.is_dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_position
            self.move(self.pos() + delta)
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.is_dragging = False

def configurator(shutdown_event):
    # Жёсткая блокировка: после истечения срока показываем только уведомление
    # удалено: проверка истечения срока
    try:
        _set_win_app_id("BLACKSCOPE.Config")
        app = QtWidgets.QApplication(sys.argv)
        _apply_app_font(app)
        _apply_app_icon(app)
        window = ConfigWindow(shutdown_event=shutdown_event)
        _apply_app_icon(app, window)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Ошибка при запуске конфигуратора: {e}")
        # Если произошла ошибка, создаем простое окно с сообщением
        try:
            error_app = QtWidgets.QApplication(sys.argv) if QtWidgets.QApplication.instance() is None else QtWidgets.QApplication.instance()
            _apply_app_font(error_app)
            error_window = QtWidgets.QWidget()
            error_window.setWindowTitle("BLACKSCOPE - Error")
            error_window.setFixedSize(450, 250)
            error_window.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
            error_window.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            
            # Main container with styling
            container = QtWidgets.QFrame(error_window)
            container.setObjectName("ErrorContainer")
            container.setGeometry(0, 0, 450, 250)
            
            # Title bar
            title_bar = QtWidgets.QFrame(container)
            title_bar.setObjectName("ErrorTitleBar")
            title_bar.setGeometry(0, 0, 450, 50)
            
            title_layout = QtWidgets.QHBoxLayout(title_bar)
            title_layout.setContentsMargins(16, 10, 16, 10)
            
            # Icon and title
            icon_label = QtWidgets.QLabel("●")
            icon_label.setObjectName("ErrorIcon")
            title_label = QtWidgets.QLabel("BLACKSCOPE")
            title_label.setObjectName("ErrorBrand")
            
            title_layout.addWidget(icon_label)
            title_layout.addWidget(title_label)
            title_layout.addStretch(1)
            
            # Close button
            close_btn = QtWidgets.QPushButton("×")
            close_btn.setObjectName("ErrorCloseBtn")
            close_btn.setFixedSize(32, 32)
            close_btn.clicked.connect(error_window.close)
            title_layout.addWidget(close_btn)
            
            # Content area
            content_frame = QtWidgets.QFrame(container)
            content_frame.setObjectName("ErrorContent")
            content_frame.setGeometry(0, 50, 450, 200)
            
            content_layout = QtWidgets.QVBoxLayout(content_frame)
            content_layout.setContentsMargins(30, 40, 30, 40)
            
            # Error message
            error_label = QtWidgets.QLabel("Произошла ошибка при запуске конфигуратора.\nПопробуйте перезапустить программу.")
            error_label.setObjectName("ErrorMessage")
            error_label.setAlignment(QtCore.Qt.AlignCenter)
            error_label.setWordWrap(True)
            content_layout.addWidget(error_label)
            
            # Apply styling
            error_window.setStyleSheet("""
                QFrame#ErrorContainer {
                    background: #0b0d15;
                    border-radius: 20px;
                    border: 1px solid #1a1f2e;
                }
                QFrame#ErrorTitleBar {
                    background: #0a0c12;
                    border-bottom: 1px solid #1a1e28;
                    border-top-left-radius: 20px;
                    border-top-right-radius: 20px;
                }
                QFrame#ErrorContent {
                    background: transparent;
                    border-bottom-left-radius: 20px;
                    border-bottom-right-radius: 20px;
                }
                QLabel#ErrorIcon {
                    font: 700 16px 'Segoe UI';
                    color: #ff6b6b;
                }
                QLabel#ErrorBrand {
                    font: 700 16px 'Segoe UI Variable Text';
                    color: #ffffff;
                    letter-spacing: 0.4px;
                }
                QLabel#ErrorMessage {
                    font: 500 15px 'Segoe UI Variable Text';
                    color: #e1e5ff;
                    line-height: 1.5;
                }
                QPushButton#ErrorCloseBtn {
                    background: #121622;
                    border: 1px solid #20263a;
                    border-radius: 16px;
                    color: #d4d9ef;
                    font: 600 16px 'Segoe UI';
                }
                QPushButton#ErrorCloseBtn:hover {
                    background: #2a0f14;
                    color: #ffd6db;
                    border-color: #4a2028;
                }
            """)
            
            # Make window draggable
            def mousePressEvent(event):
                if event.button() == QtCore.Qt.LeftButton:
                    error_window._drag_pos = event.globalPos() - error_window.frameGeometry().topLeft()
                    event.accept()
            
            def mouseMoveEvent(event):
                if event.buttons() == QtCore.Qt.LeftButton and hasattr(error_window, '_drag_pos'):
                    error_window.move(event.globalPos() - error_window._drag_pos)
                    event.accept()
            
            title_bar.mousePressEvent = mousePressEvent
            title_bar.mouseMoveEvent = mouseMoveEvent
            
            error_window.show()
            sys.exit(error_app.exec())
        except:
            # В случае критической ошибки просто выходим
            sys.exit(1)

# ESP
class ESPWindow(QtWidgets.QWidget):
    def __init__(self, settings, shutdown_event=None):
        # Жёсткая блокировка ещё и на уровне конструктора окна ESP
        # удалено: проверка истечения срока
        super().__init__()
        self.settings = settings
        self._shutdown_event = shutdown_event
        self.setWindowTitle('ESP Overlay')
        self._panel_visible = False
        self._panel_ref = None
        self._panel_visible = False
        self.window_width, self.window_height = get_window_size("Counter-Strike 2")
        if self.window_width is None or self.window_height is None:
            print("Ошибка: окно игры не найдено.")
            sys.exit(1)
        self.setGeometry(0, 0, self.window_width, self.window_height)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        hwnd = self.winId()
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

        self.file_watcher = QFileSystemWatcher([CONFIG_FILE])
        self.file_watcher.fileChanged.connect(self.reload_settings)

        # Получаем оффсеты и информацию о клиенте
        try:
            self.offsets, self.client_dll = get_offsets_and_client_dll()
            print("Оффсеты успешно получены")
        except Exception as e:
            print(f"Ошибка при получении оффсетов: {e}")
            raise
            
        # Подключаемся к игре
        try:
            self.pm = pymem.Pymem("cs2.exe")
            self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
            print("Успешное подключение к игре")
        except Exception as e:
            print(f"Ошибка при подключении к игре: {e}")
            raise

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setGeometry(0, 0, self.window_width, self.window_height)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: transparent;")
        self.view.setSceneRect(0, 0, self.window_width, self.window_height)
        self.view.setFrameShape(QtWidgets.QFrame.NoFrame)
        # Ensure no effects on view to avoid nested painters
        self.view.setGraphicsEffect(None)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_scene)
        # Начальный запуск; интервал синхронизируем под лимит FPS
        self._apply_overlay_fps_limit()

        # Периодический опрос горячей клавиши
        self.hotkey_timer = QtCore.QTimer(self)
        self.hotkey_timer.timeout.connect(self._poll_hotkey)
        self.hotkey_timer.start(60)

        # Таймер логики ботов (снижаем частоту опроса для стабильности)
        self.logic_timer = QtCore.QTimer(self)
        self.logic_timer.timeout.connect(self._run_assist_logic)
        self.logic_timer.start(8)  # ~125 Гц вместо 1 мс, чтобы не перегружать цикл

        self.last_time = time.time()
        self.frame_count = 0
        self.fps = 0

        # Упрощаем аим: без фонового воркера и без внутреннего биаса/сглаживания
        # Используем параметры динамики из usa.py
        self._aim_last_dxdy = None
        self.stop_radius = int(self.settings.get("aim_stop_radius", 2))
        # Сглаживание целевой точки (низкочастотный фильтр) — для борьбы с рывками
        self._aim_target_sx = None
        self._aim_target_sy = None
        # Детектор «пустых кадров» (ничего не рисуем) для авто-восстановления
        self._empty_frames = 0
        self._last_heal_ts = 0.0

    def reload_settings(self):
        # Автономный режим: перезагружаем только локальные настройки, без лиценз. валидаций
        self.settings = load_settings()
        self.window_width, self.window_height = get_window_size("Counter-Strike 2")
        if self.window_width is None or self.window_height is None:
            print("Ошибка: окно игры не найдено.")
            sys.exit(1)
        self.setGeometry(0, 0, self.window_width, self.window_height)
        self._apply_overlay_fps_limit()
        self.update_scene()

    def _apply_overlay_fps_limit(self):
        try:
            fps = int(self.settings.get("overlay_fps_limit", 144))
            fps = max(40, min(300, fps))
            interval_ms = max(1, int(1000 / fps))
            self.timer.start(interval_ms)
        except Exception:
            self.timer.start(0)

    # Глобальный хоткей (Windows) — перехват в отдельном таймере опроса
    def _is_hotkey_pressed(self) -> bool:
        # На Windows используем GetAsyncKeyState
        key_name = (self.settings.get("toggle_hotkey_key", "F6") or "F6").upper()
        vk_map = {
            "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75,
            "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
            "F13": 0x7C, "F14": 0x7D, "F15": 0x7E, "F16": 0x7F, "F17": 0x80, "F18": 0x81,
            "F19": 0x82, "F20": 0x83, "F21": 0x84, "F22": 0x85, "F23": 0x86, "F24": 0x87,
            "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
            "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
            "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45, "F": 0x46,
            "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A, "K": 0x4B, "L": 0x4C,
            "M": 0x4D, "N": 0x4E, "O": 0x4F, "P": 0x50, "Q": 0x51, "R": 0x52,
            "S": 0x53, "T": 0x54, "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58,
            "Y": 0x59, "Z": 0x5A
        }
        vk = vk_map.get(key_name)
        if vk is None:
            return False
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)

    def _poll_hotkey(self):
        if self._is_hotkey_pressed():
            # debounce: ждём отпускание
            # Логика: хоткей всегда ПЕРЕкладывает панель в видимое состояние
            self._panel_visible = True
            while self._is_hotkey_pressed():
                QtWidgets.QApplication.processEvents()
                time.sleep(0.02)
            self._show_or_reuse_config_panel()

    def _show_or_reuse_config_panel(self):
        # Ищем уже созданную панель
        if self._panel_ref is not None and isinstance(self._panel_ref, ConfigWindow):
            panel = self._panel_ref
            if panel.isHidden():
                panel.show()
            panel.raise_()
            panel.activateWindow()
            return
        panel = ConfigWindow(shutdown_event=None)
        # Используем флаг Window вместо Tool, чтобы окно нормально всплывало поверх полноэкранной игры
        panel.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        # Делаем окно видимым для мыши (отключаем WS_EX_TRANSPARENT)
        hwnd = int(panel.winId())
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        ex_style = ex_style & ~win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        panel.show()
        panel.raise_()
        panel.activateWindow()
        self._panel_ref = panel
        try:
            panel.destroyed.connect(self._on_panel_destroyed)
        except Exception:
            pass

    def _hide_config_panel(self):
        if self._panel_ref is not None:
            try:
                self._panel_ref.close()
            except Exception:
                pass

    def _on_panel_destroyed(self, *args):
        # Сброс состояния при закрытии панели
        self._panel_ref = None
        self._panel_visible = False

    # --- ЛОГИКА AIM/TRIGGER ---
    def _mouse_event(self, left_down: bool = False, left_up: bool = False):
        try:
            inputs = []
            if left_down:
                inputs.append((0x0002,))  # MOUSEEVENTF_LEFTDOWN
            if left_up:
                inputs.append((0x0004,))  # MOUSEEVENTF_LEFTUP
            for (flag,) in inputs:
                ctypes.windll.user32.mouse_event(flag, 0, 0, 0, 0)
            # При клике обновляем авто-биас относительно последнего наведения
            if left_down and not left_up and hasattr(self, "_aim_last_dxdy") and self._aim_last_dxdy is not None:
                try:
                    dx, dy = self._aim_last_dxdy
                    # Внешний чит не знает точного центра хита, примем, что промах равен остаточному dx/dy
                    # Знак обратный: если тянули вправо, а промах вправо — сместим цель влево в будущем
                    self._register_hit_feedback(-dx, -dy)
                except Exception:
                    pass
        except Exception:
            pass

    def _register_hit_feedback(self, hit_center_dx: float, hit_center_dy: float):
        # По событию выстрела/клика корректируем биас, чтобы «прибить» постоянную косину
        try:
            if int(self.settings.get("aim_auto_bias", 1)) != 1:
                return
            rate = float(self.settings.get("aim_bias_rate", 0.15))
            limit = float(self.settings.get("aim_bias_limit_px", 60))
            # Экспоненциальное приближение
            self._aim_bias_x = max(-limit, min(limit, (1.0 - rate) * getattr(self, "_aim_bias_x", 0.0) + rate * hit_center_dx))
            self._aim_bias_y = max(-limit, min(limit, (1.0 - rate) * getattr(self, "_aim_bias_y", 0.0) + rate * hit_center_dy))
        except Exception:
            pass

    def _is_hold_active(self, key_name: str) -> bool:
        if key_name is None:
            return False
        name = key_name.upper()
        vk_map = {
            "LMB": 0x01, "RMB": 0x02,
            "SHIFT": 0x10, "CTRL": 0x11, "ALT": 0x12,
            "MOUSE4": 0x05, "MOUSE5": 0x06,
        }
        vk = vk_map.get(name)
        if vk is None:
            return False
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)

    def _cursor_pos(self):
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def _move_mouse(self, dx: float, dy: float):
        try:
            ctypes.windll.user32.mouse_event(0x0001, int(round(dx)), int(round(dy)), 0, 0)
        except Exception:
            pass

    def _run_assist_logic(self):
        try:
            # Настройки обновляются через QFileSystemWatcher в reload_settings();
            # избегаем чтения диска на каждом тике, чтобы не душить FPS
            if not self.is_game_window_active():
                return

            # Простая выборка цели: ближайшая к центру FOV по голове/груди
            aim_enabled = int(self.settings.get("aim_enabled", 0)) == 1
            trigger_enabled = int(self.settings.get("trigger_enabled", 0)) == 1

            if not (aim_enabled or trigger_enabled):
                return

            # Выполняем тяжёлый поиск целей только если реально требуется:
            # - Aimbot: когда удерживается назначенная кнопка
            # - Trigger: когда режим Always или удерживается назначенная кнопка
            need_scan = False
            if aim_enabled:
                hold_name = self.settings.get("aim_hold_key", "RMB")
                if self._is_hold_active(hold_name):
                    need_scan = True
            if not need_scan and trigger_enabled:
                trig_mode = self.settings.get("trigger_hold_key", "ALT")
                if trig_mode == "Always" or self._is_hold_active(trig_mode):
                    need_scan = True
            if not need_scan:
                return

            # Получаем матрицу и локала
            dwEntityList = self.offsets['client.dll']['dwEntityList']
            dwLocalPlayerPawn = self.offsets['client.dll']['dwLocalPlayerPawn']
            m_iTeamNum = self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum']
            m_lifeState = self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_lifeState']
            m_pGameSceneNode = self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_pGameSceneNode']
            m_modelState = self.client_dll['client.dll']['classes']['CSkeletonInstance']['fields']['m_modelState']

            view_matrix = [self.pm.read_float(self.client + self.offsets['client.dll']['dwViewMatrix'] + i * 4) for i in range(16)]
            local_player_pawn_addr = self.pm.read_longlong(self.client + dwLocalPlayerPawn)
            try:
                local_team = self.pm.read_int(local_player_pawn_addr + m_iTeamNum)
            except Exception:
                return

            entity_list = self.pm.read_longlong(self.client + dwEntityList)
            entity_ptr = self.pm.read_longlong(entity_list + 0x10)
            if entity_ptr == 0:
                return

            center_x = self.window_width / 2
            center_y = self.window_height / 2

            best_dist = 1e9
            best_screen = None
            best_bone = None
            best_team_equal = False

            no_through_walls = False

            def is_visible(pawn_addr: int) -> bool:
                # Базовая эвристика видимости: если точка головы проецируется и не за экраном,
                # и если доступен флаг spotted/lastVisibleTime — использовать его (если присутствует в дампе).
                try:
                    game_scene = self.pm.read_longlong(pawn_addr + m_pGameSceneNode)
                    bone_matrix = self.pm.read_longlong(game_scene + m_modelState + 0x80)
                    headX = self.pm.read_float(bone_matrix + 6 * 0x20)
                    headY = self.pm.read_float(bone_matrix + 6 * 0x20 + 0x4)
                    headZ = self.pm.read_float(bone_matrix + 6 * 0x20 + 0x8)
                    pos = w2s(view_matrix, headX, headY, headZ, self.window_width, self.window_height)
                    if pos[0] < 0 or pos[1] < 0:
                        return False
                except Exception:
                    return False
                # Дополнительно: попробуем прочитать возможный флаг spotted, если он есть в client_dll
                try:
                    spotted_off = self.client_dll['client.dll']['classes']['C_BaseEntity']['fields'].get('m_bSpotted', None)
                    if spotted_off is not None:
                        return bool(self.pm.read_bool(pawn_addr + spotted_off))
                except Exception:
                    pass
                return True

            for i in range(1, 64):
                try:
                    controller = self.pm.read_longlong(entity_ptr + 0x78 * (i & 0x1FF))
                    if controller == 0:
                        continue
                    pawn_handle = self.pm.read_longlong(controller + self.client_dll['client.dll']['classes']['CCSPlayerController']['fields']['m_hPlayerPawn'])
                    if pawn_handle == 0:
                        continue
                    list_pawn = self.pm.read_longlong(entity_list + 0x8 * ((pawn_handle & 0x7FFF) >> 0x9) + 0x10)
                    if list_pawn == 0:
                        continue
                    pawn_addr = self.pm.read_longlong(list_pawn + 0x78 * (pawn_handle & 0x1FF))
                    if pawn_addr == 0 or pawn_addr == local_player_pawn_addr:
                        continue
                    team = self.pm.read_int(pawn_addr + m_iTeamNum)
                    hp_state = self.pm.read_int(pawn_addr + m_lifeState)
                    if hp_state != 256:
                        continue
                    # Проверка видимости отключена (по запросу)
                    # фильтр по команде для целей Aimbot/Trigger
                    is_same_team = (team == local_team)
                    if int(self.settings.get("aim_team", 0)) == 0 and is_same_team:
                        # aim по врагам только
                        pass
                    # Берём кости
                    game_scene = self.pm.read_longlong(pawn_addr + m_pGameSceneNode)
                    bone_matrix = self.pm.read_longlong(game_scene + m_modelState + 0x80)
                    # Выбор кости головы/тела с поддержкой смешанной точки (среднее между костями)
                    if int(self.settings.get("aim_bone", 0)) == 0:
                        head_id = int(self.settings.get("aim_head_bone_id", 6))
                        neck_id = 5
                        # читаем голову и шею
                        hx = self.pm.read_float(bone_matrix + head_id * 0x20)
                        hy = self.pm.read_float(bone_matrix + head_id * 0x20 + 0x4)
                        hz = self.pm.read_float(bone_matrix + head_id * 0x20 + 0x8)
                        nx = self.pm.read_float(bone_matrix + neck_id * 0x20)
                        ny = self.pm.read_float(bone_matrix + neck_id * 0x20 + 0x4)
                        nz = self.pm.read_float(bone_matrix + neck_id * 0x20 + 0x8)
                        # смешиваем для устойчивости (0.0=чистая голова, 1.0=чистая шея)
                        mix = float(self.settings.get("aim_head_mix", 0.15))
                        bx = hx * (1.0 - mix) + nx * mix
                        by = hy * (1.0 - mix) + ny * mix
                        bz = hz * (1.0 - mix) + nz * mix
                        try:
                            bz += float(self.settings.get("aim_head_z_offset", 6))
                        except Exception:
                            pass
                    else:
                        chest_id = 4
                        bx = self.pm.read_float(bone_matrix + chest_id * 0x20)
                        by = self.pm.read_float(bone_matrix + chest_id * 0x20 + 0x4)
                        bz = self.pm.read_float(bone_matrix + chest_id * 0x20 + 0x8)
                    pos = w2s(view_matrix, bx, by, bz, self.window_width, self.window_height)
                    # Тонкая экранная юстировка (пиксели + проценты от роста бокса + дальняя поправка)
                    try:
                        off_x = int(self.settings.get("aim_screen_offset_x", 0))
                        off_y = int(self.settings.get("aim_screen_offset_y", 0))
                        dyn_x = float(self.settings.get("aim_dynamic_x_pct", 0.0))
                        dyn_y = float(self.settings.get("aim_dynamic_y_pct", 0.0))
                        far_down = int(self.settings.get("aim_far_down_px", 2))
                        far_thr = float(self.settings.get("aim_far_height_threshold", 110))
                        # Оценка роста на экране по разнице головы и ног
                        try:
                            legZ_tmp = self.pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                            leg_pos_tmp = w2s(view_matrix, bx, by, legZ_tmp, self.window_width, self.window_height)
                            height_px = abs(pos[1] - leg_pos_tmp[1])
                        except Exception:
                            height_px = 0
                        pos[0] += off_x + int(height_px * dyn_x)
                        pos[1] += off_y + int(height_px * dyn_y) + (far_down if height_px > 0 and height_px < far_thr else 0)
                    except Exception:
                        pass
                    if pos[0] < 0 or pos[1] < 0:
                        continue
                    # расстояние на экране
                    dx = pos[0] - center_x
                    dy = pos[1] - center_y
                    dist = (dx*dx + dy*dy) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        best_screen = pos
                        best_bone = (bx, by, bz)
                        best_team_equal = is_same_team
                except Exception:
                    continue

            # Aimbot (usa.py-стиль динамики наведения + сглаживание и humanize)
            if aim_enabled and best_screen is not None:
                fov_px = float(self.settings.get("aim_fov", 80))
                allow_team = int(self.settings.get("aim_team", 0)) == 1
                if best_dist <= fov_px and (allow_team or not best_team_equal):
                    hold_name = self.settings.get("aim_hold_key", "RMB")
                    if self._is_hold_active(hold_name):
                        # Сглаживание целевой точки в экранных координатах
                        try:
                            pct = max(0.0, min(90.0, float(self.settings.get("aim_target_smooth_pct", 35.0))))
                        except Exception:
                            pct = 35.0
                        try:
                            fire_pct = max(0.0, min(95.0, float(self.settings.get("aim_fire_smooth_pct", 20.0))))
                        except Exception:
                            fire_pct = 20.0
                        if self._is_hold_active("LMB"):
                            pct = max(pct, fire_pct)
                        alpha = 1.0 - (pct / 100.0)  # 0..90% -> 1..0.1
                        if self._aim_target_sx is None:
                            self._aim_target_sx = best_screen[0]
                            self._aim_target_sy = best_screen[1]
                        else:
                            self._aim_target_sx = (1.0 - alpha) * self._aim_target_sx + alpha * best_screen[0]
                            self._aim_target_sy = (1.0 - alpha) * self._aim_target_sy + alpha * best_screen[1]

                        dx = self._aim_target_sx - center_x
                        dy = self._aim_target_sy - center_y
                        distance = max(0.0, (dx*dx + dy*dy) ** 0.5)
                        if distance > float(self.settings.get("aim_stop_radius", 2)):
                            speed = float(self.settings.get("aimbot_speed", 1.6))
                            ease = float(self.settings.get("aimbot_ease_out", 0.85))
                            step = speed * (distance ** max(0.1, min(1.0, ease)))
                            step = min(distance, step)
                            move_x = (dx / distance) * step if distance > 0 else 0
                            move_y = (dy / distance) * step if distance > 0 else 0
                            # overshoot
                            try:
                                if random.random() < float(self.settings.get("aimbot_overshoot_chance", 0.3)) and distance > 0:
                                    strength = float(self.settings.get("aimbot_overshoot_strength", 3.5))
                                    ox = (dx / distance) * strength * random.uniform(0.4, 1.0)
                                    oy = (dy / distance) * strength * random.uniform(0.4, 1.0)
                                    ox += (-dy / distance) * strength * random.uniform(-0.5, 0.5)
                                    oy += (dx / distance) * strength * random.uniform(-0.5, 0.5)
                                    move_x += ox
                                    move_y += oy
                            except Exception:
                                pass
                            # Humanize: лёгкий шум, уменьшающийся по мере приближения
                            try:
                                if int(self.settings.get("aim_humanize", 1)) == 1 and distance > 0:
                                    noise_max = min(0.10, 0.001 * distance)
                                    move_x += random.uniform(-noise_max, noise_max)
                                    move_y += random.uniform(-noise_max, noise_max)
                            except Exception:
                                pass
                            self._move_mouse(move_x, move_y)

            # Trigger Bot
            if trigger_enabled and best_screen is not None:
                radius = float(self.settings.get("trigger_radius", 10))
                delay = int(self.settings.get("trigger_delay_ms", 30))
                mode = self.settings.get("trigger_hold_key", "ALT")
                if mode == "Always" or self._is_hold_active(mode):
                    if best_dist <= radius and (int(self.settings.get("aim_team", 0)) == 1 or not best_team_equal):
                        # быстрый клик (неблокирующий)
                        self._mouse_event(left_down=True)
                        if delay > 0:
                            QtCore.QTimer.singleShot(max(0, delay), lambda: self._mouse_event(left_up=True))
                        else:
                            self._mouse_event(left_up=True)
        except Exception as e:
            # Не падаем из-за ошибок логики
            pass
    def update_scene(self):
        if not self.is_game_window_active():
            self.scene.clear()
            return

        self.scene.clear()
        try:
            # Считаем, добавилось ли что-то на сцену
            before_cnt = len(self.scene.items())
            esp(self.scene, self.pm, self.client, self.offsets, self.client_dll, self.window_width, self.window_height, self.settings)
            after_cnt = len(self.scene.items())
            current_time = time.time()
            self.frame_count += 1
            if current_time - self.last_time >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_time = current_time
            if self.settings.get("show_fps", 1) == 1:
                fps_text = self.scene.addText(f"BLACKSCOPE | ФПС: {self.fps}", QtGui.QFont('DejaVu Sans', 12, QtGui.QFont.Bold))
                fps_text.setPos(5, 5)
                fps_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))

            # Авто-восстановление при длительной «пустоте» (ESP включён, игра активна)
            if int(self.settings.get('esp_rendering', 1)) == 1 and after_cnt == before_cnt:
                self._empty_frames += 1
            else:
                self._empty_frames = 0

            # Если ничего не рисуем более ~2 секунд при активной игре — попытаться перелинковать хэндлы/оффсеты
            if self._empty_frames > max(120, int(self.settings.get('overlay_fps_limit', 144)) * 2 // 3):
                self._try_self_heal()
        except Exception as e:
            print(f"Ошибка обновления сцены: {e}")
            # if drawing fails repeatedly, request shutdown to avoid zombie process
            if self._shutdown_event is not None:
                self._shutdown_event.set()
            QtWidgets.QApplication.quit()

    def is_game_window_active(self):
        hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        if hwnd:
            foreground_hwnd = win32gui.GetForegroundWindow()
            return hwnd == foreground_hwnd
        return False

    def _try_self_heal(self):
        now = time.time()
        # не чаще раза в 3 секунды
        if now - float(self._last_heal_ts or 0) < 3.0:
            return
        self._last_heal_ts = now
        try:
            # Переустанавливаем window flags и прозрачность (иногда Windows сбрасывает стили)
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
            hwnd = self.winId()
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
        except Exception as e:
            print(f"heal: window styles: {e}")
        try:
            # Обновляем базовый адрес client.dll
            self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
        except Exception as e:
            print(f"heal: refresh client.dll base failed: {e}")
            try:
                # Переоткрываем процесс игры
                self.pm = pymem.Pymem("cs2.exe")
                self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
            except Exception as e2:
                print(f"heal: reopen Pymem failed: {e2}")
        try:
            # На случай внутреннего изменения — перечитываем оффсеты
            self.offsets, self.client_dll = get_offsets_and_client_dll()
        except Exception as e:
            print(f"heal: refresh offsets failed: {e}")
        # сбрасываем счётчик пустых кадров
        self._empty_frames = 0

def esp(scene, pm, client, offsets, client_dll, window_width, window_height, settings):
    if settings['esp_rendering'] == 0:
        return

    dwEntityList = offsets['client.dll']['dwEntityList']
    dwLocalPlayerPawn = offsets['client.dll']['dwLocalPlayerPawn']
    dwViewMatrix = offsets['client.dll']['dwViewMatrix']
    dwPlantedC4 = offsets['client.dll']['dwPlantedC4']
    m_iTeamNum = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum']
    m_lifeState = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_lifeState']
    m_pGameSceneNode = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_pGameSceneNode']
    m_modelState = client_dll['client.dll']['classes']['CSkeletonInstance']['fields']['m_modelState']
    m_hPlayerPawn = client_dll['client.dll']['classes']['CCSPlayerController']['fields']['m_hPlayerPawn']
    m_iHealth = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iHealth']
    m_iszPlayerName = client_dll['client.dll']['classes']['CBasePlayerController']['fields']['m_iszPlayerName']
    # m_pClippingWeapon may be absent in some dumps/versions; use .get() to avoid KeyError
    m_pClippingWeapon = client_dll['client.dll']['classes']['C_CSPlayerPawnBase']['fields'].get('m_pClippingWeapon', None)
    m_AttributeManager = client_dll['client.dll']['classes']['C_EconEntity']['fields']['m_AttributeManager']
    m_Item = client_dll['client.dll']['classes']['C_AttributeContainer']['fields']['m_Item']
    m_iItemDefinitionIndex = client_dll['client.dll']['classes']['C_EconItemView']['fields']['m_iItemDefinitionIndex']
    m_ArmorValue = client_dll['client.dll']['classes']['C_CSPlayerPawn']['fields']['m_ArmorValue']
    m_vecAbsOrigin = client_dll['client.dll']['classes']['CGameSceneNode']['fields']['m_vecAbsOrigin']
    m_flTimerLength = client_dll['client.dll']['classes']['C_PlantedC4']['fields']['m_flTimerLength']
    m_flDefuseLength = client_dll['client.dll']['classes']['C_PlantedC4']['fields']['m_flDefuseLength']
    m_bBeingDefused = client_dll['client.dll']['classes']['C_PlantedC4']['fields']['m_bBeingDefused']

    view_matrix = [pm.read_float(client + dwViewMatrix + i * 4) for i in range(16)]

    local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
    try:
        local_player_team = pm.read_int(local_player_pawn_addr + m_iTeamNum)
    except:
        return

    no_center_x = window_width / 2
    no_center_y = window_height * 0.9
    entity_list = pm.read_longlong(client + dwEntityList)
    entity_ptr = pm.read_longlong(entity_list + 0x10)

    def bombisplant():
        global BombPlantedTime
        bombisplant = pm.read_bool(client + dwPlantedC4 - 0x8)
        if bombisplant:
            if (BombPlantedTime == 0):
                BombPlantedTime = time.time()
        else:
            BombPlantedTime = 0
        return bombisplant
    
    def getC4BaseClass():
        plantedc4 = pm.read_longlong(client + dwPlantedC4)
        plantedc4class = pm.read_longlong(plantedc4)
        return plantedc4class
    
    def getPositionWTS():
        c4node = pm.read_longlong(getC4BaseClass() + m_pGameSceneNode)
        c4posX = pm.read_float(c4node + m_vecAbsOrigin)
        c4posY = pm.read_float(c4node + m_vecAbsOrigin + 0x4)
        c4posZ = pm.read_float(c4node + m_vecAbsOrigin + 0x8)
        bomb_pos = w2s(view_matrix, c4posX, c4posY, c4posZ, window_width, window_height)
        return bomb_pos
    
    def getBombTime():
        BombTime = pm.read_float(getC4BaseClass() + m_flTimerLength) - (time.time() - BombPlantedTime)
        return BombTime if (BombTime >= 0) else 0
    
    def isBeingDefused():
        global BombDefusedTime
        BombIsDefused = pm.read_bool(getC4BaseClass() + m_bBeingDefused)
        if (BombIsDefused):
            if (BombDefusedTime == 0):
                BombDefusedTime = time.time() 
        else:
            BombDefusedTime = 0
        return BombIsDefused
    
    def getDefuseTime():
        DefuseTime = pm.read_float(getC4BaseClass() + m_flDefuseLength) - (time.time() - BombDefusedTime)
        return DefuseTime if (isBeingDefused() and DefuseTime >= 0) else 0

    bfont = QtGui.QFont('DejaVu Sans', 10, QtGui.QFont.Bold)

    if settings.get('bomb_esp', 0) == 1:
        if bombisplant():
            BombPosition = getPositionWTS()
            BombTime = getBombTime()
            DefuseTime = getDefuseTime()
        
            if (BombPosition[0] > 0 and BombPosition[1] > 0):
                if DefuseTime > 0:
                    c4_name_text = scene.addText(f'БОМБА {round(BombTime, 2)} | РАЗМ {round(DefuseTime, 2)}', bfont)
                else:
                    c4_name_text = scene.addText(f'БОМБА {round(BombTime, 2)}', bfont)
                c4_name_x = BombPosition[0]
                c4_name_y = BombPosition[1]
                c4_name_text.setPos(c4_name_x, c4_name_y)
                c4_name_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))

    # (удалено) наблюдатели
    for i in range(1, 64):
        try:
            if entity_ptr == 0:
                break

            entity_controller = pm.read_longlong(entity_ptr + 0x78 * (i & 0x1FF))
            if entity_controller == 0:
                continue

            entity_controller_pawn = pm.read_longlong(entity_controller + m_hPlayerPawn)
            if entity_controller_pawn == 0:
                continue

            entity_list_pawn = pm.read_longlong(entity_list + 0x8 * ((entity_controller_pawn & 0x7FFF) >> 0x9) + 0x10)
            if entity_list_pawn == 0:
                continue

            entity_pawn_addr = pm.read_longlong(entity_list_pawn + 0x78 * (entity_controller_pawn & 0x1FF))
            if entity_pawn_addr == 0 or entity_pawn_addr == local_player_pawn_addr:
                continue

            entity_team = pm.read_int(entity_pawn_addr + m_iTeamNum)
            if entity_team == local_player_team and settings['esp_mode'] == 0:
                continue

            prev_hp = _LAST_HP_BY_ENTITY.get(entity_pawn_addr, None)
            entity_hp = pm.read_int(entity_pawn_addr + m_iHealth)
            armor_hp = pm.read_int(entity_pawn_addr + m_ArmorValue)
            if entity_hp <= 0:
                continue
            # Если HP уменьшился — показываем всплывающую цифру урона
            try:
                if prev_hp is not None and entity_hp < prev_hp:
                    dmg_val = max(1, prev_hp - entity_hp)
                    _DAMAGE_FLOATS.append({
                        "x": head_pos[0],
                        "y": head_pos[1],
                        "value": dmg_val,
                        "t0": time.time(),
                    })
                    # Срабатывание HITMARKER (без координат — рисуем по центру)
                    if int(settings.get('hitmarker_enabled', 1)) == 1:
                        _HITMARKERS.append({"t0": time.time(), "value": dmg_val})
            except Exception:
                pass
            _LAST_HP_BY_ENTITY[entity_pawn_addr] = entity_hp

            entity_alive = pm.read_int(entity_pawn_addr + m_lifeState)
            if entity_alive != 256:
                continue

            # Safely attempt to read weapon info. If the offset is missing or any read fails,
            # fall back to a default 'Unknown' name instead of raising and breaking the whole frame.
            weapon_name = 'Unknown'
            try:
                if m_pClippingWeapon is not None:
                    weapon_pointer = pm.read_longlong(entity_pawn_addr + m_pClippingWeapon)
                    if weapon_pointer:
                        # read chained offsets guardedly
                        try:
                            weapon_index = pm.read_int(weapon_pointer + m_AttributeManager + m_Item + m_iItemDefinitionIndex)
                            weapon_name = get_weapon_name_by_index(weapon_index)
                        except Exception:
                            # leave weapon_name as 'Unknown' on any failure
                            weapon_name = 'Unknown'
            except Exception:
                weapon_name = 'Unknown'

            base_friend = QtGui.QColor(71, 167, 106)
            base_enemy = QtGui.QColor(196, 30, 58)
            color = base_friend if entity_team == local_player_team else base_enemy
            game_scene = pm.read_longlong(entity_pawn_addr + m_pGameSceneNode)
            bone_matrix = pm.read_longlong(game_scene + m_modelState + 0x80)

            try:
                headX = pm.read_float(bone_matrix + 6 * 0x20)
                headY = pm.read_float(bone_matrix + 6 * 0x20 + 0x4)
                headZ = pm.read_float(bone_matrix + 6 * 0x20 + 0x8) + 8
                head_pos = w2s(view_matrix, headX, headY, headZ, window_width, window_height)
                if head_pos[1] < 0:
                    continue
                if settings['line_rendering'] == 1:
                    legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                    leg_pos = w2s(view_matrix, headX, headY, legZ, window_width, window_height)
                    bottom_left_x = head_pos[0] - (head_pos[0] - leg_pos[0]) // 2
                    bottom_y = leg_pos[1]
                    line = scene.addLine(bottom_left_x, bottom_y, no_center_x, no_center_y, QtGui.QPen(color, 1))

                legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                leg_pos = w2s(view_matrix, headX, headY, legZ, window_width, window_height)
                deltaZ = abs(head_pos[1] - leg_pos[1])
                leftX = head_pos[0] - deltaZ // 4
                rightX = head_pos[0] + deltaZ // 4
                # Styled box
                box_style = int(settings.get('box_style', 0))
                box_thickness = int(settings.get('box_thickness', 2))
                box_opacity = int(settings.get('box_opacity', 220))
                box_fill = bool(settings.get('box_fill', 0))
                draw_styled_box(
                    scene,
                    leftX,
                    head_pos[1],
                    rightX,
                    leg_pos[1],
                    color,
                    style=box_style,
                    thickness=box_thickness,
                    opacity=box_opacity,
                    fill=box_fill,
                    fill_alpha_pct=int(settings.get('box_fill_alpha_pct', 25)),
                    fill_gradient=bool(settings.get('box_fill_gradient', 1)),
                )

                # Neon outline effect
                if settings.get('neon_outline', 0) == 1:
                    neon_color_idx = settings.get('neon_outline_color', 0)
                    # Противоположные цвета неона для союзников/врагов
                    if entity_team == local_player_team:
                        # союзники — зелёные боксы; неон делаем голубым/фиолетовым/жёлтым в зависимости от выбора
                        if neon_color_idx == 0:
                            neon = QtGui.QColor(0, 160, 255, 200)
                        elif neon_color_idx == 1:
                            neon = QtGui.QColor(160, 80, 255, 200)
                        else:
                            neon = QtGui.QColor(255, 210, 0, 200)
                    else:
                        # враги — красные боксы; неон делаем контрастным к выбранному: жёлтый/голубой/фиолетовый
                        if neon_color_idx == 0:
                            neon = QtGui.QColor(255, 210, 0, 200)
                        elif neon_color_idx == 1:
                            neon = QtGui.QColor(0, 160, 255, 200)
                        else:
                            neon = QtGui.QColor(160, 80, 255, 200)
                    try:
                        # Адаптивная толщина всегда включена при активном неоне
                        draw_neon_silhouette(
                            scene, pm, bone_matrix, view_matrix,
                            window_width, window_height, neon,
                            adaptive=True
                        )
                    except Exception:
                        pass

                if settings['hp_bar_rendering'] == 1:
                    max_hp = 100
                    hp_percentage = min(1.0, max(0.0, entity_hp / max_hp))
                    hp_bar_width = 3
                    hp_bar_height = deltaZ
                    hp_bar_x_left = leftX - hp_bar_width - 3
                    hp_bar_y_top = head_pos[1]
                    # фон
                    scene.addRect(QtCore.QRectF(hp_bar_x_left, hp_bar_y_top, hp_bar_width, hp_bar_height), QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(12, 12, 12, 220))
                    # текущее HP
                    current_hp_height = max(0.0, hp_bar_height * hp_percentage)
                    hp_bar_y_bottom = hp_bar_y_top + hp_bar_height - current_hp_height
                    if int(settings.get('hp_bar_gradient', 1)) == 1:
                        # градиент по стилю
                        style = int(settings.get('hp_bar_gradient_style', 0))
                        grad = QtGui.QLinearGradient(QtCore.QPointF(hp_bar_x_left, hp_bar_y_bottom), QtCore.QPointF(hp_bar_x_left, hp_bar_y_top + hp_bar_height))
                        if style == 0:
                            c1, c2 = QtGui.QColor(255, 70, 70), QtGui.QColor(255, 220, 90)
                        elif style == 1:
                            c1, c2 = QtGui.QColor(54, 211, 153), QtGui.QColor(160, 255, 190)
                        else:
                            c1, c2 = QtGui.QColor(80, 160, 255), QtGui.QColor(150, 210, 255)
                        grad.setColorAt(0.0, c1)
                        grad.setColorAt(1.0, c2)
                        brush = QtGui.QBrush(grad)
                    else:
                        brush = QtGui.QBrush(QtGui.QColor(255, 70, 70))
                    scene.addRect(QtCore.QRectF(hp_bar_x_left, hp_bar_y_bottom, hp_bar_width, current_hp_height), QtGui.QPen(QtCore.Qt.NoPen), brush)
                    max_armor_hp = 100
                    armor_hp_percentage = min(1.0, max(0.0, armor_hp / max_armor_hp))
                    armor_bar_width = 2
                    armor_bar_height = deltaZ
                    armor_bar_x_left = hp_bar_x_left - armor_bar_width - 2
                    armor_bar_y_top = head_pos[1]
                
                    armor_bar = scene.addRect(QtCore.QRectF(armor_bar_x_left, armor_bar_y_top, armor_bar_width, armor_bar_height), QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(0, 0, 0))
                    current_armor_height = armor_bar_height * armor_hp_percentage
                    armor_bar_y_bottom = armor_bar_y_top + armor_bar_height - current_armor_height
                    armor_bar_current = scene.addRect(QtCore.QRectF(armor_bar_x_left, armor_bar_y_bottom, armor_bar_width, current_armor_height), QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(62, 95, 138))


                if settings['head_hitbox_rendering'] == 1:
                    head_hitbox_size = (rightX - leftX) / 5
                    head_hitbox_radius = head_hitbox_size * 2 ** 0.5 / 2
                    head_hitbox_x = leftX + 2.5 * head_hitbox_size
                    head_hitbox_y = head_pos[1] + deltaZ / 9
                    ellipse = scene.addEllipse(QtCore.QRectF(head_hitbox_x - head_hitbox_radius, head_hitbox_y - head_hitbox_radius, head_hitbox_radius * 2, head_hitbox_radius * 2), QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(255, 0, 0, 128))

                if settings.get('bons', 0) == 1:
                    draw_bones(scene, pm, bone_matrix, view_matrix, window_width, window_height)

                if settings.get('nickname', 0) == 1:
                    player_name = pm.read_string(entity_controller + m_iszPlayerName, 32)
                    font_size = max(6, min(18, deltaZ / 25))
                    font = QtGui.QFont('DejaVu Sans', font_size, QtGui.QFont.Bold)
                    name_text = scene.addText(player_name, font)
                    text_rect = name_text.boundingRect()
                    name_x = head_pos[0] - text_rect.width() / 2
                    name_y = head_pos[1] - text_rect.height()
                    name_text.setPos(name_x, name_y)
                    name_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))
                
                if settings.get('weapon', 0) == 1:
                    weapon_name_text = scene.addText(weapon_name, font)
                    text_rect = weapon_name_text.boundingRect()
                    weapon_name_x = head_pos[0] - text_rect.width() / 2
                    weapon_name_y = head_pos[1] + deltaZ
                    weapon_name_text.setPos(weapon_name_x, weapon_name_y)
                    weapon_name_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))


                if 'radius' in settings:
                    if settings['radius'] != 0:
                        center_x = window_width / 2
                        center_y = window_height / 2
                        screen_radius = settings['radius'] / 100.0 * min(center_x, center_y)
                        ellipse = scene.addEllipse(QtCore.QRectF(center_x - screen_radius, center_y - screen_radius, screen_radius * 2, screen_radius * 2), QtGui.QPen(QtGui.QColor(255, 255, 255, 16), 0.5), QtCore.Qt.NoBrush)

                # (удалено) наблюдатели

            except:
                return
        except:
            return

    # (удалено) вывод наблюдателей

    # Отрисовка HITMARKER: показываем число урона по центру экрана с плавным подъёмом и затуханием
    try:
        if int(settings.get('hitmarker_enabled', 1)) == 1 and len(_HITMARKERS) > 0:
            duration = max(200, min(4000, int(settings.get('hitmarker_duration_ms', 1700)))) / 1000.0
            cx = window_width / 2
            cy = window_height / 2
            keep = []
            for ev in _HITMARKERS:
                t = time.time() - ev.get("t0", 0)
                if 0 <= t <= duration:
                    k = 1.0 - (t / duration)
                    alpha = int(255 * k)
                    dy = -40 * (t / duration)
                    dmg = int(max(1, ev.get("value", 1)))
                    font = QtGui.QFont('Segoe UI', 14, QtGui.QFont.Bold)
                    text_item = scene.addText(f"-{dmg}", font)
                    text_item.setDefaultTextColor(QtGui.QColor(255, 80, 80, max(0, min(255, alpha))))
                    br = text_item.boundingRect()
                    text_item.setPos(cx - br.width()/2, cy - br.height()/2 + dy)
                    keep.append(ev)
            _HITMARKERS[:] = keep
    except Exception:
        pass

def get_weapon_name_by_index(index):
    weapon_names = {
    32: "P2000",
    61: "USP-S",
    4: "Glock",
    2: "Dual Berettas",
    36: "P250",
    30: "Tec-9",
    63: "CZ75-Auto",
    1: "Desert Eagle",
    3: "Five-SeveN",
    64: "R8",
    35: "Nova",
    25: "XM1014",
    27: "MAG-7",
    29: "Sawed-Off",
    14: "M249",
    28: "Negev",
    17: "MAC-10",
    23: "MP5-SD",
    24: "UMP-45",
    19: "P90",
    26: "Bizon",
    34: "MP9",
    33: "MP7",
    10: "FAMAS",
    16: "M4A4",
    60: "M4A1-S",
    8: "AUG",
    43: "Galil",
    7: "AK-47",
    39: "SG 553",
    40: "SSG 08",
    9: "AWP",
    38: "SCAR-20",
    11: "G3SG1",
    43: "Flashbang",
    44: "Hegrenade",
    45: "Smoke",
    46: "Molotov",
    47: "Decoy",
    48: "Incgrenage",
    49: "C4",
    31: "Taser",
    42: "Knife",
    41: "Knife Gold",
    59: "Knife",
    80: "Knife Ghost",
    500: "Knife Bayonet",
    505: "Knife Flip",
    506: "Knife Gut",
    507: "Knife Karambit",
    508: "Knife M9",
    509: "Knife Tactica",
    512: "Knife Falchion",
    514: "Knife Survival Bowie",
    515: "Knife Butterfly",
    516: "Knife Rush",
    519: "Knife Ursus",
    520: "Knife Gypsy Jackknife",
    522: "Knife Stiletto",
    523: "Knife Widowmaker"
}
    return weapon_names.get(index, 'Unknown')

def draw_bones(scene, pm, bone_matrix, view_matrix, width, height):
    bone_ids = {
        "head": 6,
        "neck": 5,
        "spine": 4,
        "pelvis": 0,
        "left_shoulder": 13,
        "left_elbow": 14,
        "left_wrist": 15,
        "right_shoulder": 9,
        "right_elbow": 10,
        "right_wrist": 11,
        "left_hip": 25,
        "left_knee": 26,
        "left_ankle": 27,
        "right_hip": 22,
        "right_knee": 23,
        "right_ankle": 24,
    }
    bone_connections = [
        ("head", "neck"),
        ("neck", "spine"),
        ("spine", "pelvis"),
        ("pelvis", "left_hip"),
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("pelvis", "right_hip"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
        ("neck", "left_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("neck", "right_shoulder"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
    ]
    bone_positions = {}
    try:
        for bone_name, bone_id in bone_ids.items():
            boneX = pm.read_float(bone_matrix + bone_id * 0x20)
            boneY = pm.read_float(bone_matrix + bone_id * 0x20 + 0x4)
            boneZ = pm.read_float(bone_matrix + bone_id * 0x20 + 0x8)
            bone_pos = w2s(view_matrix, boneX, boneY, boneZ, width, height)
            if bone_pos[0] != -999 and bone_pos[1] != -999:
                bone_positions[bone_name] = bone_pos
        for connection in bone_connections:
            if connection[0] in bone_positions and connection[1] in bone_positions:
                scene.addLine(
                    bone_positions[connection[0]][0], bone_positions[connection[0]][1],
                    bone_positions[connection[1]][0], bone_positions[connection[1]][1],
                    QtGui.QPen(QtGui.QColor(255, 255, 255, 128), 1)
                )
    except Exception as e:
        print(f"Error drawing bones: {e}")

def draw_neon_silhouette(scene, pm, bone_matrix, view_matrix, width, height, neon_color: QtGui.QColor, adaptive: bool = False):
    # Points around the body to draw an approximated silhouette glow
    bone_ids_main = {
        "head": 6, "neck": 5, "spine": 4, "pelvis": 0,
        "l_sh": 13, "l_el": 14, "l_wr": 15,
        "r_sh": 9,  "r_el": 10, "r_wr": 11,
        "l_hip": 25, "l_kn": 26, "l_an": 27,
        "r_hip": 22, "r_kn": 23, "r_an": 24,
    }
    def pos(bid):
        x = pm.read_float(bone_matrix + bid * 0x20)
        y = pm.read_float(bone_matrix + bid * 0x20 + 0x4)
        z = pm.read_float(bone_matrix + bid * 0x20 + 0x8)
        return w2s(view_matrix, x, y, z, width, height)

    try:
        pts = {name: pos(bid) for name, bid in bone_ids_main.items()}
        # validate
        if any(v[0] == -999 or v[1] == -999 for v in pts.values()):
            return

        # Determine adaptive thickness based on on-screen height of silhouette
        if adaptive:
            ys = [p[1] for p in pts.values()]
            height_px = max(ys) - min(ys)
            base_w = int(max(1, min(4, height_px / 120.0 + 1)))  # 1..4
            widths = [max(1, base_w + 1), base_w, max(1, base_w - 1)]
            alphas = [min(255, neon_color.alpha()), max(60, neon_color.alpha() - 60), max(40, neon_color.alpha() - 120)]
        else:
            widths = [3, 2, 1]
            alphas = [min(255, neon_color.alpha()), max(60, neon_color.alpha() - 60), max(40, neon_color.alpha() - 120)]

        pen_layers = []
        for w, a in zip(widths, alphas):
            c = QtGui.QColor(neon_color.red(), neon_color.green(), neon_color.blue(), a)
            pen_layers.append(QtGui.QPen(c, int(w), QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))

        outline_pairs = [
            ("head", "neck"), ("neck", "spine"), ("spine", "pelvis"),
            ("neck", "l_sh"), ("l_sh", "l_el"), ("l_el", "l_wr"),
            ("neck", "r_sh"), ("r_sh", "r_el"), ("r_el", "r_wr"),
            ("pelvis", "l_hip"), ("l_hip", "l_kn"), ("l_kn", "l_an"),
            ("pelvis", "r_hip"), ("r_hip", "r_kn"), ("r_kn", "r_an"),
        ]
        for pen in pen_layers:
            for a, b in outline_pairs:
                scene.addLine(pts[a][0], pts[a][1], pts[b][0], pts[b][1], pen)
    except Exception as e:
        print(f"Error drawing neon silhouette: {e}")

def draw_styled_box(
    scene: QGraphicsScene,
    left_x: float,
    top_y: float,
    right_x: float,
    bottom_y: float,
    base_color: QtGui.QColor,
    style: int = 0,
    thickness: int = 2,
    opacity: int = 220,
    fill: bool = False,
    fill_alpha_pct: int = 25,
    fill_gradient: bool = True,
):
    try:
        if right_x <= left_x or bottom_y <= top_y:
            return
        width = right_x - left_x
        height = bottom_y - top_y

        pen_color = QtGui.QColor(base_color)
        pen_color.setAlpha(max(0, min(255, int(opacity))))
        pen = QtGui.QPen(pen_color, max(1, int(thickness)))

        if fill:
            alpha = max(0, min(100, int(fill_alpha_pct)))
            fill_alpha = int(255 * (alpha / 100.0))
            if fill_gradient:
                grad = QtGui.QLinearGradient(QtCore.QPointF(left_x, top_y), QtCore.QPointF(right_x, bottom_y))
                c1 = QtGui.QColor(base_color); c1.setAlpha(fill_alpha)
                c2 = QtGui.QColor(base_color); c2.setAlpha(int(fill_alpha * 0.5))
                grad.setColorAt(0.0, c1); grad.setColorAt(1.0, c2)
                brush = QtGui.QBrush(grad)
            else:
                brush_color = QtGui.QColor(base_color)
                brush_color.setAlpha(fill_alpha)
                brush = QtGui.QBrush(brush_color)
        else:
            brush = QtCore.Qt.NoBrush

        if style == 0:
            # Классический прямоугольник
            scene.addRect(QtCore.QRectF(left_x, top_y, width, height), pen, brush)
            return

        if style == 1:
            # Угловой бокс: рисуем углы; опционально полупрозрачная заливка
            corner_len = max(4.0, min(width, height) * 0.25)
            # TL
            scene.addLine(left_x, top_y, left_x + corner_len, top_y, pen)
            scene.addLine(left_x, top_y, left_x, top_y + corner_len, pen)
            # TR
            scene.addLine(right_x - corner_len, top_y, right_x, top_y, pen)
            scene.addLine(right_x, top_y, right_x, top_y + corner_len, pen)
            # BL
            scene.addLine(left_x, bottom_y, left_x + corner_len, bottom_y, pen)
            scene.addLine(left_x, bottom_y - corner_len, left_x, bottom_y, pen)
            # BR
            scene.addLine(right_x - corner_len, bottom_y, right_x, bottom_y, pen)
            scene.addLine(right_x, bottom_y - corner_len, right_x, bottom_y, pen)
            if fill:
                scene.addRect(QtCore.QRectF(left_x, top_y, width, height), QtGui.QPen(QtCore.Qt.NoPen), brush)
            return

        if style == 2:
            # Капсула (скруглённый прямоугольник с большим радиусом)
            path = QtGui.QPainterPath()
            radius = max(2.0, min(width, height) / 2.0)
            path.addRoundedRect(QtCore.QRectF(left_x, top_y, width, height), radius, radius)
            scene.addPath(path, pen, brush)
            return
    except Exception as e:
        print(f"Error drawing styled box: {e}")

def esp_main(shutdown_event):
    # Жёсткая блокировка: после истечения срока показываем только уведомление
        # удалено: проверка истечения срока
    settings = enforce_license_gating(verify_license_settings(load_settings()))
    _set_win_app_id("BLACKSCOPE.ESP")
    app = QtWidgets.QApplication(sys.argv)
    _apply_app_icon(app)
    # Рисуем всплывающие цифры урона и чистим устаревшие
    try:
        now = time.time()
        lifetime = 1.2
        keep = []
        for item in _DAMAGE_FLOATS:
            t = now - item.get("t0", now)
            if 0 <= t <= lifetime:
                dy = -40 * (t / lifetime)
                alpha = int(255 * (1.0 - t / lifetime))
                txt = scene.addText(f"-{item['value']}", QtGui.QFont('Segoe UI', 10, QtGui.QFont.Bold))
                txt.setDefaultTextColor(QtGui.QColor(255, 80, 80, max(0, min(255, alpha))))
                txt.setPos(item['x'], item['y'] + dy)
                keep.append(item)
        _DAMAGE_FLOATS[:] = keep
    except Exception:
        pass
    # Проверяем, запущена ли игра CS2
    cs2_found = False
    try:
        # Пытаемся найти процесс CS2
        print("Поиск процесса CS2...")
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                pm = pymem.Pymem("cs2.exe")
                client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
                cs2_found = True
                print("CS2 найден!")
                break
            except Exception:
                if attempt < max_attempts - 1:
                    print(f"Попытка {attempt+1}/{max_attempts} не удалась, повторяем...")
                    time.sleep(0.5)
                else:
                    print("CS2 не найден после нескольких попыток.")
        
        if cs2_found:
            # Пытаемся создать окно ESP только если игра запущена
            window = ESPWindow(settings, shutdown_event=shutdown_event)
            _apply_app_icon(app, window)
            window.show()
            sys.exit(app.exec())
        else:
            raise Exception("CS2 не запущен")
    except Exception as e:
        print(f"Ошибка при запуске ESP: {e}")
        # Если игра не запущена, создаем простое окно с сообщением
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        # Определяем язык из настроек
        try:
            _settings_lang = load_settings().get("language", "en")
        except Exception:
            _settings_lang = "en"
        def _t3(en: str, ru: str, uk: str) -> str:
            return en if _settings_lang == "en" else (ru if _settings_lang == "ru" else uk)
        def _tr(base_ru: str) -> str:
            mapping = {
                "CS2 не запущен или не найден": ("CS2 is not running or not found", "CS2 не запущений або не знайдений"),
                "Запустите игру и перезапустите программу": ("Start the game and restart the application", "Запустіть гру та перезапустіть програму"),
                "Если игра запущена, возможные причины:": ("If the game is running, possible causes:", "Якщо гра запущена, можливі причини:"),
                "• Антивирус блокирует доступ\n• FACEIT AC активен\n• GameGuardian AC активен": ("• Antivirus blocking access\n• FACEIT AC is active\n• GameGuardian AC is active", "• Антивірус блокує доступ\n• FACEIT AC активний\n• GameGuardian AC активний"),
                "Отключите проверку в реальном времени или весь антивирус, а также деактивируйте античиты": ("Disable real-time protection or entire antivirus, and deactivate anti-cheats", "Вимкніть перевірку в реальному часі або весь антивірус, а також деактивуйте античіти")
            }
            if base_ru in mapping:
                en, uk = mapping[base_ru]
                return base_ru if _settings_lang == "ru" else (en if _settings_lang == "en" else uk)
            return base_ru
        # Create styled error window
        error_window = QtWidgets.QWidget()
        error_window.setWindowTitle(_t3("BLACKSCOPE - Error", "BLACKSCOPE - Ошибка", "BLACKSCOPE - Помилка"))
        error_window.setFixedSize(520, 420)
        error_window.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        error_window.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Main container with styling
        container = QtWidgets.QFrame(error_window)
        container.setObjectName("ErrorContainer")
        container.setGeometry(0, 0, 520, 420)
        
        # Title bar
        title_bar = QtWidgets.QFrame(container)
        title_bar.setObjectName("ErrorTitleBar")
        title_bar.setGeometry(0, 0, 520, 50)
        
        title_layout = QtWidgets.QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 10, 16, 10)
        
        # Icon and title
        icon_label = QtWidgets.QLabel("●")
        icon_label.setObjectName("ErrorIcon")
        title_label = QtWidgets.QLabel("BLACKSCOPE")
        title_label.setObjectName("ErrorBrand")
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        
        # Close button
        close_btn = QtWidgets.QPushButton("✕")
        close_btn.setObjectName("ErrorCloseBtn")
        close_btn.setFixedSize(36, 36)
        close_btn.clicked.connect(error_window.close)
        close_btn.setToolTip("Закрыть")
        title_layout.addWidget(close_btn)
        
        # Content area
        content_frame = QtWidgets.QFrame(container)
        content_frame.setObjectName("ErrorContent")
        content_frame.setGeometry(0, 50, 520, 370)
        
        content_layout = QtWidgets.QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(15)
        
        # Main error title
        title_label = QtWidgets.QLabel(_tr("CS2 не запущен или не найден"))
        title_label.setObjectName("ErrorTitle")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        content_layout.addWidget(title_label)
        
        # Main instruction
        instruction_label = QtWidgets.QLabel(_tr("Запустите игру и перезапустите программу"))
        instruction_label.setObjectName("ErrorInstruction")
        instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        instruction_label.setWordWrap(True)
        content_layout.addWidget(instruction_label)
        
        # Separator line
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setObjectName("ErrorSeparator")
        content_layout.addWidget(separator)
        
        # Troubleshooting section
        trouble_title = QtWidgets.QLabel(_tr("Если игра запущена, возможные причины:"))
        trouble_title.setObjectName("ErrorTroubleTitle")
        trouble_title.setAlignment(QtCore.Qt.AlignLeft)
        content_layout.addWidget(trouble_title)
        
        # Causes list
        causes_text = _tr("• Антивирус блокирует доступ\n• FACEIT AC активен\n• GameGuardian AC активен")
        causes_label = QtWidgets.QLabel(causes_text)
        causes_label.setObjectName("ErrorCauses")
        causes_label.setAlignment(QtCore.Qt.AlignLeft)
        content_layout.addWidget(causes_label)
        
        # Solution
        solution_label = QtWidgets.QLabel(_tr("Отключите проверку в реальном времени или весь антивирус, а также деактивируйте античиты"))
        solution_label.setObjectName("ErrorSolution")
        solution_label.setAlignment(QtCore.Qt.AlignLeft)
        solution_label.setWordWrap(True)
        content_layout.addWidget(solution_label)
        
        content_layout.addStretch(1)
        
        # Apply styling
        error_window.setStyleSheet(f"""
            QFrame#ErrorContainer {{
                background: #0b0d15;
                border-radius: 20px;
                border: 1px solid #1a1f2e;
            }}
            QFrame#ErrorTitleBar {{
                background: #0a0c12;
                border-bottom: 1px solid #1a1e28;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }}
            QFrame#ErrorContent {{
                background: transparent;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }}
            QLabel#ErrorIcon {{
                font: 700 16px 'Segoe UI';
                color: #ff6b6b;
            }}
            QLabel#ErrorBrand {{
                font: 700 16px 'Segoe UI Variable Text';
                color: #ffffff;
                letter-spacing: 0.4px;
            }}
            QLabel#ErrorTitle {{
                font: 700 16px 'Segoe UI Variable Text';
                color: #ff6b6b;
                margin-bottom: 6px;
            }}
            QLabel#ErrorInstruction {{
                font: 500 14px 'Segoe UI Variable Text';
                color: #e1e5ff;
                margin-bottom: 8px;
            }}
            QFrame#ErrorSeparator {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.5 #ff6b6b, stop:1 transparent);
                height: 1px;
                border: none;
                margin: 6px 20px;
            }}
            QLabel#ErrorTroubleTitle {{
                font: 600 13px 'Segoe UI Variable Text';
                color: #f0f2ff;
                margin-bottom: 6px;
                margin-top: 4px;
            }}
            QLabel#ErrorCauses {{
                font: 500 13px 'Segoe UI Variable Text';
                color: #d4d9ef;
                margin-left: 8px;
                line-height: 1.5;
                margin-bottom: 8px;
            }}
            QLabel#ErrorSolution {{
                font: 500 12px 'Segoe UI Variable Text';
                color: #b8c2e8;
                margin-top: 8px;
                padding: 10px;
                background: rgba(90, 120, 255, 0.1);
                border-radius: 6px;
                border-left: 3px solid #5a78ff;
            }}
            QPushButton#ErrorCloseBtn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1f2e, stop:1 #121622);
                border: 1px solid #2a3248;
                border-radius: 18px;
                color: #d4d9ef;
                font: 600 14px 'Segoe UI';
            }}
            QPushButton#ErrorCloseBtn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2d1218, stop:1 #1f0c10);
                color: #ffd6db;
                border-color: #4a2028;
                transform: scale(1.05);
            }}
            QPushButton#ErrorCloseBtn:pressed {{
                background: #1a0e12;
                transform: scale(0.95);
            }}
        """)
        
        # Make window draggable
        def mousePressEvent(event):
            if event.button() == QtCore.Qt.LeftButton:
                error_window._drag_pos = event.globalPos() - error_window.frameGeometry().topLeft()
                event.accept()
        
        def mouseMoveEvent(event):
            if event.buttons() == QtCore.Qt.LeftButton and hasattr(error_window, '_drag_pos'):
                error_window.move(event.globalPos() - error_window._drag_pos)
                event.accept()
        
        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent
        
        error_window.show()
        sys.exit(app.exec())

# Trigger Bot and Aim Bot removed — keeping only ESP functionality

if __name__ == "__main__":
    # Проверка срока действия до запуска любых процессов
    # удалено: проверка истечения срока
    # Исправление для работы в скомпилированном exe
    # Используем multiprocessing.freeze_support() для корректной работы в exe
    multiprocessing.freeze_support()
    
    # Создаем событие завершения для всех процессов
    shutdown_event = multiprocessing.Event()
    
    # Запускаем конфигуратор в отдельном процессе
    # Он не зависит от наличия CS2
    process1 = multiprocessing.Process(target=configurator, args=(shutdown_event,))
    process1.daemon = True
    process1.start()
    
    # Запускаем ESP в отдельном процессе
    # ESP будет сам проверять наличие CS2 и показывать ошибку если нужно
    process2 = multiprocessing.Process(target=esp_main, args=(shutdown_event,))
    process2.daemon = True
    process2.start()

    # Если кто-то нажал закрыть в любом процессе — завершаем оба
    try:
        while process1.is_alive() or process2.is_alive():
            if shutdown_event.is_set():
                for p in (process1, process2):
                    if p.is_alive():
                        p.terminate()
                break
            time.sleep(0.2)
    except KeyboardInterrupt:
        # Обработка прерывания с клавиатуры
        shutdown_event.set()
    finally:
        # Гарантированное завершение процессов
        for p in (process1, process2):
            if p.is_alive():
                p.terminate()
        for p in (process1, process2):
            p.join()
    


