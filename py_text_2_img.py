# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Data to Image Encoder - Enhanced Version with GUI
Encodes arbitrary data into images using full RGB color depth.
Features:
- Reed-Solomon error correction
- GUI interface
- Drag & drop support
- Progress indicators
- Configurable compression
"""
import sys
import struct
import zlib
import math
from pathlib import Path
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QFileDialog, QMessageBox, QComboBox,
                             QSpinBox, QProgressBar, QGroupBox, QRadioButton,
                             QButtonGroup)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent


class ReedSolomonCodec:
    """Reed-Solomon error correction codec"""

    def __init__(self, nsym=10):
        """
        Initialize Reed-Solomon codec

        Args:
            nsym: Number of error correction symbols (default: 10 bytes)
        """
        self.nsym = nsym
        try:
            from reedsolo import RSCodec
            self.rsc = RSCodec(nsym)
        except ImportError:
            raise ImportError("reedsolo library required. Install with: pip install reedsolo")

    def encode(self, data):
        """Add error correction to data"""
        return self.rsc.encode(data)

    def decode(self, data):
        """Decode and correct errors in data"""
        try:
            return self.rsc.decode(data)[0]
        except Exception as e:
            raise ValueError(f"Error correction failed: {e}")


class DataWorker(QThread):
    """Background worker for data encoding/decoding"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object, str)
    error = pyqtSignal(str)

    def __init__(self, operation, encoder, **kwargs):
        super().__init__()
        self.operation = operation
        self.encoder = encoder
        self.kwargs = kwargs

    def run(self):
        try:
            self.progress.emit(10)

            if self.operation == 'encode':
                result = self.encoder.encode(**self.kwargs)
                self.progress.emit(100)
                self.finished.emit(result, 'encode')
            elif self.operation == 'decode':
                result = self.encoder.decode(**self.kwargs)
                self.progress.emit(100)
                self.finished.emit(result, 'decode')

        except Exception as e:
            self.error.emit(str(e))


class DataImageEncoder:
    """
    Encodes data into images using full RGB color depth.
    Each pixel stores 3 bytes (one per RGB channel).
    """

    MAGIC = b'DATA'
    HEADER_SIZE = 16
    BYTES_PER_PIXEL = 3

    # Flags
    FLAG_ERROR_CORRECTION = 0x01
    FLAG_RESERVED_1 = 0x02
    FLAG_RESERVED_2 = 0x04
    FLAG_RESERVED_3 = 0x08

    def __init__(self, ecc_symbols=10):
        """
        Initialize encoder

        Args:
            ecc_symbols: Number of error correction symbols (default: 10)
        """
        self.rs_codec = ReedSolomonCodec(ecc_symbols)

    def calculate_image_size(self, data_length):
        """Calculate optimal image dimensions for given data length"""
        total_bytes = self.HEADER_SIZE + data_length
        pixels_needed = math.ceil(total_bytes / self.BYTES_PER_PIXEL)

        # Calculate square-ish dimensions (prefer 4:3 ratio)
        width = math.ceil(math.sqrt(pixels_needed * 4 / 3))
        height = math.ceil(pixels_needed / width)

        # Ensure minimum size
        width = max(width, 10)
        height = max(height, 10)

        return (width, height)

    def encode(self, data, output_path=None):
        """Encode data into an image"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        original_length = len(data)

        # Apply Reed-Solomon error correction
        encoded_data = self.rs_codec.encode(data)
        ecc_overhead = len(encoded_data) - len(data)

        # Calculate CRC32 checksum
        crc = zlib.crc32(encoded_data) & 0xFFFFFFFF

        # Create flags byte
        flags = self.FLAG_ERROR_CORRECTION

        # Create header
        header = (
                self.MAGIC +
                bytes([flags]) +
                b'\x00\x00\x00' +
                struct.pack('<I', len(encoded_data)) +
                struct.pack('<I', crc)
        )

        # Combine header + data
        full_data = header + encoded_data

        # Calculate image size
        img_size = self.calculate_image_size(len(encoded_data))

        # Create image with data
        img = self._create_image_with_data(full_data, img_size)

        # Save if path provided
        if output_path:
            img.save(output_path, 'PNG')

        # Metadata
        metadata = {
            'image_size': f"{img_size[0]}x{img_size[1]}",
            'original_data_bytes': original_length,
            'encoded_bytes': len(encoded_data),
            'ecc_overhead_bytes': ecc_overhead,
            'ecc_symbols': self.rs_codec.nsym,
            'total_bytes_with_header': len(full_data),
            'pixels_used': math.ceil(len(full_data) / self.BYTES_PER_PIXEL),
            'total_pixels': img_size[0] * img_size[1],
            'efficiency': f"{(len(full_data) / (img_size[0] * img_size[1] * 3)) * 100:.1f}%",
            'crc32': f"{crc:08X}"
        }

        return img, metadata

    def decode(self, img):
        """Extract data from an image"""
        if isinstance(img, str):
            img = Image.open(img)

        img = img.convert('RGB')
        width, height = img.size
        pixels = img.load()

        # Extract all bytes from image
        byte_array = bytearray()
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                byte_array.extend([r, g, b])

        # Extract and validate header
        if len(byte_array) < self.HEADER_SIZE:
            raise ValueError("Image too small to contain valid data!")

        magic = bytes(byte_array[:4])
        if magic != self.MAGIC:
            raise ValueError(f"Invalid magic bytes! Expected {self.MAGIC}, got {magic}")

        flags = byte_array[4]
        has_ecc = bool(flags & self.FLAG_ERROR_CORRECTION)

        if not has_ecc:
            raise ValueError("Image does not have error correction!")

        data_length = struct.unpack('<I', bytes(byte_array[8:12]))[0]
        stored_crc = struct.unpack('<I', bytes(byte_array[12:16]))[0]

        # Check if image contains enough data
        total_needed = self.HEADER_SIZE + data_length
        if len(byte_array) < total_needed:
            raise ValueError(f"Image too small! Need {total_needed} bytes, have {len(byte_array)}")

        # Extract data
        data_bytes = bytes(byte_array[self.HEADER_SIZE:self.HEADER_SIZE + data_length])

        # Verify CRC
        calculated_crc = zlib.crc32(data_bytes) & 0xFFFFFFFF
        if calculated_crc != stored_crc:
            raise ValueError(f"CRC mismatch! Data may be corrupted.")

        # Apply Reed-Solomon error correction
        try:
            decoded_data = self.rs_codec.decode(data_bytes)
        except Exception as e:
            raise ValueError(f"Error correction failed: {e}")

        # Metadata
        metadata = {
            'image_size': f"{width}x{height}",
            'decoded_bytes': len(decoded_data),
            'encoded_bytes': data_length,
            'ecc_symbols': self.rs_codec.nsym,
            'crc32': f"{stored_crc:08X}",
            'crc_valid': True
        }

        return decoded_data, metadata

    def _create_image_with_data(self, data, img_size):
        """Create image and embed data using full color depth"""
        width, height = img_size
        img = Image.new('RGB', img_size, color='white')
        pixels = img.load()

        byte_index = 0

        for y in range(height):
            for x in range(width):
                if byte_index >= len(data):
                    pixels[x, y] = (255, 255, 255)
                    continue

                r = data[byte_index] if byte_index < len(data) else 255
                byte_index += 1

                g = data[byte_index] if byte_index < len(data) else 255
                byte_index += 1

                b = data[byte_index] if byte_index < len(data) else 255
                byte_index += 1

                pixels[x, y] = (r, g, b)

        return img

    def get_capacity(self, img_size):
        """Calculate data capacity for given image size"""
        width, height = img_size
        total_pixels = width * height
        total_bytes = total_pixels * self.BYTES_PER_PIXEL
        usable_bytes = total_bytes - self.HEADER_SIZE

        ecc_overhead = self.rs_codec.nsym
        usable_data = usable_bytes - ecc_overhead

        return {
            'image_size': f"{width}x{height}",
            'total_pixels': total_pixels,
            'total_bytes': total_bytes,
            'usable_bytes': usable_bytes,
            'ecc_overhead': ecc_overhead,
            'ecc_symbols': self.rs_codec.nsym,
            'usable_data_bytes': max(0, usable_data),
            'usable_kb': f"{max(0, usable_data) / 1024:.2f} KB",
            'header_overhead': self.HEADER_SIZE
        }


class DataImageGUI(QMainWindow):
    """GUI for data to image encoding"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data to Image Encoder")
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)

        self.encoder = None
        self.worker = None
        self.current_image = None

        self.setup_ui()

    def setup_ui(self):
        """Create user interface"""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Operation mode selection
        mode_group = QGroupBox("Operation Mode")
        mode_layout = QHBoxLayout()
        mode_group.setLayout(mode_layout)

        self.mode_group = QButtonGroup()
        self.encode_radio = QRadioButton("Encode")
        self.decode_radio = QRadioButton("Decode")
        self.encode_radio.setChecked(True)
        self.mode_group.addButton(self.encode_radio)
        self.mode_group.addButton(self.decode_radio)

        mode_layout.addWidget(self.encode_radio)
        mode_layout.addWidget(self.decode_radio)
        mode_layout.addStretch()

        self.encode_radio.toggled.connect(self.on_mode_changed)

        main_layout.addWidget(mode_group)

        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        settings_group.setLayout(settings_layout)

        # ECC symbols
        ecc_layout = QHBoxLayout()
        ecc_layout.addWidget(QLabel("Error Correction Symbols:"))
        self.ecc_spin = QSpinBox()
        self.ecc_spin.setRange(2, 50)
        self.ecc_spin.setValue(10)
        self.ecc_spin.setToolTip("Number of Reed-Solomon error correction bytes")
        ecc_layout.addWidget(self.ecc_spin)
        ecc_layout.addStretch()
        settings_layout.addLayout(ecc_layout)

        main_layout.addWidget(settings_group)

        # Input/Output group
        io_group = QGroupBox("Input/Output")
        io_layout = QVBoxLayout()
        io_group.setLayout(io_layout)

        # Input for encoding
        self.input_label = QLabel("Data to encode:")
        io_layout.addWidget(self.input_label)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter text or drag & drop file here...")
        self.input_text.setMaximumHeight(150)
        io_layout.addWidget(self.input_text)

        input_btn_layout = QHBoxLayout()
        self.load_file_btn = QPushButton("📁 Load File")
        self.load_file_btn.clicked.connect(self.load_input_file)
        input_btn_layout.addWidget(self.load_file_btn)
        input_btn_layout.addStretch()
        io_layout.addLayout(input_btn_layout)

        # Image selection
        img_layout = QHBoxLayout()
        self.img_label = QLabel("Output Image:")
        img_layout.addWidget(self.img_label)
        self.img_path_input = QLineEdit()
        self.img_path_input.setPlaceholderText("Select image path...")
        img_layout.addWidget(self.img_path_input)
        self.browse_img_btn = QPushButton("Browse")
        self.browse_img_btn.clicked.connect(self.browse_image)
        img_layout.addWidget(self.browse_img_btn)
        io_layout.addLayout(img_layout)

        main_layout.addWidget(io_group)

        # Capacity info
        self.capacity_label = QLabel("Click 'Calculate Capacity' to see available space")
        self.capacity_label.setStyleSheet("padding: 10px; background: #e0e0e0; font-weight: bold;")
        main_layout.addWidget(self.capacity_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.action_btn = QPushButton("🔐 Encode")
        self.action_btn.setMinimumHeight(40)
        self.action_btn.clicked.connect(self.perform_action)
        btn_layout.addWidget(self.action_btn)

        self.calc_capacity_btn = QPushButton("📊 Calculate Capacity")
        self.calc_capacity_btn.clicked.connect(self.calculate_capacity)
        btn_layout.addWidget(self.calc_capacity_btn)

        main_layout.addLayout(btn_layout)

        # Output display (for decoding)
        self.output_group = QGroupBox("Decoded Output")
        self.output_group.setVisible(False)
        output_layout = QVBoxLayout()
        self.output_group.setLayout(output_layout)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        output_btn_layout = QHBoxLayout()
        self.save_output_btn = QPushButton("💾 Save Output")
        self.save_output_btn.clicked.connect(self.save_output)
        output_btn_layout.addWidget(self.save_output_btn)
        output_btn_layout.addStretch()
        output_layout.addLayout(output_btn_layout)

        main_layout.addWidget(self.output_group)

        self.setCentralWidget(main_widget)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.load_file(files[0])

    def on_mode_changed(self):
        """Handle operation mode change"""
        is_encode = self.encode_radio.isChecked()

        self.input_label.setText("Data to encode:" if is_encode else "Encoded Image:")
        self.input_text.setVisible(is_encode)
        self.load_file_btn.setVisible(is_encode)

        self.img_label.setText("Output Image:" if is_encode else "Select Data Image:")

        self.output_group.setVisible(not is_encode)
        self.action_btn.setText("🔐 Encode" if is_encode else "🔓 Decode")
        self.calc_capacity_btn.setVisible(is_encode)

    def load_input_file(self):
        """Load file content for encoding"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load File",
            "",
            "All Files (*)"
        )

        if filename:
            self.load_file(filename)

    def load_file(self, filename):
        """Load file content"""
        try:
            with open(filename, 'rb') as f:
                content = f.read()

            try:
                text = content.decode('utf-8')
                self.input_text.setPlainText(text)
            except:
                self.input_text.setPlainText(f"[Binary file: {len(content)} bytes loaded]")
                self.input_text.setProperty('binary_data', content)

            self.capacity_label.setText(f"Loaded: {len(content):,} bytes from {Path(filename).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def browse_image(self):
        """Browse for image file"""
        is_encode = self.encode_radio.isChecked()

        if is_encode:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Data Image",
                "data_output.png",
                "PNG Images (*.png)"
            )
        else:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open Data Image",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp)"
            )

        if filename:
            self.img_path_input.setText(filename)

    def calculate_capacity(self):
        """Calculate and display capacity"""
        try:
            # Get sample data to calculate size
            data = self.input_text.toPlainText()
            if not data:
                binary_data = self.input_text.property('binary_data')
                if not binary_data:
                    QMessageBox.warning(self, "Error", "No data to calculate capacity for!")
                    return
                data = binary_data

            encoder = DataImageEncoder(ecc_symbols=self.ecc_spin.value())

            # Calculate required size
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data

            img_size = encoder.calculate_image_size(len(data_bytes) + encoder.rs_codec.nsym)
            capacity = encoder.get_capacity(img_size)

            self.capacity_label.setText(
                f"Required Image: {capacity['image_size']} | "
                f"Capacity: {capacity['usable_kb']} | "
                f"Data: {len(data_bytes):,} bytes | "
                f"ECC: {capacity['ecc_overhead']} bytes"
            )
            self.capacity_label.setStyleSheet("padding: 10px; background: #90EE90; font-weight: bold;")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to calculate capacity:\n{str(e)}")

    def perform_action(self):
        """Perform encode or decode operation"""
        if self.encode_radio.isChecked():
            self.encode_data()
        else:
            self.decode_data()

    def encode_data(self):
        """Encode data into image"""
        data = self.input_text.toPlainText()
        if not data:
            binary_data = self.input_text.property('binary_data')
            if not binary_data:
                QMessageBox.warning(self, "Error", "Please enter data or load a file!")
                return
            data = binary_data

        output_path = self.img_path_input.text()
        if not output_path:
            QMessageBox.warning(self, "Error", "Please specify output image path!")
            return

        try:
            self.encoder = DataImageEncoder(ecc_symbols=self.ecc_spin.value())

            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.action_btn.setEnabled(False)

            self.worker = DataWorker(
                'encode',
                self.encoder,
                data=data,
                output_path=output_path
            )
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_encode_finished)
            self.worker.error.connect(self.on_error)
            self.worker.start()

        except Exception as e:
            self.progress_bar.hide()
            self.action_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Encoding failed:\n{str(e)}")

    def decode_data(self):
        """Decode data from image"""
        input_path = self.img_path_input.text()
        if not input_path or not Path(input_path).exists():
            QMessageBox.warning(self, "Error", "Please select a valid data image!")
            return

        try:
            self.encoder = DataImageEncoder(ecc_symbols=self.ecc_spin.value())

            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.action_btn.setEnabled(False)

            self.worker = DataWorker(
                'decode',
                self.encoder,
                img=input_path
            )
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_decode_finished)
            self.worker.error.connect(self.on_error)
            self.worker.start()

        except Exception as e:
            self.progress_bar.hide()
            self.action_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Decoding failed:\n{str(e)}")

    def on_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def on_encode_finished(self, result, operation):
        """Handle successful encoding"""
        self.progress_bar.hide()
        self.action_btn.setEnabled(True)

        img, metadata = result

        QMessageBox.information(
            self,
            "Success",
            f"Data successfully encoded!\n\n"
            f"Output: {self.img_path_input.text()}\n"
            f"Image size: {metadata['image_size']}\n"
            f"Data: {metadata['original_data_bytes']:,} bytes\n"
            f"With ECC: {metadata['encoded_bytes']:,} bytes\n"
            f"Efficiency: {metadata['efficiency']}\n"
            f"CRC32: {metadata['crc32']}"
        )

    def on_decode_finished(self, result, operation):
        """Handle successful decoding"""
        self.progress_bar.hide()
        self.action_btn.setEnabled(True)

        payload, metadata = result

        try:
            text = payload.decode('utf-8')
            self.output_text.setPlainText(text)
        except:
            self.output_text.setPlainText(
                f"[Binary data: {len(payload)} bytes]\n\n"
                f"Metadata:\n"
                f"Image size: {metadata['image_size']}\n"
                f"Decoded bytes: {metadata['decoded_bytes']}\n"
                f"ECC symbols: {metadata['ecc_symbols']}\n"
                f"CRC32: {metadata['crc32']} (Valid: {metadata['crc_valid']})"
            )

        self.output_text.setProperty('binary_data', payload)

        QMessageBox.information(
            self,
            "Success",
            f"Data successfully decoded!\n\n"
            f"Size: {len(payload):,} bytes\n"
            f"CRC32: {metadata['crc32']} ✓"
        )

    def on_error(self, error_msg):
        """Handle operation error"""
        self.progress_bar.hide()
        self.action_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_msg)

    def save_output(self):
        """Save decoded output to file"""
        binary_data = self.output_text.property('binary_data')
        if not binary_data:
            text_data = self.output_text.toPlainText()
            if not text_data:
                QMessageBox.warning(self, "Error", "No data to save!")
                return
            binary_data = text_data.encode('utf-8')

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Decoded Data",
            "decoded_output.txt",
            "All Files (*)"
        )

        if filename:
            try:
                with open(filename, 'wb') as f:
                    f.write(binary_data)
                QMessageBox.information(self, "Success", f"Data saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = DataImageGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
