"""Historial editable de comandos READY, independiente de Qt.

↑ y ↓ recorren entradas previas. Al volver al final se restaura la linea
que el usuario estaba escribiendo. No almacena datos de INPUT ni INKEY$.
"""


class CommandHistory:
    def __init__(self, limit=100):
        self.limit = limit
        self.entries = []
        self.position = None
        self.draft = ''

    def record(self, command):
        if command.strip() and (not self.entries or self.entries[-1] != command):
            self.entries.append(command)
            if len(self.entries) > self.limit:
                self.entries.pop(0)
        self.position = None
        self.draft = ''

    def previous(self, current):
        if not self.entries:
            return current
        if self.position is None:
            self.draft = current
            self.position = len(self.entries) - 1
        elif self.position > 0:
            self.position -= 1
        return self.entries[self.position]

    def next(self, current):
        if self.position is None:
            return current
        if self.position < len(self.entries) - 1:
            self.position += 1
            return self.entries[self.position]
        self.position = None
        return self.draft
