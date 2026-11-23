"""Textos de la interfaz de BASIC PicoCalc Emulator.

No traduce el lenguaje BASIC ni la salida de los programas.
No depende de Qt y puede probarse independientemente.
"""

LANGUAGES = ("es", "en")
DEFAULT_LANGUAGE = "es"

TRANSLATIONS = {
    "es": {
        # Menús principales
        "menu.file": "Archivo",
        "menu.drives": "Unidades",
        "menu.libraries": "Bibliotecas",
        "menu.view": "Ver",
        "menu.help": "Ayuda",

        # Archivo
        "file.open": "Abrir programa .BAS...",
        "file.edit": "Editar BASIC",
        "file.run": "Ejecutar",
        "file.stop": "Detener",
        "file.transcript": "Ver / copiar transcripción...",
        "file.exit": "Salir",

        # Unidades y bibliotecas
        "drives.flash": "Montar A: (Flash)...",
        "drives.sd": "Montar B: (tarjeta SD)...",
        "libraries.attach": "Adjuntar biblioteca .BAS...",

        # Vistas e idioma
        "view.vertical": "Skin vertical",
        "view.horizontal": "Skin horizontal",
        "view.large": "Pantalla 2× (sin teclado)",
        "view.compact": "Pantalla 1× (sin teclado)",
        "view.language": "Idioma",
        "language.es": "Español",
        "language.en": "English",

        # Ayuda
        "help.guide_title": "Cómo usar BASIC PicoCalc Emulator",
        "help.guide_body": """BASIC PICOCALC EMULATOR - GUÍA DE USO

1. VISTAS
En Ver podés elegir entre las cuatro skins fotográficas:
vertical, horizontal, pantalla 1× sin teclado y
pantalla 2× sin teclado.
La pantalla virtual mantiene las proporciones originales.

2. ABRIR PROGRAMAS
Archivo → Abrir programa .BAS permite cargar un archivo.
También podés utilizar LOAD desde BASIC con las unidades
virtuales correctamente montadas.

3. EJECUTAR Y DETENER
Archivo → Ejecutar inicia el programa cargado.
Archivo → Detener o el botón STOP interrumpen la ejecución.
Ctrl+C permite detener BASIC durante la ejecución.

4. EDITOR BASIC
Archivo → Editar BASIC abre el editor del programa en memoria.
Ctrl+Enter aplica los cambios; Esc cancela.
Aplicar los cambios NO guarda automáticamente el archivo.
Usá SAVE cuando necesites conservarlos.

5. UNIDADES VIRTUALES
Desde Unidades podés montar A: (Flash) y B: (tarjeta SD).
El emulador utiliza carpetas de Linux como unidades virtuales.
Los programas pueden utilizar rutas BASIC como A:/ y B:/.

6. BIBLIOTECAS
Bibliotecas → Adjuntar biblioteca .BAS permite incorporar
código BASIC adicional al entorno de ejecución.

7. TECLADO Y ENTRADA
Podés escribir con el teclado de la computadora.
En las skins con teclado también podés pulsar sus teclas
con el mouse. Las teclas de función y de dirección están
integradas al entorno emulado.

8. VOLUMEN
Las flechas situadas en el borde de la PicoCalc permiten
subir o bajar el volumen en pasos del 5 %.
La preferencia queda guardada entre sesiones.
El ajuste durante la reproducción depende del sistema de audio.

9. IDIOMA
Ver → Idioma permite cambiar entre Español y English.
La selección se aplica inmediatamente y queda guardada.
Los comandos BASIC no se traducen.

10. TRANSCRIPCIÓN
Archivo → Ver / copiar transcripción permite consultar
la transcripción auxiliar de la sesión.

COMPATIBILIDAD
El entorno busca reproducir el comportamiento de MMBasic
en PicoCalc. No todas sus funciones están necesariamente
implementadas. Los programas destinados al dispositivo
deben comprobarse también en una PicoCalc física.
""",
        "about.body": """BASIC PicoCalc Emulator {version}

Emulador e intérprete independiente para ejecutar y
desarrollar programas BASIC compatibles con PicoCalc/MMBasic.

Desarrollo: Ariel Palazzesi
Colaboración técnica: ChatGPT (OpenAI)

Pantalla virtual: 320 × 320 píxeles.
Cuatro interfaces fotográficas y editor BASIC integrado.

Proyecto independiente y no oficial.
No está afiliado a los fabricantes de PicoCalc ni a
los responsables del firmware MMBasic/PicoMite.

Agradecimientos a la comunidad PicoCalc y a los autores
de proyectos abiertos que contribuyen a este ecosistema.

La compatibilidad debe verificarse con el hardware real.
Las licencias y atribuciones de componentes de terceros
se documentarán antes de la publicación pública.
""",
        "status.mounts_unavailable": "Montajes no disponibles: {details}",
        "status.sd_auto_fixed": "B: corregida a la raíz de la tarjeta SD (carpeta superior a bas/)",
        "status.last_program_missing": "Último programa no disponible: {path}",
        "status.flash_mounted": "A: montada en {path}",
        "status.sd_adjusted": "B: ajustada a la raíz SD: {path}",
        "status.sd_mounted": "B: montada en {path}",
        "status.remember_failed": "No se pudo recordar el BAS: {error}",
        "status.running": "RUN — teclas para INKEY$, Ctrl+C para STOP",
        "status.volume_failed": "Volumen: {volume}% guardado; no se pudo cambiar el audio actual",
        "status.volume_no_pactl": "Volumen: {volume}% guardado (instalar pulseaudio-utils para ajuste en vivo)",
        "status.volume_applying": "Volumen: {volume}% (aplicando...)",
        "status.active_drive": "Unidad activa: {path}",
        "status.current_directory": "Directorio actual: {path}",
        "status.editor_applied": "Editor: cambios aplicados a memoria (sin guardar)",
        "dialog.preferences": "Preferencias",
        "dialog.load_failed": "No se pudo cargar",
        "error.save_mounts": "No se pudieron guardar las unidades: {error}",
        "error.save_library": "No se pudo guardar la biblioteca: {error}",
        "help.user_guide": "Cómo usar el emulador...",
        "help.environment": "Información del entorno...",
        "help.about": "Acerca de BASIC PicoCalc Emulator...",

        # Editor
        "editor.title": "Editor BASIC · programa en memoria",
        "editor.heading": "EDITOR BASIC / Ctrl+Enter: aplicar · Esc: cancelar",
        "editor.cancel": "Cancelar",
        "editor.apply": "Aplicar a memoria",
        "editor.position": "Línea {line} · Columna {column}",

        # Diálogos y controles
        "common.close": "Cerrar",
        "common.cancel": "Cancelar",
        "common.open": "Abrir",
        "common.save": "Guardar",
        "dialog.open_basic": "Abrir BASIC",
        "dialog.mount_flash": "Seleccionar raíz flash virtual (A:)",
        "dialog.mount_sd": "Seleccionar raíz de SD virtual (B:)",
        "dialog.attach_library": "Adjuntar biblioteca BAS",
        "dialog.transcript": "Transcripción de salida BASIC",
        "dialog.environment": "Información del entorno",
        "dialog.about": "Acerca de BASIC PicoCalc Emulator",

        # Mensajes de aplicación
        "status.volume_saved": "Volumen: {volume}% guardado",
        "status.volume_applied": "Volumen: {volume}% (aplicado)",
        "status.library_attached": "Biblioteca adjunta: {name}",
        "status.saved": "Guardado: {path}",
        "status.loaded": "Cargado: {path}",
        "error.stop_before_open": "Detener la ejecución antes de abrir.",
        "error.stop_before_edit": "Detené el programa antes de editar.",
        "error.missing_skin": "Falta la imagen del modo {mode}",
        "info.memory_program": "Programa en memoria (sin guardar)",
        "info.no_program": "Ningún programa cargado",
        "info.unsaved_changes": "Cambios en memoria pendientes de SAVE",
        "info.sd_card": "Tarjeta SD",
        "info.not_mounted": "Sin montar",
        "info.no_functions": "Sin asignaciones personalizadas",
        "info.none": "Ninguna",
        "info.program": "PROGRAMA",
        "info.drives": "UNIDADES VIRTUALES",
        "info.libraries": "BIBLIOTECAS ADJUNTAS",
        "info.functions": "TECLAS PROGRAMADAS",
    },
    "en": {
        # Main menus
        "menu.file": "File",
        "menu.drives": "Drives",
        "menu.libraries": "Libraries",
        "menu.view": "View",
        "menu.help": "Help",

        # File
        "file.open": "Open .BAS program...",
        "file.edit": "Edit BASIC",
        "file.run": "Run",
        "file.stop": "Stop",
        "file.transcript": "View / copy transcript...",
        "file.exit": "Exit",

        # Drives and libraries
        "drives.flash": "Mount A: (Flash)...",
        "drives.sd": "Mount B: (SD card)...",
        "libraries.attach": "Attach .BAS library...",

        # Views and language
        "view.vertical": "Vertical skin",
        "view.horizontal": "Horizontal skin",
        "view.large": "2× display (no keyboard)",
        "view.compact": "1× display (no keyboard)",
        "view.language": "Language",
        "language.es": "Español",
        "language.en": "English",

        # Help
        "help.guide_title": "How to use BASIC PicoCalc Emulator",
        "help.guide_body": """BASIC PICOCALC EMULATOR - USER GUIDE

1. DISPLAY MODES
The View menu offers four photographic skins:
vertical, horizontal, 1× display without keyboard and
2× display without keyboard.
The virtual screen preserves its original proportions.

2. OPENING PROGRAMS
File → Open .BAS program loads a BASIC file.
You can also use LOAD from BASIC after mounting
the appropriate virtual drives.

3. RUNNING AND STOPPING
File → Run starts the loaded program.
File → Stop or the STOP button interrupts execution.
Ctrl+C can also stop a running BASIC program.

4. BASIC EDITOR
File → Edit BASIC opens the in-memory program editor.
Ctrl+Enter applies changes; Esc cancels.
Applying changes does NOT automatically save the file.
Use SAVE to keep your work.

5. VIRTUAL DRIVES
The Drives menu lets you mount A: (Flash) and B: (SD card).
Linux folders are used as virtual drives.
BASIC programs can access paths such as A:/ and B:/.

6. LIBRARIES
Libraries → Attach .BAS library makes additional BASIC
code available to the execution environment.

7. KEYBOARD AND INPUT
You can type using your computer keyboard.
On skins with a keyboard, you can also click the
photographic keys. Function and arrow keys are supported.

8. VOLUME
The arrows on the PicoCalc bezel adjust volume in 5% steps.
Your volume preference is saved between sessions.
Live volume adjustment depends on the system audio setup.

9. LANGUAGE
View → Language switches between Español and English.
Changes take effect immediately and are remembered.
BASIC commands are never translated.

10. TRANSCRIPT
File → View / copy transcript displays the auxiliary
transcript of your session.

COMPATIBILITY
The environment aims to reproduce MMBasic behavior
on PicoCalc. Some features may not be implemented.
Programs intended for the device should also be
tested on physical PicoCalc hardware.
""",
        "about.body": """BASIC PicoCalc Emulator {version}

Independent emulator and interpreter for developing
and running PicoCalc/MMBasic-compatible BASIC programs.

Development: Ariel Palazzesi
Technical collaboration: ChatGPT (OpenAI)

Virtual display: 320 × 320 pixels.
Four photographic interfaces and an integrated BASIC editor.

Independent, unofficial project.
Not affiliated with PicoCalc manufacturers or the
maintainers of MMBasic/PicoMite firmware.

Thanks to the PicoCalc community and the authors
of open projects contributing to this ecosystem.

Compatibility should be verified on physical hardware.
Third-party licenses and attributions will be
documented before public release.
""",
        "status.mounts_unavailable": "Unavailable mounts: {details}",
        "status.sd_auto_fixed": "B: corrected to SD card root (folder above bas/)",
        "status.last_program_missing": "Last program unavailable: {path}",
        "status.flash_mounted": "A: mounted at {path}",
        "status.sd_adjusted": "B: adjusted to SD root: {path}",
        "status.sd_mounted": "B: mounted at {path}",
        "status.remember_failed": "Could not remember BAS file: {error}",
        "status.running": "RUN — keys sent to INKEY$, Ctrl+C to STOP",
        "status.volume_failed": "Volume: {volume}% saved; could not change current audio",
        "status.volume_no_pactl": "Volume: {volume}% saved (install pulseaudio-utils for live adjustment)",
        "status.volume_applying": "Volume: {volume}% (applying...)",
        "status.active_drive": "Active drive: {path}",
        "status.current_directory": "Current directory: {path}",
        "status.editor_applied": "Editor: changes applied to memory (not saved)",
        "dialog.preferences": "Preferences",
        "dialog.load_failed": "Could not load",
        "error.save_mounts": "Could not save drives: {error}",
        "error.save_library": "Could not save library: {error}",
        "help.user_guide": "How to use the emulator...",
        "help.environment": "Environment information...",
        "help.about": "About BASIC PicoCalc Emulator...",

        # Editor
        "editor.title": "BASIC Editor · program in memory",
        "editor.heading": "BASIC EDITOR / Ctrl+Enter: apply · Esc: cancel",
        "editor.cancel": "Cancel",
        "editor.apply": "Apply to memory",
        "editor.position": "Line {line} · Column {column}",

        # Dialogs and controls
        "common.close": "Close",
        "common.cancel": "Cancel",
        "common.open": "Open",
        "common.save": "Save",
        "dialog.open_basic": "Open BASIC",
        "dialog.mount_flash": "Select virtual Flash root (A:)",
        "dialog.mount_sd": "Select virtual SD root (B:)",
        "dialog.attach_library": "Attach BAS library",
        "dialog.transcript": "BASIC output transcript",
        "dialog.environment": "Environment information",
        "dialog.about": "About BASIC PicoCalc Emulator",

        # Application messages
        "status.volume_saved": "Volume: {volume}% saved",
        "status.volume_applied": "Volume: {volume}% (applied)",
        "status.library_attached": "Library attached: {name}",
        "status.saved": "Saved: {path}",
        "status.loaded": "Loaded: {path}",
        "error.stop_before_open": "Stop execution before opening a file.",
        "error.stop_before_edit": "Stop the program before editing.",
        "error.missing_skin": "Missing image for {mode} mode",
        "info.memory_program": "Program in memory (not saved)",
        "info.no_program": "No program loaded",
        "info.unsaved_changes": "Unsaved changes in memory (SAVE pending)",
        "info.sd_card": "SD card",
        "info.not_mounted": "Not mounted",
        "info.no_functions": "No custom assignments",
        "info.none": "None",
        "info.program": "PROGRAM",
        "info.drives": "VIRTUAL DRIVES",
        "info.libraries": "ATTACHED LIBRARIES",
        "info.functions": "PROGRAMMED KEYS",
    },
}


def translate(key: str, language: str = DEFAULT_LANGUAGE, **params) -> str:
    """Obtiene un texto traducido y sustituye sus parámetros.

    Un idioma desconocido utiliza español. Una clave inexistente
    produce KeyError para detectar errores de programación.
    """
    if language not in LANGUAGES:
        language = DEFAULT_LANGUAGE

    text = TRANSLATIONS[language][key]
    return text.format(**params) if params else text
