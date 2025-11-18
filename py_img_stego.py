# py_img_stego_updated.py
from PIL import Image
import zlib, struct, hashlib, io, random
MAGIC = b'PYST'   # 4 bytes
VERSION = 1       # 1 byte version
RESERVED = b'\x00\x00\x00'  # 3 bytes reserved (padding)
HEADER_SIZE = 4 + 1 + 3 + 4 + 32  # 44 bytes

class StegoError(Exception): pass
class InsufficientCapacityError(StegoError): pass
class IntegrityError(StegoError): pass

class ImageSteganography:
    def __init__(self, img_size=(800,600), bits_per_channel=2):
        self.image_size = (int(img_size[0]), int(img_size[1]))
        if bits_per_channel not in (1,2,3):
            raise ValueError('bits_per_channel must be 1,2 or 3')
        self.bits_per_channel = bits_per_channel
        self.header_size = HEADER_SIZE
        self._recompute_capacity()

    def _recompute_capacity(self):
        w,h = self.image_size
        total_bits = w * h * 3 * self.bits_per_channel
        total_bytes = total_bits // 8
        self.max_capacity = total_bytes - self.header_size if total_bytes > self.header_size else 0

    def get_info(self):
        return {
            'image_size': f'{self.image_size[0]}x{self.image_size[1]}',
            'bits_per_channel': self.bits_per_channel,
            'header_overhead': self.header_size,
            'max_capacity_bytes': self.max_capacity,
            'max_capacity_kb': f'{self.max_capacity/1024:.2f} KB'
        }

    @staticmethod
    def clamp(v):
        return max(0, min(255, int(v)))

    @staticmethod
    def choose_bits_for_payload(image_size, payload_len, min_bits=1, max_bits=3):
        w,h = int(image_size[0]), int(image_size[1])
        for b in range(min_bits, max_bits+1):
            total_bits = w * h * 3 * b
            total_bytes = total_bits // 8
            usable = total_bytes - HEADER_SIZE
            if usable >= payload_len:
                return b
        raise InsufficientCapacityError(f'Payload {payload_len} B does not fit into image {w}x{h} even with {max_bits} bits/channel.')

    def _prepare_payload(self, data, compress=True):
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

    def encode(self, data, compress=True, output_path=None, auto_bits=False):
        payload, sha256 = self._prepare_payload(data, compress=compress)
        payload_len = len(payload)
        if auto_bits:
            chosen = self.choose_bits_for_payload(self.image_size, payload_len)
            self.bits_per_channel = chosen
            self._recompute_capacity()
        if payload_len > self.max_capacity:
            raise InsufficientCapacityError(f'Payload {payload_len} B exceeds capacity {self.max_capacity} B for image {self.image_size} at {self.bits_per_channel} bpc.')
        header = MAGIC + bytes([VERSION]) + RESERVED + struct.pack('<I', payload_len) + sha256
        full = header + payload
        # make image
        w,h = self.image_size
        img = Image.new('RGB', (w,h))
        pixels = img.load()
        for y in range(h):
            for x in range(w):
                base = 120 + ((x * y) % 40)
                r = self.clamp(base + random.randint(-20,20))
                g = self.clamp(base + random.randint(-20,20))
                b = self.clamp(base + random.randint(-20,20))
                pixels[x,y] = (r,g,b)
        # bits iterator MSB-first per byte
        bits = []
        for byte in full:
            for i in range(8):
                bits.append((byte >> (7-i)) & 1)
        bitpos = 0
        total_bits = len(bits)
        idx = 0
        for y in range(h):
            for x in range(w):
                r,g,b = pixels[x,y]
                channels = [r,g,b]
                for ch in range(3):
                    for bpos in range(self.bits_per_channel):
                        if idx >= total_bits:
                            pixels[x,y] = (channels[0], channels[1], channels[2])
                            continue
                        val = channels[ch] & (~(1 << bpos)) | (bits[idx] << bpos)
                        channels[ch] = self.clamp(val)
                        idx += 1
                pixels[x,y] = (channels[0], channels[1], channels[2])
                if idx >= total_bits:
                    break
            if idx >= total_bits:
                break
        if idx < total_bits:
            raise InsufficientCapacityError('Ran out of pixels while embedding (unexpected).')
        if output_path:
            img.save(output_path, 'PNG')
            return output_path
        return img

    def decode(self, image_path, compressed=True):
        img = Image.open(image_path).convert('RGB')
        w,h = img.size
        pixels = img.load()
        header_bits_needed = HEADER_SIZE * 8
        bits = []
        idx = 0
        for y in range(h):
            for x in range(w):
                r,g,b = pixels[x,y]
                channels = [r,g,b]
                for ch in range(3):
                    for bpos in range(self.bits_per_channel):
                        if idx < header_bits_needed:
                            bits.append((channels[ch] >> bpos) & 1)
                            idx += 1
                        else:
                            break
                    if idx >= header_bits_needed:
                        break
                if idx >= header_bits_needed:
                    break
            if idx >= header_bits_needed:
                break
        if len(bits) < header_bits_needed:
            raise StegoError('Not enough bits for header.')
        header_bytes = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bits[i+j]
            header_bytes.append(byte)
        if len(header_bytes) < HEADER_SIZE:
            raise StegoError('Incomplete header bytes.')
        magic = bytes(header_bytes[0:4])
        if magic != MAGIC:
            raise IntegrityError('Magic mismatch.')
        version = header_bytes[4]
        payload_len = struct.unpack('<I', bytes(header_bytes[8:12]))[0]
        sha256_read = bytes(header_bytes[12:44])
        payload_bits_needed = payload_len * 8
        bits = []
        idx = 0
        bit_counter = 0
        for y in range(h):
            for x in range(w):
                r,g,b = pixels[x,y]
                channels = [r,g,b]
                for ch in range(3):
                    for bpos in range(self.bits_per_channel):
                        if bit_counter >= header_bits_needed and idx < payload_bits_needed:
                            bits.append((channels[ch] >> bpos) & 1)
                            idx += 1
                        bit_counter += 1
                        if idx >= payload_bits_needed:
                            break
                    if idx >= payload_bits_needed:
                        break
                if idx >= payload_bits_needed:
                    break
            if idx >= payload_bits_needed:
                break
        if len(bits) < payload_bits_needed:
            raise StegoError('Not enough bits for payload (image too small or wrong bits_per_channel).')
        payload_bytes = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bits[i+j]
            payload_bytes.append(byte)
        sha256_calc = hashlib.sha256(bytes(payload_bytes)).digest()
        if sha256_calc != sha256_read:
            raise IntegrityError('SHA-256 mismatch; data corrupted or wrong bits_per_channel used.')
        try:
            if compressed:
                payload = zlib.decompress(bytes(payload_bytes))
            else:
                payload = bytes(payload_bytes)
        except zlib.error:
            payload = bytes(payload_bytes)
        return payload, {'version': version, 'payload_len': payload_len, 'sha256': sha256_read.hex()}


def demo():
    # instantiate
    st = ImageSteganography(img_size=(800, 600), bits_per_channel=1)

    # prepare sample text
    sample_text = "Dies ist ein Test für Steganographie, Hash SHA-256, Version 1."
    payload, sha = st._prepare_payload(sample_text, compress=True)
    print("raw bytes:", len(sample_text.encode()))
    print("transformed (compressed) bytes:", len(payload))
    print("sha256:", sha.hex())

    # automatic selection of minimal bits
    bits = ImageSteganography.choose_bits_for_payload((800, 600), len(payload))
    print("chosen bits per channel:", bits)

    # encode to file (auto_bits True)
    out = st.encode(sample_text, compress=True, output_path='stego_output.png', auto_bits=True)
    print("Saved to:", out)

    # decode and verify
    st2 = ImageSteganography(img_size=(800, 600), bits_per_channel=st.bits_per_channel)
    decoded, info = st2.decode('stego_output.png', compressed=True)
    print("decoded snippet:", decoded[:120])
    print("info:", info)


if __name__ == "__main__":
    demo()