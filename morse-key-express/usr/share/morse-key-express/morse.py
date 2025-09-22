#!/usr/bin/env python3

import sys
import os
import time
import math
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QLabel, QDialog, QSizePolicy)
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QColor, QFont
from PyQt5.QtCore import Qt, QSize, QTimer, QByteArray, QBuffer, QIODevice
from PyQt5.QtMultimedia import QAudioFormat, QAudioOutput, QAudio

# Vendoring için gerekli olan PATH eklemesi (İPTAL EDİLDİ SQERİM ÖYLE KÜTÜPHANEYİ)
# sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))
# Not: simpleaudio artık kullanılmadığı için bu satıra gerek kalmayabilir.
# Yine de diğer kütüphaneler için tutulabilir.

import numpy as np

# Qt platform plugin sorununu çözmek için ortam değişkenlerini ayarla
# Bu ortam değişkeni ayarları gnome'da sorunsuz çalışma için gerekli
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
os.environ['QT_PLUGIN_PATH'] = ''

# Yeni About penceresi sınıfı
class AboutDialog(QDialog):
    def __init__(self, parent=None, icon_path=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(350, 450)
        
        # Renk paletini ana pencere ile aynı yap
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#2E2E2E"))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setAlignment(Qt.AlignCenter)
        
        # Program İkonu ve Adı
        icon_label = QLabel(self)
        icon_label.setAlignment(Qt.AlignCenter)
        if icon_path and os.path.exists(icon_path):
            icon_label.setPixmap(QPixmap(icon_path).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        title_label = QLabel("Morse Key Express", self)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        self.layout.addWidget(icon_label)
        self.layout.addWidget(title_label)

        # Versiyon ve diğer bilgiler
        info_text = f"""
        <p style="text-align: center;"><b>Version:</b> 1.0.1</p>
        <p style="text-align: center;"><b>Licence:</b> GNU GPLv3</p>
        <p style="text-align: center;"><b>Programming language:</b> Python3</p>
        <p style="text-align: center;"><b>GUI:</b> Qt5</p>
        <p style="text-align: center;"><b>Author:</b> A. Serhat KILIÇOĞLU</p>
        <p style="text-align: center;"><b>Github:</b> <a href="http://www.github.com/shampuan" style="color: white; text-decoration: none;">www.github.com/shampuan</a></p>
        """
        info_label = QLabel(info_text, self)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setOpenExternalLinks(True)
        self.layout.addWidget(info_label)
        
        self.layout.addSpacing(10)

        # İngilizce açıklama ve uyarı
        desc_label = QLabel("This program interprets texts into Morse code and reproduces it with sound.", self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: white;")
        desc_label.setAlignment(Qt.AlignCenter)
        
        warning_label = QLabel("This program comes with no warranty.", self)
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #FF6347; font-weight: bold;")
        warning_label.setAlignment(Qt.AlignCenter)
        
        self.layout.addWidget(desc_label)
        self.layout.addWidget(warning_label)
        
        self.setLayout(self.layout)

class MorseKeyExpressApp(QWidget):
    def __init__(self):
        super().__init__()
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.current_image_pixmap = None
        self.audio_output = None
        self.initUI()
        self.load_images()
        self.setup_connections()
        
        # Mors alfabesi sözlüğü
        self.morse_code = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
            'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
            'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
            'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
            'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
            'Z': '--..', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
            '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
            '0': '-----', ' ': ' ',
            '.': '.-.-.-',
            ',': '--..--',
            ':': '---...',
            ';': '-.-.-.',
            '-': '-....-',
            '_': '..--.-',
            '?': '..--..',
            '!': '-.-.--'
        }
        
        self.is_playing = False
        self.frequency = 650
        self.dot_duration = 0.07
        self.dash_duration = 0.2
        self.signal_gap_duration = self.dot_duration * 0.5
        self.char_gap_duration = self.dot_duration * 2.5
        self.word_gap_duration = self.dot_duration * 6
        self.sample_rate = 44100
        self.timers = []
        
        self.setup_audio_output()

    def initUI(self):
        self.setWindowTitle('Morse Key Express')
        self.setFixedSize(550, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#2E2E2E"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor("#3D3D3D"))
        palette.setColor(QPalette.Text, Qt.white)
        self.setPalette(palette)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.text_input = QTextEdit(self)
        self.text_input.setMinimumHeight(100)
        self.text_input.setStyleSheet("QTextEdit { background-color: #3D3D3D; color: white; border: 1px solid gray; padding: 5px; }")
        main_layout.addWidget(self.text_input)
        
        screen_led_layout = QHBoxLayout()
        screen_led_layout.setSpacing(10)

        self.image_label = QLabel(self)
        self.image_label.setFixedSize(489, 142)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        self.image_label.setAlignment(Qt.AlignCenter)

        self.morse_text_label = QLabel(self)
        self.morse_text_label.setFixedSize(self.image_label.size())
        self.morse_text_label.setStyleSheet("background-color: transparent; color: #2E2E2E;")
        self.morse_text_label.setFont(QFont("monospace", 10, QFont.Bold))
        self.morse_text_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.morse_text_label.setWordWrap(True)
        self.morse_text_label.setContentsMargins(15, 15, 15, 15)

        self.morse_text_label.setParent(self.image_label)
        self.morse_text_label.setGeometry(self.image_label.rect())
        
        self.led_label = QLabel(self)
        self.led_label.setFixedSize(20, 20)
        self.led_label.setAlignment(Qt.AlignCenter)
        self.led_label.setStyleSheet("background-color: transparent; border: none;")
        
        screen_led_layout.addStretch()
        screen_led_layout.addWidget(self.image_label)
        screen_led_layout.addWidget(self.led_label)
        screen_led_layout.addStretch()
        
        main_layout.addLayout(screen_led_layout)

        button_layout = QHBoxLayout()
        self.translate_button = QPushButton("Interpret", self)
        self.play_button = QPushButton("Play", self)
        self.about_button = QPushButton("About", self)
        
        button_icon_size = QSize(20, 20)
        self.translate_button.setIconSize(button_icon_size)
        self.play_button.setIconSize(button_icon_size)
        self.about_button.setIconSize(button_icon_size)
        
        button_style = "QPushButton { background-color: #3D3D3D; color: white; border: 1px solid #5A5A5A; border-radius: 5px; padding: 10px; }" \
                       "QPushButton:hover { background-color: #5A5A5A; }"
        
        self.translate_button.setStyleSheet(button_style)
        self.play_button.setStyleSheet(button_style)
        self.about_button.setStyleSheet(button_style)
        
        button_layout.addWidget(self.translate_button)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.about_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def load_images(self):
        # 1. Öncelikli olarak programın çalıştığı klasördeki 'guithings' klasörünü ara
        guithings_path = os.path.join(self.base_path, "guithings")

        # 2. Eğer bu klasör bulunamazsa, sistem yolunu dene
        if not os.path.exists(guithings_path):
            guithings_path = "/usr/share/morse-key-express/guithings"
        
        self.icon_path = os.path.join(guithings_path, "morseicon.png")
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        self.screen_off_pixmap = QPixmap(os.path.join(guithings_path, "screenoff.png"))
        self.screen_on_pixmap = QPixmap(os.path.join(guithings_path, "screenon.png"))
        
        self.led_off_pixmap = QPixmap(os.path.join(guithings_path, "LED_off.png"))
        self.led_on_pixmap = QPixmap(os.path.join(guithings_path, "LED_on.png"))

        self.interpret_icon = QIcon(os.path.join(guithings_path, "interpret.png"))
        self.play_icon = QIcon(os.path.join(guithings_path, "play.png"))
        self.about_icon = QIcon(os.path.join(guithings_path, "about.png"))
        
        if not self.interpret_icon.isNull():
            self.translate_button.setIcon(self.interpret_icon)
        if not self.play_icon.isNull():
            self.play_button.setIcon(self.play_icon)
        if not self.about_icon.isNull():
            self.about_button.setIcon(self.about_icon)


        if not self.screen_off_pixmap.isNull():
            self.current_image_pixmap = self.screen_off_pixmap.copy()
            self.image_label.setPixmap(self.current_image_pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        if not self.led_off_pixmap.isNull():
            self.led_label.setPixmap(self.led_off_pixmap.scaled(
                self.led_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def setup_audio_output(self):
        format = QAudioFormat()
        format.setSampleRate(self.sample_rate)
        format.setChannelCount(1)
        format.setSampleSize(16)
        format.setCodec("audio/pcm")
        format.setByteOrder(QAudioFormat.LittleEndian)
        format.setSampleType(QAudioFormat.SignedInt)
        
        self.audio_output = QAudioOutput(format, self)

    def setup_connections(self):
        self.translate_button.clicked.connect(self.translate_text)
        self.play_button.clicked.connect(self.play_morse)
        self.about_button.clicked.connect(self.show_about_dialog)

    def show_about_dialog(self):
        about_dialog = AboutDialog(self, icon_path=self.icon_path)
        about_dialog.exec_()

    def display_morse_on_label(self, morse_text):
        self.morse_text_label.setText(morse_text)

    def translate_text(self, text_to_translate=None):
        input_text = self.text_input.toPlainText().upper()
        translated_morse = ""
        for char in input_text:
            if char in self.morse_code:
                translated_morse += self.morse_code[char] + " "
        
        self.display_morse_on_label(translated_morse.strip())

    def get_wave_data(self, duration, is_tone=True):
        num_samples = int(self.sample_rate * duration)
        if is_tone:
            t = np.linspace(0., duration, num_samples, endpoint=False)
            amplitude = np.iinfo(np.int16).max * 0.5
            audio_data = amplitude * np.sin(2. * np.pi * self.frequency * t)
            audio_data = audio_data.astype(np.int16)
        else:
            audio_data = np.zeros(num_samples, dtype=np.int16)
        return audio_data

    def play_morse(self):
        if self.is_playing:
            return

        input_text = self.text_input.toPlainText().upper()
        if not input_text:
            return

        translated_morse = ""
        for char in input_text:
            if char in self.morse_code:
                translated_morse += self.morse_code[char] + " "
        
        self.display_morse_on_label(translated_morse.strip())
        
        self.is_playing = True
        self.play_button.setEnabled(False)
        self.translate_button.setEnabled(False)

        full_audio_sequence = []
        timing_events = []
        current_time = 0

        for char in input_text:
            if char == ' ':
                silence = self.get_wave_data(self.word_gap_duration, is_tone=False)
                full_audio_sequence.append(silence)
                current_time += self.word_gap_duration
                continue

            morse_char = self.morse_code.get(char, None)
            if not morse_char:
                continue
            
            for i, signal in enumerate(morse_char):
                if signal == '.':
                    tone_duration = self.dot_duration
                elif signal == '-':
                    tone_duration = self.dash_duration
                
                tone_wave = self.get_wave_data(tone_duration)
                full_audio_sequence.append(tone_wave)
                
                timing_events.append((current_time, "on"))
                current_time += tone_duration
                timing_events.append((current_time, "off"))

                if i < len(morse_char) - 1:
                    silence_duration = self.signal_gap_duration
                    silence_wave = self.get_wave_data(silence_duration, is_tone=False)
                    full_audio_sequence.append(silence_wave)
                    current_time += silence_duration

            silence_duration = self.char_gap_duration
            silence_wave = self.get_wave_data(silence_duration, is_tone=False)
            full_audio_sequence.append(silence_wave)
            current_time += silence_duration

        full_audio_array = np.concatenate(full_audio_sequence)
        audio_data = QByteArray(full_audio_array.tobytes())
        
        buffer = QBuffer(self)
        buffer.setData(audio_data)
        buffer.open(QIODevice.ReadOnly)
        
        self.audio_output.start(buffer)
        
        def handle_audio_state_change(state):
            if state == QAudio.IdleState:
                self.audio_output.stop()
                self.is_playing = False
                self.play_button.setEnabled(True)
                self.translate_button.setEnabled(True)

        self.audio_output.stateChanged.connect(handle_audio_state_change)
        
        self.start_time = time.time()
        self.timing_events = timing_events

        def update_display_logic():
            if not self.is_playing:
                return

            current_play_time = time.time() - self.start_time
            
            while self.timing_events and current_play_time >= self.timing_events[0][0]:
                event_time, event_type = self.timing_events.pop(0)
                if event_type == "on":
                    self.image_label.setPixmap(self.screen_on_pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.led_label.setPixmap(self.led_on_pixmap.scaled(self.led_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                elif event_type == "off":
                    self.image_label.setPixmap(self.screen_off_pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.led_label.setPixmap(self.led_off_pixmap.scaled(self.led_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

            QTimer.singleShot(10, update_display_logic)

        QTimer.singleShot(1, update_display_logic)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MorseKeyExpressApp()
    ex.show()
    sys.exit(app.exec_())
