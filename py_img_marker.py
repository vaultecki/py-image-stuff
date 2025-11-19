# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Image Marker Tool - Enhanced Version
Interactive tool for marking and annotating points on images.
Features:
- Marker categories/tags with custom colors
- Text labels on markers
- Relative coordinate system (resolution-independent)
- CSV and JSON export/import
- Undo/Redo functionality
- Marker search
"""
import json
import csv
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


class MarkerCategory:
    """Defines a marker category with name and color"""

    # Default categories
    DEFAULTS = {
        'defect': {'name': 'Defect', 'color': '#FF0000', 'description': 'Product defects'},
        'measurement': {'name': 'Measurement', 'color': '#00FF00', 'description': 'Measurement points'},
        'note': {'name': 'Note', 'color': '#0000FF', 'description': 'General notes'},
        'roi': {'name': 'ROI', 'color': '#FFFF00', 'description': 'Region of interest'},
        'annotation': {'name': 'Annotation', 'color': '#FF00FF', 'description': 'Annotations'},
    }

    def __init__(self, id, name, color, description=''):
        self.id = id
        self.name = name
        self.color = QtGui.QColor(color) if isinstance(color, str) else color
        self.description = description

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color.name(),
            'description': self.description
        }

    @staticmethod
    def from_dict(data):
        """Create from dictionary"""
        return MarkerCategory(
            data['id'],
            data['name'],
            data['color'],
            data.get('description', '')
        )


class MarkerManager:
    """Manages markers and their storage with relative coordinates and categories"""

    def __init__(self):
        self.markers = []
        self.categories = self._load_default_categories()
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.image_width = 1
        self.image_height = 1

        # Undo/Redo stacks
        self.history = []  # List of (action, data) tuples
        self.future = []  # For redo
        self.max_history = 100

    def _load_default_categories(self):
        """Load default marker categories"""
        categories = {}
        for cat_id, cat_data in MarkerCategory.DEFAULTS.items():
            categories[cat_id] = MarkerCategory(
                cat_id,
                cat_data['name'],
                cat_data['color'],
                cat_data['description']
            )
        return categories

    def add_category(self, id, name, color, description=''):
        """Add a new category"""
        self.categories[id] = MarkerCategory(id, name, color, description)

    def get_category(self, category_id):
        """Get category by ID"""
        return self.categories.get(category_id, self.categories['note'])

    def set_image_dimensions(self, width, height):
        """Set current image dimensions for coordinate conversion"""
        self.image_width = max(1, width)
        self.image_height = max(1, height)

    def add_marker(self, x, y, category_id='note', label='', description='', record_history=True):
        """Add a new marker with category, label, and relative coordinates"""
        marker = {
            'x_rel': float(x / self.image_width),
            'y_rel': float(y / self.image_height),
            'x_abs': float(x),
            'y_abs': float(y),
            'category': category_id,
            'label': label,
            'description': description,
            'id': len(self.markers)
        }
        self.markers.append(marker)

        if record_history:
            self._record_action('add', marker.copy())

        return marker

    def update_marker(self, marker_id, label=None, description=None, category=None, record_history=True):
        """Update marker properties"""
        if 0 <= marker_id < len(self.markers):
            if record_history:
                old_marker = self.markers[marker_id].copy()

            if label is not None:
                self.markers[marker_id]['label'] = label
            if description is not None:
                self.markers[marker_id]['description'] = description
            if category is not None:
                self.markers[marker_id]['category'] = category

            if record_history:
                self._record_action('update', {'old': old_marker, 'new': self.markers[marker_id].copy()})

            return True
        return False

    def get_absolute_coords(self, marker):
        """Get absolute coordinates from relative coordinates"""
        return (
            marker['x_rel'] * self.image_width,
            marker['y_rel'] * self.image_height
        )

    def remove_last(self, record_history=True):
        """Remove the last marker"""
        if self.markers:
            marker = self.markers.pop()
            if record_history:
                self._record_action('remove', marker)
            return marker
        return None

    def remove_marker(self, marker_id, record_history=True):
        """Remove marker by ID"""
        if 0 <= marker_id < len(self.markers):
            marker = self.markers.pop(marker_id)
            # Update remaining IDs
            for i, m in enumerate(self.markers):
                m['id'] = i

            if record_history:
                self._record_action('remove', marker)
            return True
        return False

    def remove_all(self, record_history=True):
        """Remove all markers"""
        if record_history and self.markers:
            self._record_action('remove_all', self.markers.copy())
        self.markers.clear()

    def _record_action(self, action_type, data):
        """Record action for undo/redo"""
        self.history.append((action_type, data))
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.future.clear()  # Clear redo stack on new action

    def undo(self):
        """Undo last action"""
        if not self.history:
            return None

        action_type, data = self.history.pop()
        self.future.append((action_type, data))

        if action_type == 'add':
            # Remove the added marker
            self.markers.pop()
        elif action_type == 'remove':
            # Re-add the removed marker
            self.markers.append(data)
        elif action_type == 'remove_all':
            # Restore all markers
            self.markers = data.copy()
        elif action_type == 'update':
            # Restore old marker state
            marker_id = data['old']['id']
            if marker_id < len(self.markers):
                self.markers[marker_id] = data['old']

        return action_type

    def redo(self):
        """Redo last undone action"""
        if not self.future:
            return None

        action_type, data = self.future.pop()
        self.history.append((action_type, data))

        if action_type == 'add':
            # Re-add the marker
            self.markers.append(data)
        elif action_type == 'remove':
            # Remove the marker again
            marker_id = data['id']
            if marker_id < len(self.markers):
                self.markers.pop(marker_id)
        elif action_type == 'remove_all':
            # Clear all markers again
            self.markers.clear()
        elif action_type == 'update':
            # Apply new marker state
            marker_id = data['new']['id']
            if marker_id < len(self.markers):
                self.markers[marker_id] = data['new']

        return action_type

    def search_markers(self, query):
        """Search markers by label or description"""
        query_lower = query.lower()
        return [m for m in self.markers
                if query_lower in m.get('label', '').lower()
                or query_lower in m.get('description', '').lower()]

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
                'categories': {
                    cat_id: cat.to_dict()
                    for cat_id, cat in self.categories.items()
                },
                'markers': self.markers,
                'count': len(self.markers),
                'version': '3.0'
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

            if not isinstance(data, dict) or 'markers' not in data:
                return False

            # Load categories if present
            if 'categories' in data:
                self.categories = {}
                for cat_id, cat_data in data['categories'].items():
                    self.categories[cat_id] = MarkerCategory.from_dict(cat_data)

            # Check version and handle legacy formats
            version = data.get('version', '1.0')

            if version in ['1.0', '2.0']:
                # Legacy format - convert to new format
                self.markers = []
                for marker in data['markers']:
                    x_rel = marker.get('x_rel', marker.get('x', 0) / self.image_width)
                    y_rel = marker.get('y_rel', marker.get('y', 0) / self.image_height)

                    new_marker = {
                        'x_rel': x_rel,
                        'y_rel': y_rel,
                        'x_abs': x_rel * self.image_width,
                        'y_abs': y_rel * self.image_height,
                        'category': marker.get('category', 'note'),
                        'label': marker.get('label', ''),
                        'description': marker.get('description', ''),
                        'id': marker.get('id', len(self.markers))
                    }
                    self.markers.append(new_marker)
            else:
                # New format
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
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Category", "Label", "X_Relative", "Y_Relative",
                                 "X_Absolute", "Y_Absolute", "Description"])

                for marker in self.markers:
                    category = self.get_category(marker.get('category', 'note'))
                    writer.writerow([
                        marker['id'],
                        category.name,
                        marker.get('label', ''),
                        f"{marker['x_rel']:.6f}",
                        f"{marker['y_rel']:.6f}",
                        f"{marker['x_abs']:.2f}",
                        f"{marker['y_abs']:.2f}",
                        marker.get('description', '')
                    ])

            return filename, None
        except Exception as e:
            return None, f"Error exporting: {e}"

    def import_from_csv(self, csv_path):
        """Import markers from CSV file"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                imported_count = 0

                for row in reader:
                    # Find category by name
                    category_id = 'note'
                    for cat_id, cat in self.categories.items():
                        if cat.name == row['Category']:
                            category_id = cat_id
                            break

                    # Use relative coordinates
                    x = float(row['X_Relative']) * self.image_width
                    y = float(row['Y_Relative']) * self.image_height

                    self.add_marker(
                        x, y,
                        category_id=category_id,
                        label=row.get('Label', ''),
                        description=row.get('Description', ''),
                        record_history=False  # Don't record during import
                    )
                    imported_count += 1

                return imported_count, None
        except Exception as e:
            return 0, f"Error importing: {e}"


class MarkerEditDialog(QtWidgets.QDialog):
    """Dialog for editing marker properties"""

    def __init__(self, marker, categories, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.categories = categories
        self.setWindowTitle("Edit Marker")
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Category
        cat_layout = QtWidgets.QHBoxLayout()
        cat_layout.addWidget(QtWidgets.QLabel("Category:"))
        self.category_combo = QtWidgets.QComboBox()
        for cat_id, category in self.categories.items():
            self.category_combo.addItem(category.name, cat_id)

        # Set current category
        current_cat = self.marker.get('category', 'note')
        index = self.category_combo.findData(current_cat)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)

        cat_layout.addWidget(self.category_combo)
        layout.addLayout(cat_layout)

        # Label
        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(QtWidgets.QLabel("Label:"))
        self.label_input = QtWidgets.QLineEdit()
        self.label_input.setText(self.marker.get('label', ''))
        self.label_input.setPlaceholderText("Short label for marker")
        label_layout.addWidget(self.label_input)
        layout.addLayout(label_layout)

        # Description
        layout.addWidget(QtWidgets.QLabel("Description:"))
        self.description_input = QtWidgets.QTextEdit()
        self.description_input.setText(self.marker.get('description', ''))
        self.description_input.setPlaceholderText("Detailed description (optional)")
        self.description_input.setMaximumHeight(80)
        layout.addWidget(self.description_input)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_values(self):
        """Get edited values"""
        return {
            'category': self.category_combo.currentData(),
            'label': self.label_input.text(),
            'description': self.description_input.toPlainText()
        }


class ImageMarker(QtWidgets.QMainWindow):
    """Main window for image marking"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Marker Tool - Enhanced")
        self.setGeometry(100, 100, 1400, 900)

        # Variables
        self.current_image_path = None
        self.pixmap_item = None
        self.marker_items = []
        self.marker_manager = MarkerManager()
        self.marker_size = 10
        self.current_category = 'note'

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
        sidebar.setMaximumWidth(300)
        layout = QtWidgets.QVBoxLayout()
        sidebar.setLayout(layout)

        # File operations
        file_group = QtWidgets.QGroupBox("File")
        file_layout = QtWidgets.QVBoxLayout()
        file_group.setLayout(file_layout)

        self.open_btn = QtWidgets.QPushButton("📂 Open Image")
        self.open_btn.clicked.connect(self.open_file)
        file_layout.addWidget(self.open_btn)

        self.save_btn = QtWidgets.QPushButton("💾 Save JSON")
        self.save_btn.clicked.connect(self.save_markers)
        file_layout.addWidget(self.save_btn)

        self.export_csv_btn = QtWidgets.QPushButton("📊 Export CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        file_layout.addWidget(self.export_csv_btn)

        self.import_csv_btn = QtWidgets.QPushButton("📥 Import CSV")
        self.import_csv_btn.clicked.connect(self.import_csv)
        file_layout.addWidget(self.import_csv_btn)

        layout.addWidget(file_group)

        # Marker category selection
        category_group = QtWidgets.QGroupBox("Marker Category")
        category_layout = QtWidgets.QVBoxLayout()
        category_group.setLayout(category_layout)

        self.category_combo = QtWidgets.QComboBox()
        for cat_id, category in self.marker_manager.categories.items():
            self.category_combo.addItem(category.name, cat_id)
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        category_layout.addWidget(self.category_combo)

        # Category color indicator
        self.category_color_label = QtWidgets.QLabel("●")
        self.category_color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_category_color()
        category_layout.addWidget(self.category_color_label)

        layout.addWidget(category_group)

        # Marker operations
        marker_group = QtWidgets.QGroupBox("Markers")
        marker_layout = QtWidgets.QVBoxLayout()
        marker_group.setLayout(marker_layout)

        # Undo/Redo buttons
        undo_redo_layout = QtWidgets.QHBoxLayout()
        self.undo_btn = QtWidgets.QPushButton("↶ Undo")
        self.undo_btn.clicked.connect(self.undo_action)
        undo_redo_layout.addWidget(self.undo_btn)

        self.redo_btn = QtWidgets.QPushButton("↷ Redo")
        self.redo_btn.clicked.connect(self.redo_action)
        undo_redo_layout.addWidget(self.redo_btn)
        marker_layout.addLayout(undo_redo_layout)

        self.remove_last_btn = QtWidgets.QPushButton("↩ Remove Last")
        self.remove_last_btn.clicked.connect(self.remove_last_marker)
        marker_layout.addWidget(self.remove_last_btn)

        self.remove_all_btn = QtWidgets.QPushButton("🗑 Remove All")
        self.remove_all_btn.clicked.connect(self.remove_all_markers)
        marker_layout.addWidget(self.remove_all_btn)

        layout.addWidget(marker_group)

        # Marker settings
        settings_group = QtWidgets.QGroupBox("Display Settings")
        settings_layout = QtWidgets.QVBoxLayout()
        settings_group.setLayout(settings_layout)

        # Marker size
        size_layout = QtWidgets.QHBoxLayout()
        size_layout.addWidget(QtWidgets.QLabel("Size:"))
        self.size_spin = QtWidgets.QSpinBox()
        self.size_spin.setRange(5, 50)
        self.size_spin.setValue(10)
        self.size_spin.valueChanged.connect(self.update_marker_size)
        size_layout.addWidget(self.size_spin)
        settings_layout.addLayout(size_layout)

        # Show labels checkbox
        self.show_labels_check = QtWidgets.QCheckBox("Show Labels")
        self.show_labels_check.setChecked(True)
        self.show_labels_check.stateChanged.connect(self.redraw_all_markers)
        settings_layout.addWidget(self.show_labels_check)

        layout.addWidget(settings_group)

        # Search box
        search_group = QtWidgets.QGroupBox("Search")
        search_layout = QtWidgets.QVBoxLayout()
        search_group.setLayout(search_layout)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search markers...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_group)

        # Marker list with filter
        list_group = QtWidgets.QGroupBox("Marker List")
        list_layout = QtWidgets.QVBoxLayout()
        list_group.setLayout(list_layout)

        # Filter by category
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter:"))
        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItem("All Categories", None)
        for cat_id, category in self.marker_manager.categories.items():
            self.filter_combo.addItem(category.name, cat_id)
        self.filter_combo.currentIndexChanged.connect(self.update_marker_list)
        filter_layout.addWidget(self.filter_combo)
        list_layout.addLayout(filter_layout)

        self.marker_list = QtWidgets.QListWidget()
        self.marker_list.itemDoubleClicked.connect(self.edit_marker_from_list)
        self.marker_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.marker_list.customContextMenuRequested.connect(self.show_marker_context_menu)
        list_layout.addWidget(self.marker_list)

        layout.addWidget(list_group)

        # Info label
        self.info_label = QtWidgets.QLabel("Load an image to start marking")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 10px; background: #f0f0f0;")
        layout.addWidget(self.info_label)

        layout.addStretch()

        return sidebar

    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Ctrl+Z for Undo
        undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_action)

        # Ctrl+Y for Redo
        redo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.redo_action)

        # Ctrl+O for Open
        open_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        open_shortcut.activated.connect(self.open_file)

        # Ctrl+S for Save
        save_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_markers)

        # Delete for remove all
        delete_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.remove_all_markers)

        # Ctrl+F for search
        search_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(lambda: self.search_input.setFocus())

        # Number keys 1-5 for quick category selection
        for i in range(1, 6):
            if i <= self.category_combo.count():
                shortcut = QtGui.QShortcut(QtGui.QKeySequence(str(i)), self)
                shortcut.activated.connect(lambda idx=i - 1: self.category_combo.setCurrentIndex(idx))

    def on_category_changed(self):
        """Handle category selection change"""
        self.current_category = self.category_combo.currentData()
        self.update_category_color()

    def update_category_color(self):
        """Update category color indicator"""
        category = self.marker_manager.get_category(self.current_category)
        color = category.color.name()
        self.category_color_label.setStyleSheet(
            f"font-size: 36pt; color: {color};"
        )

    def on_search_changed(self, text):
        """Handle search input change"""
        if not text:
            self.update_marker_list()
            return

        # Search and update list
        results = self.marker_manager.search_markers(text)
        self.marker_list.clear()

        for marker in results:
            category = self.marker_manager.get_category(marker.get('category', 'note'))
            x, y = self.marker_manager.get_absolute_coords(marker)
            label = marker.get('label', '')

            item_text = f"#{marker['id'] + 1} [{category.name}] {label} ({x:.1f}, {y:.1f})"
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, marker['id'])
            item.setForeground(QtGui.QBrush(category.color))
            self.marker_list.addItem(item)

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
        self.marker_manager.remove_all(record_history=False)
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
                f"Image loaded: {Path(filepath).name}\n"
                f"{len(self.marker_manager.markers)} markers restored"
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

            # Add marker with current category
            marker = self.marker_manager.add_marker(
                x, y,
                category_id=self.current_category,
                label=f"M{len(self.marker_manager.markers)}"
            )

            self.draw_marker(marker)
            self.update_marker_list()

            # Update info
            category = self.marker_manager.get_category(marker['category'])
            self.info_label.setText(
                f"Markers: {len(self.marker_manager.markers)}\n"
                f"Last: {category.name} at ({x:.1f}, {y:.1f})"
            )

    def draw_marker(self, marker):
        """Draw a single marker with label"""
        # Get absolute coordinates and category
        x, y = self.marker_manager.get_absolute_coords(marker)
        category = self.marker_manager.get_category(marker.get('category', 'note'))
        size = self.marker_size

        # Create pen with category color
        pen = QtGui.QPen(category.color, 2)

        # Draw cross
        h_line = self.scene.addLine(x - size, y, x + size, y, pen)
        v_line = self.scene.addLine(x, y - size, x, y + size, pen)

        # Draw circle
        circle = self.scene.addEllipse(
            x - size / 2, y - size / 2, size, size,
            pen
        )

        # Draw label if enabled and present
        label_item = None
        if self.show_labels_check.isChecked() and marker.get('label'):
            label_item = self.scene.addText(marker['label'])
            label_item.setDefaultTextColor(category.color)
            label_item.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Weight.Bold))
            label_item.setPos(x + size + 2, y - size)

        self.marker_items.append((h_line, v_line, circle, label_item))

    def redraw_all_markers(self):
        """Redraw all markers"""
        # Remove old markers
        for items in self.marker_items:
            for item in items:
                if item:
                    self.scene.removeItem(item)
        self.marker_items.clear()

        # Draw new markers
        for marker in self.marker_manager.markers:
            self.draw_marker(marker)

        self.update_marker_list()

    def update_marker_list(self):
        """Update marker list with optional filtering"""
        self.marker_list.clear()

        filter_category = self.filter_combo.currentData()

        for marker in self.marker_manager.markers:
            category = self.marker_manager.get_category(marker.get('category', 'note'))

            # Apply filter
            if filter_category and marker.get('category') != filter_category:
                continue

            x, y = self.marker_manager.get_absolute_coords(marker)
            label = marker.get('label', '')

            # Format list item with color indicator
            item_text = f"#{marker['id'] + 1} [{category.name}] {label} ({x:.1f}, {y:.1f})"
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, marker['id'])
            item.setForeground(QtGui.QBrush(category.color))
            self.marker_list.addItem(item)

    def edit_marker_from_list(self, item):
        """Edit marker when double-clicked in list"""
        marker_id = item.data(Qt.ItemDataRole.UserRole)
        if 0 <= marker_id < len(self.marker_manager.markers):
            marker = self.marker_manager.markers[marker_id]

            # Show edit dialog
            dialog = MarkerEditDialog(marker, self.marker_manager.categories, self)
            if dialog.exec():
                values = dialog.get_values()
                self.marker_manager.update_marker(
                    marker_id,
                    label=values['label'],
                    description=values['description'],
                    category=values['category']
                )
                self.redraw_all_markers()
                self.info_label.setText(f"Marker #{marker_id + 1} updated")

    def show_marker_context_menu(self, pos):
        """Show context menu for marker"""
        item = self.marker_list.itemAt(pos)
        if not item:
            return

        marker_id = item.data(Qt.ItemDataRole.UserRole)

        menu = QtWidgets.QMenu(self)

        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        jump_action = menu.addAction("Jump to Marker")

        action = menu.exec(self.marker_list.mapToGlobal(pos))

        if action == edit_action:
            self.edit_marker_from_list(item)
        elif action == delete_action:
            self.marker_manager.remove_marker(marker_id)
            self.redraw_all_markers()
        elif action == jump_action:
            marker = self.marker_manager.markers[marker_id]
            x, y = self.marker_manager.get_absolute_coords(marker)
            self.view.centerOn(x, y)

    def undo_action(self):
        """Undo last action"""
        action = self.marker_manager.undo()
        if action:
            self.redraw_all_markers()
            self.info_label.setText(f"Undone: {action}")
        else:
            self.info_label.setText("Nothing to undo")

    def redo_action(self):
        """Redo last undone action"""
        action = self.marker_manager.redo()
        if action:
            self.redraw_all_markers()
            self.info_label.setText(f"Redone: {action}")
        else:
            self.info_label.setText("Nothing to redo")

    def remove_last_marker(self):
        """Remove the last marker"""
        marker = self.marker_manager.remove_last()
        if marker and self.marker_items:
            # Remove graphical elements
            items = self.marker_items.pop()
            for item in items:
                if item:
                    self.scene.removeItem(item)

            # Update list
            self.update_marker_list()

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
                f"Markers saved:\n{filename}\n\n"
                f"Total markers: {len(self.marker_manager.markers)}"
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

    def import_csv(self):
        """Import markers from CSV"""
        if not self.current_image_path:
            QtWidgets.QMessageBox.warning(self, "Error", "No image loaded!")
            return

        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("CSV Files (*.csv)")

        if dialog.exec():
            csv_path = dialog.selectedFiles()[0]
            count, error = self.marker_manager.import_from_csv(csv_path)

            if error:
                QtWidgets.QMessageBox.warning(self, "Error", error)
            else:
                self.redraw_all_markers()
                QtWidgets.QMessageBox.information(
                    self, "Imported",
                    f"Successfully imported {count} markers"
                )
                self.info_label.setText(f"Imported {count} markers from CSV")

    def update_marker_size(self, value):
        """Update marker size"""
        self.marker_size = value
        self.redraw_all_markers()


def main():
    """Main entry point"""
    app = QtWidgets.QApplication(sys.argv)
    window = ImageMarker()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
