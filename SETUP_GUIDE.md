# Setup Guide - Image Processing Tools Suite

Complete installation and configuration guide for all tools.

## Table of Contents
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Platform-Specific Setup](#platform-specific-setup)
- [Configuration](#configuration)
- [Logging Setup](#logging-setup)
- [Testing Installation](#testing-installation)
- [Troubleshooting](#troubleshooting)

## Quick Start

For experienced users who want to get started immediately:

```bash
# Clone repository
git clone <repository-url>
cd image-processing-tools

# Install dependencies
pip install -r requirements.txt

# Run a tool
python py_img_compare.py
```

## Detailed Installation

### Step 1: Check Prerequisites

Verify Python installation:
```bash
python --version
# Should show Python 3.8 or higher
```

If Python is not installed:
- **Windows**: Download from https://www.python.org/downloads/
- **Linux**: `sudo apt-get install python3 python3-pip`
- **macOS**: `brew install python3`

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install individually:
pip install PyQt6>=6.6.0
pip install Pillow>=10.0.0
pip install opencv-python>=4.8.0
pip install scikit-image>=0.21.0
pip install numpy>=1.24.0
pip install qrcode[pil]>=7.4.0
pip install pyzbar>=0.1.9
pip install reportlab>=4.0.0
pip install reedsolo>=1.7.0
pip install cryptography>=41.0.0
pip install colorlog>=6.7.0  # Optional: For colored logs
```

### Step 4: Verify Installation

```bash
# Test imports
python -c "import PyQt6; print('PyQt6: OK')"
python -c "import PIL; print('Pillow: OK')"
python -c "import cv2; print('OpenCV: OK')"
python -c "import qrcode; print('qrcode: OK')"
python -c "from reedsolo import RSCodec; print('reedsolo: OK')"
```

## Platform-Specific Setup

### Windows

#### 1. Install Visual C++ Redistributable

Some packages (like OpenCV) require Visual C++ runtime:

Download and install from:
https://aka.ms/vs/17/release/vc_redist.x64.exe

#### 2. Install zbar for QR Code Decoding

1. Download zbar DLL from: https://sourceforge.net/projects/zbar/
2. Extract to a folder (e.g., `C:\zbar`)
3. Add to PATH:
   - Open "Environment Variables"
   - Edit "Path" in User Variables
   - Add `C:\zbar\bin`
4. Restart terminal

#### 3. Verify zbar Installation

```bash
python -c "from pyzbar import pyzbar; print('pyzbar: OK')"
```

### Linux (Ubuntu/Debian)

#### 1. Install System Dependencies

```bash
# Update package list
sudo apt-get update

# Install system dependencies
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    libzbar0 \
    libopencv-dev \
    libjpeg-dev \
    zlib1g-dev
```

#### 2. Install Python Packages

```bash
pip install -r requirements.txt
```

#### 3. Fix Permission Issues (if needed)

```bash
# If you get permission errors
pip install --user -r requirements.txt
```

### Linux (Fedora/RHEL)

```bash
# Install dependencies
sudo dnf install -y \
    python3-devel \
    zbar \
    opencv-devel \
    libjpeg-turbo-devel \
    zlib-devel

# Install Python packages
pip install -r requirements.txt
```

### macOS

#### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install System Dependencies

```bash
# Install zbar for QR code decoding
brew install zbar

# Install other dependencies
brew install python3
brew install opencv
```

#### 3. Install Python Packages

```bash
pip3 install -r requirements.txt
```

#### 4. Fix OpenCV Issues (if needed)

```bash
# If OpenCV doesn't work
pip3 uninstall opencv-python
pip3 install opencv-python --no-cache-dir
```

## Configuration

### Directory Structure

Create the following directory structure:

```
image-processing-tools/
├── config/
│   ├── config.json (optional)
│   └── logs/ (auto-created)
├── py_img_compare.py
├── py_img_marker.py
├── py_img_stego.py
├── py_qr_code_generator.py
├── py_text_2_img.py
├── utils_logger.py
├── utils_error_handler.py
├── requirements.txt
├── README.md
└── SETUP_GUIDE.md
```

### Create Configuration File (Optional)

Create `config/config.json`:

```json
{
  "main_window_name": "Image Processing Tools",
  "icon": "assets/icon.png",
  "textbox": "https://example.com",
  "filename": "output.png",
  "log_level": "INFO",
  "log_to_file": true,
  "log_to_console": true,
  "log_rotation": true,
  "max_log_size_mb": 10,
  "max_log_backups": 5
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `main_window_name` | string | "Image Processing Tools" | Main window title |
| `icon` | string | "assets/icon.png" | Path to window icon |
| `textbox` | string | "https://example.com" | Default text for QR generator |
| `filename` | string | "output.png" | Default output filename |
| `log_level` | string | "INFO" | Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `log_to_file` | boolean | true | Enable file logging |
| `log_to_console` | boolean | true | Enable console logging |
| `log_rotation` | boolean | true | Enable log rotation |
| `max_log_size_mb` | number | 10 | Max log file size in MB |
| `max_log_backups` | number | 5 | Number of backup log files |

## Logging Setup

### Default Logging

Logs are automatically created in `config/logs/` when you run any tool:

```
config/logs/
├── py_img_compare.log
├── py_img_marker.log
├── py_img_stego.log
├── py_qr_code_generator.log
└── py_text_2_img.log
```

### Log Levels

Set log level in code or config file:

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors

### Viewing Logs

```bash
# View latest entries
tail -f config/logs/py_img_compare.log

# View all logs
cat config/logs/py_img_compare.log

# Search logs
grep "ERROR" config/logs/*.log
```

### Log Rotation

Logs automatically rotate when they reach 10 MB (configurable).
Up to 5 backup files are kept (configurable).

Example log files:
```
py_img_compare.log          # Current log
py_img_compare.log.1        # 1st backup
py_img_compare.log.2        # 2nd backup
...
py_img_compare.log.5        # 5th backup (oldest)
```

### Colored Console Output

Install `colorlog` for colored console output:

```bash
pip install colorlog
```

Colors by log level:
- DEBUG: Cyan
- INFO: Green
- WARNING: Yellow
- ERROR: Red
- CRITICAL: Magenta

## Testing Installation

### Test 1: Import All Modules

```bash
python -c "
from utils_logger import get_logger
from utils_error_handler import handle_errors
from PIL import Image
import cv2
import qrcode
from reedsolo import RSCodec
print('✓ All modules imported successfully')
"
```

### Test 2: Run Logger Test

```bash
python utils_logger.py
```

Expected output:
```
[timestamp] INFO - Logger initialized for test_tool
[timestamp] DEBUG - This is a debug message
[timestamp] INFO - This is an info message
...
Logs written to: /path/to/config/logs
```

### Test 3: Run Error Handler Test

```bash
python utils_error_handler.py
```

Expected output:
```
[timestamp] ERROR - ToolError in test_function_1: Test file error
Result: None
...
Check logs in config/logs/error_handler_test.log
```

### Test 4: Run Each Tool

```bash
# Test Image Comparison Tool
python py_img_compare.py
# Load two images, click "Compare"

# Test Image Marker Tool
python py_img_marker.py
# Load an image, place markers

# Test Steganography Tool
python py_img_stego.py
# Enter text, click "Encode"

# Test QR Code Generator
python py_qr_code_generator.py
# Enter text, click "Generate"

# Test Data Encoder
python py_text_2_img.py
# Enter text, click "Encode"
```

### Test 5: Check Log Files

```bash
# Verify logs were created
ls -la config/logs/

# Check a log file
cat config/logs/py_img_compare.log
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'X'"

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install <package-name>

# If still failing, try:
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Issue: "ImportError: DLL load failed" (Windows)

**Solution:**
1. Install Visual C++ Redistributable (see Windows setup)
2. Reinstall problematic package:
```bash
pip uninstall opencv-python
pip install opencv-python --no-cache-dir
```

### Issue: pyzbar not working

**Windows:**
```bash
# Ensure zbar is in PATH
echo %PATH%
# Should include C:\zbar\bin

# Test zbar installation
python -c "from ctypes import cdll; cdll.LoadLibrary('libzbar-64.dll'); print('OK')"
```

**Linux:**
```bash
# Reinstall zbar
sudo apt-get install --reinstall libzbar0

# Check if library exists
ldconfig -p | grep zbar
```

**macOS:**
```bash
# Reinstall zbar
brew reinstall zbar

# Check installation
brew list zbar
```

### Issue: Permission denied errors

**Linux/macOS:**
```bash
# Use user installation
pip install --user -r requirements.txt

# Or fix permissions
sudo chown -R $USER ~/.local
```

**Windows:**
```bash
# Run as administrator
# Right-click Command Prompt → Run as Administrator
pip install -r requirements.txt
```

### Issue: High memory usage

**Solution:**
1. Close other applications
2. Process smaller images
3. Reduce batch size
4. Check logs for memory warnings:
```bash
grep "memory\|Memory" config/logs/*.log
```

### Issue: GUI doesn't start

**Solution:**
```bash
# Check Python version
python --version
# Must be 3.8 or higher

# Check PyQt6 installation
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6: OK')"

# Reinstall PyQt6
pip uninstall PyQt6
pip install PyQt6
```

### Issue: Logs not being created

**Solution:**
```bash
# Check permissions
ls -la config/

# Create logs directory manually
mkdir -p config/logs
chmod 755 config/logs

# Check disk space
df -h

# Run tool with elevated permissions (if needed)
sudo python py_img_compare.py  # Linux/macOS
# Run as Administrator (Windows)
```

### Issue: Images not displaying correctly

**Solution:**
```bash
# Reinstall Pillow
pip uninstall Pillow
pip install Pillow --no-cache-dir

# Check image format
file path/to/image.png

# Try different image format
convert image.jpg image.png  # If ImageMagick installed
```

### Issue: Slow performance

**Solution:**
1. **For Image Comparison:**
   - Use lower resolution images
   - Reduce threshold
   - Disable SSIM heatmap

2. **For Marker Tool:**
   - Limit markers to < 1000 per image
   - Disable label display

3. **For Steganography:**
   - Use 2 bits per channel (not 3)
   - Enable compression

4. **General:**
   - Check CPU usage
   - Close other applications
   - Update drivers

### Issue: cryptography package fails to install

**Windows:**
```bash
# Install build tools
pip install wheel setuptools

# Install cryptography
pip install cryptography
```

**Linux:**
```bash
# Install development packages
sudo apt-get install build-essential libssl-dev libffi-dev python3-dev

# Install cryptography
pip install cryptography
```

**macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install cryptography
pip install cryptography
```

## Getting Help

### Check Logs First

```bash
# View recent errors
grep "ERROR\|CRITICAL" config/logs/*.log | tail -20

# View specific tool log
less config/logs/py_img_compare.log
```

### Enable Debug Logging

Add to beginning of any script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set in `config/config.json`:
```json
{
  "log_level": "DEBUG"
}
```

### Collect System Information

```bash
# Python version
python --version

# Installed packages
pip list

# Operating system
# Linux:
uname -a
# Windows:
systeminfo
# macOS:
sw_vers
```

### Report Issues

When reporting issues, include:
1. Error message
2. Relevant log entries from `config/logs/`
3. Python version
4. Operating system
5. Steps to reproduce

## Advanced Setup

### Running from Source (Development)

```bash
# Clone repository
git clone <repository-url>
cd image-processing-tools

# Create development environment
python -m venv dev-venv
source dev-venv/bin/activate  # Linux/macOS
dev-venv\Scripts\activate     # Windows

# Install in editable mode
pip install -e .

# Run tests (if available)
python -m pytest tests/
```

### Docker Setup (Future)

```bash
# Build Docker image
docker build -t image-processing-tools .

# Run container
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  image-processing-tools
```

### Creating Executable (PyInstaller)

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --windowed py_img_compare.py

# Executable will be in dist/
```

## Next Steps

After successful installation:

1. **Read the README.md** for usage examples
2. **Check the logs** to verify everything works
3. **Try each tool** with sample data
4. **Configure settings** in `config/config.json`
5. **Set up shortcuts** for frequently used tools

---

**Need more help?** Check the [README.md](README.md) or open an issue on GitHub.
