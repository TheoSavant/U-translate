import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QPushButton,
                             QComboBox, QTextEdit, QTabWidget, QLineEdit, QHBoxLayout)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
import translation
import constants

class TranslatorApp(QWidget):
    translation_signal = pyqtSignal(str, str, str, str)
    partial_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bidirectional Whisper Translator")
        self.setGeometry(200, 200, 800, 600)

        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # -----------------------------
        # Speech Translator Tab
        # -----------------------------
        self.speech_tab = QWidget()
        speech_layout = QVBoxLayout()

        self.langA = QComboBox()
        self.langA.addItems(constants.langs.keys())
        self.langA.setCurrentText("English")
        self.langB = QComboBox()
        self.langB.addItems(constants.langs.keys())
        self.langB.setCurrentText("French")

        speech_layout.addWidget(QLabel("Language A (native):"))
        speech_layout.addWidget(self.langA)
        speech_layout.addWidget(QLabel("Language B (target):"))
        speech_layout.addWidget(self.langB)

        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        speech_layout.addWidget(self.textEdit)

        self.status_label = QLabel("Press start to begin…")
        speech_layout.addWidget(self.status_label)

        self.start_btn = QPushButton("▶️ Start Listening")
        self.stop_btn = QPushButton("⏹ Stop Listening")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        speech_layout.addLayout(btn_layout)

        self.speech_tab.setLayout(speech_layout)
        self.tabs.addTab(self.speech_tab, "Speech Translator")

        # -----------------------------
        # Text-to-Text Translator Tab
        # -----------------------------
        self.text_tab = QWidget()
        text_layout = QVBoxLayout()

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text to translate…")
        self.text_translate_btn = QPushButton("Translate")
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)

        text_layout.addWidget(QLabel("Input text:"))
        text_layout.addWidget(self.text_input)
        text_layout.addWidget(QLabel("Select languages:"))
        self.text_langA = QComboBox()
        self.text_langA.addItems(constants.langs.keys())
        self.text_langA.setCurrentText("English")
        self.text_langB = QComboBox()
        self.text_langB.addItems(constants.langs.keys())
        self.text_langB.setCurrentText("French")
        text_layout.addWidget(self.text_langA)
        text_layout.addWidget(self.text_langB)
        text_layout.addWidget(self.text_translate_btn)
        text_layout.addWidget(QLabel("Translated output:"))
        text_layout.addWidget(self.text_output)

        self.text_tab.setLayout(text_layout)
        self.tabs.addTab(self.text_tab, "Text Translator")

        # -----------------------------
        # Real-Time Transcription Tab
        # -----------------------------
        self.transcribe_tab = QWidget()
        transcribe_layout = QVBoxLayout()

        self.transcribe_lang = QComboBox()
        self.transcribe_lang.addItems(constants.langs.keys())
        self.transcribe_lang.setCurrentText("English")

        transcribe_layout.addWidget(QLabel("Select language:"))
        transcribe_layout.addWidget(self.transcribe_lang)

        self.transcribe_text = QTextEdit()
        self.transcribe_text.setReadOnly(True)
        transcribe_layout.addWidget(self.transcribe_text)

        self.start_transcribe_btn = QPushButton("▶️ Start Transcription")
        self.stop_transcribe_btn = QPushButton("⏹ Stop Transcription")
        t_btn_layout = QHBoxLayout()
        t_btn_layout.addWidget(self.start_transcribe_btn)
        t_btn_layout.addWidget(self.stop_transcribe_btn)
        transcribe_layout.addLayout(t_btn_layout)

        self.transcribe_tab.setLayout(transcribe_layout)
        self.tabs.addTab(self.transcribe_tab, "Real-Time Transcription")

        # -----------------------------
        # Signals / Slots
        # -----------------------------
        self.start_btn.clicked.connect(self.startListening)
        self.stop_btn.clicked.connect(self.stopListening)
        self.translation_signal.connect(self.update_gui)
        self.text_translate_btn.clicked.connect(self.translate_text)

        self.start_transcribe_btn.clicked.connect(self.startTranscription)
        self.stop_transcribe_btn.clicked.connect(self.stopTranscription)
        self.partial_signal.connect(self.update_partial_transcription)

        self.setLayout(layout)
        self.is_listening = False
        self.is_transcribing = False

    # -----------------------------
    # Language getters
    # -----------------------------
    def get_lang_a(self):
        return constants.langs2.get(self.langA.currentText(), "en")

    def get_lang_b(self):
        return constants.langs2.get(self.langB.currentText(), "en")

    def get_transcribe_lang(self):
        return constants.langs2.get(self.transcribe_lang.currentText(), "en")

    # -----------------------------
    # Speech Translation Functions
    # -----------------------------
    def update_status(self, translated, original, src, dest):
        self.translation_signal.emit(translated, original, src, dest)

    def update_gui(self, translated, original, src, dest):
        src_name = [k for k, v in constants.langs2.items() if v == src]
        dest_name = [k for k, v in constants.langs2.items() if v == dest]
        src_display = src_name[0] if src_name else src
        dest_display = dest_name[0] if dest_name else dest

        msg = f"Detected: {src_display}\nOriginal: {original}\n→ {dest_display}: {translated}"
        self.status_label.setText(f"Last detected: {src_display}")

        cursor = self.textEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("blue") if src_display == self.langA.currentText() else QColor("green"))
        cursor.setCharFormat(fmt)
        cursor.insertText(msg + "\n\n")
        self.textEdit.setTextCursor(cursor)
        self.textEdit.ensureCursorVisible()
        print(msg)

    def startListening(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.status_label.setText("🎤 Listening…")
        translation.threadedAndBetter2(self.get_lang_a, self.get_lang_b, self.update_status)

    def stopListening(self):
        if not self.is_listening:
            return
        translation.stopListening()
        self.is_listening = False
        self.status_label.setText("⏹ Stopped listening.")

    # -----------------------------
    # Text Translator
    # -----------------------------
    def translate_text(self):
        text = self.text_input.text().strip()
        if not text:
            return
        src = constants.langs2.get(self.text_langA.currentText(), "en")
        dest = constants.langs2.get(self.text_langB.currentText(), "en")
        try:
            translated = translation.translator.translate(text, src=src, dest=dest).text
            self.text_output.append(f"Original ({self.text_langA.currentText()}): {text}")
            self.text_output.append(f"Translated ({self.text_langB.currentText()}): {translated}\n")
            translation.enqueue_tts(translated, dest)
        except Exception as e:
            self.text_output.append(f"❌ Translation error: {e}")

    # -----------------------------
    # Real-Time Transcription Functions
    # -----------------------------
    def update_partial_transcription(self, text):
        # Append new text incrementally like live subtitles
        if not text:
            return
        current_text = self.transcribe_text.toPlainText()
        if not current_text.endswith(text):
            self.transcribe_text.append(text)
        # Scroll to bottom
        cursor = self.transcribe_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.transcribe_text.setTextCursor(cursor)
        self.transcribe_text.ensureCursorVisible()

    def startTranscription(self):
        if self.is_transcribing:
            return
        self.is_transcribing = True
        translation.threadedAndBetter2(
            lambda: self.get_transcribe_lang(),
            lambda: self.get_transcribe_lang(),
            callback=None,
            partial_callback=lambda t: self.partial_signal.emit(t)
        )

    def stopTranscription(self):
        if not self.is_transcribing:
            return
        translation.stopListening()
        self.is_transcribing = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TranslatorApp()
    window.show()
    sys.exit(app.exec_())
