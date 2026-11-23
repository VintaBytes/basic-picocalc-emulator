"""Editor de fuente BASIC independiente del intérprete.

El editor trabaja sobre una copia del texto en memoria. Aceptar aplica la
copia; cancelar no modifica ni el programa ni archivos de la SD.
"""
import re

from basic_cde.gui.i18n import translate

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QShortcut, QKeySequence
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit,
                               QPushButton, QVBoxLayout)


class BasicHighlighter(QSyntaxHighlighter):
    """Colorea comentarios, cadenas, números de línea y palabras BASIC."""

    KEYWORDS = frozenset('PRINT INPUT LINE IF THEN ELSE ELSEIF END FOR NEXT DO LOOP '
                          'WHILE WEND SELECT CASE SUB FUNCTION LOCAL STATIC GLOBAL '
                          'DIM CONST LET GOTO GOSUB RETURN EXIT RUN DATA READ RESTORE '
                          'COLOR COLOUR CLS FONT TEXT PIXEL BOX CIRCLE OPEN CLOSE '
                          'OPTION ON ERROR PAUSE'.split())

    def __init__(self, document):
        super().__init__(document)
        self.keyword = self._style('#79baff', bold=True)
        self.number = self._style('#8ed9b0')
        self.string = self._style('#e9c886')
        self.comment = self._style('#8494ab')
        self.lineno = self._style('#77d7c9', bold=True)

    @staticmethod
    def _style(color, bold=False):
        result = QTextCharFormat()
        result.setForeground(QColor(color))
        if bold:
            result.setFontWeight(QFont.Weight.Bold)
        return result

    def highlightBlock(self, text):
        # El lexer respeta comillas escapadas por duplicación y el apóstrofo
        # que inicia comentario fuera de una cadena.
        match = re.match(r'^\s*(\d+)(?=\s|$)', text)
        if match:
            self.setFormat(match.start(1), len(match.group(1)), self.lineno)
        i = 0
        while i < len(text):
            if text[i] == "'":
                self.setFormat(i, len(text)-i, self.comment)
                break
            if text[i] == '"':
                start = i
                i += 1
                while i < len(text):
                    if text[i] == '"':
                        i += 1
                        if i < len(text) and text[i] == '"':
                            i += 1
                            continue
                        break
                    i += 1
                self.setFormat(start, i-start, self.string)
                continue
            found = re.match(r'[A-Za-z_][A-Za-z_0-9]*', text[i:])
            if found:
                token = found.group()
                if token.upper() in self.KEYWORDS:
                    self.setFormat(i, len(token), self.keyword)
                i += len(token)
                continue
            i += 1


class BasicEditorDialog(QDialog):
    """Editor de texto de programa en memoria, no un editor de archivo."""

    def __init__(self, source, parent=None, language=None):
        super().__init__(parent)
        self.language = language or getattr(parent, 'language', 'es')
        tr = lambda key: translate(key, self.language)
        self.setWindowTitle(tr('editor.title'))
        self.resize(820, 650)
        self.setMinimumSize(460, 320)
        self.setModal(True)
        layout = QVBoxLayout(self)
        heading = QLabel(tr('editor.heading'))
        heading.setStyleSheet('color: #9eb0c8; font-weight: bold; padding: 4px;')
        layout.addWidget(heading)
        self.text = QPlainTextEdit()
        self.text.setObjectName('basic-source-editor')
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text.setTabStopDistance(32)
        self.text.setStyleSheet('QPlainTextEdit { background: #0b1017; color: #e6edf5; '
                                'border: 1px solid #40536b; padding: 10px; '
                                'selection-background-color: #315c80; }')
        font = QFont('DejaVu Sans Mono', 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text.setFont(font)
        self.text.setPlainText(source)
        self.highlighter = BasicHighlighter(self.text.document())
        layout.addWidget(self.text, 1)
        footer = QHBoxLayout()
        self.position = QLabel()
        self.position.setStyleSheet('color: #9eb0c8;')
        footer.addWidget(self.position)
        footer.addStretch()
        cancel = QPushButton(tr('editor.cancel'))
        apply = QPushButton(tr('editor.apply'))
        apply.setDefault(True)
        footer.addWidget(cancel)
        footer.addWidget(apply)
        layout.addLayout(footer)
        cancel.clicked.connect(self.reject)
        apply.clicked.connect(self.accept)
        self.text.cursorPositionChanged.connect(self.update_position)
        self.update_position()
        self.accept_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.accept_shortcut.activated.connect(self.accept)
        self.text.setFocus()

    def update_position(self):
        cursor = self.text.textCursor()
        self.position.setText(translate('editor.position', self.language,
                                        line=cursor.blockNumber()+1,
                                        column=cursor.positionInBlock()+1))

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.accept()
            return
        super().keyPressEvent(event)

    def source(self):
        value = self.text.toPlainText()
        # Qt no preserva el salto final de línea al editar un documento.
        return value + '\n' if value and not value.endswith('\n') else value
