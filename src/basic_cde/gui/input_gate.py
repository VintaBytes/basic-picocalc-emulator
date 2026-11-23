"""Aislamiento del Enter que confirma INPUT respecto de INKEY$.

No depende de Qt: el widget traduce los eventos reales y este objeto
solamente decide cuándo una pulsación nueva puede llegar a BASIC.
"""


class InputKeyGate:
    """Evita que la tecla de confirmación atraviese el cambio de modo.

    El evento de pulsación de Enter ya se usó en QLineEdit. El widget
    puede cambiar a modo RUN antes de recibir KeyRelease o repeticiones
    del mismo Enter. Esos eventos no pertenecen a INKEY$.
    """

    def __init__(self):
        self.awaiting_enter_release = False

    def after_input(self):
        self.awaiting_enter_release = True

    def release(self, *, enter=False):
        if enter:
            self.awaiting_enter_release = False

    def allow_press(self, *, enter=False, auto_repeat=False):
        if not self.awaiting_enter_release:
            return True
        if enter or auto_repeat:
            return False
        # Un teclado o gestor de ventanas puede omitir el KeyRelease
        # tras desactivar QLineEdit. Otra tecla nueva es una orden BASIC
        # legítima y por eso reactivamos la lectura al verla.
        self.awaiting_enter_release = False
        return True

    def reset(self):
        self.awaiting_enter_release = False
