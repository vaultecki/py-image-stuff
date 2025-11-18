# -*- coding: utf-8 -*-
"""
Image Comparison Tool
Compares two images and highlights differences with red bounding boxes.
"""
import sys
import numpy as np
from PIL import Image
from PyQt6.QtGui import QPixmap, QImage, QPen, QColor
from PyQt6.QtCore import Qt, QRectF, QThread, pyqtSignal
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget,
                             QFileDialog, QHBoxLayout,
                             QVBoxLayout, QPushButton, QGraphicsView,
                             QGraphicsScene, QGraphicsPixmapItem, QLabel,
                             QSpinBox, QMessageBox, QProgressBar)


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

            self.progress.emit(30)

            # Resize to match
            self.comparator.resize_images_to_match()
            self.progress.emit(50)

            # Find differences
            self.comparator.find_differences()
            self.progress.emit(90)

            # Emit results
            self.finished.emit(self.comparator)
            self.progress.emit(100)

        except Exception as e:
            self.error.emit(f"Comparison error: {str(e)}")


class ImageComparator:
    """Compares two images and finds differences"""

    def __init__(self, img1_path, img2_path, threshold=30, min_area=100):
        self.img1_path = img1_path
        self.img2_path = img2_path
        self.threshold = threshold
        self.min_area = min_area
        self.differences = []

    def load_images(self):
        """Load both images"""
        try:
            self.img1 = Image.open(self.img1_path).convert('RGB')
            self.img2 = Image.open(self.img2_path).convert('RGB')
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

            self.img1 = self.img1.resize((max_width, max_height), Image.LANCZOS)
            self.img2 = self.img2.resize((max_width, max_height), Image.LANCZOS)

    def find_differences(self):
        """Find differences between images"""
        # Convert to numpy arrays
        arr1 = np.array(self.img1)
        arr2 = np.array(self.img2)

        # Calculate absolute difference
        diff = np.abs(arr1.astype(int) - arr2.astype(int))

        # Grayscale difference (average across RGB channels)
        gray_diff = np.mean(diff, axis=2).astype(np.uint8)

        # Create binary mask (differences above threshold)
        mask = (gray_diff > self.threshold).astype(np.uint8) * 255

        # Find connected regions
        self.differences = self._find_contours(mask)

        return len(self.differences)

    def _find_contours(self, mask):
        """Find connected difference regions using iterative flood fill"""
        height, width = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        regions = []

        def flood_fill_iterative(start_x, start_y):
            """Non-recursive flood fill algorithm using stack"""
            stack = [(start_x, start_y)]
            points = []

            while stack:
                x, y = stack.pop()

                # Boundary check
                if x < 0 or x >= width or y < 0 or y >= height:
                    continue

                # Already visited or not part of region
                if visited[y, x] or mask[y, x] == 0:
                    continue

                visited[y, x] = True
                points.append((x, y))

                # Add 4-connected neighbors to stack
                stack.append((x + 1, y))
                stack.append((x - 1, y))
                stack.append((x, y + 1))
                stack.append((x, y - 1))

            return points

        # Scan through all pixels
        for y in range(height):
            for x in range(width):
                if mask[y, x] > 0 and not visited[y, x]:
                    region_points = flood_fill_iterative(x, y)

                    if len(region_points) >= self.min_area:
                        # Calculate bounding box
                        xs = [p[0] for p in region_points]
                        ys = [p[1] for p in region_points]

                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)

                        # Add some padding
                        padding = 5
                        regions.append({
                            'x': max(0, x_min - padding),
                            'y': max(0, y_min - padding),
                            'width': min(width - x_min, x_max - x_min + 2 * padding),
                            'height': min(height - y_min, y_max - y_min + 2 * padding),
                            'area': len(region_points)
                        })

        return regions


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = "Image Comparison Tool"
        self.setWindowTitle(self.title)

        # Data structure for loaded images
        self.image_paths = {1: None, 2: None}
        self.pixmap_items = {1: None, 2: None}
        self.worker = None

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

        btn_reset = QPushButton("🔄 Reset")
        btn_reset.clicked.connect(self.reset_view)
        button_layout.addWidget(btn_reset)

        main_layout.addLayout(button_layout)

        # Parameter settings
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Threshold:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 255)
        self.threshold_spin.setValue(30)
        param_layout.addWidget(self.threshold_spin)

        param_layout.addWidget(QLabel("Min. Area Size:"))
        self.min_area_spin = QSpinBox()
        self.min_area_spin.setRange(1, 1000)
        self.min_area_spin.setValue(100)
        param_layout.addWidget(self.min_area_spin)

        param_layout.addStretch()
        self.info_label = QLabel("Load two images to compare")
        param_layout.addWidget(self.info_label)

        main_layout.addLayout(param_layout)

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

            # Update info
            if all(self.image_paths.values()):
                self.info_label.setText("Both images loaded - Click 'Compare'")
            else:
                self.info_label.setText(f"Image {image_num} loaded")

    def compare_images(self):
        """Compare the two images"""
        if not all(self.image_paths.values()):
            QMessageBox.warning(self, "Error", "Please load both images first!")
            return

        # Create comparator
        comparator = ImageComparator(
            self.image_paths[1],
            self.image_paths[2],
            threshold=self.threshold_spin.value(),
            min_area=self.min_area_spin.value()
        )

        # Show progress bar
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.info_label.setText("Comparing images...")

        # Create worker thread
        self.worker = ComparisonWorker(comparator)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_comparison_finished)
        self.worker.error.connect(self.on_comparison_error)
        self.worker.start()

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def on_comparison_finished(self, comparator):
        """Handle comparison completion"""
        # Hide progress bar
        self.progress_bar.hide()

        # Visualize differences
        self.draw_differences(comparator.differences)

        # Update info
        num_diffs = len(comparator.differences)
        total_area = sum(d['area'] for d in comparator.differences)
        self.info_label.setText(
            f"✓ {num_diffs} differences found (Total pixels: {total_area})"
        )

    def on_comparison_error(self, error_msg):
        """Handle comparison error"""
        self.progress_bar.hide()
        self.info_label.setText("Comparison failed")
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

    def reset_view(self):
        """Reset the view"""
        self.scene1.clear()
        self.scene2.clear()
        self.image_paths = {1: None, 2: None}
        self.pixmap_items = {1: None, 2: None}
        self.progress_bar.hide()
        self.info_label.setText("Load two images to compare")


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
