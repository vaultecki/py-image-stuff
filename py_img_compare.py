# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Image Comparison Tool - With Enhanced Logging & Error Handling
Example integration showing how to use the new utilities.
"""
import sys
import json
import tempfile
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import cv2
from skimage.metrics import structural_similarity as ssim
from PyQt6.QtGui import QPixmap, QImage, QPen, QColor
from PyQt6.QtCore import Qt, QRectF, QThread, pyqtSignal
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget,
                             QFileDialog, QHBoxLayout, QVBoxLayout,
                             QPushButton, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QLabel, QSpinBox,
                             QMessageBox, QProgressBar, QComboBox,
                             QGroupBox, QAction)

# Import new utilities
from utils_logger import get_logger, LoggedOperation
from utils_error_handler import (handle_errors, ErrorHandler, ImageError,
                                 FileError, validate_image_file,
                                 safe_file_operation, ErrorSeverity)


class ZoomableGraphicsView(QGraphicsView):
    """Graphics View with zoom functionality"""

    def __init__(self, scene):
        super().__init__(scene)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._zoom = 0

    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        if event.angleDelta().y() > 0:
            factor = 1.15
            self._zoom += 1
        else:
            factor = 1 / 1.15
            self._zoom -= 1

        if self._zoom > 0:
            self.scale(factor, factor)
        elif self._zoom == 0:
            self.resetTransform()
        else:
            self._zoom = 0


class ComparisonWorker(QThread):
    """Background worker for image comparison"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, comparator, logger):
        super().__init__()
        self.comparator = comparator
        self.logger = logger

    def run(self):
        """Run comparison with logging"""
        try:
            with LoggedOperation(self.logger, "image_comparison",
                                 img1=self.comparator.img1_path,
                                 img2=self.comparator.img2_path):

                self.progress.emit(10)
                self.logger.info("Loading images...")

                if not self.comparator.load_images():
                    raise ImageError("Failed to load images",
                                     details={'issue': 'invalid_data'})

                self.progress.emit(20)
                self.logger.info("Resizing images to match dimensions...")
                self.comparator.resize_images_to_match()

                self.progress.emit(30)
                self.logger.info("Calculating histogram similarity...")
                self.comparator.calculate_histogram_similarity()

                self.progress.emit(40)
                self.logger.info("Calculating SSIM...")
                self.comparator.calculate_ssim()

                self.progress.emit(50)
                self.logger.info("Finding differences with OpenCV...")
                diff_count = self.comparator.find_differences_opencv()
                self.logger.info(f"Found {diff_count} difference regions")

                self.progress.emit(70)
                self.logger.info("Creating difference overlay...")
                self.comparator.create_difference_overlay()

                self.progress.emit(90)

                # Log metrics
                self.logger.log_performance_metric("ssim_score",
                                                   self.comparator.ssim_score, "%")
                self.logger.log_performance_metric("histogram_similarity",
                                                   self.comparator.histogram_similarity, "%")
                self.logger.log_performance_metric("difference_regions",
                                                   len(self.comparator.differences))

                self.finished.emit(self.comparator)
                self.progress.emit(100)

        except Exception as e:
            self.logger.exception(f"Comparison failed: {e}")
            self.error.emit(str(e))


class ImageComparator:
    """Compares two images with multiple methods"""

    def __init__(self, img1_path, img2_path, threshold=30, min_area=100, logger=None):
        self.img1_path = img1_path
        self.img2_path = img2_path
        self.threshold = threshold
        self.min_area = min_area
        self.logger = logger or get_logger("image_comparator")

        self.differences = []
        self.histogram_similarity = None
        self.ssim_score = None
        self.ssim_image = None
        self.overlay_image = None
        self.img1_cv = None
        self.img2_cv = None

        self.logger.debug(f"ImageComparator initialized with threshold={threshold}, min_area={min_area}")

    @handle_errors(show_dialog=False)
    def load_images(self):
        """Load both images with validation"""
        self.logger.info(f"Loading image 1: {self.img1_path}")
        validate_image_file(self.img1_path)

        self.logger.info(f"Loading image 2: {self.img2_path}")
        validate_image_file(self.img2_path)

        try:
            # Load with PIL
            self.img1 = Image.open(self.img1_path).convert('RGB')
            self.img2 = Image.open(self.img2_path).convert('RGB')

            # Load with OpenCV
            self.img1_cv = cv2.imread(str(self.img1_path))
            self.img2_cv = cv2.imread(str(self.img2_path))

            self.logger.info(f"Images loaded successfully - Image1: {self.img1.size}, Image2: {self.img2.size}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load images: {e}", exc_info=True)
            raise ImageError(
                f"Error loading images: {e}",
                details={'issue': 'invalid_data'}
            )

    def resize_images_to_match(self):
        """Resize images to match dimensions"""
        if self.img1.size != self.img2.size:
            max_width = max(self.img1.width, self.img2.width)
            max_height = max(self.img1.height, self.img2.height)

            self.logger.info(f"Resizing images to {max_width}x{max_height}")

            self.img1 = self.img1.resize((max_width, max_height), Image.LANCZOS)
            self.img2 = self.img2.resize((max_width, max_height), Image.LANCZOS)
            self.img1_cv = cv2.resize(self.img1_cv, (max_width, max_height))
            self.img2_cv = cv2.resize(self.img2_cv, (max_width, max_height))

    def calculate_histogram_similarity(self):
        """Calculate histogram similarity using OpenCV"""
        hsv1 = cv2.cvtColor(self.img1_cv, cv2.COLOR_BGR2HSV)
        hsv2 = cv2.cvtColor(self.img2_cv, cv2.COLOR_BGR2HSV)

        hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

        cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        self.histogram_similarity = (correlation + 1) / 2 * 100

        self.logger.debug(f"Histogram similarity calculated: {self.histogram_similarity:.2f}%")

    def calculate_ssim(self):
        """Calculate Structural Similarity Index (SSIM)"""
        gray1 = cv2.cvtColor(self.img1_cv, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(self.img2_cv, cv2.COLOR_BGR2GRAY)

        score, diff = ssim(gray1, gray2, full=True)
        self.ssim_score = score * 100

        diff = (diff * 255).astype("uint8")
        self.ssim_image = diff

        self.logger.debug(f"SSIM calculated: {self.ssim_score:.2f}%")

    def find_differences_opencv(self):
        """Find differences using OpenCV"""
        gray1 = cv2.cvtColor(self.img1_cv, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(self.img2_cv, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        self.differences = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(contour)
                padding = 5
                self.differences.append({
                    'x': max(0, x - padding),
                    'y': max(0, y - padding),
                    'width': w + 2 * padding,
                    'height': h + 2 * padding,
                    'area': int(area)
                })

        return len(self.differences)

    def create_difference_overlay(self):
        """Create an overlay visualization showing differences"""
        overlay = self.img1.copy()
        draw = ImageDraw.Draw(overlay, 'RGBA')

        for diff in self.differences:
            draw.rectangle(
                [diff['x'], diff['y'],
                 diff['x'] + diff['width'], diff['y'] + diff['height']],
                fill=(255, 0, 0, 80),
                outline=(255, 0, 0, 255),
                width=3
            )

        self.overlay_image = overlay

    @handle_errors(show_dialog=True)
    def export_json(self, output_path):
        """Export comparison results as JSON"""
        self.logger.info(f"Exporting JSON to: {output_path}")

        def _export():
            data = {
                'timestamp': datetime.now().isoformat(),
                'image1': str(Path(self.img1_path).name),
                'image2': str(Path(self.img2_path).name),
                'metrics': {
                    'ssim_score': float(self.ssim_score),
                    'histogram_similarity': float(self.histogram_similarity),
                    'difference_regions': len(self.differences),
                    'total_different_pixels': sum(d['area'] for d in self.differences)
                },
                'differences': self.differences,
                'settings': {
                    'threshold': self.threshold,
                    'min_area': self.min_area
                }
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"JSON export successful: {output_path}")
            return True

        return safe_file_operation(
            _export,
            output_path,
            "JSON export",
            logger=self.logger,
            show_dialog=True
        )

    @handle_errors(show_dialog=True)
    def export_pdf_report(self, output_path):
        """Export comparison results as PDF report"""
        self.logger.info(f"Exporting PDF to: {output_path}")

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError as e:
            self.logger.error("reportlab not installed")
            raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")

        with ErrorHandler(self.logger, "PDF export", show_dialog=True):
            c = canvas.Canvas(str(output_path), pagesize=A4)
            width, height = A4

            # [PDF generation code - same as before]
            # Title, summary, images, etc.

            c.save()
            self.logger.info(f"PDF export successful: {output_path}")


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = "Image Comparison Tool - Enhanced"
        self.setWindowTitle(self.title)

        # Initialize logger
        self.logger = get_logger("image_compare_tool")
        self.session_id = self.logger.create_session_log()

        self.logger.info(f"Application started - Version 3.0")

        # Data structure
        self.image_paths = {1: None, 2: None}
        self.pixmap_items = {1: None, 2: None}
        self.worker = None
        self.comparator = None

        self.setup_ui()
        self.setup_menu()
        self.showMaximized()

    def setup_ui(self):
        """Create user interface"""
        # [UI setup code - same as before but with logging for user actions]
        self.logger.debug("Setting up user interface")
        # ... rest of UI code ...

    def setup_menu(self):
        """Create menu bar"""
        # [Menu setup code - same as before]
        self.logger.debug("Setting up menu bar")
        # ... rest of menu code ...

    @handle_errors(show_dialog=True)
    def load_image(self, image_num):
        """Load an image with error handling"""
        self.logger.log_user_action("load_image", f"image_{image_num}")

        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.gif)")

        if file_dialog.exec():
            filename = file_dialog.selectedFiles()[0]

            # Validate image
            with ErrorHandler(self.logger, f"loading image {image_num}", show_dialog=True):
                validate_image_file(filename)

                self.image_paths[image_num] = filename
                pixmap = QPixmap(filename)

                scene = self.scene1 if image_num == 1 else self.scene2
                scene.clear()

                item = QGraphicsPixmapItem(pixmap)
                scene.addItem(item)
                self.pixmap_items[image_num] = item

                self.logger.log_file_operation("read", filename, success=True)
                self.logger.info(f"Image {image_num} loaded: {Path(filename).name}")

    @handle_errors(show_dialog=True)
    def compare_images(self):
        """Compare the two images"""
        self.logger.log_user_action("compare_images")

        if not all(self.image_paths.values()):
            self.logger.warning("Attempted comparison without both images loaded")
            QMessageBox.warning(self, "Error", "Please load both images first!")
            return

        # Create comparator with logger
        self.comparator = ImageComparator(
            self.image_paths[1],
            self.image_paths[2],
            threshold=self.threshold_spin.value(),
            min_area=self.min_area_spin.value(),
            logger=self.logger
        )

        # Show progress bar
        self.progress_bar.show()
        self.progress_bar.setValue(0)

        # Create worker thread with logger
        self.worker = ComparisonWorker(self.comparator, self.logger)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_comparison_finished)
        self.worker.error.connect(self.on_comparison_error)
        self.worker.start()

    def on_comparison_finished(self, comparator):
        """Handle comparison completion"""
        self.progress_bar.hide()
        self.comparator = comparator

        self.logger.info(f"Comparison completed - SSIM: {comparator.ssim_score:.2f}%, "
                         f"Differences: {len(comparator.differences)}")

        # Update UI
        # [UI update code - same as before]

    def on_comparison_error(self, error_msg):
        """Handle comparison error"""
        self.progress_bar.hide()
        self.logger.error(f"Comparison error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)

    def closeEvent(self, event):
        """Handle application close"""
        self.logger.end_session_log(self.session_id)
        self.logger.info("Application closed")
        event.accept()


def main():
    """Main entry point"""
    # Create logger for main
    logger = get_logger("main")
    logger.info("=== Image Comparison Tool Starting ===")

    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        exit_code = app.exec()

        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
