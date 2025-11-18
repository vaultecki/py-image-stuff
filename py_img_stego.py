# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Image Steganography Tool
LSB (Least Significant Bit) steganography with configurable algorithms.
Features:
- Multiple steganography algorithms
- Configurable bits per channel
- SHA-256 integrity checking
- Automatic bit selection
- Version control
"""
import zlib
import struct
import hashlib
import random
from enum import Enum
from PIL import Image


class StegoAlgorithm(Enum):
    """Supported steganography algorithms"""
    LSB = 1  # Least Significant Bit
    LSB_RANDOM = 2  # LSB with random positioning
    # Future algorithms can be added here
    # DCT = 3        # Discrete Cosine Transform
    # F5 = 4         # F5 algorithm


class StegoConfig:
    """Configuration for steganography operations"""

    # Magic bytes for different algorithms
    MAGIC_BYTES = {
        StegoAlgorithm.LSB: b'STLB',  # STenography Least Bit
        StegoAlgorithm.LSB_RANDOM: b'STLR',  # STenography Least Random
    }

    # Version information
    VERSION_MAJOR = 2
    VERSION_MINOR = 0

    # Header format constants
    MAGIC_SIZE = 4  # Magic identifier
    VERSION_SIZE = 1  # Version byte
    ALGORITHM_SIZE = 1  # Algorithm identifier
    RESERVED_SIZE = 2  # Reserved for future use
    LENGTH_SIZE = 4  # Data length (uint32)
    HASH_SIZE = 32  # SHA-256 hash

    # Total header size: 4 + 1 + 1 + 2 + 4 + 32 = 44 bytes
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


class ImageSteganography:
    """
    Image steganography with configurable algorithms and settings
    """

    def __init__(self, img_size=(800, 600), bits_per_channel=2, algorithm=StegoAlgorithm.LSB):
        """
        Initialize steganography encoder/decoder

        Args:
            img_size: Tuple of (width, height)
            bits_per_channel: Number of LSBs to use (1-3)
            algorithm: Steganography algorithm to use
        """
        self.image_size = (int(img_size[0]), int(img_size[1]))

        if bits_per_channel not in (1, 2, 3):
            raise ValueError('bits_per_channel must be 1, 2, or 3')

        self.bits_per_channel = bits_per_channel
        self.algorithm = algorithm
        self.config = StegoConfig()
        self._recompute_capacity()

    def _recompute_capacity(self):
        """Recalculate maximum data capacity"""
        w, h = self.image_size
        total_bits = w * h * 3 * self.bits_per_channel
        total_bytes = total_bits // 8
        self.max_capacity = total_bytes - self.config.HEADER_SIZE if total_bytes > self.config.HEADER_SIZE else 0

    def get_info(self):
        """Get information about current configuration"""
        return {
            'algorithm': self.algorithm.name,
            'image_size': f'{self.image_size[0]}x{self.image_size[1]}',
            'bits_per_channel': self.bits_per_channel,
            'header_overhead': self.config.HEADER_SIZE,
            'max_capacity_bytes': self.max_capacity,
            'max_capacity_kb': f'{self.max_capacity / 1024:.2f} KB',
            'version': f'{self.config.VERSION_MAJOR}.{self.config.VERSION_MINOR}'
        }

    @staticmethod
    def clamp(v):
        """Clamp value to valid pixel range (0-255)"""
        return max(0, min(255, int(v)))

    @staticmethod
    def choose_bits_for_payload(image_size, payload_len, min_bits=1, max_bits=3):
        """
        Automatically choose minimum bits per channel needed for payload

        Args:
            image_size: Tuple of (width, height)
            payload_len: Length of payload in bytes
            min_bits: Minimum bits per channel to try
            max_bits: Maximum bits per channel to try

        Returns:
            int: Optimal bits per channel

        Raises:
            InsufficientCapacityError: If payload doesn't fit
        """
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
        """
        Prepare payload for encoding

        Args:
            data: Raw data (bytes or string)
            compress: Whether to compress data

        Returns:
            Tuple of (payload_bytes, sha256_hash)
        """
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = bytes(data)

        if compress:
            payload = zlib.compress(data_bytes, level=9)
        else:
            payload = data_bytes

        sha256 = hashlib.sha256(payload).digest()
        return payload, sha256

    def _create_header(self, payload_len, sha256):
        """
        Create steganography header

        Args:
            payload_len: Length of payload
            sha256: SHA-256 hash of payload

        Returns:
            bytes: Complete header
        """
        magic = self.config.get_magic(self.algorithm)
        version = bytes([self.config.VERSION_MAJOR])
        algorithm_byte = bytes([self.algorithm.value])
        reserved = b'\x00\x00'
        length = struct.pack('<I', payload_len)

        header = magic + version + algorithm_byte + reserved + length + sha256

        assert len(header) == self.config.HEADER_SIZE, \
            f"Header size mismatch: {len(header)} != {self.config.HEADER_SIZE}"

        return header

    def _parse_header(self, header_bytes):
        """
        Parse steganography header

        Args:
            header_bytes: Header bytes to parse

        Returns:
            dict: Parsed header information

        Raises:
            IntegrityError: If header is invalid
            UnsupportedAlgorithmError: If algorithm is not supported
        """
        if len(header_bytes) < self.config.HEADER_SIZE:
            raise IntegrityError('Incomplete header')

        magic = bytes(header_bytes[0:4])
        algorithm = self.config.get_algorithm_from_magic(magic)

        if algorithm is None:
            raise UnsupportedAlgorithmError(
                f'Unknown magic bytes: {magic}. '
                f'Expected one of: {list(self.config.MAGIC_BYTES.values())}'
            )

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
        """
        Encode data into image

        Args:
            data: Data to encode (bytes or string)
            compress: Whether to compress data
            output_path: Path to save image (optional)
            auto_bits: Automatically select minimum bits per channel

        Returns:
            PIL Image or path (if output_path provided)

        Raises:
            InsufficientCapacityError: If data doesn't fit
        """
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
                f'Payload {payload_len} B exceeds capacity {self.max_capacity} B '
                f'for image {self.image_size} at {self.bits_per_channel} bpc.'
            )

        # Create header
        header = self._create_header(payload_len, sha256)

        # Combine header + payload
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

        # Create base image with slight variation
        for y in range(h):
            for x in range(w):
                base = 120 + ((x * y) % 40)
                r = self.clamp(base + random.randint(-20, 20))
                g = self.clamp(base + random.randint(-20, 20))
                b = self.clamp(base + random.randint(-20, 20))
                pixels[x, y] = (r, g, b)

        # Convert data to bits (MSB first)
        bits = []
        for byte in data:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)

        # Embed bits into LSBs
        bit_idx = 0
        total_bits = len(bits)

        for y in range(h):
            for x in range(w):
                if bit_idx >= total_bits:
                    break

                r, g, b = pixels[x, y]
                channels = [r, g, b]

                # Embed in each channel
                for ch in range(3):
                    for bit_pos in range(self.bits_per_channel):
                        if bit_idx >= total_bits:
                            break

                        # Clear bit and set new value
                        val = channels[ch] & (~(1 << bit_pos))
                        val = val | (bits[bit_idx] << bit_pos)
                        channels[ch] = self.clamp(val)
                        bit_idx += 1

                pixels[x, y] = tuple(channels)

                if bit_idx >= total_bits:
                    break

        if bit_idx < total_bits:
            raise InsufficientCapacityError('Ran out of pixels while embedding')

        return img

    def _encode_lsb_random(self, data):
        """Encode using LSB with random pixel positioning"""
        # Similar to LSB but with pseudo-random pixel order
        # This provides slightly better security
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

        # Generate pseudo-random pixel order (deterministic)
        random.seed(42)  # Fixed seed for deterministic behavior
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
        """
        Decode data from image

        Args:
            image_path: Path to image file
            compressed: Whether data was compressed

        Returns:
            Tuple of (decoded_data, metadata_dict)

        Raises:
            IntegrityError: If data is corrupted
            UnsupportedAlgorithmError: If algorithm is not supported
        """
        img = Image.open(image_path).convert('RGB')
        w, h = img.size
        pixels = img.load()

        # Extract header
        header_bits_needed = self.config.HEADER_SIZE * 8
        header_bits = self._extract_bits(pixels, w, h, header_bits_needed)
        header_bytes = self._bits_to_bytes(header_bits)

        # Parse header
        header_info = self._parse_header(header_bytes)

        # Check if we need to use different algorithm for decoding
        if header_info['algorithm'] != self.algorithm:
            print(f"Note: Image uses {header_info['algorithm'].name}, "
                  f"but decoder is set to {self.algorithm.name}")
            # Automatically switch algorithm
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
            raise IntegrityError(
                f'SHA-256 mismatch; data corrupted or wrong bits_per_channel used. '
                f'Expected: {sha256_stored.hex()}, Got: {sha256_calc.hex()}'
            )

        # Decompress if needed
        try:
            if compressed:
                payload = zlib.decompress(bytes(payload_bytes))
            else:
                payload = bytes(payload_bytes)
        except zlib.error:
            payload = bytes(payload_bytes)

        # Metadata
        metadata = {
            'algorithm': header_info['algorithm'].name,
            'version': header_info['version'],
            'payload_len': payload_len,
            'sha256': sha256_stored.hex(),
            'compressed': compressed
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


def demo():
    """Demonstrate usage with different algorithms"""
    print("=== Image Steganography Tool ===\n")

    # Test with LSB algorithm
    print("Testing LSB Algorithm:")
    print("-" * 50)

    stego_lsb = ImageSteganography(
        img_size=(800, 600),
        bits_per_channel=2,
        algorithm=StegoAlgorithm.LSB
    )

    info = stego_lsb.get_info()
    print("Configuration:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    print()

    # Sample data
    sample_text = "This is a test for LSB steganography with configurable algorithms!"

    print(f"Original text ({len(sample_text)} characters):")
    print(f"  {sample_text}\n")

    # Encode with auto-bit selection
    print("Encoding with auto-bit selection...")
    output = stego_lsb.encode(
        sample_text,
        compress=True,
        output_path='stego_lsb.png',
        auto_bits=True
    )
    print(f"✓ Saved to: {output}")
    print(f"  Bits per channel used: {stego_lsb.bits_per_channel}\n")

    # Decode
    print("Decoding...")
    decoded, metadata = stego_lsb.decode('stego_lsb.png', compressed=True)
    decoded_text = decoded.decode('utf-8')

    print("Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    print()

    print(f"Decoded text: {decoded_text}\n")

    if sample_text == decoded_text:
        print("✓ SUCCESS: LSB algorithm works correctly!\n")
    else:
        print("✗ ERROR: Text mismatch!\n")

    # Test with LSB_RANDOM algorithm
    print("\n" + "=" * 50)
    print("Testing LSB_RANDOM Algorithm:")
    print("-" * 50)

    stego_random = ImageSteganography(
        img_size=(800, 600),
        bits_per_channel=2,
        algorithm=StegoAlgorithm.LSB_RANDOM
    )

    print("Encoding with random positioning...")
    stego_random.encode(
        sample_text,
        compress=True,
        output_path='stego_random.png',
        auto_bits=True
    )
    print("✓ Saved to: stego_random.png\n")

    print("Decoding...")
    decoded_random, metadata_random = stego_random.decode('stego_random.png', compressed=True)
    decoded_text_random = decoded_random.decode('utf-8')

    if sample_text == decoded_text_random:
        print("✓ SUCCESS: LSB_RANDOM algorithm works correctly!\n")
    else:
        print("✗ ERROR: Text mismatch!\n")

    # Algorithm comparison
    print("\n" + "=" * 50)
    print("Algorithm Comparison:")
    print("-" * 50)
    print(f"LSB:        Magic bytes = {StegoConfig.MAGIC_BYTES[StegoAlgorithm.LSB]}")
    print(f"LSB_RANDOM: Magic bytes = {StegoConfig.MAGIC_BYTES[StegoAlgorithm.LSB_RANDOM]}")
    print("\nBoth algorithms successfully encoded and decoded the same data!")


def main():
    """Main entry point"""
    demo()


if __name__ == "__main__":
    main()
