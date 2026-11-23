"""Primera interfaz Qt: consola de texto y monitor de framebuffer.

La GUI NO interpreta sentencias BASIC. El bucle corre en un QThread;
los eventos de texto y peticiones INPUT se entregan con señales.
"""
from pathlib import Path
import shutil
import threading
import time

from PySide6.QtCore import QThread, Signal, Qt, QEvent, QTimer
from PySide6.QtGui import QImage, QPixmap, QKeyEvent, QActionGroup
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QDialog,
                               QMainWindow, QMessageBox, QPlainTextEdit, QComboBox,
                               QFrame,
                               QPushButton, QVBoxLayout, QWidget, QLineEdit)

from basic_cde import __version__
from basic_cde.core.machine import KeyboardBuffer
from basic_cde.app.session import BasicSession
from basic_cde.app.trace import run_trace, describe_program
from basic_cde.app.direct import DirectConsole, DirectCommandError, DirectExecutor
from basic_cde.app.file_listing import files_listing
from basic_cde.app.memory_report import memory_report
from basic_cde.app.history import CommandHistory
from basic_cde.app.settings import MountSettings
from basic_cde.gui.i18n import translate
from basic_cde.app.audio_volume import set_player_volume
from basic_cde.app.function_keys import key_text, split_key_input, BUILTIN_KEYS
from basic_cde.devices.drives import VirtualDrives, detect_sd_root
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay
from basic_cde.gui.keymap import mmbasic_key
from basic_cde.gui.input_gate import InputKeyGate
from basic_cde.gui.inline_input import input_anchor, input_preview
from basic_cde.gui.editor import BasicEditorDialog
from basic_cde.gui.skin import layout_for_mode, skin_asset_path, horizontal_skin_asset_path
from basic_cde.gui.skin_widget import SkinKeyboard
from basic_cde.gui.skin_keys import visual_key_for_host
from basic_cde.gui.skin_modern import (modern_skin_asset_path, modern_skin_layout,
                                        stop_button_rect)


def is_visible_frame_boundary(command):
    """Detecta el compromiso explícito del framebuffer en N visible."""
    if not command or command[0] != 'framebuffer':
        return False
    action = str(command[1]).upper()
    if action == 'MERGE':
        return True
    return action == 'COPY' and len(command) >= 4 and str(command[3]).upper() == 'N'


class ExecutionWorker(QThread):
    output = Signal(str)
    prompt = Signal(str)
    graphics = Signal(tuple)
    completed = Signal(str)
    audioPidChanged = Signal(int)
    trace = Signal(str)  # Transcripcion auxiliar, NO salida BASIC / framebuffer.

    def __init__(self, source, drives=None, libraries=(), volume=70):
        super().__init__()
        self.source = source
        self.drives = drives
        self.libraries = libraries
        self.volume = volume
        self.active_audio_pid = None
        self.frame_ack = threading.Event()
        self.stopping = threading.Event()
        self.input_ready = threading.Event()
        self.input_text = ""
        self.keyboard = KeyboardBuffer()

    def send_key(self, value):
        self.keyboard.push(value)

    def send_input(self, value):
        # La linea editada en QLineEdit ya fue consumida por INPUT.
        # No arrastrar teclas anteriores del menu (ni el ENTER del
        # formulario) a un INKEY$ posterior, como LEER_TECLA$().
        self.keyboard.clear()
        self.input_text = value
        self.input_ready.set()

    def stop(self):
        self.stopping.set()
        self.input_ready.set()

    def run(self):
        try:
            session = BasicSession.with_library_files(self.source, self.libraries,
                         keyboard=self.keyboard, drives=self.drives, volume=self.volume)
            machine = session.machine
            # Advertencias de compilacion solo en la transcripcion auxiliar.
            def emit_warnings(target_machine):
                for warning in target_machine.warnings:
                    self.trace.emit(warning + '\n')

            emit_warnings(machine)
            prior_program = session.active_path
            steps_since_yield = 0
            graphic_batch = []
            last_graphics_flush = time.monotonic()

            last_frame_presented = 0.0

            def flush_graphics(*, frame_boundary=False):
                nonlocal last_graphics_flush, last_frame_presented
                if not graphic_batch:
                    return
                # FRAMEBUFFER COPY ... ,N / MERGE son limites reales de
                # fotograma. La interfaz debe presentarlo ANTES de que el
                # motor siga dibujando otro, evitando cuadros perdidos.
                if frame_boundary:
                    self.frame_ack.clear()
                if frame_boundary:
                    self.graphics.emit(('frame_batch', tuple(graphic_batch)))
                else:
                    self.graphics.emit(('batch', tuple(graphic_batch)))
                graphic_batch.clear()
                last_graphics_flush = time.monotonic()
                if frame_boundary:
                    # Qt confirma el repintado. Ceder CPU y limitar el flujo
                    # a unos 30 cuadros/s, sin acumular una cola infinita.
                    while not self.stopping.is_set():
                        if self.frame_ack.wait(timeout=0.05):
                            break
                    elapsed = time.monotonic() - last_frame_presented
                    if elapsed < 1 / 30:
                        self.stopping.wait(1 / 30 - elapsed)
                    last_frame_presented = time.monotonic()

            while not self.stopping.is_set():
                result = session.step()
                player = session._mod_player
                pid = player.pid if player is not None and player.poll() is None else None
                if pid != self.active_audio_pid:
                    self.active_audio_pid = pid
                    self.audioPidChanged.emit(pid or 0)
                if session.active_path != prior_program:
                    prior_program = session.active_path
                    self.trace.emit(run_trace('RUN encadenado', prior_program, self.drives))
                if session.machine is not machine:
                    machine = session.machine
                    emit_warnings(machine)
                steps_since_yield += 1
                if steps_since_yield >= 500:
                    # Ceder el GIL y dar oportunidad a STOP/teclado sin bloquear GUI.
                    self.stopping.wait(0.002)
                    steps_since_yield = 0
                if result.state == "waiting_time":
                    # Despertar rapidamente al presionar STOP.
                    self.stopping.wait(0.005)
                frame_boundary = False
                if result.graphics:
                    graphic_batch.append(result.graphics)
                    frame_boundary = is_visible_frame_boundary(result.graphics)
                if frame_boundary:
                    flush_graphics(frame_boundary=True)
                now = time.monotonic()
                # Máximo ~30 fps; limite de memoria aun si una demo emite
                # muchisimas operaciones sin ceder el control del motor.
                if graphic_batch and (len(graphic_batch) >= 512 or now - last_graphics_flush >= 1/30):
                    flush_graphics()
                if result.output:
                    flush_graphics()
                    self.output.emit(result.output)
                if result.state == "finished":
                    flush_graphics()
                    session.stop_audio()
                    self.completed.emit("READY")
                    return
                if result.state == "waiting_input":
                    flush_graphics()
                    self.prompt.emit(result.prompt)
                    self.input_ready.wait()
                    self.input_ready.clear()
                    if self.stopping.is_set():
                        break
                    session.input_value(self.input_text)
            flush_graphics()
            session.stop_audio()
            self.completed.emit("STOP")
        except Exception as exc:
            if 'session' in locals():
                session.stop_audio()
            if 'flush_graphics' in locals():
                flush_graphics()
            # Si el destino falla antes de convertirse en active_path, registrar
            # tambien el RUN intentado; asi se distingue menu.bas de rpn2g.bas.
            if 'session' in locals() and session.chain_requested is not None:
                target = session.chain_target
                if target is not None:
                    self.trace.emit(run_trace('RUN destino con error', target, self.drives))
                else:
                    self.trace.emit(f'[BASIC PicoCalc Emulator] RUN destino no cargado: '
                                    f'{session.chain_requested}\n')
            self.completed.emit(f"? {exc}")


class MainWindow(QMainWindow):
    liveVolumeApplied = Signal(int, bool)
    def __init__(self, initial_program=None, *, mount_a=None, mount_b=None, libraries=()):
        super().__init__()
        self.setWindowTitle("PicoCalc BASIC")
        self.resize(760, 790)
        self.setMinimumSize(620, 450)
        self.setStyleSheet(WINDOW_STYLE)
        self.mount_settings = MountSettings()
        self.volume = self.mount_settings.load_volume()
        self.language = self.mount_settings.load_language()
        self._audio_pid = 0
        self._volume_serial = 0
        self._volume_lock = threading.Lock()
        self.liveVolumeApplied.connect(self._volume_result)
        self.drives = VirtualDrives()
        self.mount_warnings = []
        # Opciones explicitas de CLI tienen prioridad sobre preferencias guardadas.
        saved_mounts = self.mount_settings.load()
        self.auto_adjusted_sd = False
        for unit, override in (('A', mount_a), ('B', mount_b)):
            folder = override if override is not None else saved_mounts.get(unit)
            if folder:
                try:
                    if unit == 'B':
                        corrected = detect_sd_root(folder)
                        self.auto_adjusted_sd = str(corrected) != str(Path(folder).expanduser().resolve())
                        folder = corrected
                    self.drives.mount(unit, folder)
                except (BasicError, OSError) as exc:
                    self.mount_warnings.append(f'{unit}: {exc}')
        # Preferencias guardadas, mas posibles argumentos --library de CLI.
        # Si algun archivo desaparecio, se omite sin impedir el arranque.
        self.libraries = []
        for entry in [*self.mount_settings.load_libraries(), *libraries]:
            path = Path(entry).expanduser()
            if not path.is_file():
                self.mount_warnings.append(f'Biblioteca no disponible: {path}')
            elif path not in self.libraries:
                self.libraries.append(path)
        self.path = None
        self.source = ""
        self.program_dirty = False
        self.worker = None
        self.run_active = False
        self.waiting_for_input = False
        self.input_key_gate = InputKeyGate()
        self.function_keys = self.mount_settings.load_function_keys()
        self.direct = DirectConsole()
        self.command_history = CommandHistory()
        self.direct_executor = DirectExecutor(drives=self.drives)
        self.direct_ready = False
        # Guardia ante callbacks Qt reentrantes durante el reenvio de teclas.
        self._routing_ready_key = False
        self._macro_key_in_progress = None

        self.transcript = ''
        self.display = BitmapDisplay()
        self.framebuffer = self.display.framebuffer
        self.screen_scale = 2
        self.display_mode = 'skin-vertical'
        self.graphics_redraw_pending = False
        self._skin_pixmaps = {}
        self._skin_layout = layout_for_mode('vertical', 320)
        self._skin_shift = False
        self._skin_ctrl = False
        self._skin_alt = False
        self._skin_caps = False
        # La vista normal conserva su tamaño al entrar y salir del skin.
        self._plain_window_size = None

        root = QWidget()
        root.setObjectName('workbench')
        self.setCentralWidget(root)
        vertical = QVBoxLayout(root)
        # Vista compacta: menús, acciones y pantalla; sin título ni marcos.
        vertical.setContentsMargins(0,0,0,0)
        vertical.setSpacing(0)
        # Sin toolbar: el cuerpo de la ventana es la fotografia del dispositivo.

        # Única zona central: la pantalla de PicoCalc, sin panel lateral.
        lcd_column = QVBoxLayout()
        lcd_column.setSpacing(0)
        self.lcd_frame = QFrame()
        self.lcd_frame.setObjectName('lcd-frame')
        lcd_frame_layout = QVBoxLayout(self.lcd_frame)
        lcd_frame_layout.setContentsMargins(0, 0, 0, 0)
        lcd_frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_host = QWidget()
        self.display_host.setObjectName('display-host')
        self.skin_background = SkinKeyboard(self.display_host)
        self.skin_background.keyClicked.connect(self.on_skin_key_clicked)
        self.skin_background.volumeChange.connect(self.change_volume)
        self.skin_background.setScaledContents(True)
        self.skin_background.hide()
        self.screen = QLabel(self.display_host)
        self.screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen.setStyleSheet('background: #000000; border: none;')
        self.screen.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.stop_button = QPushButton('', self.display_host)
        self.stop_button.setObjectName('stop-action')
        self.stop_button.setToolTip('Detener BASIC (Ctrl+C)')
        self.stop_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_label = QLabel('STOP', self.display_host)
        self.stop_label.setObjectName('stop-caption')
        self.stop_label.setStyleSheet('color: #ffffff; background: transparent; '
                                      'font-weight: bold; font-size: 11px; border: none;')
        self.stop_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        # Área de clic sobre el conjunto completo: cuadrado rojo + STOP.
        # El botón superpuesto NO pinta: no cambia la estética del bisel.
        self.stop_hitbox = QPushButton('', self.display_host)
        self.stop_hitbox.setObjectName('stop-hitbox')
        self.stop_hitbox.setToolTip('Detener BASIC (Ctrl+C)')
        self.stop_hitbox.setAccessibleName('Detener BASIC')
        self.stop_hitbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_hitbox.setStyleSheet('QPushButton { background: transparent; border: none; padding: 0; }')
        lcd_frame_layout.addWidget(self.display_host, 0, Qt.AlignmentFlag.AlignCenter)
        lcd_column.addWidget(self.lcd_frame, 0, Qt.AlignmentFlag.AlignHCenter)
        vertical.addLayout(lcd_column, 0)
        # Sin espacio bajo la foto.

        # Editor invisible: Qt gestiona IME y Backspace; el LCD dibuja texto.
        self.command = QLineEdit(self.screen)
        self.command.setObjectName('basic-inline-input')
        self.command.setGeometry(0, 0, 1, 1)
        self.command.setStyleSheet('QLineEdit { border: none; padding: 0; '
                                   'background: transparent; color: transparent; }')
        self.command.setEnabled(False)
        self.input_anchor = None
        self.apply_display_mode()
        self.draw_framebuffer()

        # Las acciones de gestión quedan en menús, no consumen espacio de LCD.
        self.build_menus()
        self.statusBar().setObjectName('basic-status')
        self.statusBar().showMessage(
            translate('status.mounts_unavailable', self.language,
                      details='; '.join(self.mount_warnings))
            if self.mount_warnings else 'READY'
        )
        self.stop_button.clicked.connect(self.stop_run)
        self.stop_hitbox.clicked.connect(self.stop_run)
        self.command.returnPressed.connect(self.submit_input)
        self.command.textChanged.connect(self.preview_input)
        self.stop_button.setEnabled(False)
        self.stop_hitbox.setEnabled(False)
        QApplication.instance().installEventFilter(self)
        if self.auto_adjusted_sd:
            # Migrar preferencia antigua a la raiz fisica de la SD.
            # Asi CHDIR "B:/bas/juegosg" funciona tambien al salir de Sokoban.
            self.save_mounts()
            self.statusBar().showMessage(translate('status.sd_auto_fixed', self.language))
        # El argumento CLI tiene prioridad. Restaurar solo la carga, NO RUN.
        # Un archivo movido o eliminado no debe impedir abrir la ventana.
        restore = initial_program or self.mount_settings.load_last_program()
        if restore:
            candidate = Path(restore).expanduser()
            if candidate.is_file():
                self.load(candidate, remember=False)
            else:
                self.statusBar().showMessage(
                    translate('status.last_program_missing', self.language, path=candidate))
        if not self.direct_ready:
            self.show_startup_banner()
            self.activate_ready()
        self._plain_window_size = self.size()
        self.enable_skin_vertical()

    def build_menus(self):
        """Acciones de gestión apartadas de la zona de visualización."""
        menu_file = self.menuBar().addMenu('Archivo')
        self.menu_file = menu_file
        self.action_open = menu_file.addAction('Abrir programa .BAS...', self.open_file)
        self.action_edit = menu_file.addAction('Editar BASIC', self.edit_source)
        menu_file.addSeparator()
        self.action_run = menu_file.addAction('Ejecutar', self.start_run)
        self.action_stop = menu_file.addAction('Detener', self.stop_run)
        menu_file.addSeparator()
        self.action_transcript = menu_file.addAction('Ver / copiar transcripción...', self.show_transcript)
        menu_file.addSeparator()
        self.action_exit = menu_file.addAction('Salir', self.close)

        menu_drives = self.menuBar().addMenu('Unidades')
        self.menu_drives = menu_drives
        self.action_flash = menu_drives.addAction('Montar A: (Flash)...', self.mount_flash)
        self.action_sd = menu_drives.addAction('Montar B: (tarjeta SD)...', self.mount_disk)

        menu_libraries = self.menuBar().addMenu('Bibliotecas')
        self.menu_libraries = menu_libraries
        self.action_library = menu_libraries.addAction('Adjuntar biblioteca .BAS...', self.add_library)

        menu_view = self.menuBar().addMenu('Ver')
        self.menu_view = menu_view
        self.action_skin_vertical = menu_view.addAction('Skin vertical')
        self.action_skin_vertical.setCheckable(True)
        self.action_skin_vertical.triggered.connect(self.enable_skin_vertical)
        self.action_skin_horizontal = menu_view.addAction('Skin horizontal')
        self.action_skin_horizontal.setCheckable(True)
        self.action_skin_horizontal.triggered.connect(self.enable_skin_horizontal)
        menu_view.addSeparator()
        self.action_plain_2x = menu_view.addAction('Pantalla 2× (sin teclado)')
        self.action_plain_2x.setCheckable(True)
        self.action_plain_2x.triggered.connect(lambda checked=False: self.change_screen_scale_to(2))
        self.action_plain_1x = menu_view.addAction('Pantalla 1× (sin teclado)')
        self.action_plain_1x.setCheckable(True)
        self.action_plain_1x.triggered.connect(lambda checked=False: self.change_screen_scale_to(1))
        menu_view.addSeparator()
        self.menu_language = menu_view.addMenu('Idioma')
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.language_actions = {}
        for code, label in (('es', 'Español'), ('en', 'English')):
            action = self.menu_language.addAction(label)
            action.setCheckable(True)
            self.language_group.addAction(action)
            action.triggered.connect(
                lambda checked=False, lang=code: self.set_language(lang))
            self.language_actions[code] = action
        self.view_menu = menu_view
        self.refresh_view_actions()

        menu_help = self.menuBar().addMenu('Ayuda')
        self.menu_help = menu_help
        self.action_help_guide = menu_help.addAction(
            'Cómo usar el emulador...', self.show_user_guide)
        menu_help.addSeparator()
        self.action_info = menu_help.addAction(
            'Información del entorno...', self.show_info)
        self.action_about = menu_help.addAction(
            'Acerca de BASIC PicoCalc Emulator...', self.show_about)
        self.apply_language()

        # Los menús se sincronizan con el estado de ejecución real.
        self.refresh_menu_actions()

    def set_language(self, language):
        """Cambia el idioma sin reconstruir los menús ni reiniciar Qt."""
        if language not in ('es', 'en'):
            raise ValueError(f'Idioma no admitido: {language!r}')
        if language != self.language:
            self.mount_settings.save_language(language)
            self.language = language
        self.apply_language()

    def apply_language(self):
        """Actualiza los textos de las acciones Qt existentes."""
        tr = lambda key: translate(key, self.language)

        for menu, key in (
            (self.menu_file, 'menu.file'),
            (self.menu_drives, 'menu.drives'),
            (self.menu_libraries, 'menu.libraries'),
            (self.menu_view, 'menu.view'),
            (self.menu_help, 'menu.help'),
            (self.menu_language, 'view.language'),
        ):
            menu.setTitle(tr(key))

        for action, key in (
            (self.action_open, 'file.open'),
            (self.action_edit, 'file.edit'),
            (self.action_run, 'file.run'),
            (self.action_stop, 'file.stop'),
            (self.action_transcript, 'file.transcript'),
            (self.action_exit, 'file.exit'),
            (self.action_flash, 'drives.flash'),
            (self.action_sd, 'drives.sd'),
            (self.action_library, 'libraries.attach'),
            (self.action_skin_vertical, 'view.vertical'),
            (self.action_skin_horizontal, 'view.horizontal'),
            (self.action_plain_2x, 'view.large'),
            (self.action_plain_1x, 'view.compact'),
            (self.action_help_guide, 'help.user_guide'),
            (self.action_info, 'help.environment'),
            (self.action_about, 'help.about'),
        ):
            action.setText(tr(key))

        for code, action in self.language_actions.items():
            action.setText(tr('language.' + code))
            action.setChecked(code == self.language)

    def refresh_menu_actions(self):
        running = self.run_active
        for action in (self.action_open, self.action_edit, self.action_run,
                       self.action_flash, self.action_sd, self.action_library):
            action.setEnabled(not running)
        self.action_stop.setEnabled(running)

    def refresh_view_actions(self):
        if not hasattr(self, 'action_skin_vertical'):
            return
        self.action_skin_vertical.setChecked(self.display_mode == 'skin-vertical')
        self.action_skin_horizontal.setChecked(self.display_mode == 'skin-horizontal')
        self.action_plain_2x.setChecked(self.display_mode == 'skin-large')
        self.action_plain_1x.setChecked(self.display_mode == 'skin-compact')

    def apply_display_mode(self):
        """The photo occupies the body; LCD is never distorted."""
        mode = self.display_mode.removeprefix('skin-')
        if mode not in ('vertical','horizontal','large','compact'):
            mode = 'vertical'
            self.display_mode = 'skin-vertical'
        if mode not in self._skin_pixmaps:
            self._skin_pixmaps[mode] = QPixmap(modern_skin_asset_path(mode))
        pixmap = self._skin_pixmaps[mode]
        if pixmap.isNull():
            QMessageBox.warning(self, 'Skin PicoCalc',
                                translate('error.missing_skin', self.language, mode=mode))
            return
        layout = modern_skin_layout(mode)
        self._skin_layout = layout
        self.screen_scale = 2 if mode == 'large' else 1
        self.display_host.setFixedSize(layout.host_width,layout.host_height)
        self.skin_background.setGeometry(0,0,layout.host_width,layout.host_height)
        self.skin_background.set_orientation(mode)
        self.skin_background.set_picture(pixmap)
        self.skin_background.show()
        self.screen.setGeometry(layout.screen_x,layout.screen_y,
                                layout.screen_side,layout.screen_side)
        self.screen.setFixedSize(layout.screen_side,layout.screen_side)
        # Cuadrado rojo + STOP forman un unico grupo visual centrado
        # en la parte superior del bisel de todas las fotografias.
        _, by, side = stop_button_rect(mode)
        if mode == 'large':
            by = max(2, by - 5)  # 2×: STOP más alto en el bisel superior.
        caption_width = 44
        gap = 5
        group_width = side + gap + caption_width
        bx = (layout.host_width - group_width) // 2
        self.stop_button.setGeometry(bx, by, side, side)
        self.stop_label.setGeometry(bx + side + gap, by - 2,
                                    caption_width, side + 4)
        self.stop_button.raise_()
        self.stop_label.raise_()
        # Margen mínimo de tolerancia para apuntar fácilmente con el ratón.
        self.stop_hitbox.setGeometry(bx - 3, by - 3,
                                      group_width + 6, side + 6)
        self.stop_hitbox.raise_()
        self.refresh_view_actions()

    def resize_to_skin(self):
        """Window shrinks to the photo and native menu only."""
        self.centralWidget().layout().activate()
        self.setMinimumSize(0,0)
        self.setMaximumSize(16777215,16777215)
        self.setFixedSize(self._skin_layout.host_width,
                          self._skin_layout.host_height+self.menuBar().sizeHint().height())

    def change_screen_scale_to(self,scale):
        if scale in (1,2):
            self._enable_skin('large' if scale==2 else 'compact')

    def _enable_skin(self,orientation):
        self.display_mode=f'skin-{orientation}'
        self.apply_display_mode()
        self.statusBar().hide()
        self.resize_to_skin()
        if (self.waiting_for_input or self.direct_ready) and self.input_anchor is not None:
            self.preview_input(self.command.text())
        else:
            self.draw_framebuffer()

    def enable_skin_vertical(self):
        self._enable_skin('vertical')

    def enable_skin_horizontal(self):
        self._enable_skin('horizontal')

    def info_text(self):
        """Estado real del entorno, presentado en el idioma elegido."""
        tr = lambda key: translate(key, self.language)

        if self.path is None:
            program = (tr('info.memory_program') if self.source
                       else tr('info.no_program'))
        else:
            program = str(self.path)
            if self.program_dirty:
                program += '\n' + tr('info.unsaved_changes')

        drives = []
        for unit, description in (
            ('A', 'Flash'), ('B', tr('info.sd_card'))
        ):
            root = self.drives.roots[unit]
            location = str(root) if root is not None else tr('info.not_mounted')
            drives.append(f'{unit}: ({description})\n  {location}')

        function_keys = (
            '\n'.join(
                f'F{k}: {self.function_keys[k]!r}'
                for k in sorted(self.function_keys)
            ) or tr('info.no_functions')
        )
        libraries = (
            '\n'.join(str(path) for path in self.libraries)
            if self.libraries else tr('info.none')
        )

        return (
            f"{tr('info.program')}\n{program}\n\n"
            f"{tr('info.drives')}\n{chr(10).join(drives)}\n\n"
            f"{tr('info.libraries')}\n{libraries}\n\n"
            f"{tr('info.functions')}\n{function_keys}"
        )

    def show_info(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(translate('dialog.environment', self.language))
        dialog.resize(600, 410)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit(dialog)
        text.setReadOnly(True)
        text.setPlainText(self.info_text())
        layout.addWidget(text)
        close = QPushButton(translate('common.close', self.language))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def show_user_guide(self):
        """Guía de uso del entorno, no documentación de MMBasic."""
        dialog = QDialog(self)
        dialog.setWindowTitle(
            translate('help.guide_title', self.language))
        dialog.resize(690, 550)

        layout = QVBoxLayout(dialog)
        body = QPlainTextEdit(dialog)
        body.setReadOnly(True)
        body.setPlainText(
            translate('help.guide_body', self.language))
        layout.addWidget(body)

        close = QPushButton(
            translate('common.close', self.language))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def show_about(self):
        """Información bilingüe y atribuciones del proyecto."""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(
            translate('dialog.about', self.language))
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setText(
            translate('about.body', self.language,
                      version=__version__))
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.setStyleSheet('''
            QMessageBox { background-color: #1c252b; }
            QMessageBox QLabel { color: #f3f5f6; background: transparent;
                                  font-size: 12px; }
            QMessageBox QPushButton { background: #344953; color: white;
                                     border: 1px solid #7b9aa6;
                                     padding: 5px 15px; min-width: 55px; }
            QMessageBox QPushButton:hover { background: #46636f; }
        ''')
        dialog.exec()


    def draw_framebuffer(self, snapshot=None):
        snap = self.framebuffer.snapshot() if snapshot is None else snapshot
        image = QImage(snap, self.framebuffer.width, self.framebuffer.height,
                       QImage.Format.Format_RGBA8888).copy()
        pixmap = QPixmap.fromImage(image)
        if self.screen_scale != 1:
            pixmap = pixmap.scaled(320 * self.screen_scale, 320 * self.screen_scale,
                                   Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.FastTransformation)
        self.screen.setPixmap(pixmap)

    def save_mounts(self):
        """Persistir sólo raíces montadas, sin modificar los ficheros BAS."""
        try:
            self.mount_settings.save(self.drives.roots)
        except OSError as exc:
            QMessageBox.warning(self, translate('dialog.preferences', self.language),
                                translate('error.save_mounts', self.language, error=exc))

    def mount_flash(self):
        if self.worker and self.worker.isRunning():
            return
        folder = QFileDialog.getExistingDirectory(self, translate('dialog.mount_flash', self.language))
        if folder:
            try:
                self.drives.mount('A', folder)
                self.save_mounts()
                self.statusBar().showMessage(translate('status.flash_mounted', self.language, path=folder))
            except (BasicError, OSError) as exc:
                QMessageBox.warning(self, 'Unidad A:', str(exc))

    def mount_disk(self):
        if self.worker and self.worker.isRunning():
            return
        folder = QFileDialog.getExistingDirectory(self, translate('dialog.mount_sd', self.language))
        if folder:
            try:
                corrected = detect_sd_root(folder)
                self.drives.mount('B', corrected)
                self.save_mounts()
                if str(corrected) != str(Path(folder).resolve()):
                    self.statusBar().showMessage(translate('status.sd_adjusted', self.language, path=corrected))
                else:
                    self.statusBar().showMessage(translate('status.sd_mounted', self.language, path=corrected))
            except (BasicError, OSError) as exc:
                QMessageBox.warning(self, 'Unidad B:', str(exc))

    def add_library(self):
        if self.worker and self.worker.isRunning():
            return
        filename, _ = QFileDialog.getOpenFileName(self, translate('dialog.attach_library', self.language), '', 'BASIC (*.bas *.BAS)')
        if filename:
            path = Path(filename)
            if path not in self.libraries:
                self.libraries.append(path)
                try:
                    self.mount_settings.save_libraries(self.libraries)
                    self.statusBar().showMessage(translate('status.library_attached', self.language, name=path.name))
                except OSError as exc:
                    QMessageBox.warning(self, translate('dialog.preferences', self.language),
                                        translate('error.save_library', self.language, error=exc))

    def open_file(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "BASIC", translate("error.stop_before_open", self.language))
            return
        path, _ = QFileDialog.getOpenFileName(self, translate("dialog.open_basic", self.language), "", "Programas BASIC (*.bas *.BAS);;Todos (*)")
        if path:
            self.load(Path(path))

    def show_startup_banner(self, loaded_program=None):
        """Banner de consola objetivo y version actual del emulador."""
        from basic_cde.app.console_banner import startup_lines
        # activate_ready() imprime READY exactamente una vez.
        banner = '\n'.join(startup_lines(
            linux_version=__version__.removesuffix('-dev'),
            loaded_program=loaded_program)[:-1]) + '\n'
        self.transcript = banner
        self.display.cls()
        self.display.console(banner)
        self.draw_framebuffer()

    def load(self, path, *, remember=True):
        try:
            self.source = path.read_text(encoding="utf-8-sig")
        except (UnicodeError, OSError) as exc:
            QMessageBox.warning(self,
                        translate('dialog.load_failed', self.language), str(exc))
            return
        self.path = path
        self.program_dirty = False
        if remember:
            try:
                self.mount_settings.save_last_program(path.resolve())
            except OSError as exc:
                self.statusBar().showMessage(translate('status.remember_failed', self.language, error=exc))
        # Proponer la raiz real de la SD, si el programa viene de .../bas/... .
        if self.drives.roots['B'] is None:
            for ancestor in path.parents:
                if ancestor.name.lower() == 'bas':
                    self.drives.mount('B', detect_sd_root(ancestor))
                    self.save_mounts()
                    break
        # Abrir un BAS situado en una unidad cambia el directorio de trabajo
        # del interprete a la carpeta que contiene ese programa.
        # Los paths de cada montaje siguen siendo independientes y persistentes.
        resolved = path.resolve()
        for letter in ('B', 'A'):
            root = self.drives.roots[letter]
            if root is not None and resolved.is_relative_to(root):
                self.drives.current = letter
                self.drives.cwd[letter] = resolved.parent.relative_to(root).parts
                break
        self.statusBar().showMessage(str(path))
        self.direct.source = self.source
        self.direct_executor.reset()
        self.show_startup_banner(path.name)
        self.activate_ready()

    def start_run(self):
        if not self.source:
            self.open_file()
            if not self.source: return
        if self.worker and self.worker.isRunning():
            return
        self.direct_ready = False
        self.run_active = True
        self.direct.source = self.source
        self.direct_executor.reset()
        # El registro identifica exactamente el programa inicial. No se
        # inserta este encabezado en el LCD, solo en Ver > Transcripcion.
        self.transcript = run_trace('RUN inicial', self.path, self.drives)
        if self._macro_key_in_progress is not None:
            self.transcript += (f'[BASIC PicoCalc Emulator] Activado por F'
                                f'{self._macro_key_in_progress}\n')
        if self.program_dirty:
            self.transcript += '[BASIC PicoCalc Emulator] Aviso: fuente modificada en memoria (sin SAVE)\n'
        self.input_key_gate.reset()
        # Cada RUN comienza con fuentes y estado visual nuevos.
        self.display = BitmapDisplay()
        self.framebuffer = self.display.framebuffer
        self.graphics_redraw_pending = False
        self.draw_framebuffer()
        self.command.setEnabled(False)
        self.input_anchor = None
        self.stop_button.setEnabled(True)
        self.stop_hitbox.setEnabled(True)
        self.refresh_menu_actions()
        self.worker = ExecutionWorker(self.source, drives=self.drives, libraries=tuple(self.libraries), volume=self.volume)
        self.worker.audioPidChanged.connect(self.on_audio_pid_changed)
        self.worker.output.connect(self.append_output)
        self.worker.trace.connect(self.append_trace)
        self.worker.graphics.connect(self.on_graphics)
        self.worker.prompt.connect(self.ask_input)
        self.worker.completed.connect(self.on_complete)
        self.worker.start()
        self.refresh_menu_actions()
        self.statusBar().showMessage(translate('status.running', self.language))

    def focus_ready_input(self):
        """El prompt usa un QLineEdit oculto: asegurar foco tras SHOW.

        Durante __init__ la ventana aun no es visible y setFocus() puede
        perderse cuando Qt muestra/activa la ventana por primera vez.
        """
        if self.direct_ready or self.waiting_for_input:
            self.command.setFocus(Qt.FocusReason.OtherFocusReason)

    def showEvent(self, event):
        super().showEvent(event)
        # Ejecutarlo al volver al event loop, una vez que Qt asigno focos.
        QTimer.singleShot(0, self.focus_ready_input)

    def eventFilter(self, obj, event):
        """Convierte eventos Qt a codigos PicoMite durante RUN.

        Se filtra en QApplication para captar teclas incluso cuando el foco
        esta en widgets distintos de la pantalla. INPUT sigue usando QLineEdit.
        """
        if event.type() == QEvent.Type.KeyPress and not event.isAutoRepeat():
            self.flash_host_key(event)

        # Historial del prompt de PicoMite. Debe interceptarse tambien
        # cuando el foco ya esta en QLineEdit (el filtro global lo ve).
        if (event.type() == QEvent.Type.KeyPress
                and self.direct_ready and self.isActiveWindow()
                and QApplication.activePopupWidget() is None
                and QApplication.activeModalWidget() is None
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
                and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down)):
            self.recall_command(event.key() == Qt.Key.Key_Up)
            return True

        # F1/F5..F9 son macros de consola programables. Las F2/F3/F4
        # mantienen sus atajos predefinidos de PicoMite. Nunca interceptar
        # durante RUN: alli todas las F deben llegar a INKEY$.
        if (event.type() == QEvent.Type.KeyPress
                and self.direct_ready and self.isActiveWindow()
                and QApplication.activePopupWidget() is None
                and QApplication.activeModalWidget() is None
                and not self._routing_ready_key
                and not event.isAutoRepeat()
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
                and Qt.Key.Key_F1 <= event.key() <= Qt.Key.Key_F9):
            number = int(event.key()) - int(Qt.Key.Key_F1) + 1
            macro = key_text(number, self.function_keys)
            if macro:
                self._apply_ready_macro(macro, function_number=number)
                return True

        # READY no tiene un worker en marcha. Si Qt dejo el foco en la
        # ventana, el LCD o los controles, reenviar el teclado al editor
        # invisible del framebuffer. No reenviar desde el propio editor:
        # eso causaria un bucle de eventos.
        if (event.type() == QEvent.Type.KeyPress
                and self.direct_ready and self.isActiveWindow()
                and obj is not self.command
                and QApplication.activePopupWidget() is None
                and QApplication.activeModalWidget() is None
                and not self._routing_ready_key
                and not event.modifiers() & (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.AltModifier
                    | Qt.KeyboardModifier.MetaModifier)):
            key = event.key()
            # No interceptar espacio/Enter sobre botones (activacion Qt).
            focus = QApplication.focusWidget()
            from_button = isinstance(focus, (QPushButton, QComboBox))
            printable = bool(event.text() and event.text().isprintable())
            navigation = key in (
                Qt.Key.Key_Backspace, Qt.Key.Key_Delete,
                Qt.Key.Key_Left, Qt.Key.Key_Right,
                Qt.Key.Key_Home, Qt.Key.Key_End,
                Qt.Key.Key_Return, Qt.Key.Key_Enter)
            if (printable or navigation) and not (
                from_button and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter,
                                        Qt.Key.Key_Space)):
                self.command.setFocus(Qt.FocusReason.OtherFocusReason)
                # NO reenviar por la cola de eventos Qt dentro del eventFilter
                # global: ese envio vuelve a atravesar este mismo filtro y
                # puede provocar recursion infinita en PySide6/Qt.
                # Llamar al manejador del editor directamente evita reinyectar
                # el evento en la cadena global de filtros de QApplication.
                # La guardia es adicional: returnPressed llama sincronicamente
                # a submit_direct(), que puede reconstruir el prompt READY.
                self._routing_ready_key = True
                try:
                    self.command.keyPressEvent(event)
                finally:
                    self._routing_ready_key = False
                return True

        # Pulsar el LCD vuelve a enfocar el editor de comandos / INPUT.
        if (obj is self.screen and event.type() == QEvent.Type.MouseButtonPress
                and (self.direct_ready or self.waiting_for_input)):
            QTimer.singleShot(0, self.focus_ready_input)

        if (event.type() == QEvent.Type.KeyRelease
                and self.worker is not None and self.worker.isRunning()):
            self.input_key_gate.release(
                enter=event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter))
        if (event.type() == QEvent.Type.KeyPress and self.worker is not None
                and self.worker.isRunning() and not self.waiting_for_input
                and self.isActiveWindow()):
            key = event.key()
            if not self.input_key_gate.allow_press(
                    enter=key in (Qt.Key.Key_Return, Qt.Key.Key_Enter),
                    auto_repeat=event.isAutoRepeat()):
                return True
            modifiers = event.modifiers()
            if key == Qt.Key.Key_C and modifiers & Qt.KeyboardModifier.ControlModifier:
                self.stop_run()
                return True
            value = mmbasic_key(key, modifiers, event.text(),
                                auto_repeat=event.isAutoRepeat())
            if value:
                self.worker.send_key(value)
                return True
        return super().eventFilter(obj, event)

    def _apply_ready_macro(self, macro, *, function_number=None):
        """Inserta texto de F-key en READY; CR ejecuta comandos de verdad.

        No envía QKeyEvent desde un filtro global (regresión recursiva
        0.2.26). Para instrucciones múltiples, RUN detiene la secuencia:
        la ejecución futura no recibe comandos accidentales.
        """
        self._macro_key_in_progress = function_number
        try:
            lines, remainder = split_key_input(macro)
            for line in lines:
                if not self.direct_ready:
                    return
                self.command.setText(self.command.text() + line)
                self.submit_direct()
            if self.direct_ready and remainder:
                self.command.setText(self.command.text() + remainder)
        finally:
            self._macro_key_in_progress = None

    def flash_host_key(self, event):
        """La foto muestra una pulsacion breve de la misma tecla de la PC."""
        if not self.display_mode.startswith('skin-') or not self.isActiveWindow():
            return
        if QApplication.activePopupWidget() or QApplication.activeModalWidget():
            return
        key = event.key()
        name = visual_key_for_host(key, event.text(),
                                   qt_f1=int(Qt.Key.Key_F1),
                                   qt_a=int(Qt.Key.Key_A),
                                   qt_0=int(Qt.Key.Key_0), qt_1=int(Qt.Key.Key_1))
        named = {
            Qt.Key.Key_Up: 'Up', Qt.Key.Key_Down: 'Down',
            Qt.Key.Key_Left: 'Left', Qt.Key.Key_Right: 'Right',
            Qt.Key.Key_Escape: 'Esc', Qt.Key.Key_Tab: 'Tab',
            Qt.Key.Key_CapsLock: 'CapsLock', Qt.Key.Key_Delete: 'Delete',
            Qt.Key.Key_Backspace: 'Backspace',
            Qt.Key.Key_Return: 'Enter', Qt.Key.Key_Enter: 'Enter',
            Qt.Key.Key_Space: 'Space', Qt.Key.Key_Control: 'Ctrl',
            Qt.Key.Key_Alt: 'Alt', Qt.Key.Key_Shift: 'ShiftLeft',
        }
        name = name or named.get(key)
        if name:
            self.skin_background.flash_key(name)

    def _apply_live_volume(self, pid: int, volume: int, serial: int):
        """No bloquear el hilo Qt durante las consultas pactl."""
        with self._volume_lock:
            if serial != self._volume_serial or pid != self._audio_pid:
                return
            success = set_player_volume(pid, volume)
        self.liveVolumeApplied.emit(serial, success)

    def _volume_result(self, serial: int, applied: bool):
        if serial != self._volume_serial:
            return
        if applied:
            self.statusBar().showMessage(translate('status.volume_applied', self.language, volume=self.volume))
        else:
            self.statusBar().showMessage(
                translate('status.volume_failed', self.language, volume=self.volume))

    def _request_live_volume(self):
        """La GUI puede seguir repintando mientras se ajusta la musica."""
        if not self._audio_pid:
            return
        self._volume_serial += 1
        serial = self._volume_serial
        pid, volume = self._audio_pid, self.volume
        threading.Thread(target=self._apply_live_volume,
                         args=(pid, volume, serial), daemon=True).start()

    def change_volume(self, direction):
        """El porcentaje se persiste siempre; el flujo se ajusta si existe."""
        self.volume = max(0, min(100, self.volume + 5 * int(direction)))
        self.mount_settings.save_volume(self.volume)
        if self._audio_pid:
            if shutil.which('pactl') is None:
                self.statusBar().showMessage(
                    translate('status.volume_no_pactl', self.language, volume=self.volume))
            else:
                self.statusBar().showMessage(translate('status.volume_applying', self.language, volume=self.volume))
                self._request_live_volume()
        else:
            self.statusBar().showMessage(translate('status.volume_saved', self.language, volume=self.volume))

    def on_audio_pid_changed(self, pid):
        self._audio_pid = pid
        if pid:
            # El sink puede aparecer despues de arrancar el proceso ffplay.
            QTimer.singleShot(300, lambda: self._request_live_volume()
                              if self._audio_pid == pid else None)
            QTimer.singleShot(850, lambda: self._request_live_volume()
                              if self._audio_pid == pid else None)

    def on_skin_key_clicked(self, name):
        """Clic fisico sobre una tecla: una sola entrada BASIC sin eventos globales.

        Se llama a QLineEdit.keyPressEvent directamente: nunca se usa
        la reinyeccion de eventos Qt porque causaba recursion en eventFilter.
        """
        if not self.display_mode.startswith('skin-'):
            return
        if name in ('ShiftLeft', 'ShiftRight'):
            self._skin_shift = not self._skin_shift
            return
        if name == 'Ctrl':
            self._skin_ctrl = not self._skin_ctrl
            return
        if name == 'Alt':
            self._skin_alt = not self._skin_alt
            return
        if name == 'CapsLock':
            self._skin_caps = not self._skin_caps
            return

        mods = Qt.KeyboardModifier.NoModifier
        if self._skin_shift:
            mods |= Qt.KeyboardModifier.ShiftModifier
        if self._skin_ctrl:
            mods |= Qt.KeyboardModifier.ControlModifier
        if self._skin_alt:
            mods |= Qt.KeyboardModifier.AltModifier
        special = {
            'Up': Qt.Key.Key_Up, 'Down': Qt.Key.Key_Down,
            'Left': Qt.Key.Key_Left, 'Right': Qt.Key.Key_Right,
            'Esc': Qt.Key.Key_Escape, 'Tab': Qt.Key.Key_Tab,
            'Delete': Qt.Key.Key_Delete, 'Backspace': Qt.Key.Key_Backspace,
            'Enter': Qt.Key.Key_Return, 'Space': Qt.Key.Key_Space,
        }
        # El texto tiene que representar la tecla real, no una secuencia
        # BASIC inventada. SHIFT en la foto permite acceder a F6..F10.
        if name.startswith('F') and name[1:].isdigit():
            function_number = int(name[1:]) + (5 if self._skin_shift else 0)
            qkey = int(Qt.Key.Key_F1) + function_number - 1
            typed = ''
            mods = Qt.KeyboardModifier.NoModifier
        elif name in special:
            qkey = int(special[name])
            typed = ' ' if name == 'Space' else ('\r' if name == 'Enter' else '')
        else:
            shifted = {'1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
                       '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
                       '`': '~', '/': '?', '\\': '|', '-': '_',
                       '=': '+', '[': '{', ']': '}', ',': '<', '.': '>',
                       ';': ':', "'": '"'}
            char = name
            if len(char) == 1 and char.isalpha():
                typed = char.upper() if self._skin_shift ^ self._skin_caps else char.lower()
                qkey = ord(char.upper())
            else:
                typed = shifted.get(char, char) if self._skin_shift else char
                qkey = ord(char.upper()) if len(char) == 1 else 0
        try:
            # Las teclas programadas se procesan solo en READY; INKEY$
            # mantiene los codigos especiales durante RUN.
            if self.direct_ready and (Qt.Key.Key_F1 <= qkey <= Qt.Key.Key_F9):
                macro = key_text(qkey - int(Qt.Key.Key_F1) + 1, self.function_keys)
                if macro:
                    self._apply_ready_macro(macro, function_number=qkey - int(Qt.Key.Key_F1) + 1)
                return
            if self.direct_ready and qkey in (int(Qt.Key.Key_Up), int(Qt.Key.Key_Down)):
                self.recall_command(qkey == int(Qt.Key.Key_Up))
                return
            if self.direct_ready or self.waiting_for_input:
                self.command.setFocus(Qt.FocusReason.MouseFocusReason)
                key_event = QKeyEvent(QEvent.Type.KeyPress, qkey, mods, typed)
                self.command.keyPressEvent(key_event)
            elif self.worker is not None and self.worker.isRunning():
                if qkey == int(Qt.Key.Key_C) and mods & Qt.KeyboardModifier.ControlModifier:
                    self.stop_run()
                    return
                value = mmbasic_key(qkey, mods, typed)
                if value:
                    self.worker.send_key(value)
        finally:
            # Los modificadores gráficos son de una sola pulsacion.
            self._skin_shift = False
            self._skin_ctrl = False
            self._skin_alt = False

    def append_trace(self, value):
        """Registro del entorno en la transcripcion, sin cambiar la salida BASIC."""
        self.transcript += value

    def append_output(self, value):
        self.transcript += value
        self.display.console(value)
        self.draw_framebuffer()

    def on_graphics(self, graphic):
        # El hilo BASIC ya ha ejecutado estas operaciones sobre su propia
        # pantalla. Aquí reproducimos el lote preservando el orden y solo
        # presentamos un fotograma final, en lugar de uno por PIXEL/LINE.
        commands = graphic[1] if graphic[0] in ('batch', 'frame_batch') else (graphic,)
        try:
            for command in commands:
                self.display.graphics(command)
        except (BasicError, TypeError, ValueError) as exc:
            self.append_output(f"\n? Grafico: {exc}\n")
            if self.worker:
                self.worker.stop()
        # El hilo puede producir cientos de lotes de trazos por segundo.
        # Qt no debe reconstruir/escalar el fotograma en cada lote: se
        # presenta como máximo uno cada 33 ms. Los comandos se aplican
        # inmediatamente en orden, por lo que nunca se pierde información.
        if graphic[0] == 'frame_batch':
            # El ACK se emite tras dibujar; la siguiente iteracion BASIC
            # no puede pisar este fotograma antes de que Qt lo presente.
            try:
                self.graphics_redraw_pending = False
                self.draw_framebuffer()
                # Presentar el pixmap ahora, no solo en el siguiente turno Qt.
                self.screen.repaint()
            finally:
                if self.worker is not None:
                    self.worker.frame_ack.set()
        elif not self.graphics_redraw_pending:
            self.graphics_redraw_pending = True
            QTimer.singleShot(33, self.redraw_graphics)

    def redraw_graphics(self):
        self.graphics_redraw_pending = False
        self.draw_framebuffer()

    def show_transcript(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(translate('dialog.transcript', self.language))
        dialog.resize(670, 510)
        layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(self.transcript)
        layout.addWidget(editor)
        dialog.exec()

    def ask_input(self, prompt):
        self.append_output(prompt)
        self.waiting_for_input = True
        # El prompt ya forma parte del bitmap; guardar su estado para poder
        # repintar la linea al editar sin dejar caracteres anteriores.
        self.input_anchor = input_anchor(self.display)
        self.command.clear()
        self.command.setEnabled(True)
        self.command.setFocus()
        self.preview_input('')

    def preview_input(self, value):
        if not (self.waiting_for_input or self.direct_ready) or self.input_anchor is None:
            return
        self.draw_framebuffer(input_preview(self.input_anchor, value))

    def submit_input(self):
        if self.direct_ready:
            self.submit_direct()
            return
        if not self.waiting_for_input or not self.worker: return
        text = self.command.text()
        self.waiting_for_input = False
        self.input_anchor = None
        self.append_output(text + "\n")
        self.command.clear()
        self.command.setEnabled(False)
        self.input_key_gate.after_input()
        self.worker.send_input(text)

    def stop_run(self):
        if self.worker:
            self.worker.stop()

    def on_complete(self, message):
        if message != 'READY':
            self.append_output("\n" + message + "\n")
        self.statusBar().showMessage(message)
        self.command.setEnabled(False)
        self.waiting_for_input = False
        self.input_anchor = None
        self.input_key_gate.reset()
        self.stop_button.setEnabled(False)
        self.stop_hitbox.setEnabled(False)
        self.run_active = False
        self.activate_ready()
        self.refresh_menu_actions()

    def recall_command(self, backwards):
        """Cambia solo la linea editable; no imprime otra linea en LCD."""
        current = self.command.text()
        recalled = (self.command_history.previous(current) if backwards
                    else self.command_history.next(current))
        self.command.setText(recalled)
        self.command.setCursorPosition(len(recalled))

    def activate_ready(self):
        """Mostrar READY y habilitar comandos en el propio LCD."""
        self.waiting_for_input = False
        self.direct_ready = True
        self.append_output('\nREADY\n> ')
        self.input_anchor = input_anchor(self.display)
        self.command.clear()
        self.command.setEnabled(True)
        self.command.setFocus()
        self.preview_input('')

    def submit_direct(self):
        text = self.command.text()
        self.command_history.record(text)
        self.direct_ready = False
        self.input_anchor = None
        self.command.setEnabled(False)
        self.append_output(text + '\n')
        try:
            result = self.direct.execute(text)
            if result.modified:
                self.source = self.direct.source
                if result.action == 'new':
                    self.direct_executor.reset()
                    self.path = None
                    self.program_dirty = False
                else:
                    self.program_dirty = True
            if result.message:
                self.append_output(result.message)
            if result.action == 'option_function_key':
                number, value = result.argument.split('\x00', 1)
                number = int(number)
                updated = dict(self.function_keys)
                if value:
                    updated[number] = value
                else:
                    updated.pop(number, None)
                self.mount_settings.save_function_keys(updated)
                self.function_keys = updated
            if result.action == 'memory':
                self.append_output(memory_report(
                    self.direct.source, self.direct_executor.context.variables,
                    library_size=sum(path.stat().st_size for path in self.libraries
                                     if path.exists())))
            if result.action == 'files':
                self.append_output(self.files_listing())
            if result.action == 'drive':
                self.drives.drive(result.argument)
                self.statusBar().showMessage(translate('status.active_drive', self.language,
                          path=self.drives.cwd_string))
            if result.action == 'chdir':
                self.drives.chdir(result.argument)
                self.statusBar().showMessage(translate('status.current_directory', self.language,
                          path=self.drives.cwd_string))
            if result.action == 'option_list':
                lines = [f'OPTION F{k} {self.function_keys[k]!r}'
                         for k in sorted(self.function_keys)]
                self.append_output('\n'.join(lines) + ('\n' if lines else 'Sin opciones F modificadas\n'))
            if result.action == 'immediate':
                for step in self.direct_executor.execute(result.argument):
                    if step.graphics:
                        self.on_graphics(step.graphics)
                    if step.output:
                        self.append_output(step.output)
            if result.action == 'edit':
                self.edit_source()
            if result.action == 'save':
                path = self.drives.save_program(result.argument, self.direct.source)
                self.path = path
                self.program_dirty = False
                self.statusBar().showMessage(translate('status.saved', self.language, path=path))
                self.append_output(f'Guardado: {path.name}\n')
            if result.action in ('load', 'run_file'):
                source, path = self.drives.load_program(result.argument)
                self.source = source
                self.direct.source = source
                self.direct_executor.reset()
                self.path = path
                self.program_dirty = False
                self.statusBar().showMessage(translate('status.loaded', self.language, path=path))
                self.append_trace(run_trace('LOAD', path, self.drives))
            if result.action in ('run', 'run_file'):
                self.start_run()
                return
        except (DirectCommandError, BasicError, OSError, UnicodeError) as exc:
            self.append_output(f'? {exc}\n')
        self.activate_ready()

    def files_listing(self):
        """Listado FILES con el formato textual de la PicoCalc 6.0003."""
        return files_listing(self.drives)

    def edit_source(self):
        """Abrir editor sin interferir con el filtro global del prompt READY.

        El usuario edita una copia; la fuente solo cambia cuando acepta.
        No se guarda en disco (el comando SAVE sigue siendo explícito).
        """
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, 'Editor BASIC',
                                    translate('error.stop_before_edit', self.language))
            return
        was_ready = self.direct_ready
        self.direct_ready = False
        self.command.setEnabled(False)
        dialog = BasicEditorDialog(self.direct.source, self)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated = dialog.source()
                if updated != self.direct.source:
                    self.direct.source = updated
                    self.source = updated
                    self.direct_executor.reset()
                    self.program_dirty = True
                    self.statusBar().showMessage(translate('status.editor_applied', self.language))
        finally:
            if was_ready:
                # El prompt anterior sigue en pantalla: no añadir otro READY.
                self.direct_ready = True
                self.command.setEnabled(True)
                self.input_anchor = input_anchor(self.display)
                self.command.clear()
                self.preview_input('')
                QTimer.singleShot(0, self.focus_ready_input)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(2000):
                event.ignore()
                return
        super().closeEvent(event)


def launch(initial_program=None, *, mount_a=None, mount_b=None, libraries=()):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(initial_program, mount_a=mount_a, mount_b=mount_b, libraries=libraries)
    window.show()
    return app.exec()


# Diseño independiente del motor BASIC: solo aplica a los widgets Qt.
WINDOW_STYLE = """
QMainWindow, QWidget#workbench { background: #08090a; color: #dce6f3; }
QLabel { color: #dce6f3; }
QFrame#tool-panel, QFrame#lcd-frame { background: transparent; border: none; }
QPushButton, QComboBox { color: #e3ecf7; background: #2a3749; border: 1px solid #40536b;
                         border-radius: 5px; padding: 4px 6px; font-size: 11px; font-weight: bold; }
QPushButton:hover, QComboBox:hover { background: #35475f; border-color: #6b8da8; }
QPushButton:disabled { background: #1a2431; color: #68788e; border-color: #29364a; }
QPushButton#run-action { background: #146e67; border-color: #269c90; color: #ffffff; }
QPushButton#run-action:hover { background: #188a7e; }
QPushButton#stop-action { background: #b72d31; color: white; border: 1px solid #f36b6d;
                          border-radius: 2px; padding: 0; font-size: 10px; font-weight: bold; }
QPushButton#stop-action:enabled:hover { background: #dc3338; border-color: #ff9898; }
QPushButton#stop-action:disabled { background: #421c1f; color: #855456; border: 1px solid #623338; }
QMenuBar { background: #151d29; color: #dce6f3; padding: 4px; }
QMenuBar::item:selected, QMenu::item:selected { background: #2a4659; }
QMenu { background: #1d2735; color: #dce6f3; border: 1px solid #40536b; }
QStatusBar { background: #0e141d; color: #a8bbd0; border-top: 1px solid #2b3b50; }
"""
