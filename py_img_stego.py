# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Image Steganography Tool - Enhanced Version
LSB (Least Significant Bit) steganography with GUI.
Features:
- Multiple steganography algorithms
- Configurable bits per channel
- SHA-256 integrity checking
- Automatic bit selection
- Password encryption
- GUI interface
"""
import sys
import zlib
import struct
import hashlib
import random
from enum import Enum
from pathlib import Path
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QFileDialog, QMessageBox, QComboBox,
                             QSpinBox, QProgressBar, QGroupBox, QCheckBox,
                             QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap


class StegoAlgorithm(Enum):
    """Supported steganography algorithms"""
    LSB = 1  # Least Significant Bit
    LSB_RANDOM = 2  # LSB with random positioning


class StegoConfig:
    """Configuration for steganography operations"""

    # Magic bytes for different algorithms
    MAGIC_BYTES = {
        StegoAlgorithm.LSB: b'STLB',
        StegoAlgorithm.LSB_RANDOM: b'STLR',
    }

    # Version information
    VERSION_MAJOR = 2
    VERSION_MINOR = 0

    # Header format constants
    MAGIC_SIZE = 4
    VERSION_SIZE = 1
    ALGORITHM_SIZE = 1
    RESERVED_SIZE = 2
    LENGTH_SIZE = 4
    HASH_SIZE = 32

    HEADER_SIZE = MAGIC_SIZE + VERSION_SIZE + ALGORITHM_SIZE + RESERVED_SIZE + LENGTH_SIZE + HASH_SIZE

    @staticmethod
    def get_magic(algorithm):
        """Get magic bytes for algorithm"""
        return StegoConfig.MAGIC_BYTES.get(algorithm, b'STEG')

    @staticmethod
    def get_algorithm_from_magic(magic):
        """Get algorithm from magic bytes"""
        for algo, magic_bytes in StegoConfig.MAGIC_BYTES.items():
            if magic == magic_bytes:
                return algo
        return None


class StegoError(Exception):
    """Base exception for steganography errors"""
    pass


class InsufficientCapacityError(StegoError):
    """Raised when data doesn't fit in image"""
    pass


class IntegrityError(StegoError):
    """Raised when data integrity check fails"""
    pass


class UnsupportedAlgorithmError(StegoError):
    """Raised when algorithm is not supported"""
    pass


class StegoWorker(QThread):
    """Background worker for steganography operations"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object, str)
    error = pyqtSignal(str)

    def __init__(self, operation, stego, **kwargs):
        super().__init__()
        self.operation = operation
        self.stego = stego
        self.kwargs = kwargs

    def run(self):
        try:
            self.progress.emit(10)

            if self.operation == 'encode':
                result = self.stego.encode(**self.kwargs)
                self.progress.emit(100)
                self.finished.emit(result, 'encode')
            elif self.operation == 'decode':
                result = self.stego.decode(**self.kwargs)
                self.progress.emit(100)
                self.finished.emit(result, 'decode')

        except Exception as e:
            self.error.emit(str(e))


class ImageSteganography:
    """Image steganography with configurable algorithms and settings"""

    def __init__(self, img_size=(800, 600), bits_per_channel=2, algorithm=StegoAlgorithm.LSB,
                 password=None):
        """
        Initialize steganography encoder/decoder

        Args:
            img_size: Tuple of (width, height)
            bits_per_channel: Number of LSBs to use (1-3)
            algorithm: Steganography algorithm to use
            password: Optional password for encryption
        """
        self.image_size = (int(img_size[0]), int(img_size[1]))

        if bits_per_channel not in (1, 2, 3):
            raise ValueError('bits_per_channel must be 1, 2, or 3')

        self.bits_per_channel = bits_per_channel
        self.algorithm = algorithm
        self.password = password
        self.config = StegoConfig()
        self._recompute_capacity()

    def _recompute_capacity(self):
        """Recalculate maximum data capacity"""
        w, h = self.image_size
        total_bits = w * h * 3 * self.bits_per_channel
        total_bytes = total_bits // 8
        self.max_capacity = total_bytes - self.config.HEADER_SIZE if total_bytes > self.config.HEADER_SIZE else 0

    def _encrypt_data(self, data):
        """Encrypt data with password using AES"""
        if not self.password:
            return data

        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend
            import os

            # Generate salt
            salt = os.urandom(16)

            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(self.password.encode())

            # Generate IV
            iv = os.urandom(16)

            # Encrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            # Pad data to multiple of 16
            pad_length = 16 - (len(data) % 16)
            padded_data = data + bytes([pad_length] * pad_length)

            encrypted = encryptor.update(padded_data) + encryptor.finalize()

            # Prepend salt and IV
            return salt + iv + encrypted
        except ImportError:
            raise ImportError("cryptography library required for encryption. Install with: pip install cryptography")

    def _decrypt_data(self, data):
        """Decrypt data with password"""
        if not self.password:
            return data

        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend

            # Extract salt, IV, and encrypted data
            salt = data[:16]
            iv = data[16:32]
            encrypted = data[32:]

            # Derive key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(self.password.encode())

            # Decrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()

            # Remove padding
            pad_length = decrypted_padded[-1]
            return decrypted_padded[:-pad_length]
        except ImportError:
            raise ImportError("cryptography library required for decryption")

    def get_info(self):
        """Get information about current configuration"""
        return {
            'algorithm': self.algorithm.name,
            'image_size': f'{self.image_size[0]}x{self.image_size[1]}',
            'bits_per_channel': self.bits_per_channel,
            'header_overhead': self.config.HEADER_SIZE,
            'max_capacity_bytes': self.max_capacity,
            'max_capacity_kb': f'{self.max_capacity / 1024:.2f} KB',
            'version': f'{self.config.VERSION_MAJOR}.{self.config.VERSION_MINOR}',
            'encrypted': self.password is not None
        }

    @staticmethod
    def clamp(v):
        """Clamp value to valid pixel range (0-255)"""
        return max(0, min(255, int(v)))

    @staticmethod
    def choose_bits_for_payload(image_size, payload_len, min_bits=1, max_bits=3):
        """Automatically choose minimum bits per channel needed for payload"""
        w, h = int(image_size[0]), int(image_size[1])

        for b in range(min_bits, max_bits + 1):
            total_bits = w * h * 3 * b
            total_bytes = total_bits // 8
            usable = total_bytes - StegoConfig.HEADER_SIZE

            if usable >= payload_len:
                return b

        raise InsufficientCapacityError(
            f'Payload {payload_len} B does not fit into image {w}x{h} '
            f'even with {max_bits} bits/channel.'
        )

    def _prepare_payload(self, data, compress=True):
        """Prepare payload for encoding"""
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = bytes(data)

        # Encrypt if password provided
        if self.password:
            data_bytes = self._encrypt_data(data_bytes)

        if compress:
            payload = zlib.compress(data_bytes, level=9)
        else:
            payload = data_bytes

        sha256 = hashlib.sha256(payload).digest()
        return payload, sha256

    def _create_header(self, payload_len, sha256):
        """Create steganography header"""
        magic = self.config.get_magic(self.algorithm)
        version = bytes([self.config.VERSION_MAJOR])
        algorithm_byte = bytes([self.algorithm.value])
        reserved = b'\x00\x00'
        length = struct.pack('<I', payload_len)

        header = magic + version + algorithm_byte + reserved + length + sha256
        return header

    def _parse_header(self, header_bytes):
        """Parse steganography header"""
        if len(header_bytes) < self.config.HEADER_SIZE:
            raise IntegrityError('Incomplete header')

        magic = bytes(header_bytes[0:4])
        algorithm = self.config.get_algorithm_from_magic(magic)

        if algorithm is None:
            raise UnsupportedAlgorithmError(f'Unknown magic bytes: {magic}')

        version = header_bytes[4]
        algorithm_byte = header_bytes[5]
        payload_len = struct.unpack('<I', bytes(header_bytes[8:12]))[0]
        sha256_read = bytes(header_bytes[12:44])

        return {
            'magic': magic,
            'algorithm': algorithm,
            'version': version,
            'algorithm_byte': algorithm_byte,
            'payload_len': payload_len,
            'sha256': sha256_read
        }

    def encode(self, data, compress=True, output_path=None, auto_bits=False):
        """Encode data into image"""
        payload, sha256 = self._prepare_payload(data, compress=compress)
        payload_len = len(payload)

        # Auto-select bits if requested
        if auto_bits:
            chosen = self.choose_bits_for_payload(self.image_size, payload_len)
            self.bits_per_channel = chosen
            self._recompute_capacity()

        # Check capacity
        if payload_len > self.max_capacity:
            raise InsufficientCapacityError(
                f'Payload {payload_len} B exceeds capacity {self.max_capacity} B'
            )

        # Create header
        header = self._create_header(payload_len, sha256)
        full_data = header + payload

        # Create image with embedded data
        if self.algorithm == StegoAlgorithm.LSB:
            img = self._encode_lsb(full_data)
        elif self.algorithm == StegoAlgorithm.LSB_RANDOM:
            img = self._encode_lsb_random(full_data)
        else:
            raise UnsupportedAlgorithmError(f'Algorithm {self.algorithm} not implemented')

        # Save if path provided
        if output_path:
            img.save(output_path, 'PNG', compress_level=0)
            return output_path

        return img

    def _encode_lsb(self, data):
        """Encode using standard LSB algorithm"""
        w, h = self.image_size
        img = Image.new('RGB', (w, h))
        pixels = img.load()

        # Create base image
        for y in range(h):
            for x in range(w):
                base = 120 + ((x * y) % 40)
                r = self.clamp(base + random.randint(-20, 20))
                g = self.clamp(base + random.randint(-20, 20))
                b = self.clamp(base + random.randint(-20, 20))
                pixels[x, y] = (r, g, b)

        # Convert data to bits
        bits = []
        for byte in data:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)

        # Embed bits
        bit_idx = 0
        total_bits = len(bits)

        for y in range(h):
            for x in range(w):
                if bit_idx >= total_bits:
                    break

                r, g, b = pixels[x, y]
                channels = [r, g, b]

                for ch in range(3):
                    for bit_pos in range(self.bits_per_channel):
                        if bit_idx >= total_bits:
                            break

                        val = channels[ch] & (~(1 << bit_pos))
                        val = val | (bits[bit_idx] << bit_pos)
                        channels[ch] = self.clamp(val)
                        bit_idx += 1

                pixels[x, y] = tuple(channels)

        return img

    def _encode_lsb_random(self, data):
        """Encode using LSB with random pixel positioning"""
        w, h = self.image_size
        img = Image.new('RGB', (w, h))
        pixels = img.load()

        # Create base image
        for y in range(h):
            for x in range(w):
                base = 120 + ((x * y) % 40)
                r = self.clamp(base + random.randint(-20, 20))
                g = self.clamp(base + random.randint(-20, 20))
                b = self.clamp(base + random.randint(-20, 20))
                pixels[x, y] = (r, g, b)

        # Generate pseudo-random pixel order
        random.seed(42)
        pixel_order = [(x, y) for y in range(h) for x in range(w)]
        random.shuffle(pixel_order)

        # Convert data to bits
        bits = []
        for byte in data:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)

        # Embed bits
        bit_idx = 0
        total_bits = len(bits)

        for x, y in pixel_order:
            if bit_idx >= total_bits:
                break

            r, g, b = pixels[x, y]
            channels = [r, g, b]

            for ch in range(3):
                for bit_pos in range(self.bits_per_channel):
                    if bit_idx >= total_bits:
                        break

                    val = channels[ch] & (~(1 << bit_pos))
                    val = val | (bits[bit_idx] << bit_pos)
                    channels[ch] = self.clamp(val)
                    bit_idx += 1

            pixels[x, y] = tuple(channels)

        return img

    def decode(self, image_path, compressed=True):
        """Decode data from image"""
        img = Image.open(image_path).convert('RGB')
        w, h = img.size
        pixels = img.load()

        # Extract header
        header_bits_needed = self.config.HEADER_SIZE * 8
        header_bits = self._extract_bits(pixels, w, h, header_bits_needed)
        header_bytes = self._bits_to_bytes(header_bits)

        # Parse header
        header_info = self._parse_header(header_bytes)

        # Auto-switch algorithm
        if header_info['algorithm'] != self.algorithm:
            self.algorithm = header_info['algorithm']

        payload_len = header_info['payload_len']
        sha256_stored = header_info['sha256']

        # Extract payload
        payload_bits_needed = payload_len * 8

        if self.algorithm == StegoAlgorithm.LSB:
            payload_bits = self._extract_bits(pixels, w, h, payload_bits_needed,
                                              offset=header_bits_needed)
        elif self.algorithm == StegoAlgorithm.LSB_RANDOM:
            payload_bits = self._extract_bits_random(pixels, w, h, payload_bits_needed,
                                                     offset=header_bits_needed)
        else:
            raise UnsupportedAlgorithmError(f'Algorithm {self.algorithm} not implemented')

        payload_bytes = self._bits_to_bytes(payload_bits)

        # Verify SHA-256
        sha256_calc = hashlib.sha256(bytes(payload_bytes)).digest()
        if sha256_calc != sha256_stored:
            raise IntegrityError('SHA-256 mismatch; data corrupted or wrong password')

        # Decompress if needed
        try:
            if compressed:
                payload = zlib.decompress(bytes(payload_bytes))
            else:
                payload = bytes(payload_bytes)
        except zlib.error:
            payload = bytes(payload_bytes)

        # Decrypt if password provided
        if self.password:
            payload = self._decrypt_data(payload)

        # Metadata
        metadata = {
            'algorithm': header_info['algorithm'].name,
            'version': header_info['version'],
            'payload_len': payload_len,
            'sha256': sha256_stored.hex(),
            'compressed': compressed,
            'encrypted': self.password is not None
        }

        return payload, metadata

    def _extract_bits(self, pixels, w, h, num_bits, offset=0):
        """Extract bits using standard LSB order"""
        bits = []
        bit_counter = 0

        for y in range(h):
            for x in range(w):
                r, g, b = pixels[x, y]
                channels = [r, g, b]

                for ch in range(3):
                    for bit_pos in range(self.bits_per_channel):
                        if bit_counter >= offset and len(bits) < num_bits:
                            bits.append((channels[ch] >> bit_pos) & 1)
                        bit_counter += 1

                        if len(bits) >= num_bits:
                            return bits

        return bits

    def _extract_bits_random(self, pixels, w, h, num_bits, offset=0):
        """Extract bits using random pixel order"""
        # Regenerate same random order
        random.seed(42)
        pixel_order = [(x, y) for y in range(h) for x in range(w)]
        random.shuffle(pixel_order)

        bits = []
        bit_counter = 0

        for x, y in pixel_order:
            r, g, b = pixels[x, y]
            channels = [r, g, b]

            for ch in range(3):
                for bit_pos in range(self.bits_per_channel):
                    if bit_counter >= offset and len(bits) < num_bits:
                        bits.append((channels[ch] >> bit_pos) & 1)
                    bit_counter += 1

                    if len(bits) >= num_bits:
                        return bits

        return bits

    def _bits_to_bytes(self, bits):
        """Convert list of bits to bytes"""
        byte_array = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
                else:
                    byte = byte << 1
            byte_array.append(byte)
        return bytes(byte_array)


class StegoGUI(QMainWindow):
    """GUI for steganography operations"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Steganography Tool")
        self.setGeometry(100, 100, 900, 700)

        self.stego = None
        self.worker = None

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

        # Algorithm selection
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel("Algorithm:"))
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItem("LSB (Standard)", StegoAlgorithm.LSB)
        self.algorithm_combo.addItem("LSB Random", StegoAlgorithm.LSB_RANDOM)
        algo_layout.addWidget(self.algorithm_combo)
        algo_layout.addStretch()
        settings_layout.addLayout(algo_layout)

        # Bits per channel
        bits_layout = QHBoxLayout()
        bits_layout.addWidget(QLabel("Bits per Channel:"))
        self.bits_spin = QSpinBox()
        self.bits_spin.setRange(1, 3)
        self.bits_spin.setValue(2)
        self.bits_spin.setToolTip("Number of LSBs to use (1-3)")
        bits_layout.addWidget(self.bits_spin)

        self.auto_bits_check = QCheckBox("Auto-select")
        self.auto_bits_check.setToolTip("Automatically choose minimum bits needed")
        bits_layout.addWidget(self.auto_bits_check)
        bits_layout.addStretch()
        settings_layout.addLayout(bits_layout)

        # Image size (for encoding only)
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Image Size:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 5000)
        self.width_spin.setValue(800)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("x"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 5000)
        self.height_spin.setValue(600)
        size_layout.addWidget(self.height_spin)
        size_layout.addStretch()
        self.size_widgets = [self.width_spin, self.height_spin]
        settings_layout.addLayout(size_layout)

        # Compression
        self.compress_check = QCheckBox("Compress data")
        self.compress_check.setChecked(True)
        settings_layout.addWidget(self.compress_check)

        # Password
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(QLabel("Password (optional):"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Leave empty for no encryption")
        pwd_layout.addWidget(self.password_input)
        settings_layout.addLayout(pwd_layout)

        main_layout.addWidget(settings_group)

        # Input/Output group
        io_group = QGroupBox("Input/Output")
        io_layout = QVBoxLayout()
        io_group.setLayout(io_layout)

        # Input for encoding
        self.input_label = QLabel("Message to encode:")
        io_layout.addWidget(self.input_label)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter text or load file...")
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
        self.capacity_label = QLabel("Capacity: N/A")
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

    def on_mode_changed(self):
        """Handle operation mode change"""
        is_encode = self.encode_radio.isChecked()

        # Update UI visibility
        self.input_label.setText("Message to encode:" if is_encode else "Encoded Image:")
        self.input_text.setVisible(is_encode)
        self.load_file_btn.setVisible(is_encode)

        self.img_label.setText("Output Image:" if is_encode else "Select Stego Image:")

        for widget in self.size_widgets:
            widget.setVisible(is_encode)

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
            try:
                with open(filename, 'rb') as f:
                    content = f.read()
                # Try to decode as text
                try:
                    text = content.decode('utf-8')
                    self.input_text.setPlainText(text)
                except:
                    # Binary file
                    self.input_text.setPlainText(f"[Binary file: {len(content)} bytes]")
                    self.input_text.setProperty('binary_data', content)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def browse_image(self):
        """Browse for image file"""
        is_encode = self.encode_radio.isChecked()

        if is_encode:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Stego Image",
                "stego_output.png",
                "PNG Images (*.png)"
            )
        else:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open Stego Image",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp)"
            )

        if filename:
            self.img_path_input.setText(filename)

    def calculate_capacity(self):
        """Calculate and display image capacity"""
        try:
            width = self.width_spin.value()
            height = self.height_spin.value()
            bits = self.bits_spin.value()

            stego = ImageSteganography(
                img_size=(width, height),
                bits_per_channel=bits
            )

            info = stego.get_info()

            self.capacity_label.setText(
                f"Capacity: {info['max_capacity_kb']} "
                f"({info['max_capacity_bytes']:,} bytes) "
                f"at {bits} bits/channel"
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
        # Validate inputs
        data = self.input_text.toPlainText()
        if not data:
            # Check for binary data
            binary_data = self.input_text.property('binary_data')
            if not binary_data:
                QMessageBox.warning(self, "Error", "Please enter text or load a file!")
                return
            data = binary_data

        output_path = self.img_path_input.text()
        if not output_path:
            QMessageBox.warning(self, "Error", "Please specify output image path!")
            return

        try:
            # Create steganography instance
            password = self.password_input.text() if self.password_input.text() else None

            self.stego = ImageSteganography(
                img_size=(self.width_spin.value(), self.height_spin.value()),
                bits_per_channel=self.bits_spin.value(),
                algorithm=self.algorithm_combo.currentData(),
                password=password
            )

            # Show progress
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.action_btn.setEnabled(False)

            # Start encoding in background
            self.worker = StegoWorker(
                'encode',
                self.stego,
                data=data,
                compress=self.compress_check.isChecked(),
                output_path=output_path,
                auto_bits=self.auto_bits_check.isChecked()
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
            QMessageBox.warning(self, "Error", "Please select a valid stego image!")
            return

        try:
            # Create steganography instance
            password = self.password_input.text() if self.password_input.text() else None

            self.stego = ImageSteganography(
                bits_per_channel=self.bits_spin.value(),
                password=password
            )

            # Show progress
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.action_btn.setEnabled(False)

            # Start decoding in background
            self.worker = StegoWorker(
                'decode',
                self.stego,
                image_path=input_path,
                compressed=self.compress_check.isChecked()
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

        info = self.stego.get_info()

        QMessageBox.information(
            self,
            "Success",
            f"Data successfully encoded!\n\n"
            f"Output: {result}\n"
            f"Algorithm: {info['algorithm']}\n"
            f"Bits/channel: {info['bits_per_channel']}\n"
            f"Image size: {info['image_size']}\n"
            f"Encrypted: {'Yes' if info['encrypted'] else 'No'}"
        )

    def on_decode_finished(self, result, operation):
        """Handle successful decoding"""
        self.progress_bar.hide()
        self.action_btn.setEnabled(True)

        payload, metadata = result

        # Try to display as text
        try:
            text = payload.decode('utf-8')
            self.output_text.setPlainText(text)
        except:
            self.output_text.setPlainText(
                f"[Binary data: {len(payload)} bytes]\n\n"
                f"Metadata:\n"
                f"Algorithm: {metadata['algorithm']}\n"
                f"Compressed: {metadata['compressed']}\n"
                f"Encrypted: {metadata['encrypted']}\n"
                f"SHA-256: {metadata['sha256']}"
            )

        # Store binary data for saving
        self.output_text.setProperty('binary_data', payload)

        QMessageBox.information(
            self,
            "Success",
            f"Data successfully decoded!\n\n"
            f"Size: {len(payload)} bytes\n"
            f"Algorithm: {metadata['algorithm']}\n"
            f"Encrypted: {'Yes' if metadata['encrypted'] else 'No'}"
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
    window = StegoGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
