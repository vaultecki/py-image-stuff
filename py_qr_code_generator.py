# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import sys
import json
import os
from pathlib import Path  # Modernes Pfad-Handling
import qrcode
from PIL import ImageQt

# PyQt6 Imports explizit für bessere Lesbarkeit und Code-Completion
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QIcon, QPixmap


def json_file_read(filename: str) -> dict:
    """Liest eine JSON-Datei und gibt den Inhalt als Dict zurück.

    :param filename: Pfad zur Datei
    :return: Dictionary mit Daten oder leeres Dict bei Fehler
    """
    path = Path(filename)
    if not path.exists():
        print(f"Warnung: Konfigurationsdatei '{filename}' nicht gefunden.")
        return {}

    try:
        # Encoding explizit setzen für Cross-Platform Kompatibilität
        with open(path, mode='r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Fehler beim Lesen der JSON: {e}")
        return {}


class QRGuiApp:
    """QT App um QR Codes zu generieren und anzuzeigen"""

    def __init__(self):
        """QT App Init"""
        # 1. Pfad relativ zum Skript-Ort ermitteln (Robuster als getcwd)
        base_path = Path(__file__).parent
        config_path = base_path / "config" / "config.json"

        self.data = json_file_read(str(config_path))
        self.current_pil_image = None  # Zwischenspeicher für das originale PIL Bild

        # Init Qt App
        self.app = QApplication(sys.argv)  # sys.argv ist Standardpraxis
        self.main_window = QWidget()

        # Icon Setup
        icon_path = self.data.get("icon")
        if icon_path:
            # Prüfen, ob Icon existiert, oder absoluten Pfad bauen
            full_icon_path = base_path / icon_path
            if full_icon_path.exists():
                self.main_window.setWindowIcon(QIcon(str(full_icon_path)))

        self.main_window.setWindowTitle(self.data.get("main_window_name", "TGA QR Generator"))
        self.main_window.resize(400, 500)  # Startgröße definieren

        # Layout
        layout = QVBoxLayout()

        # Textbox
        default_url = self.data.get("textbox", "https://vaultcity.net")
        self.textbox = QLineEdit(default_url)
        self.textbox.setPlaceholderText("URL oder Text hier eingeben...")
        # Optional: QR Code generieren, wenn Enter gedrückt wird
        self.textbox.returnPressed.connect(self.on_click_button_gen)
        layout.addWidget(self.textbox)

        # Generate Button
        self.btn_generate = QPushButton("Generieren")
        self.btn_generate.clicked.connect(self.on_click_button_gen)
        layout.addWidget(self.btn_generate)

        # Image Label (Zentriert und ohne Verzerrung)
        self.img_label = QLabel()
        self.img_label.setScaledContents(False)
        layout.addWidget(self.img_label)

        # Save Button
        self.btn_save = QPushButton("Speichern")
        self.btn_save.clicked.connect(self.on_click_button_save)
        layout.addWidget(self.btn_save)

        # 2. Layout-Tuning: Schiebt alles nach oben zusammen
        layout.addStretch()
        self.main_window.setLayout(layout)

        # Initial generieren
        self.on_click_button_gen()

    def on_click_button_gen(self):
        """Generiert den QR Code und zeigt ihn an."""
        text = self.textbox.text()
        if not text:
            return

        try:
            # QR Code erstellen
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(text)
            qr.make(fit=True)

            # 3. Bild im Speicher halten (für Save-Funktion)
            self.current_pil_image = qr.make_image(fill_color="black", back_color="white")

            # Konvertierung für Qt Anzeige
            qt_image = ImageQt.ImageQt(self.current_pil_image)
            pixmap = QPixmap.fromImage(qt_image)

            # Label anpassen
            self.img_label.setPixmap(pixmap)
            self.img_label.adjustSize()
        except Exception as e:
            print(f"Fehler bei Generierung: {e}")

    def on_click_button_save(self):
        """Speichert den aktuell angezeigten QR Code."""
        # Falls noch kein Bild da ist, erst generieren
        if not self.current_pil_image:
            self.on_click_button_gen()
            if not self.current_pil_image: return  # Abbruch wenn immer noch leer

        default_name = self.data.get("filename", "qrcode.png")

        # Dateidialog öffnen
        filename, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "QR Code speichern",
            default_name,
            "PNG Images (*.png);;All Files (*)"
        )

        if filename:
            try:
                # 4. Das bereits generierte Bild speichern (kein neues qrcode.make nötig)
                self.current_pil_image.save(filename)
                print(f"Gespeichert unter: {filename}")
            except Exception as e:
                # User-Feedback bei Fehler (wichtig für GUI Apps)
                QMessageBox.critical(self.main_window, "Fehler", f"Konnte Bild nicht speichern:\n{e}")

    def run(self):
        """Startet die App Loop."""
        self.main_window.show()
        sys.exit(self.app.exec())


if __name__ == '__main__':
    gui = QRGuiApp()
    gui.run()
