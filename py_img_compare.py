# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Image Comparison Tool - Enhanced Version
Compares two images with multiple methods:
- Pixel difference detection with OpenCV
- Histogram comparison
- SSIM (Structural Similarity Index)
- PDF report export
"""
import sys
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
from skimage.metrics import structural_similarity as ssim
from PyQt6.QtGui import QPixmap, QImage, QPen, QColor, QBrush
from PyQt6.QtCore import Qt, QRectF, QThread, pyqtSignal
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget,
                             QFileDialog, QHBoxLayout, QVBoxLayout,
                             QPushButton, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QLabel, QSpinBox,
                             QMessageBox, QProgressBar, QComboBox,
                             QCheckBox, QGroupBox)


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

    def __init__(self, comparator):
        super().__init__()
        self.comparator = comparator

    def run(self):
        try:
            self.progress.emit(10)

            # Load images
            if not self.comparator.load_images():
                self.error.emit("Failed to load images!")
                return

            self.progress.emit(20)

            # Resize to match
            self.comparator.resize_images_to_match()
            self.progress.emit(30)

            # Calculate histogram comparison
            self.comparator.calculate_histogram_similarity()
            self.progress.emit(40)

            # Calculate SSIM
            self.comparator.calculate_ssim()
            self.progress.emit(50)

            # Find differences with OpenCV
            self.comparator.find_differences_opencv()
            self.progress.emit(70)

            # Create overlay visualization
            self.comparator.create_difference_overlay()
            self.progress.emit(90)

            # Emit results
            self.finished.emit(self.comparator)
            self.progress.emit(100)

        except Exception as e:
            self.error.emit(f"Comparison error: {str(e)}")


class ImageComparator:
    """Compares two images with multiple methods"""

    def __init__(self, img1_path, img2_path, threshold=30, min_area=100):
        self.img1_path = img1_path
        self.img2_path = img2_path
        self.threshold = threshold
        self.min_area = min_area
        self.differences = []
        self.histogram_similarity = None
        self.ssim_score = None
        self.ssim_image = None
        self.overlay_image = None
        self.img1_cv = None
        self.img2_cv = None

    def load_images(self):
        """Load both images"""
        try:
            # Load with PIL
            self.img1 = Image.open(self.img1_path).convert('RGB')
            self.img2 = Image.open(self.img2_path).convert('RGB')

            # Load with OpenCV (for faster processing)
            self.img1_cv = cv2.imread(str(self.img1_path))
            self.img2_cv = cv2.imread(str(self.img2_path))

            return True
        except Exception as e:
            print(f"Error loading images: {e}")
            return False

    def resize_images_to_match(self):
        """Resize images to match dimensions"""
        if self.img1.size != self.img2.size:
            # Resize to larger dimensions
            max_width = max(self.img1.width, self.img2.width)
            max_height = max(self.img1.height, self.img2.height)

            # Resize PIL images
            self.img1 = self.img1.resize((max_width, max_height), Image.LANCZOS)
            self.img2 = self.img2.resize((max_width, max_height), Image.LANCZOS)

            # Resize OpenCV images
            self.img1_cv = cv2.resize(self.img1_cv, (max_width, max_height))
            self.img2_cv = cv2.resize(self.img2_cv, (max_width, max_height))

    def calculate_histogram_similarity(self):
        """Calculate histogram similarity using OpenCV"""
        # Convert to HSV for better comparison
        hsv1 = cv2.cvtColor(self.img1_cv, cv2.COLOR_BGR2HSV)
        hsv2 = cv2.cvtColor(self.img2_cv, cv2.COLOR_BGR2HSV)

        # Calculate histograms
        hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

        # Normalize histograms
        cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

        # Calculate correlation (higher is more similar, range: -1 to 1)
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # Convert to percentage (0-100%)
        self.histogram_similarity = (correlation + 1) / 2 * 100

    def calculate_ssim(self):
        """Calculate Structural Similarity Index (SSIM)"""
        # Convert to grayscale
        gray1 = cv2.cvtColor(self.img1_cv, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(self.img2_cv, cv2.COLOR_BGR2GRAY)

        # Calculate SSIM
        score, diff = ssim(gray1, gray2, full=True)
        self.ssim_score = score * 100  # Convert to percentage

        # Convert SSIM difference image for visualization
        diff = (diff * 255).astype("uint8")
        self.ssim_image = diff

    def find_differences_opencv(self):
        """Find differences using OpenCV (much faster than flood fill)"""
        # Convert to grayscale
        gray1 = cv2.cvtColor(self.img1_cv, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(self.img2_cv, cv2.COLOR_BGR2GRAY)

        # Calculate absolute difference
        diff = cv2.absdiff(gray1, gray2)

        # Apply threshold
        _, thresh = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)

        # Find contours (OpenCV is much faster than manual flood fill)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Process contours
        self.differences = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(contour)

                # Add padding
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
        # Create a copy of image 1
        overlay = self.img1.copy()
        draw = ImageDraw.Draw(overlay, 'RGBA')

        # Draw semi-transparent red rectangles over differences
        for diff in self.differences:
            # Draw filled rectangle with transparency
            draw.rectangle(
                [
                    diff['x'],
                    diff['y'],
                    diff['x'] + diff['width'],
                    diff['y'] + diff['height']
                ],
                fill=(255, 0, 0, 80),  # Red with 80/255 transparency
                outline=(255, 0, 0, 255),  # Solid red border
                width=3
            )

        self.overlay_image = overlay

    def export_pdf_report(self, output_path):
        """Export comparison results as PDF report"""
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.units import inch
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors

        # Create PDF
        c = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4

        # Title
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, height - 50, "Image Comparison Report")

        # Timestamp
        c.setFont("Helvetica", 10)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.drawString(50, height - 70, f"Generated: {timestamp}")

        # Separator line
        c.line(50, height - 80, width - 50, height - 80)

        # Summary section
        y_pos = height - 110
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "Comparison Summary")

        y_pos -= 25
        c.setFont("Helvetica", 11)
        c.drawString(70, y_pos, f"Image 1: {Path(self.img1_path).name}")
        y_pos -= 20
        c.drawString(70, y_pos, f"Image 2: {Path(self.img2_path).name}")

        y_pos -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Metrics:")

        y_pos -= 25
        c.setFont("Helvetica", 11)
        c.drawString(70, y_pos, f"• SSIM Score: {self.ssim_score:.2f}% (higher is more similar)")
        y_pos -= 20
        c.drawString(70, y_pos, f"• Histogram Similarity: {self.histogram_similarity:.2f}%")
        y_pos -= 20
        c.drawString(70, y_pos, f"• Difference Regions: {len(self.differences)}")
        y_pos -= 20
        total_area = sum(d['area'] for d in self.differences)
        c.drawString(70, y_pos, f"• Total Different Pixels: {total_area:,}")

        # Add images section
        y_pos -= 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "Visual Comparison")

        # Calculate image dimensions to fit on page
        img_width = (width - 120) / 2
        img_height = img_width * 0.75  # Maintain aspect ratio

        y_pos -= 30

        # Save temporary images for PDF
        temp_img1 = Path("temp_img1.png")
        temp_img2 = Path("temp_img2.png")
        temp_overlay = Path("temp_overlay.png")

        self.img1.save(temp_img1)
        self.img2.save(temp_img2)
        if self.overlay_image:
            self.overlay_image.save(temp_overlay)

        # Add images to PDF
        try:
            # Image 1
            c.drawString(50, y_pos, "Image 1:")
            c.drawImage(str(temp_img1), 50, y_pos - img_height - 5,
                        width=img_width, height=img_height, preserveAspectRatio=True)

            # Image 2
            c.drawString(width / 2 + 10, y_pos, "Image 2:")
            c.drawImage(str(temp_img2), width / 2 + 10, y_pos - img_height - 5,
                        width=img_width, height=img_height, preserveAspectRatio=True)

            # New page for overlay
            if self.overlay_image:
                c.showPage()
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, height - 50, "Difference Overlay")
                c.setFont("Helvetica", 10)
                c.drawString(50, height - 70, "Red areas indicate detected differences")

                # Full width overlay
                overlay_width = width - 100
                overlay_height = overlay_width * 0.75
                c.drawImage(str(temp_overlay), 50, height - 100 - overlay_height,
                            width=overlay_width, height=overlay_height, preserveAspectRatio=True)

        finally:
            # Clean up temporary files
            temp_img1.unlink(missing_ok=True)
            temp_img2.unlink(missing_ok=True)
            temp_overlay.unlink(missing_ok=True)

        # Save PDF
        c.save()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = "Image Comparison Tool - Enhanced"
        self.setWindowTitle(self.title)

        # Data structure for loaded images
        self.image_paths = {1: None, 2: None}
        self.pixmap_items = {1: None, 2: None}
        self.worker = None
        self.comparator = None

        self.setup_ui()
        self.showMaximized()

    def setup_ui(self):
        """Create user interface"""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Top buttons
        button_layout = QHBoxLayout()
        btn_load1 = QPushButton("📁 Load Image 1")
        btn_load1.clicked.connect(lambda: self.load_image(1))
        button_layout.addWidget(btn_load1)

        btn_load2 = QPushButton("📁 Load Image 2")
        btn_load2.clicked.connect(lambda: self.load_image(2))
        button_layout.addWidget(btn_load2)

        btn_compare = QPushButton("🔍 Compare")
        btn_compare.clicked.connect(self.compare_images)
        button_layout.addWidget(btn_compare)

        btn_export = QPushButton("📄 Export PDF Report")
        btn_export.clicked.connect(self.export_pdf)
        button_layout.addWidget(btn_export)

        btn_reset = QPushButton("🔄 Reset")
        btn_reset.clicked.connect(self.reset_view)
        button_layout.addWidget(btn_reset)

        main_layout.addLayout(button_layout)

        # Settings group
        settings_group = QGroupBox("Comparison Settings")
        settings_layout = QHBoxLayout()

        settings_layout.addWidget(QLabel("Threshold:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 255)
        self.threshold_spin.setValue(30)
        self.threshold_spin.setToolTip("Sensitivity for pixel difference (1-255)")
        settings_layout.addWidget(self.threshold_spin)

        settings_layout.addWidget(QLabel("Min. Area:"))
        self.min_area_spin = QSpinBox()
        self.min_area_spin.setRange(1, 1000)
        self.min_area_spin.setValue(100)
        self.min_area_spin.setToolTip("Minimum pixel area to consider")
        settings_layout.addWidget(self.min_area_spin)

        settings_layout.addWidget(QLabel("View Mode:"))
        self.view_mode = QComboBox()
        self.view_mode.addItems(["Side by Side", "Overlay", "SSIM Heatmap"])
        self.view_mode.currentTextChanged.connect(self.change_view_mode)
        settings_layout.addWidget(self.view_mode)

        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Metrics display
        metrics_group = QGroupBox("Comparison Metrics")
        metrics_layout = QHBoxLayout()

        self.ssim_label = QLabel("SSIM: N/A")
        self.ssim_label.setStyleSheet("font-weight: bold; padding: 5px;")
        metrics_layout.addWidget(self.ssim_label)

        self.hist_label = QLabel("Histogram: N/A")
        self.hist_label.setStyleSheet("font-weight: bold; padding: 5px;")
        metrics_layout.addWidget(self.hist_label)

        self.diff_label = QLabel("Differences: N/A")
        self.diff_label.setStyleSheet("font-weight: bold; padding: 5px;")
        metrics_layout.addWidget(self.diff_label)

        metrics_layout.addStretch()
        metrics_group.setLayout(metrics_layout)
        main_layout.addWidget(metrics_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Image views
        images_layout = QHBoxLayout()

        # Image 1
        self.scene1 = QGraphicsScene()
        self.view1 = ZoomableGraphicsView(self.scene1)
        images_layout.addWidget(self.view1)

        # Image 2
        self.scene2 = QGraphicsScene()
        self.view2 = ZoomableGraphicsView(self.scene2)
        images_layout.addWidget(self.view2)

        main_layout.addLayout(images_layout)

        self.setCentralWidget(main_widget)

    def load_image(self, image_num):
        """Load an image"""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.gif)")

        if file_dialog.exec():
            filename = file_dialog.selectedFiles()[0]
            self.image_paths[image_num] = filename

            # Load image into corresponding scene
            pixmap = QPixmap(filename)
            scene = self.scene1 if image_num == 1 else self.scene2
            scene.clear()

            item = QGraphicsPixmapItem(pixmap)
            scene.addItem(item)
            self.pixmap_items[image_num] = item

    def compare_images(self):
        """Compare the two images"""
        if not all(self.image_paths.values()):
            QMessageBox.warning(self, "Error", "Please load both images first!")
            return

        # Create comparator
        self.comparator = ImageComparator(
            self.image_paths[1],
            self.image_paths[2],
            threshold=self.threshold_spin.value(),
            min_area=self.min_area_spin.value()
        )

        # Show progress bar
        self.progress_bar.show()
        self.progress_bar.setValue(0)

        # Create worker thread
        self.worker = ComparisonWorker(self.comparator)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_comparison_finished)
        self.worker.error.connect(self.on_comparison_error)
        self.worker.start()

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def on_comparison_finished(self, comparator):
        """Handle comparison completion"""
        self.progress_bar.hide()
        self.comparator = comparator

        # Update metrics
        self.ssim_label.setText(f"SSIM: {comparator.ssim_score:.2f}%")
        self.hist_label.setText(f"Histogram: {comparator.histogram_similarity:.2f}%")
        self.diff_label.setText(f"Differences: {len(comparator.differences)} regions")

        # Color code SSIM (green=similar, yellow=medium, red=different)
        if comparator.ssim_score > 90:
            self.ssim_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #90EE90;")
        elif comparator.ssim_score > 70:
            self.ssim_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #FFFFE0;")
        else:
            self.ssim_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #FFB6C1;")

        # Apply current view mode
        self.change_view_mode(self.view_mode.currentText())

    def change_view_mode(self, mode):
        """Change visualization mode"""
        if not self.comparator:
            return

        if mode == "Side by Side":
            # Show original images with red boxes
            self.scene1.clear()
            self.scene2.clear()

            # Reload original images
            item1 = QGraphicsPixmapItem(QPixmap(self.image_paths[1]))
            item2 = QGraphicsPixmapItem(QPixmap(self.image_paths[2]))
            self.scene1.addItem(item1)
            self.scene2.addItem(item2)

            # Draw difference boxes
            self.draw_differences(self.comparator.differences)

        elif mode == "Overlay":
            # Show overlay on both views
            if self.comparator.overlay_image:
                self.scene1.clear()
                self.scene2.clear()

                # Convert PIL to QPixmap
                overlay_array = np.array(self.comparator.overlay_image)
                height, width, channel = overlay_array.shape
                bytes_per_line = 3 * width
                q_image = QImage(overlay_array.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)

                item1 = QGraphicsPixmapItem(pixmap)
                item2 = QGraphicsPixmapItem(QPixmap(self.image_paths[2]))
                self.scene1.addItem(item1)
                self.scene2.addItem(item2)

        elif mode == "SSIM Heatmap":
            # Show SSIM difference heatmap
            if self.comparator.ssim_image is not None:
                self.scene1.clear()
                self.scene2.clear()

                # Apply colormap to SSIM image
                ssim_colored = cv2.applyColorMap(self.comparator.ssim_image, cv2.COLORMAP_JET)
                ssim_colored = cv2.cvtColor(ssim_colored, cv2.COLOR_BGR2RGB)

                height, width, channel = ssim_colored.shape
                bytes_per_line = 3 * width
                q_image = QImage(ssim_colored.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)

                item1 = QGraphicsPixmapItem(pixmap)
                item2 = QGraphicsPixmapItem(QPixmap(self.image_paths[2]))
                self.scene1.addItem(item1)
                self.scene2.addItem(item2)

    def on_comparison_error(self, error_msg):
        """Handle comparison error"""
        self.progress_bar.hide()
        QMessageBox.critical(self, "Error", error_msg)

    def draw_differences(self, differences):
        """Draw red rectangles around differences"""
        pen = QPen(QColor(255, 0, 0), 3)

        for diff in differences:
            rect = QRectF(
                diff['x'],
                diff['y'],
                diff['width'],
                diff['height']
            )

            # Draw in both scenes
            self.scene1.addRect(rect, pen)
            self.scene2.addRect(rect, pen)

    def export_pdf(self):
        """Export comparison as PDF report"""
        if not self.comparator:
            QMessageBox.warning(self, "Error", "Please compare images first!")
            return

        # Ask for save location
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF Report",
            f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF Files (*.pdf)"
        )

        if filename:
            try:
                self.comparator.export_pdf_report(filename)
                QMessageBox.information(self, "Success", f"Report exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export PDF:\n{str(e)}")

    def reset_view(self):
        """Reset the view"""
        self.scene1.clear()
        self.scene2.clear()
        self.image_paths = {1: None, 2: None}
        self.pixmap_items = {1: None, 2: None}
        self.comparator = None
        self.progress_bar.hide()

        # Reset metrics
        self.ssim_label.setText("SSIM: N/A")
        self.ssim_label.setStyleSheet("font-weight: bold; padding: 5px;")
        self.hist_label.setText("Histogram: N/A")
        self.diff_label.setText("Differences: N/A")


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    