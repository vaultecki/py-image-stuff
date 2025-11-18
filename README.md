# Image Processing Tools Collection

A comprehensive suite of Python-based image processing tools with GUI interfaces built using PyQt6.

## 📦 Tools Overview

### 1. **py_img_compare.py** - Image Comparison Tool
Visual comparison tool that identifies and highlights differences between two images.

**Features:**
- Side-by-side image comparison
- Automatic difference detection with configurable threshold
- Red bounding boxes around detected differences
- Mouse wheel zoom functionality
- Drag-to-pan image navigation
- Adjustable sensitivity and minimum area filters
- Statistical difference reporting

**Usage:**
```bash
python py_img_compare.py
```

**Controls:**
- Mouse wheel: Zoom in/out
- Left click + drag: Pan image
- Load both images → Adjust parameters → Click "Compare"

---

### 2. **py_img_marker.py** - Image Annotation Tool
Interactive tool for marking and annotating points on images.

**Features:**
- Click to place markers on images
- Customizable marker size (3-50 pixels)
- Customizable marker color
- Zoom and pan support
- JSON export/import for marker positions
- CSV export for compatibility
- Automatic marker restoration
- Undo/Redo functionality
- Jump to marker from list

**Usage:**
```bash
python py_img_marker.py
```

**Keyboard Shortcuts:**
- `Ctrl+O`: Open image
- `Ctrl+S`: Save markers (JSON)
- `Ctrl+Z`: Undo last marker
- `Delete`: Remove all markers
- `Space + Drag`: Pan mode

---

### 3. **py_text_2_img.py** - Data to Image Encoder
Encodes arbitrary data into PNG images using full RGB color depth (3 bytes per pixel).

**Features:**
- Base64 encoding for data integrity
- CRC32 checksum validation
- Automatic image sizing based on data length
- Maximum density encoding (no hiding)
- Supports text and binary data
- No compression (maximum speed)

**Capacity:**
- 100×100 image: ~29 KB
- 500×500 image: ~732 KB
- 1000×1000 image: ~2.9 MB
- 1920×1080 image: ~6 MB

**Usage:**
```python
from py_text_2_img import DataImageEncoder

encoder = DataImageEncoder()

# Encode text
img, metadata = encoder.encode("Your text here", output_path='output.png')

# Decode
data, metadata = encoder.decode('output.png')
text = data.decode('utf-8')
```

**Demo:**
```bash
python py_text_2_img.py
```

---

### 4. **py_img_stego.py** - LSB Steganography Tool
Advanced steganography tool using Least Significant Bit (LSB) encoding.

**Features:**
- Configurable bits per channel (1-3)
- Optional zlib compression
- SHA-256 integrity checking
- Automatic bit selection for optimal capacity
- Version control in header
- Hidden data embedding

**Usage:**
```python
from py_img_stego import ImageSteganography

# Create with auto-sizing
stego = ImageSteganography(img_size=(800, 600), bits_per_channel=1)

# Encode with automatic bit selection
stego.encode("Secret message", compress=True, output_path='stego.png', auto_bits=True)

# Decode
data, info = stego.decode('stego.png', compressed=True)
```

**Demo:**
```bash
python py_img_stego.py
```

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone or download the repository:**
```bash
git clone <repository-url>
cd <repository-folder>
```

2. **Create virtual environment (recommended):**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

---

## 📋 Requirements

- **Pillow** (>=10.0.0): Image processing library
- **numpy** (>=1.24.0): Numerical computations
- **PyQt6** (>=6.5.0): GUI framework

---

## 🎯 Use Cases

### Image Comparison Tool
- Quality assurance testing
- Before/after comparisons
- Visual regression testing
- Document verification
- Design iteration tracking

### Image Marker Tool
- Defect documentation
- Landmark annotation
- Region of interest marking
- Training data labeling
- Measurement point recording

### Data to Image Encoder
- QR code alternative for larger data
- Visual data transmission
- Backup encoding
- Data embedding in images
- Offline data storage

### Steganography Tool
- Secure message hiding
- Watermarking
- Copyright protection
- Covert communication
- Data obfuscation

---

## 🔧 Configuration

### Image Compare Tool
- **Threshold** (1-255): Sensitivity for difference detection (default: 30)
- **Min Area** (1-1000): Minimum pixel area to consider as difference (default: 100)

### Image Marker Tool
- **Marker Size** (3-50): Size of marker crosshair (default: 10)
- **Marker Color**: Customizable via color picker (default: green)
- **Config Directory**: `./config/` (auto-created)

### Data Encoder
- **Image Size**: Auto-calculated based on data length
- **Aspect Ratio**: Prefers 4:3 for optimal display

### Steganography Tool
- **Bits per Channel** (1-3): LSB depth (default: 2)
- **Compression**: Optional zlib compression
- **Auto Bits**: Automatically select minimum bits needed

---

## 📁 File Structure

```
project/
│
├── py_img_compare.py          # Image comparison tool
├── py_img_marker.py            # Image annotation tool
├── py_text_2_img.py            # Data encoder (full RGB)
├── py_img_stego.py             # Steganography (LSB)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
└── config/                     # Auto-created marker storage
    ├── image_name.json         # Marker data
    └── image_name.csv          # CSV export
```

---

## 🐛 Known Issues & Limitations

### Image Compare Tool
- Large images may cause slow flood-fill operations
- Memory intensive for high-resolution comparisons
- Recursive flood-fill may hit Python recursion limit on very large regions

### Image Marker Tool
- Markers stored with absolute coordinates (not relative)
- No grouping or classification of markers
- Limited to single image at a time

### Data Encoder (py_text_2_img.py)
- No encryption (data is visible in pixel values)
- Base64 encoding increases size by ~33%
- PNG compression may not be optimal for all data patterns

### Steganography Tool (py_img_stego.py)
- Lossy formats (JPEG) will destroy embedded data
- Requires exact bits_per_channel setting for decoding
- Image transformations may corrupt data

---

## 🔮 Future Improvements

### General
- [ ] Add multi-language support
- [ ] Implement batch processing
- [ ] Add progress bars for long operations
- [ ] Create unified launcher GUI
- [ ] Add logging system

### Image Compare
- [ ] Use OpenCV for faster contour detection
- [ ] Add overlaid difference visualization
- [ ] Implement histogram comparison
- [ ] Add SSIM (Structural Similarity Index) metric
- [ ] Export difference report as PDF

### Image Marker
- [ ] Add marker categories/tags
- [ ] Implement shape annotations (rectangles, polygons)
- [ ] Add text labels to markers
- [ ] Support relative coordinate system
- [ ] Multi-image session support

### Data Encoder
- [ ] Add AES encryption option
- [ ] Implement error correction codes
- [ ] Support for multiple files in single image
- [ ] Add metadata embedding
- [ ] Optimize for specific data types

### Steganography
- [ ] Add AES encryption layer
- [ ] Implement JPEG-resistant steganography
- [ ] Add password protection
- [ ] Support for audio files
- [ ] Implement F5 algorithm

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Performance optimizations
- Additional features
- Bug fixes
- Documentation improvements
- Test coverage

---

## 📄 License

[Specify your license here]

---

## 👤 Author

[Your name/contact]

---

## 🙏 Acknowledgments

- PyQt6 for the GUI framework
- Pillow for image processing
- NumPy for efficient numerical operations

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [your-email]

---

## 🔄 Version History

### v1.0.0 (Current)
- Initial release
- Four core tools implemented
- Basic documentation
- Requirements specification

---

**Note:** These tools are for educational and legitimate purposes only. Users are responsible for ensuring their use complies with applicable laws and regulations.
