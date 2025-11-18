# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Data to Image Encoder
Encodes arbitrary data into images using full RGB color depth.
No Base64 overhead, with Reed-Solomon error correction.
"""
import struct
import zlib
import math
from PIL import Image


class ReedSolomonCodec:
    """Simple Reed-Solomon error correction codec"""

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
            self.available = True
        except ImportError:
            self.rsc = None
            self.available = False
            print("Warning: reedsolo not installed. Error correction disabled.")
            print("Install with: pip install reedsolo")

    def encode(self, data):
        """Add error correction to data"""
        if self.available:
            return self.rsc.encode(data)
        return data

    def decode(self, data):
        """Decode and correct errors in data"""
        if self.available:
            try:
                return self.rsc.decode(data)[0]
            except Exception as e:
                raise ValueError(f"Error correction failed: {e}")
        return data


class DataImageEncoder:
    """
    Encodes data into images using full RGB color depth.
    Each pixel stores 3 bytes (one per RGB channel).
    Optional Reed-Solomon error correction.
    No Base64 encoding - direct binary storage.
    """

    # Header format: MAGIC (4 bytes) + FLAGS (1 byte) + RESERVED (3 bytes) + 
    #                DATA_LENGTH (4 bytes) + CRC32 (4 bytes) = 16 bytes
    MAGIC = b'DATA'
    HEADER_SIZE = 16
    BYTES_PER_PIXEL = 3  # RGB = 3 bytes

    # Flags
    FLAG_ERROR_CORRECTION = 0x01  # Bit 0: Error correction enabled
    FLAG_RESERVED_1 = 0x02  # Bit 1: Reserved
    FLAG_RESERVED_2 = 0x04  # Bit 2: Reserved
    FLAG_RESERVED_3 = 0x08  # Bit 3: Reserved

    def __init__(self, error_correction=True, ecc_symbols=10):
        """
        Initialize encoder

        Args:
            error_correction: Enable Reed-Solomon error correction
            ecc_symbols: Number of error correction symbols (default: 10)
        """
        self.error_correction = error_correction
        self.rs_codec = ReedSolomonCodec(ecc_symbols) if error_correction else None

    def calculate_image_size(self, data_length):
        """
        Calculate optimal image dimensions for given data length

        Args:
            data_length: Length of data in bytes (after error correction if enabled)

        Returns:
            tuple: (width, height) of image
        """
        # Total bytes including header
        total_bytes = self.HEADER_SIZE + data_length

        # Total pixels needed
        pixels_needed = math.ceil(total_bytes / self.BYTES_PER_PIXEL)

        # Calculate square-ish dimensions (prefer 4:3 ratio)
        width = math.ceil(math.sqrt(pixels_needed * 4 / 3))
        height = math.ceil(pixels_needed / width)

        # Ensure minimum size
        width = max(width, 10)
        height = max(height, 10)

        return (width, height)

    def encode(self, data, output_path=None):
        """
        Encode data into an image

        Args:
            data: Bytes or string to encode
            output_path: File path to save (optional)

        Returns:
            PIL Image object and metadata dict
        """
        # Convert input to bytes
        if isinstance(data, str):
            data = data.encode('utf-8')

        original_length = len(data)

        # Apply error correction if enabled
        if self.error_correction and self.rs_codec.available:
            encoded_data = self.rs_codec.encode(data)
            ecc_overhead = len(encoded_data) - len(data)
        else:
            encoded_data = data
            ecc_overhead = 0

        # Calculate CRC32 checksum (on final encoded data)
        crc = zlib.crc32(encoded_data) & 0xFFFFFFFF

        # Create flags byte
        flags = 0
        if self.error_correction and self.rs_codec.available:
            flags |= self.FLAG_ERROR_CORRECTION

        # Create header
        header = (
                self.MAGIC +
                bytes([flags]) +
                b'\x00\x00\x00' +  # Reserved bytes
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
            'total_bytes_with_header': len(full_data),
            'pixels_used': math.ceil(len(full_data) / self.BYTES_PER_PIXEL),
            'total_pixels': img_size[0] * img_size[1],
            'efficiency': f"{(len(full_data) / (img_size[0] * img_size[1] * 3)) * 100:.1f}%",
            'error_correction': self.error_correction and self.rs_codec.available,
            'crc32': f"{crc:08X}"
        }

        return img, metadata

    def decode(self, img):
        """
        Extract data from an image

        Args:
            img: PIL Image or file path

        Returns:
            tuple: (bytes, metadata_dict) with extracted data and metadata
        """
        # Load image if path
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

        data_length = struct.unpack('<I', bytes(byte_array[8:12]))[0]
        stored_crc = struct.unpack('<I', bytes(byte_array[12:16]))[0]

        # Check if image contains enough data
        total_needed = self.HEADER_SIZE + data_length
        if len(byte_array) < total_needed:
            raise ValueError(
                f"Image too small! Need {total_needed} bytes, have {len(byte_array)}"
            )

        # Extract data
        data_bytes = bytes(byte_array[self.HEADER_SIZE:self.HEADER_SIZE + data_length])

        # Verify CRC
        calculated_crc = zlib.crc32(data_bytes) & 0xFFFFFFFF
        if calculated_crc != stored_crc:
            raise ValueError(
                f"CRC mismatch! Data may be corrupted. "
                f"Expected: {stored_crc:08X}, Got: {calculated_crc:08X}"
            )

        # Apply error correction if it was used
        if has_ecc:
            if not self.rs_codec or not self.rs_codec.available:
                raise ValueError(
                    "Image has error correction but reedsolo is not installed! "
                    "Install with: pip install reedsolo"
                )
            try:
                decoded_data = self.rs_codec.decode(data_bytes)
            except Exception as e:
                raise ValueError(f"Error correction failed: {e}")
        else:
            decoded_data = data_bytes

        # Metadata
        metadata = {
            'image_size': f"{width}x{height}",
            'decoded_bytes': len(decoded_data),
            'encoded_bytes': data_length,
            'error_correction_used': has_ecc,
            'crc32': f"{stored_crc:08X}",
            'crc_valid': True
        }

        return decoded_data, metadata

    def _create_image_with_data(self, data, img_size):
        """
        Create image and embed data using full color depth

        Args:
            data: Bytes to embed
            img_size: (width, height) tuple

        Returns:
            PIL Image
        """
        width, height = img_size
        img = Image.new('RGB', img_size, color='white')
        pixels = img.load()

        byte_index = 0

        for y in range(height):
            for x in range(width):
                if byte_index >= len(data):
                    # Fill remaining pixels with white
                    pixels[x, y] = (255, 255, 255)
                    continue

                # Read 3 bytes (one per channel) or pad with 255
                r = data[byte_index] if byte_index < len(data) else 255
                byte_index += 1

                g = data[byte_index] if byte_index < len(data) else 255
                byte_index += 1

                b = data[byte_index] if byte_index < len(data) else 255
                byte_index += 1

                pixels[x, y] = (r, g, b)

        return img

    def get_capacity(self, img_size):
        """
        Calculate data capacity for given image size

        Args:
            img_size: (width, height) tuple

        Returns:
            dict with capacity information
        """
        width, height = img_size
        total_pixels = width * height
        total_bytes = total_pixels * self.BYTES_PER_PIXEL
        usable_bytes = total_bytes - self.HEADER_SIZE

        # Account for error correction overhead if enabled
        if self.error_correction and self.rs_codec and self.rs_codec.available:
            ecc_overhead = self.rs_codec.nsym
            usable_data = usable_bytes - ecc_overhead
        else:
            ecc_overhead = 0
            usable_data = usable_bytes

        return {
            'image_size': f"{width}x{height}",
            'total_pixels': total_pixels,
            'total_bytes': total_bytes,
            'usable_bytes': usable_bytes,
            'ecc_overhead': ecc_overhead,
            'usable_data_bytes': max(0, usable_data),
            'usable_kb': f"{max(0, usable_data) / 1024:.2f} KB",
            'header_overhead': self.HEADER_SIZE
        }


def demo():
    """Demonstrate usage"""
    print("=== Data to Image Encoder Demo ===\n")

    # Create encoder with error correction
    encoder = DataImageEncoder(error_correction=True, ecc_symbols=10)

    if encoder.rs_codec and encoder.rs_codec.available:
        print("✓ Reed-Solomon error correction: ENABLED")
    else:
        print("⚠ Reed-Solomon error correction: DISABLED (reedsolo not installed)")
    print()

    # Test data
    test_text = """
    This is a test for data encoding in images!
    The data is stored using full RGB color depth.

    Features:
    - NO Base64 encoding (33% overhead removed!)
    - Reed-Solomon error correction
    - CRC32 checksum
    - Full 8-bit per channel encoding
    - Automatic image sizing

    Direct binary storage for maximum efficiency!
    """

    print(f"Original text ({len(test_text)} characters, {len(test_text.encode('utf-8'))} bytes):\n")
    print(test_text)
    print("\n" + "=" * 60 + "\n")

    # Encode
    print("Encoding data...")
    img, metadata = encoder.encode(test_text, output_path='data_image.png')

    print("✓ Image created: data_image.png\n")
    print("Encoding metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60 + "\n")

    # Decode
    print("Decoding data...")
    decoded_data, decode_metadata = encoder.decode('data_image.png')
    decoded_text = decoded_data.decode('utf-8')

    print("Decoding metadata:")
    for key, value in decode_metadata.items():
        print(f"  {key}: {value}")

    print(f"\nDecoded text ({len(decoded_text)} characters):\n")
    print(decoded_text)

    # Verification
    print("\n" + "=" * 60)
    if test_text == decoded_text:
        print("✓ SUCCESS: Original and decoded data are identical!")
    else:
        print("✗ ERROR: Data mismatch!")

    # Binary data test
    print("\n" + "=" * 60)
    print("\nTesting with binary data...")
    binary_data = bytes([i % 256 for i in range(5000)])
    print(f"Binary data: {len(binary_data)} bytes")

    img2, meta2 = encoder.encode(binary_data, output_path='data_binary.png')
    print(f"✓ Created image: {meta2['image_size']}")
    print(f"  Original: {meta2['original_data_bytes']} bytes")
    print(f"  With ECC: {meta2['encoded_bytes']} bytes")
    print(
        f"  ECC overhead: {meta2['ecc_overhead_bytes']} bytes ({meta2['ecc_overhead_bytes'] / meta2['original_data_bytes'] * 100:.1f}%)")

    decoded_binary, _ = encoder.decode('data_binary.png')

    if binary_data == decoded_binary:
        print("✓ SUCCESS: Binary data correctly encoded and decoded!")
    else:
        print("✗ ERROR: Binary data corrupted!")

    # Error correction test
    print("\n" + "=" * 60)
    print("\nTesting error correction...")

    if encoder.rs_codec and encoder.rs_codec.available:
        # Simulate corruption
        img_corrupted = Image.open('data_binary.png')
        pixels = img_corrupted.load()
        width, height = img_corrupted.size

        # Corrupt some pixels (change 5 random pixels)
        import random
        corrupted_pixels = []
        for _ in range(5):
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)
            old_val = pixels[x, y]
            pixels[x, y] = (255 - old_val[0], 255 - old_val[1], 255 - old_val[2])
            corrupted_pixels.append((x, y))

        img_corrupted.save('data_binary_corrupted.png')
        print(f"Corrupted {len(corrupted_pixels)} pixels")

        try:
            decoded_corrupted, _ = encoder.decode('data_binary_corrupted.png')
            if binary_data == decoded_corrupted:
                print("✓ SUCCESS: Error correction recovered corrupted data!")
            else:
                print("⚠ PARTIAL: Data differs but was decoded")
        except Exception as e:
            print(f"✗ ERROR: Could not recover: {e}")
    else:
        print("⚠ Error correction test skipped (reedsolo not installed)")

    # Capacity comparison
    print("\n" + "=" * 60)
    print("\nCapacity comparison (with/without error correction):")
    print("\nWith error correction:")
    for size in [(100, 100), (500, 500), (1000, 1000)]:
        capacity = encoder.get_capacity(size)
        print(f"\n{capacity['image_size']}:")
        print(f"  Usable data: {capacity['usable_kb']}")
        print(f"  ECC overhead: {capacity['ecc_overhead']} bytes")

    print("\nWithout error correction:")
    encoder_no_ecc = DataImageEncoder(error_correction=False)
    for size in [(100, 100), (500, 500), (1000, 1000)]:
        capacity = encoder_no_ecc.get_capacity(size)
        print(f"\n{capacity['image_size']}:")
        print(f"  Usable data: {capacity['usable_kb']}")


def main():
    """Main entry point"""
    demo()


if __name__ == '__main__':
    main()
