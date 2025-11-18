# -*- coding: utf-8 -*-
"""
Image Marker Tool
Interactive tool for marking and annotating points on images.
Supports relative coordinates for scalability.
"""
import json
import os
import sys
from pathlib import Path
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt


class ZoomableImageView(QtWidgets.QGraphicsView):
    """Graphics View with zoom and pan functionality"""

    def __init__(self, scene):
        super().__init__(scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.Shape.Box)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self._zoom = 0
        self._pan_mode = False

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

    def keyPressEvent(self, event):
        """Space key for pan mode"""
        if event.key() == Qt.Key.Key_Space:
            self._pan_mode = True
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Release space key"""
        if event.key() == Qt.Key.Key_Space:
            self._pan_mode = False
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        super().keyReleaseEvent(event)


class MarkerManager:
    """Manages markers and their storage with relative coordinates"""

    def __init__(self):
        self.markers = []
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.image_width = 1
        self.image_height = 1

    def set_image_dimensions(self, width, height):
        """Set current image dimensions for coordinate conversion"""
        self.image_width = max(1, width)
        self.image_height = max(1, height)

    def add_marker(self, x, y, label=""):
        """Add a new marker with both relative and absolute coordinates"""
        marker = {
            'x_rel': float(x / self.image_width),  # Relative (0-1)
            'y_rel': float(y / self.image_height),  # Relative (0-1)
            'x_abs': float(x),  # Absolute pixels
            'y_abs': float(y),  # Absolute pixels
            'label': label,
            'id': len(self.markers)
        }
        self.markers.append(marker)
        return marker

    def get_absolute_coords(self, marker):
        """Get absolute coordinates from relative coordinates"""
        return (
            marker['x_rel'] * self.image_width,
            marker['y_rel'] * self.image_height
        )

    def remove_last(self):
        """Remove the last marker"""
        if self.markers:
            return self.markers.pop()
        return None

    def remove_all(self):
        """Remove all markers"""
        self.markers.clear()

    def save_to_file(self, image_path):
        """Save markers to JSON file"""
        if not self.markers:
            return None, "No markers to save"

        # Generate filename
        img_name = Path(image_path).stem
        filename = self.config_dir / f"{img_name}.json"

        # Versioning if file exists
        counter = 1
        while filename.exists():
            filename = self.config_dir / f"{img_name}({counter}).json"
            counter += 1

        # Save
        try:
            data = {
                'image': str(Path(image_path).name),
                'image_dimensions': {
                    'width': self.image_width,
                    'height': self.image_height
                },
                'markers': self.markers,
                'count': len(self.markers),
                'version': '2.0'  # Version with relative coords
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            return filename, None
        except Exception as e:
            return None, f"Error saving: {e}"

    def load_from_file(self, image_path):
        """Load markers from the newest JSON file for the image"""
        img_name = Path(image_path).stem

        # Search for matching files
        matching_files = []
        for file in self.config_dir.glob(f"{img_name}*.json"):
            matching_files.append(file)

        if not matching_files:
            return False

        # Use newest file
        latest_file = max(matching_files, key=lambda f: f.stat().st_ctime)

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validation
            if not isinstance(data, dict) or 'markers' not in data:
                return False

            # Check version and handle legacy format
            version = data.get('version', '1.0')

            if version == '1.0':
                # Legacy format - convert to relative coordinates
                self.markers = []
                for marker in data['markers']:
                    # Assume old format has absolute coords only
                    x_abs = marker.get('x', marker.get('x_abs', 0))
                    y_abs = marker.get('y', marker.get('y_abs', 0))

                    new_marker = {
                        'x_rel': x_abs / self.image_width,
                        'y_rel': y_abs / self.image_height,
                        'x_abs': x_abs,
                        'y_abs': y_abs,
                        'label': marker.get('label', ''),
                        'id': marker.get('id', len(self.markers))
                    }
                    self.markers.append(new_marker)
            else:
                # New format with relative coordinates
                self.markers = data['markers']

            return True

        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading: {e}")
            return False

    def export_to_csv(self, image_path):
        """Export markers as CSV"""
        if not self.markers:
            return None, "No markers to export"

        img_name = Path(image_path).stem
        filename = self.config_dir / f"{img_name}.csv"

        counter = 1
        while filename.exists():
            filename = self.config_dir / f"{img_name}({counter}).csv"
            counter += 1

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("ID,X_Relative,Y_Relative,X_Absolute,Y_Absolute,Label\n")
                for marker in self.markers:
                    f.write(
                        f"{marker['id']},"
                        f"{marker['x_rel']:.6f},"
                        f"{marker['y_rel']:.6f},"
                        f"{marker['x_abs']:.2f},"
                        f"{marker['y_abs']:.2f},"
                        f"{marker.get('label', '')}\n"
                    )

            return filename, None
        except Exception as e:
            return None, f"Error exporting: {e}"


class ImageMarker(QtWidgets.QMainWindow):
    """Main window for image marking"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Marker Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Variables
        self.current_image_path = None
        self.pixmap_item = None
        self.marker_items = []
        self.marker_manager = MarkerManager()
        self.marker_size = 10
        self.marker_color = QtGui.QColor(0, 255, 0)

        # Build UI
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        """Create user interface"""
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(main_layout)

        # Scene and View
        self.scene = QtWidgets.QGraphicsScene()
        self.view = ZoomableImageView(self.scene)
        self.scene.mousePressEvent = self.on_scene_click

        main_layout.addWidget(self.view, stretch=4)

        # Right sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar, stretch=1)

        self.setCentralWidget(main_widget)

    def create_sidebar(self):
        """Create sidebar with controls"""
        sidebar = QtWidgets.QWidget()
        sidebar.setMaximumWidth(250)
        layout = QtWidgets.QVBoxLayout()
        sidebar.setLayout(layout)

        # File operations
        file_group = QtWidgets.QGroupBox("File")
        file_layout = QtWidgets.QVBoxLayout()
        file_group.setLayout(file_layout)

        self.open_btn = QtWidgets.QPushButton("📁 Open Image")
        self.open_btn.clicked.connect(self.open_file)
        file_layout.addWidget(self.open_btn)

        self.save_btn = QtWidgets.QPushButton("💾 Save (JSON)")
        self.save_btn.clicked.connect(self.save_markers)
        file_layout.addWidget(self.save_btn)

        self.export_csv_btn = QtWidgets.QPushButton("📊 Export (CSV)")
        self.export_csv_btn.clicked.connect(self.export_csv)
        file_layout.addWidget(self.export_csv_btn)

        layout.addWidget(file_group)

        # Marker operations
        marker_group = QtWidgets.QGroupBox("Markers")
        marker_layout = QtWidgets.QVBoxLayout()
        marker_group.setLayout(marker_layout)

        self.remove_last_btn = QtWidgets.QPushButton("↩ Remove Last")
        self.remove_last_btn.clicked.connect(self.remove_last_marker)
        marker_layout.addWidget(self.remove_last_btn)

        self.remove_all_btn = QtWidgets.QPushButton("🗑 Remove All")
        self.remove_all_btn.clicked.connect(self.remove_all_markers)
        marker_layout.addWidget(self.remove_all_btn)

        layout.addWidget(marker_group)

        # Marker settings
        settings_group = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QVBoxLayout()
        settings_group.setLayout(settings_layout)

        # Marker size
        size_layout = QtWidgets.QHBoxLayout()
        size_layout.addWidget(QtWidgets.QLabel("Size:"))
        self.size_spin = QtWidgets.QSpinBox()
        self.size_spin.setRange(3, 50)
        self.size_spin.setValue(10)
        self.size_spin.valueChanged.connect(self.update_marker_size)
        size_layout.addWidget(self.size_spin)
        settings_layout.addLayout(size_layout)

        # Marker color
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(QtWidgets.QLabel("Color:"))
        self.color_btn = QtWidgets.QPushButton("🎨")
        self.color_btn.clicked.connect(self.choose_color)
        self.update_color_button()
        color_layout.addWidget(self.color_btn)
        settings_layout.addLayout(color_layout)

        layout.addWidget(settings_group)

        # Marker list
        list_group = QtWidgets.QGroupBox("Marker List")
        list_layout = QtWidgets.QVBoxLayout()
        list_group.setLayout(list_layout)

        self.marker_list = QtWidgets.QListWidget()
        self.marker_list.itemDoubleClicked.connect(self.jump_to_marker)
        list_layout.addWidget(self.marker_list)

        layout.addWidget(list_group)

        # Info label
        self.info_label = QtWidgets.QLabel("Load an image to mark")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 10px; background: #f0f0f0;")
        layout.addWidget(self.info_label)

        layout.addStretch()

        return sidebar

    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Ctrl+Z for Undo
        undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.remove_last_marker)

        # Ctrl+O for Open
        open_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        open_shortcut.activated.connect(self.open_file)

        # Ctrl+S for Save
        save_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_markers)

        # Delete for remove all
        delete_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.remove_all_markers)

    def open_file(self):
        """Open an image"""
        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        dialog.setDirectory(str(Path.home() / "Downloads"))

        if dialog.exec():
            filename = dialog.selectedFiles()[0]
            self.load_image(filename)

    def load_image(self, filepath):
        """Load an image into the scene"""
        self.current_image_path = filepath

        # Clear scene
        self.scene.clear()
        self.marker_items.clear()
        self.marker_manager.remove_all()
        self.marker_list.clear()

        # Load image
        pixmap = QtGui.QPixmap(filepath)
        if pixmap.isNull():
            QtWidgets.QMessageBox.critical(self, "Error", "Could not load image!")
            return

        # Set image dimensions in marker manager
        self.marker_manager.set_image_dimensions(pixmap.width(), pixmap.height())

        # Add image to scene
        self.pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        # Adjust scene
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

        # Load saved markers
        if self.marker_manager.load_from_file(filepath):
            self.redraw_all_markers()
            self.info_label.setText(
                f"Image loaded\n{len(self.marker_manager.markers)} markers restored"
            )
        else:
            self.info_label.setText(f"Image loaded: {Path(filepath).name}")

    def on_scene_click(self, event):
        """Handle clicks on the scene"""
        if not self.pixmap_item:
            return

        pos = event.scenePos()

        # Check if click is within image
        if self.pixmap_item.contains(pos):
            x, y = pos.x(), pos.y()

            # Add marker
            marker = self.marker_manager.add_marker(x, y)
            self.draw_marker(marker)

            # Update list
            self.marker_list.addItem(
                f"#{marker['id'] + 1}: ({x:.1f}, {y:.1f}) "
                f"[rel: {marker['x_rel']:.3f}, {marker['y_rel']:.3f}]"
            )

            # Update info
            self.info_label.setText(
                f"Markers: {len(self.marker_manager.markers)}\n"
                f"Last: ({x:.1f}, {y:.1f})"
            )

    def draw_marker(self, marker):
        """Draw a single marker"""
        # Get absolute coordinates from relative
        x, y = self.marker_manager.get_absolute_coords(marker)
        size = self.marker_size

        # Draw cross
        pen = QtGui.QPen(self.marker_color, 2)

        # Horizontal line
        h_line = self.scene.addLine(x - size, y, x + size, y, pen)
        # Vertical line
        v_line = self.scene.addLine(x, y - size, x, y + size, pen)

        # Circle
        circle = self.scene.addEllipse(
            x - size / 2, y - size / 2, size, size,
            pen
        )

        self.marker_items.append((h_line, v_line, circle))

    def redraw_all_markers(self):
        """Redraw all markers"""
        # Remove old markers
        for items in self.marker_items:
            for item in items:
                self.scene.removeItem(item)
        self.marker_items.clear()
        self.marker_list.clear()

        # Draw new markers
        for marker in self.marker_manager.markers:
            self.draw_marker(marker)
            x, y = self.marker_manager.get_absolute_coords(marker)
            self.marker_list.addItem(
                f"#{marker['id'] + 1}: ({x:.1f}, {y:.1f}) "
                f"[rel: {marker['x_rel']:.3f}, {marker['y_rel']:.3f}]"
            )

    def remove_last_marker(self):
        """Remove the last marker"""
        marker = self.marker_manager.remove_last()
        if marker and self.marker_items:
            # Remove graphical elements
            items = self.marker_items.pop()
            for item in items:
                self.scene.removeItem(item)

            # Remove from list
            self.marker_list.takeItem(self.marker_list.count() - 1)

            # Update info
            self.info_label.setText(
                f"Marker removed\nRemaining: {len(self.marker_manager.markers)}"
            )

    def remove_all_markers(self):
        """Remove all markers"""
        reply = QtWidgets.QMessageBox.question(
            self, "Confirmation",
            "Really remove all markers?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.marker_manager.remove_all()
            self.redraw_all_markers()
            self.info_label.setText("All markers removed")

    def save_markers(self):
        """Save markers to JSON"""
        if not self.current_image_path:
            QtWidgets.QMessageBox.warning(self, "Error", "No image loaded!")
            return

        filename, error = self.marker_manager.save_to_file(self.current_image_path)

        if error:
            QtWidgets.QMessageBox.warning(self, "Error", error)
        else:
            QtWidgets.QMessageBox.information(
                self, "Saved",
                f"Markers saved:\n{filename}"
            )
            self.info_label.setText(f"Saved: {filename.name}")

    def export_csv(self):
        """Export markers as CSV"""
        if not self.current_image_path:
            QtWidgets.QMessageBox.warning(self, "Error", "No image loaded!")
            return

        filename, error = self.marker_manager.export_to_csv(self.current_image_path)

        if error:
            QtWidgets.QMessageBox.warning(self, "Error", error)
        else:
            QtWidgets.QMessageBox.information(
                self, "Exported",
                f"CSV exported:\n{filename}"
            )

    def update_marker_size(self, value):
        """Update marker size"""
        self.marker_size = value
        self.redraw_all_markers()

    def choose_color(self):
        """Open color picker dialog"""
        color = QtWidgets.QColorDialog.getColor(
            self.marker_color, self, "Choose Marker Color"
        )
        if color.isValid():
            self.marker_color = color
            self.update_color_button()
            self.redraw_all_markers()

    def update_color_button(self):
        """Update the color of the color button"""
        self.color_btn.setStyleSheet(
            f"background-color: {self.marker_color.name()}; color: white;"
        )

    def jump_to_marker(self, item):
        """Jump to a marker when double-clicked"""
        index = self.marker_list.row(item)
        if 0 <= index < len(self.marker_manager.markers):
            marker = self.marker_manager.markers[index]
            x, y = self.marker_manager.get_absolute_coords(marker)
            self.view.centerOn(x, y)


def main():
    """Main entry point"""
    app = QtWidgets.QApplication(sys.argv)
    window = ImageMarker()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
