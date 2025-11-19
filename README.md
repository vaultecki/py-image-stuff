# Image Processing Tools Suite

A comprehensive collection of Python-based image processing tools with modern GUI interfaces.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-brightgreen.svg)](https://www.riverbankcomputing.com/software/pyqt/)

## 🚀 Features

This suite includes five powerful tools:

1. **Image Comparison Tool** - Compare images with SSIM, histogram analysis, and pixel difference detection
2. **Image Marker Tool** - Annotate images with categorized markers and labels
3. **Steganography Tool** - Hide data in images using LSB encoding with encryption
4. **QR Code Generator** - Generate and decode QR codes with customization options
5. **Data to Image Encoder** - Encode arbitrary data into images with error correction

## 📋 Table of Contents

- [Installation](#installation)
- [Tools Overview](#tools-overview)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download

```bash
git clone <your-repository-url>
cd image-processing-tools
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Platform-Specific Setup

#### Windows
For QR code decoding, download zbar from:
https://sourceforge.net/projects/zbar/

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install libzbar0
```

#### macOS
```bash
brew install zbar
```

## 📦 Tools Overview

### 1. Image Comparison Tool

Compare two images using multiple algorithms:
- **SSIM (Structural Similarity Index)** - Measures structural similarity
- **Histogram Comparison** - Analyzes color distribution
- **Pixel Difference Detection** - Finds exact pixel changes

**Features:**
- Side-by-side comparison view
- Difference overlay visualization
- SSIM heatmap display
- PDF and JSON report export
- Batch processing for multiple image pairs

**Usage:**
```bash
python py_img_compare.py
```

### 2. Image Marker Tool

Interactive annotation tool for marking points of interest on images.

**Features:**
- Multiple marker categories with colors
- Labels and descriptions
- Resolution-independent relative coordinates
- CSV and JSON import/export
- Full undo/redo support
- Marker search functionality

**Usage:**
```bash
python py_img_marker.py
```

**Keyboard Shortcuts:**
- `Ctrl+O` - Open image
- `Ctrl+S` - Save markers
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo
- `Ctrl+F` - Search markers
- `1-5` - Quick category selection
- `Delete` - Remove all markers

### 3. Steganography Tool

Hide data within images using Least Significant Bit (LSB) encoding.

**Features:**
- Two algorithms: Standard LSB and LSB Random
- AES-256 encryption with password protection
- Configurable bits per channel (1-3)
- Automatic bit selection
- SHA-256 integrity checking
- Compression support

**Usage:**
```bash
python py_img_stego.py
```

**Security:**
- Password-based encryption using PBKDF2
- 100,000 iterations for key derivation
- AES-256-CBC encryption
- SHA-256 hash verification

### 4. QR Code Generator

Generate and decode QR codes with extensive customization.

**Features:**
- Generate QR codes with custom content
- Decode QR codes from images
- Adjustable error correction levels (7%-30%)
- Custom colors (foreground/background)
- Configurable size and border
- Batch generation from text files

**Usage:**
```bash
python py_qr_code_generator.py
```

**Error Correction Levels:**
- **Low (7%)** - Fastest generation, minimal redundancy
- **Medium (15%)** - Balanced (default)
- **Quartile (25%)** - Good error recovery
- **High (30%)** - Maximum error recovery

### 5. Data to Image Encoder

Encode arbitrary data into PNG images using full RGB color depth.

**Features:**
- 3 bytes per pixel (RGB channels)
- Reed-Solomon error correction
- CRC32 checksums for integrity
- Drag & drop file support
- Binary file support
- Capacity calculator

**Usage:**
```bash
python py_text_2_img.py
```

**Capacity Examples:**
- 100x100 image: ~29 KB
- 500x500 image: ~735 KB
- 1000x1000 image: ~2.9 MB
- 1920x1080 image: ~6.2 MB

## 💡 Usage Examples

### Example 1: Compare Two Images

```python
# Via GUI
python py_img_compare.py
# 1. Load Image 1
# 2. Load Image 2
# 3. Click "Compare"
# 4. Export results as PDF or JSON

# Batch Processing
# File → Batch Compare
# Select multiple image pairs
# Results saved automatically
```

### Example 2: Annotate an Image

```python
python py_img_marker.py
# 1. Open image
# 2. Select category
# 3. Click on image to place markers
# 4. Double-click marker to edit
# 5. Save as JSON or export to CSV
```

### Example 3: Hide Data in Image

```python
python py_img_stego.py
# Encode Mode:
# 1. Enter text or load file
# 2. Set password (optional)
# 3. Configure settings
# 4. Click "Encode"

# Decode Mode:
# 1. Select stego image
# 2. Enter password
# 3. Click "Decode"
```

### Example 4: Generate QR Codes

```python
python py_qr_code_generator.py
# 1. Enter URL or text
# 2. Adjust settings (size, colors, error correction)
# 3. Click "Generate"
# 4. Save QR code

# Batch Generation:
# Create text file with one entry per line
# Click "Batch Generate"
# Select input file and output directory
```

### Example 5: Encode Data into Image

```python
python py_text_2_img.py
# Encode:
# 1. Enter text or drop file
# 2. Set ECC symbols (10 recommended)
# 3. Click "Calculate Capacity"
# 4. Click "Encode"

# Decode:
# 1. Switch to Decode mode
# 2. Select data image
# 3. Click "Decode"
```

## ⚙️ Configuration

### Config Directory Structure

```
config/
├── config.json          # Main configuration
└── logs/               # Log files (auto-created)
```

### Sample config.json

```json
{
  "main_window_name": "Image Processing Tools",
  "icon": "assets/icon.png",
  "textbox": "https://example.com",
  "filename": "output.png",
  "log_level": "INFO",
  "log_to_file": true,
  "log_rotation": true,
  "max_log_size_mb": 10
}
```

## 📊 Logging

All tools include comprehensive logging for debugging and error tracking.

### Log Levels

- **DEBUG** - Detailed diagnostic information
- **INFO** - General informational messages
- **WARNING** - Warning messages for potential issues
- **ERROR** - Error messages for failures
- **CRITICAL** - Critical errors that may crash the application

### Log Locations

Logs are stored in:
- `config/logs/py_img_compare.log`
- `config/logs/py_img_marker.log`
- `config/logs/py_img_stego.log`
- `config/logs/py_qr_code_generator.log`
- `config/logs/py_text_2_img.log`

### Log Rotation

Logs automatically rotate when they reach 10 MB (configurable).
Up to 5 backup files are kept.

### Viewing Logs

```bash
# View latest log
tail -f config/logs/py_img_compare.log

# View with color (if colorlog installed)
cat config/logs/py_img_compare.log
```

## 🔍 Troubleshooting

### Common Issues

#### Issue: "ModuleNotFoundError: No module named 'X'"
**Solution:**
```bash
pip install -r requirements.txt
```

#### Issue: QR code decoding fails
**Solution:**
Ensure zbar is installed (see Platform-Specific Setup above)

#### Issue: "ImportError: DLL load failed" (Windows)
**Solution:**
Install Visual C++ Redistributable:
https://aka.ms/vs/17/release/vc_redist.x64.exe

#### Issue: GUI doesn't start
**Solution:**
Check Python version (must be 3.8+):
```bash
python --version
```

#### Issue: Images don't display correctly
**Solution:**
Reinstall Pillow:
```bash
pip uninstall Pillow
pip install Pillow --no-cache-dir
```

#### Issue: High memory usage
**Solution:**
- Process smaller images
- Reduce batch size
- Close other applications
- Check logs for memory warnings

### Error Messages

**"Failed to load images!"**
- Check file permissions
- Verify image format is supported (PNG, JPG, BMP, GIF)
- Ensure file path is correct

**"Insufficient capacity!"**
- Reduce data size or increase image dimensions
- Enable compression
- Use higher bits per channel

**"SHA-256 mismatch!"**
- Wrong password used
- Data corrupted
- Wrong bits per channel setting

**"No QR code found in image!"**
- Image quality too low
- QR code too small
- Wrong image selected

### Debug Mode

Enable detailed logging:

```python
# Add at the start of any script
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🧪 Testing

### Manual Testing

Each tool includes test scenarios:

```bash
# Test comparison tool
python py_img_compare.py
# Load test_images/img1.png and img2.png

# Test marker tool
python py_img_marker.py
# Load test_images/sample.jpg and place markers

# Test steganography
python py_img_stego.py
# Encode "Hello World" with password "test123"

# Test QR generator
python py_qr_code_generator.py
# Generate QR for "https://example.com"

# Test data encoder
python py_text_2_img.py
# Encode a text file
```

### Automated Testing (Future)

Unit tests will be added in the `tests/` directory.

## 📈 Performance Tips

1. **Image Comparison:**
   - Use lower resolution images for faster comparison
   - Reduce threshold for fewer difference regions
   - Disable SSIM heatmap if not needed

2. **Marker Tool:**
   - Limit markers to < 1000 per image
   - Use search instead of scrolling through all markers

3. **Steganography:**
   - Use 2 bits per channel for balance
   - Enable compression for text data
   - Use LSB Random for better security

4. **QR Generator:**
   - Use Medium error correction for balance
   - Smaller box size = smaller file size
   - Batch generate for many QR codes

5. **Data Encoder:**
   - Use 10 ECC symbols (default)
   - Compress text data
   - Calculate capacity before encoding

## 🔒 Security Considerations

### Steganography Tool
- Use strong passwords (12+ characters)
- Never reuse passwords
- Passwords are never logged
- Use LSB Random for better security

### Data Encoder
- CRC32 only detects corruption, not tampering
- Use external encryption for sensitive data
- ECC can correct limited corruption

### QR Codes
- Do not encode sensitive data without encryption
- Use HTTPS URLs only
- Higher error correction = larger QR codes

## 📝 File Formats

### Supported Input Formats
- **Images:** PNG, JPG, JPEG, BMP, GIF
- **Data:** Any file type (binary or text)
- **CSV:** UTF-8 encoded with headers

### Output Formats
- **Images:** PNG (recommended), JPG, BMP
- **Reports:** PDF, JSON, CSV
- **Markers:** JSON, CSV

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Code Style:**
   - Follow PEP 8
   - Use type hints
   - Add docstrings
   - Include error handling

2. **Testing:**
   - Test on Windows, Linux, and macOS if possible
   - Verify all features work
   - Check for memory leaks

3. **Documentation:**
   - Update README.md
   - Add comments for complex logic
   - Update requirements.txt if adding dependencies

4. **Commits:**
   - Use clear commit messages
   - One feature per commit
   - Reference issues if applicable

## 📄 License

Copyright [2025] [ecki]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## 🙏 Acknowledgments

- **PyQt6** - GUI framework
- **OpenCV** - Image processing
- **Pillow (PIL)** - Image manipulation
- **scikit-image** - SSIM calculation
- **qrcode** - QR code generation
- **pyzbar** - QR code decoding
- **reedsolo** - Reed-Solomon error correction
- **cryptography** - AES encryption

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues first
- Provide logs and error messages
- Include Python version and OS

### Version History
- **v3.0** - GUI interfaces, encryption, batch processing
- **v2.0** - Enhanced features, error correction
- **v1.0** - Initial release

## 🎓 Learning Resources

These tools demonstrate:
- PyQt6 GUI development patterns
- Image processing with OpenCV and PIL
- Threading and background workers
- Error correction algorithms
- Cryptography implementation
- File I/O and serialization
- User experience design

Perfect for learning or as reference implementations!

---

**Happy Image Processing! 🎨**
