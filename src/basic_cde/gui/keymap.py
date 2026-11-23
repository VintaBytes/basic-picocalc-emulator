"""Traduccion de QKeyEvent a los codigos de INKEY$ de PicoMite 6.00.01.

No importa Qt Widgets: este modulo se puede probar sin iniciar QApplication.
SHIFT/CTRL solos no generan un caracter MMBasic; ALT solo genera CHR$(139).
Las combinaciones de teclas quedan sujetas a la entrega del gestor de ventanas.
"""
from PySide6.QtCore import Qt

K = Qt.Key
M = Qt.KeyboardModifier

SPECIAL = {
    K.Key_Up: 128, K.Key_Down: 129, K.Key_Left: 130, K.Key_Right: 131,
    K.Key_Insert: 132, K.Key_Home: 134, K.Key_End: 135,
    K.Key_PageUp: 136, K.Key_PageDown: 137,
    K.Key_Delete: 127, K.Key_Print: 157, K.Key_Pause: 158,
    K.Key_Return: 13, K.Key_Enter: 13,
    K.Key_Backspace: 8, K.Key_Escape: 27, K.Key_Tab: 9,
}


def mmbasic_key(key, modifiers=M.NoModifier, text="", *, auto_repeat=False):
    """Retorna un unico caracter MMBasic, o '' si no hay codigo.

    La traduccion de Ctrl+letra usa ASCII de control (1..26).
    Ctrl+C se reserva en la GUI para STOP, no pasa al interprete.
    """
    if auto_repeat and key in (K.Key_Shift, K.Key_Control, K.Key_Alt, K.Key_AltGr):
        return ""
    if modifiers & M.MetaModifier:
        return ""  # evitar atajos del escritorio anfitrion
    shifted = bool(modifiers & M.ShiftModifier)
    controlled = bool(modifiers & M.ControlModifier)
    alt = bool(modifiers & M.AltModifier)
    if key == K.Key_Alt:
        return chr(139)
    if key in (K.Key_Shift, K.Key_Control, K.Key_Meta, K.Key_AltGr):
        return ""
    if K.Key_F1 <= key <= K.Key_F12:
        if alt or controlled:
            return ""  # no definido por la tabla de este manual
        return chr(145 + int(key) - int(K.Key_F1) + (64 if shifted else 0))
    if shifted and not controlled and not alt:
        shifted_special = {K.Key_Tab:159, K.Key_Delete:160,
                           K.Key_Down:161, K.Key_Right:163}
        if key in shifted_special:
            return chr(shifted_special[key])
    if key in SPECIAL:
        if alt or controlled:
            return ""  # no atribuir modificadores no documentados
        return chr(SPECIAL[key])
    if controlled and not alt and K.Key_A <= key <= K.Key_Z:
        return chr(int(key) - int(K.Key_A) + 1)
    if alt or controlled:
        return ""
    # Para caracteres escritos dependemos de Qt y del layout del usuario.
    if text and len(text) == 1 and 32 <= ord(text) <= 255:
        return text
    return ""
