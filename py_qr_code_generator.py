# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
QR Code Generator - Enhanced Version
Features:
- Generate QR codes with customization
- Decode QR codes from images
- Batch generation
- Error correction levels
- Color customization
- Size options
"""
import sys
from pathlib import Path
import qrcode
from PIL import Image, ImageQt

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QComboBox,
    QSpinBox, QGroupBox, QColorDialog, QTextEdit, QMainWindow
)
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt


class QRGeneratorGUI(QMainWindow):
    """Enhanced QR Code Generator with GUI"""

    def __init__(self):
        """Initialize QR Generator GUI"""
        super().__init__()

        # Current QR code image
        self.current_pil_image = None
        self.current_decoded_data = None

        # Setup UI first
        self.setup_window()
        self.setup_ui()

        # Generate initial QR code AFTER UI is ready
        # Use QTimer to delay generation until after window is shown
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.generate_qr)

    def setup_window(self):
        """Setup main window properties"""
        self.setWindowTitle("QR Code Generator")
        self.resize(700, 800)

    def setup_ui(self):
        """Create user interface"""
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Mode selection (Generate/Decode)
        mode_group = QGroupBox("Mode")
        mode_layout = QHBoxLayout()
        mode_group.setLayout(mode_layout)

        self.generate_btn = QPushButton("Generate QR Code")
        self.generate_btn.setCheckable(True)
        self.generate_btn.setChecked(True)
        self.generate_btn.clicked.connect(self.switch_to_generate)
        mode_layout.addWidget(self.generate_btn)

        self.decode_btn = QPushButton("Decode QR Code")
        self.decode_btn.setCheckable(True)
        self.decode_btn.clicked.connect(self.switch_to_decode)
        mode_layout.addWidget(self.decode_btn)

        main_layout.addWidget(mode_group)

        # === GENERATE MODE WIDGETS ===
        self.generate_group = QGroupBox("Generate QR Code")
        generate_layout = QVBoxLayout()
        self.generate_group.setLayout(generate_layout)

        # Input text
        input_layout = QVBoxLayout()
        input_layout.addWidget(QLabel("Content:"))
        self.textbox = QLineEdit("https://example.com")
        self.textbox.setPlaceholderText("Enter URL or text here...")
        self.textbox.returnPressed.connect(self.generate_qr)
        input_layout.addWidget(self.textbox)
        generate_layout.addLayout(input_layout)

        # Settings
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        settings_group.setLayout(settings_layout)

        # Error correction level
        error_layout = QHBoxLayout()
        error_layout.addWidget(QLabel("Error Correction:"))
        self.error_correction_combo = QComboBox()
        self.error_correction_combo.addItem("Low (7%)", qrcode.constants.ERROR_CORRECT_L)
        self.error_correction_combo.addItem("Medium (15%)", qrcode.constants.ERROR_CORRECT_M)
        self.error_correction_combo.addItem("Quartile (25%)", qrcode.constants.ERROR_CORRECT_Q)
        self.error_correction_combo.addItem("High (30%)", qrcode.constants.ERROR_CORRECT_H)
        self.error_correction_combo.setCurrentIndex(1)  # Default to Medium
        self.error_correction_combo.currentIndexChanged.connect(self.generate_qr)
        error_layout.addWidget(self.error_correction_combo)
        error_layout.addStretch()
        settings_layout.addLayout(error_layout)

        # Size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Box Size:"))
        self.box_size_spin = QSpinBox()
        self.box_size_spin.setRange(1, 50)
        self.box_size_spin.setValue(10)
        self.box_size_spin.setToolTip("Size of each box in pixels")
        self.box_size_spin.valueChanged.connect(self.generate_qr)
        size_layout.addWidget(self.box_size_spin)

        size_layout.addWidget(QLabel("Border:"))
        self.border_spin = QSpinBox()
        self.border_spin.setRange(0, 20)
        self.border_spin.setValue(4)
        self.border_spin.setToolTip("Border size in boxes")
        self.border_spin.valueChanged.connect(self.generate_qr)
        size_layout.addWidget(self.border_spin)
        size_layout.addStretch()
        settings_layout.addLayout(size_layout)

        # Colors
        color_layout = QHBoxLayout()
        self.fg_color = QColor(0, 0, 0)  # Black
        self.bg_color = QColor(255, 255, 255)  # White

        self.fg_color_btn = QPushButton("Foreground Color")
        self.fg_color_btn.clicked.connect(self.choose_fg_color)
        self.update_color_button(self.fg_color_btn, self.fg_color)
        color_layout.addWidget(self.fg_color_btn)

        self.bg_color_btn = QPushButton("Background Color")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.update_color_button(self.bg_color_btn, self.bg_color)
        color_layout.addWidget(self.bg_color_btn)

        settings_layout.addLayout(color_layout)

        generate_layout.addWidget(settings_group)

        # Generate button
        self.btn_generate = QPushButton("Generate")
        self.btn_generate.clicked.connect(self.generate_qr)
        generate_layout.addWidget(self.btn_generate)

        main_layout.addWidget(self.generate_group)

        # === DECODE MODE WIDGETS ===
        self.decode_group = QGroupBox("Decode QR Code")
        self.decode_group.setVisible(False)
        decode_layout = QVBoxLayout()
        self.decode_group.setLayout(decode_layout)

        # Load image button
        self.load_image_btn = QPushButton("📁 Load QR Code Image")
        self.load_image_btn.clicked.connect(self.load_qr_image)
        decode_layout.addWidget(self.load_image_btn)

        # Decoded output
        decode_layout.addWidget(QLabel("Decoded Content:"))
        self.decoded_output = QTextEdit()
        self.decoded_output.setReadOnly(True)
        self.decoded_output.setPlaceholderText("Load a QR code image to decode...")
        decode_layout.addWidget(self.decoded_output)

        # Copy button
        self.copy_decoded_btn = QPushButton("📋 Copy to Clipboard")
        self.copy_decoded_btn.clicked.connect(self.copy_decoded)
        decode_layout.addWidget(self.copy_decoded_btn)

        main_layout.addWidget(self.decode_group)

        # === IMAGE DISPLAY (shared) ===
        display_group = QGroupBox("QR Code Preview")
        display_layout = QVBoxLayout()
        display_group.setLayout(display_layout)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setMinimumSize(400, 400)
        self.img_label.setStyleSheet("border: 1px solid #ccc; background: white;")
        display_layout.addWidget(self.img_label)

        main_layout.addWidget(display_group)

        # === ACTION BUTTONS (shared) ===
        action_layout = QHBoxLayout()

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.clicked.connect(self.save_qr)
        action_layout.addWidget(self.btn_save)

        self.btn_batch = QPushButton("📚 Batch Generate")
        self.btn_batch.clicked.connect(self.batch_generate)
        action_layout.addWidget(self.btn_batch)

        main_layout.addLayout(action_layout)

        # Info label
        self.info_label = QLabel("Ready to generate QR codes")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 10px; background: #f0f0f0;")
        main_layout.addWidget(self.info_label)

        self.setCentralWidget(central_widget)

    def switch_to_generate(self):
        """Switch to generate mode"""
        self.generate_btn.setChecked(True)
        self.decode_btn.setChecked(False)
        self.generate_group.setVisible(True)
        self.decode_group.setVisible(False)
        self.btn_batch.setVisible(True)
        self.info_label.setText("Generate mode active")

    def switch_to_decode(self):
        """Switch to decode mode"""
        self.generate_btn.setChecked(False)
        self.decode_btn.setChecked(True)
        self.generate_group.setVisible(False)
        self.decode_group.setVisible(True)
        self.btn_batch.setVisible(False)
        self.info_label.setText("Decode mode active - Load a QR code image")

    def update_color_button(self, button, color):
        """Update button color indicator"""
        button.setStyleSheet(
            f"background-color: {color.name()}; "
            f"color: {'white' if color.lightness() < 128 else 'black'};"
        )

    def choose_fg_color(self):
        """Choose foreground color"""
        color = QColorDialog.getColor(self.fg_color, self, "Select Foreground Color")
        if color.isValid():
            self.fg_color = color
            self.update_color_button(self.fg_color_btn, self.fg_color)
            self.generate_qr()

    def choose_bg_color(self):
        """Choose background color"""
        color = QColorDialog.getColor(self.bg_color, self, "Select Background Color")
        if color.isValid():
            self.bg_color = color
            self.update_color_button(self.bg_color_btn, self.bg_color)
            self.generate_qr()

    def generate_qr(self):
        """Generate QR code with current settings"""
        text = self.textbox.text()
        if not text:
            self.info_label.setText("Please enter some text to generate QR code")
            return

        try:
            # Create QR code with settings
            qr = qrcode.QRCode(
                version=1,
                error_correction=self.error_correction_combo.currentData(),
                box_size=self.box_size_spin.value(),
                border=self.border_spin.value(),
            )
            qr.add_data(text)
            qr.make(fit=True)

            # Generate image with colors
            qr_img = qr.make_image(
                fill_color=self.fg_color.name(),
                back_color=self.bg_color.name()
            )

            # Convert to PIL Image (in case it's not already)
            self.current_pil_image = qr_img.convert('RGB')

            # Display in GUI
            self.display_image(self.current_pil_image)

            # Update info
            self.info_label.setText(
                f"QR Code generated | "
                f"Size: {self.current_pil_image.size[0]}x{self.current_pil_image.size[1]} | "
                f"Error Correction: {self.error_correction_combo.currentText()}"
            )

        except Exception as e:
            error_msg = f"Failed to generate QR code: {str(e)}"
            self.info_label.setText(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            print(f"ERROR: {error_msg}")  # Debug output
            import traceback
            traceback.print_exc()  # Print full stack trace for debugging

    def display_image(self, pil_image):
        """Display PIL image in label"""
        try:
            # Convert PIL to QPixmap
            qt_image = ImageQt.ImageQt(pil_image)
            pixmap = QPixmap.fromImage(qt_image)

            # Scale to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.img_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.img_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error displaying image: {e}")
            import traceback
            traceback.print_exc()

    def save_qr(self):
        """Save current QR code"""
        if not self.current_pil_image:
            self.generate_qr()
            if not self.current_pil_image:
                return

        default_name = "qrcode.png"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save QR Code",
            default_name,
            "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)"
        )

        if filename:
            try:
                self.current_pil_image.save(filename)
                self.info_label.setText(f"Saved to: {filename}")
                QMessageBox.information(self, "Success", f"QR Code saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save image:\n{str(e)}")

    def load_qr_image(self):
        """Load and decode QR code from image"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open QR Code Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )

        if filename:
            try:
                # Try to decode QR code
                from pyzbar.pyzbar import decode

                img = Image.open(filename)
                decoded_objects = decode(img)

                if decoded_objects:
                    # Get first QR code
                    data = decoded_objects[0].data.decode('utf-8')
                    self.decoded_output.setPlainText(data)
                    self.current_decoded_data = data

                    # Display image
                    self.current_pil_image = img
                    self.display_image(img)

                    self.info_label.setText(f"Decoded {len(decoded_objects)} QR code(s) from: {Path(filename).name}")
                else:
                    QMessageBox.warning(self, "Error", "No QR code found in image!")
                    self.info_label.setText("No QR code detected")

            except ImportError:
                QMessageBox.critical(
                    self,
                    "Missing Library",
                    "QR code decoding requires pyzbar.\n\n"
                    "Install with: pip install pyzbar\n\n"
                    "Note: You may also need to install zbar:\n"
                    "- Windows: Download from https://sourceforge.net/projects/zbar/\n"
                    "- Linux: sudo apt-get install libzbar0\n"
                    "- macOS: brew install zbar"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to decode QR code:\n{str(e)}")

    def copy_decoded(self):
        """Copy decoded text to clipboard"""
        text = self.decoded_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.info_label.setText("Copied to clipboard")
        else:
            QMessageBox.warning(self, "Error", "No decoded text to copy!")

    def batch_generate(self):
        """Generate multiple QR codes from a list"""
        # Ask for input file
        input_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input File (one entry per line)",
            "",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )

        if not input_file:
            return

        # Ask for output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )

        if not output_dir:
            return

        try:
            # Read input file
            with open(input_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            if not lines:
                QMessageBox.warning(self, "Error", "Input file is empty!")
                return

            # Generate QR codes
            output_path = Path(output_dir)
            success_count = 0

            for i, text in enumerate(lines):
                try:
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=self.error_correction_combo.currentData(),
                        box_size=self.box_size_spin.value(),
                        border=self.border_spin.value(),
                    )
                    qr.add_data(text)
                    qr.make(fit=True)

                    qr_img = qr.make_image(
                        fill_color=self.fg_color.name(),
                        back_color=self.bg_color.name()
                    )

                    # Convert to PIL Image
                    img = qr_img.convert('RGB')

                    # Save with index
                    output_file = output_path / f"qr_{i + 1:04d}.png"
                    img.save(output_file)
                    success_count += 1

                except Exception as e:
                    print(f"Failed to generate QR code for line {i + 1}: {e}")

            QMessageBox.information(
                self,
                "Batch Complete",
                f"Successfully generated {success_count} out of {len(lines)} QR codes\n"
                f"Saved to: {output_dir}"
            )
            self.info_label.setText(f"Batch: {success_count}/{len(lines)} QR codes generated")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Batch generation failed:\n{str(e)}")


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = QRGeneratorGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
    