#!/usr/bin/env python3
"""
Dynamic Palette Editor - PyQt5 Application
Allows editing image palettes in real-time with visual preview
"""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QColorDialog, 
                             QScrollArea, QFileDialog, QMessageBox, QSplitter,
                             QTabWidget, QListWidget, QListWidgetItem, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPalette
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PIL import Image
import numpy as np
import json



class ZoomableLabel(QLabel):
    """Custom QLabel that supports zoom with mouse wheel"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_factor = 1.0
        self.original_pixmap = None
        self.current_pixmap = None
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.editor = None  # Reference to PaletteEditor
        
        # Middle mouse dragging variables
        self.middle_mouse_pressed = False
        self.last_pan_point = None
        self.scroll_area = None  # Will be set by parent
    
    def setPixmap(self, pixmap):
        """Override setPixmap to store original"""
        self.original_pixmap = pixmap
        self.current_pixmap = pixmap
        self.zoom_factor = 1.0
        super().setPixmap(pixmap)
    
    def setCurrentPixmap(self, pixmap):
        """Set current pixmap without resetting zoom"""
        self.current_pixmap = pixmap
        
        # Apply current zoom
        new_width = int(pixmap.width() * self.zoom_factor)
        new_height = int(pixmap.height() * self.zoom_factor)
        
        scaled_pixmap = pixmap.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.FastTransformation  # Pixelated, no antialiasing
        )
        
        self.setFixedSize(scaled_pixmap.size())
        super().setPixmap(scaled_pixmap)
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        if self.current_pixmap is None:
            return
        
        # Get zoom direction
        delta = event.angleDelta().y()
        
        # Adjust zoom factor
        if delta > 0:
            self.zoom_factor *= 1.1  # Zoom in
        else:
            self.zoom_factor *= 0.9  # Zoom out
        
        # Limit zoom range
        self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))
        
        # Apply zoom
        new_width = int(self.current_pixmap.width() * self.zoom_factor)
        new_height = int(self.current_pixmap.height() * self.zoom_factor)
        
        scaled_pixmap = self.current_pixmap.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.FastTransformation  # Pixelated, no antialiasing
        )
        
        self.setFixedSize(scaled_pixmap.size())
        super().setPixmap(scaled_pixmap)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for color detection and middle mouse dragging"""
        if self.middle_mouse_pressed and self.scroll_area and self.last_pan_point:
            # Calculate movement delta
            delta = event.globalPos() - self.last_pan_point
            self.last_pan_point = event.globalPos()
            
            # Get current scroll bar positions
            h_scroll = self.scroll_area.horizontalScrollBar()
            v_scroll = self.scroll_area.verticalScrollBar()
            
            # Update scroll bar positions (invert delta for natural dragging feel)
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
        
        elif self.editor and self.editor.image:
            self.editor.on_preview_hover(event.pos())
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to end middle mouse dragging"""
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = False
            self.last_pan_point = None
            self.setCursor(Qt.ArrowCursor)
    
    def leaveEvent(self, event):
        """Handle mouse leave to clear underlines and reset dragging"""
        if self.editor:
            self.editor.clear_all_button_underlines()
        
        # Reset middle mouse dragging if mouse leaves the widget
        if self.middle_mouse_pressed:
            self.middle_mouse_pressed = False
            self.last_pan_point = None
            self.setCursor(Qt.ArrowCursor)
    
    def mousePressEvent(self, event):
        """Handle mouse click for color selection and middle mouse dragging"""
        if event.button() == Qt.LeftButton and self.editor and self.editor.image:
            self.editor.on_preview_click(event.pos())
        elif event.button() == Qt.RightButton and self.editor and self.editor.image:
            self.editor.on_preview_right_click(event.pos())
        elif event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = True
            self.last_pan_point = event.globalPos()
            self.setCursor(Qt.ClosedHandCursor)


class PaletteEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image = None
        self.image_array = None
        self.original_image = None  # Store original unchanged image
        self.original_palette = []
        
        # Multiple palettes support
        self.palettes = []  # List of palettes, each palette is a list of colors
        self.current_palette_index = 0
        
        self.palette_buttons = []
        self.palette_grids = []  # Store grid layouts for each palette
        
        # Undo/Redo history
        self.undo_history = []  # List of (palette_idx, color_idx, old_color)
        self.redo_history = []  # List of (palette_idx, color_idx, old_color)
        self.max_undo_history = 50
        
        # PMAP preview widgets
        self.pmap_list_widget = None
        self.pmap_raw_widget = None
        self.pmap_preview_visible = False
        self.pmap_raw_visible = False
        
        # PMAP processing
        self.pmap_update_timer = QTimer()
        self.pmap_update_timer.setSingleShot(True)
        self.pmap_update_timer.timeout.connect(self.process_pmap_update)
        
        # Chunked processing for large images
        self.pmap_chunk_timer = QTimer()
        self.pmap_chunk_timer.timeout.connect(self.process_pmap_chunk)
        self.pmap_processing_data = None
        self.pmap_current_chunk = 0
        
        # Chunked JSON generation
        self.json_chunk_timer = QTimer()
        self.json_chunk_timer.timeout.connect(self.process_json_chunk)
        self.json_processing_data = None
        self.json_current_chunk = 0
        self.json_result_parts = []
        
        # Cache for PMAP data to avoid regeneration
        self.pmap_data_cache = {}
        self.pmap_cache_key = None
        
        # Recent files tracking
        self.recent_files = []
        self.max_recent_files = 10
        self.load_recent_files()
        
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Dynamic Palette Editor')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        
        # Add menu actions with shortcuts
        open_action = file_menu.addAction('&Open')
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_image)
        
        save_action = file_menu.addAction('&Save')
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_image)
        
        file_menu.addSeparator()
        
        export_palette_action = file_menu.addAction('Export &Palette PNG')
        export_palette_action.setShortcut('Ctrl+Shift+P')
        export_palette_action.triggered.connect(self.export_palette)
        
        import_palette_action = file_menu.addAction('&Import Palette PNG')
        import_palette_action.setShortcut('Ctrl+Shift+I')
        import_palette_action.triggered.connect(self.import_palette)
        
        file_menu.addSeparator()
        
        export_positioned_action = file_menu.addAction('Export Palette &Map')
        export_positioned_action.setShortcut('Ctrl+E')
        export_positioned_action.triggered.connect(self.export_positioned)
        
        import_pmap_action = file_menu.addAction('Import Palette Ma&p')
        import_pmap_action.setShortcut('Ctrl+M')
        import_pmap_action.triggered.connect(self.import_palette_map)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('E&xit')
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        
        # Add Recent menu as separate top-level menu
        self.recent_menu = menubar.addMenu('&Recent')
        self.update_recent_menu()
        
        # Add Edit menu
        edit_menu = menubar.addMenu('&Edit')
        
        undo_action = edit_menu.addAction('&Undo')
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.undo_color_change)
        
        redo_action = edit_menu.addAction('&Redo')
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.redo_color_change)
        
        # Add View menu
        view_menu = menubar.addMenu('&View')
        
        self.pmap_preview_action = view_menu.addAction('PMAP &Preview')
        self.pmap_preview_action.setShortcut('F1')
        self.pmap_preview_action.setCheckable(True)
        self.pmap_preview_action.triggered.connect(self.toggle_pmap_preview)
        
        self.pmap_raw_action = view_menu.addAction('PMAP Preview &Raw')
        self.pmap_raw_action.setShortcut('F2')
        self.pmap_raw_action.setCheckable(True)
        self.pmap_raw_action.triggered.connect(self.toggle_pmap_raw)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create splitter for multi-column layout
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left column: Color editor
        self.color_editor = self.create_color_editor()
        self.splitter.addWidget(self.color_editor)
        
        # Middle column: Image preview
        self.image_preview = self.create_image_preview()
        self.splitter.addWidget(self.image_preview)
        
        # Create PMAP preview widgets (initially hidden)
        self.create_pmap_widgets()
        
        # Set initial splitter sizes (30% for editor, 70% for preview)
        self.splitter.setSizes([360, 840])
        
        # Connect splitter moved signal to reorganize grids
        self.splitter.splitterMoved.connect(self.reorganize_palette_grids)
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.splitter)
        main_widget.setLayout(main_layout)
        
        self.show()
    
    def switch_to_palette_tab(self, tab_index):
        """Switch to specific palette tab by index"""
        if not self.palettes or tab_index >= len(self.palettes) or tab_index < 0:
            return  # Invalid tab index
        
        # Switch to the tab
        self.palette_tabs.setCurrentIndex(tab_index)
        # The tab change will trigger on_palette_tab_changed automatically
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() >= Qt.Key_1 and event.key() <= Qt.Key_9:
            # Handle palette tab switching with keys 1-9
            tab_number = event.key() - Qt.Key_1  # Convert to 0-based index
            self.switch_to_palette_tab(tab_number)
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Handle window resize to reorganize palette grids"""
        super().resizeEvent(event)
        self.reorganize_palette_grids()
    
    def reorganize_palette_grids(self):
        """Reorganize all palette grids based on current width"""
        if not self.palette_grids:
            return
        
        # Calculate columns based on current width
        button_size = 75  # 70px button + 5px spacing
        available_width = self.color_editor.width() - 40  # Subtract margins and scrollbar
        columns = max(1, available_width // button_size)
        
        # Reorganize each grid
        for grid_layout, palette_idx in self.palette_grids:
            if palette_idx >= len(self.palette_buttons):
                continue
            
            buttons = self.palette_buttons[palette_idx]
            
            # Remove all widgets from grid
            for i in reversed(range(grid_layout.count())):
                grid_layout.itemAt(i).widget().setParent(None)
            
            # Re-add buttons with new column count
            for idx, btn in enumerate(buttons):
                row = idx // columns
                col = idx % columns
                grid_layout.addWidget(btn, row, col)
    
    def create_color_editor(self):
        """Create the color editor panel"""
        editor_widget = QWidget()
        editor_layout = QVBoxLayout()
        
        # Title and controls
        header_layout = QHBoxLayout()
        title = QLabel('Palette Colors')
        title.setStyleSheet('font-size: 16px; font-weight: bold; padding: 10px;')
        header_layout.addWidget(title)
        
        # New Palette button
        new_palette_btn = QPushButton('+ New Palette')
        new_palette_btn.setToolTip('Duplicate current palette')
        new_palette_btn.clicked.connect(self.create_new_palette)
        header_layout.addWidget(new_palette_btn)
        
        editor_layout.addLayout(header_layout)
        
        # Tab widget for multiple palettes
        self.palette_tabs = QTabWidget()
        self.palette_tabs.setTabsClosable(True)
        self.palette_tabs.tabCloseRequested.connect(self.close_palette_tab)
        self.palette_tabs.currentChanged.connect(self.on_palette_tab_changed)
        editor_layout.addWidget(self.palette_tabs)
        
        # Palette Import/Export buttons
        palette_buttons_layout = QHBoxLayout()
        
        import_btn = QPushButton('Import Palette Map')
        import_btn.clicked.connect(self.import_palette_map)
        palette_buttons_layout.addWidget(import_btn)
        
        export_btn = QPushButton('Export Palette Map')
        export_btn.clicked.connect(self.export_positioned)
        palette_buttons_layout.addWidget(export_btn)
        
        editor_layout.addLayout(palette_buttons_layout)
        
        # Currently highlighted color preview
        self.highlighted_color_widget = QWidget()
        self.highlighted_color_widget.setFixedHeight(50)
        self.highlighted_color_widget.setStyleSheet('background-color: transparent; border: 2px solid #555;')
        
        highlighted_layout = QVBoxLayout()
        self.highlighted_color_label = QLabel('Hover over a color')
        self.highlighted_color_label.setAlignment(Qt.AlignCenter)
        self.highlighted_color_label.setStyleSheet('border: none; color: #888;')
        highlighted_layout.addWidget(self.highlighted_color_label)
        self.highlighted_color_widget.setLayout(highlighted_layout)
        
        editor_layout.addWidget(self.highlighted_color_widget)
        
        editor_widget.setLayout(editor_layout)
        return editor_widget
    
    def create_image_preview(self):
        """Create the image preview panel"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        
        # Title
        title = QLabel('Image Preview (Scroll to Zoom)')
        title.setStyleSheet('font-size: 16px; font-weight: bold; padding: 10px;')
        preview_layout.addWidget(title)
        
        # Image label with zoom support
        self.image_label = ZoomableLabel()
        self.image_label.editor = self  # Set reference to editor
        self.image_label.setText('No image loaded')
        self.image_label.setStyleSheet('background-color: #1e1e1e; color: #888888;')
        
        # Scroll area for image
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidgetResizable(False)
        
        # Set scroll area reference for middle mouse dragging
        self.image_label.scroll_area = scroll
        
        preview_layout.addWidget(scroll)
        
        preview_widget.setLayout(preview_layout)
        return preview_widget
    
    def create_pmap_widgets(self):
        """Create PMAP preview widgets (initially hidden)"""
        # PMAP List Preview Widget
        self.pmap_list_widget = QWidget()
        pmap_list_layout = QVBoxLayout()
        
        # Title bar with close button
        list_title_layout = QHBoxLayout()
        list_title = QLabel('PMAP Preview')
        list_title.setStyleSheet('font-size: 16px; font-weight: bold; padding: 10px;')
        list_title_layout.addWidget(list_title)
        
        # Close button for list view
        list_close_btn = QPushButton('×')
        list_close_btn.setFixedSize(25, 25)
        list_close_btn.setStyleSheet('''
            QPushButton {
                background-color: #555;
                border: 1px solid #777;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
            QPushButton:pressed {
                background-color: #999;
            }
        ''')
        list_close_btn.setToolTip('Close PMAP Preview')
        list_close_btn.clicked.connect(self.close_pmap_preview)
        list_title_layout.addWidget(list_close_btn)
        
        pmap_list_layout.addLayout(list_title_layout)
        
        # Table widget for ID, Hex, Count columns
        self.pmap_table = QTableWidget()
        self.pmap_table.setColumnCount(3)
        self.pmap_table.setHorizontalHeaderLabels(['ID', 'HEX', 'COUNT'])
        
        # Configure table appearance
        self.pmap_table.setStyleSheet('''
            QTableWidget {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                font-family: monospace;
                font-size: 12px;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444;
            }
            QTableWidget::item:selected {
                background-color: #2a82da;
            }
            QHeaderView::section {
                background-color: #444;
                color: white;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
            }
        ''')
        
        # Configure table behavior
        self.pmap_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pmap_table.setAlternatingRowColors(True)
        self.pmap_table.verticalHeader().setVisible(False)
        
        # Auto-resize columns
        header = self.pmap_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # ID column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # HEX column
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # COUNT column
        header.resizeSection(0, 40)  # ID column width
        header.resizeSection(2, 80)  # COUNT column width
        
        pmap_list_layout.addWidget(self.pmap_table)
        
        self.pmap_list_widget.setLayout(pmap_list_layout)
        self.pmap_list_widget.hide()
        
        # PMAP Raw Preview Widget
        self.pmap_raw_widget = QWidget()
        pmap_raw_layout = QVBoxLayout()
        
        # Title bar with close button
        raw_title_layout = QHBoxLayout()
        raw_title = QLabel('PMAP Raw JSON')
        raw_title.setStyleSheet('font-size: 16px; font-weight: bold; padding: 10px;')
        raw_title_layout.addWidget(raw_title)
        
        # Close button for raw view
        raw_close_btn = QPushButton('×')
        raw_close_btn.setFixedSize(25, 25)
        raw_close_btn.setStyleSheet('''
            QPushButton {
                background-color: #555;
                border: 1px solid #777;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
            QPushButton:pressed {
                background-color: #999;
            }
        ''')
        raw_close_btn.setToolTip('Close PMAP Raw JSON')
        raw_close_btn.clicked.connect(self.close_pmap_raw)
        raw_title_layout.addWidget(raw_close_btn)
        
        pmap_raw_layout.addLayout(raw_title_layout)
        
        # Text edit for raw JSON
        self.pmap_text = QTextEdit()
        self.pmap_text.setStyleSheet('''
            QTextEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                font-family: monospace;
                font-size: 11px;
            }
        ''')
        self.pmap_text.setReadOnly(True)
        pmap_raw_layout.addWidget(self.pmap_text)
        
        self.pmap_raw_widget.setLayout(pmap_raw_layout)
        self.pmap_raw_widget.hide()
    
    def open_image(self):
        """Open an image file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open Image', '', 
            'Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)'
        )
        
        if filename:
            try:
                # Load image with PIL
                self.image = Image.open(filename)
                
                # Convert to RGBA for consistency
                if self.image.mode != 'RGBA':
                    self.image = self.image.convert('RGBA')
                
                # Store original unchanged image
                self.original_image = self.image.copy()
                
                # Extract palette
                self.extract_palette()
                
                # Display image
                self.update_preview()
                
                # Update color editor
                self.update_color_editor()
                
                # Add to recent files
                self.add_recent_file(filename)
                
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to open image: {str(e)}')
    
    def extract_palette(self):
        """Extract unique colors from the image"""
        # Convert to numpy array
        self.image_array = np.array(self.image)
        
        # Get unique colors
        pixels = self.image_array.reshape(-1, 4)
        unique_colors = []
        seen = set()
        
        for pixel in pixels:
            color_tuple = tuple(pixel)
            if color_tuple not in seen:
                seen.add(color_tuple)
                # Convert to Python int to avoid numpy type issues
                unique_colors.append([int(pixel[0]), int(pixel[1]), int(pixel[2]), int(pixel[3])])
        
        self.original_palette = unique_colors.copy()
        
        # Initialize with first palette
        self.palettes = [unique_colors.copy()]
        self.current_palette_index = 0
    
    def update_color_editor(self):
        """Update the color editor with palette tabs"""
        # Clear existing tabs
        self.palette_tabs.clear()
        self.palette_buttons = []
        self.palette_grids = []
        
        # Create a tab for each palette
        for palette_idx, palette in enumerate(self.palettes):
            tab_widget = self.create_palette_tab(palette_idx, palette)
            self.palette_tabs.addTab(tab_widget, f'Palette {palette_idx + 1}')
        
        # Set current tab
        self.palette_tabs.setCurrentIndex(self.current_palette_index)
    
    def create_palette_tab(self, palette_idx, palette):
        """Create a tab widget for a single palette"""
        tab_widget = QWidget()
        tab_layout = QVBoxLayout()
        
        # Scroll area for palette colors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        palette_container = QWidget()
        palette_layout = QVBoxLayout()
        
        # Create grid layout for color buttons
        from PyQt5.QtWidgets import QGridLayout
        grid_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)
        grid_widget.setLayout(grid_layout)
        
        # Calculate columns based on available width (70px button + 5px spacing)
        button_size = 75  # 70px + 5px spacing
        available_width = self.color_editor.width() - 40  # Subtract margins and scrollbar
        columns = max(1, available_width // button_size)
        
        # Add color buttons in grid
        buttons_for_this_palette = []
        for idx, color in enumerate(palette):
            color_btn = self.create_color_button(palette_idx, idx, color)
            row = idx // columns
            col = idx % columns
            grid_layout.addWidget(color_btn, row, col)
            buttons_for_this_palette.append(color_btn)
        
        self.palette_buttons.append(buttons_for_this_palette)
        self.palette_grids.append((grid_layout, palette_idx))
        
        palette_layout.addWidget(grid_widget)
        palette_layout.addStretch()
        palette_container.setLayout(palette_layout)
        scroll.setWidget(palette_container)
        
        tab_layout.addWidget(scroll)
        tab_widget.setLayout(tab_layout)
        
        return tab_widget
    
    def create_new_palette(self):
        """Create new palette tab by duplicating current one"""
        if not self.palettes:
            return
        
        # Duplicate current palette
        current_palette = self.palettes[self.current_palette_index]
        new_palette = current_palette.copy()
        self.palettes.append(new_palette)
        
        # Refresh UI
        self.update_color_editor()
        
        # Switch to new tab
        self.palette_tabs.setCurrentIndex(len(self.palettes) - 1)
    
    def close_palette_tab(self, index):
        """Handle tab close with validation"""
        # Don't allow closing if only one palette
        if len(self.palettes) <= 1:
            QMessageBox.warning(
                self,
                'Cannot Close',
                'Cannot close the last palette tab.'
            )
            return
        
        # Remove palette
        self.palettes.pop(index)
        
        # Update current index if needed
        if self.current_palette_index >= len(self.palettes):
            self.current_palette_index = len(self.palettes) - 1
        elif self.current_palette_index > index:
            self.current_palette_index -= 1
        
        # Refresh UI
        self.update_color_editor()
    
    def on_palette_tab_changed(self, index):
        """Switch active palette and refresh preview"""
        if index < 0 or index >= len(self.palettes):
            return
        
        self.current_palette_index = index
        
        # Apply current palette to image and update preview
        if self.original_image:
            self.apply_palette_to_image()
            self.update_preview()
            
            # Trigger PMAP refresh for new palette
            self.trigger_pmap_refresh()
    
    def create_color_button(self, palette_idx, color_idx, color):
        """Create a colored button for a single color"""
        r, g, b, a = color
        
        # Create button with color as background
        btn = QPushButton()
        btn.setFixedSize(70, 70)
        btn.setToolTip(f'#{r:02x}{g:02x}{b:02x}{a:02x}')
        
        # Set button style with color
        # Use contrasting text color based on brightness
        brightness = (int(r) * 299 + int(g) * 587 + int(b) * 114) / 1000
        text_color = 'black' if brightness > 128 else 'white'
        
        btn.setStyleSheet(f'''
            QPushButton {{
                background-color: rgba({int(r)},{int(g)},{int(b)},{int(a)});
                border: 2px solid #555;
                color: {text_color};
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid white;
            }}
            QPushButton:pressed {{
                border: 3px solid yellow;
            }}
        ''')
        
        # Show hex code on button
        btn.setText(f'#{int(r):02x}{int(g):02x}{int(b):02x}')
        
        btn.clicked.connect(lambda: self.edit_color(palette_idx, color_idx))
        
        # Add mouse press event for right-click paste
        def mousePressEvent(event):
            if event.button() == Qt.RightButton:
                self.paste_color_from_clipboard(palette_idx, color_idx)
            else:
                QPushButton.mousePressEvent(btn, event)
        
        btn.mousePressEvent = mousePressEvent
        
        # Add hover events for preview
        btn.enterEvent = lambda event: self.show_color_preview(color_idx)
        btn.leaveEvent = lambda event: self.hide_color_preview()
        
        return btn
    
    def edit_color(self, palette_idx, color_idx):
        """Edit a specific color in the palette"""
        old_color = self.palettes[palette_idx][color_idx]
        
        # Open color dialog
        initial_color = QColor(old_color[0], old_color[1], old_color[2], old_color[3])
        color = QColorDialog.getColor(
            initial_color, 
            self, 
            'Choose Color',
            QColorDialog.ShowAlphaChannel
        )
        
        if color.isValid():
            # Save to undo history
            self.save_color_to_history(palette_idx, color_idx)
            
            # Update palette
            new_color = [color.red(), color.green(), color.blue(), color.alpha()]
            self.palettes[palette_idx][color_idx] = new_color
            
            # Update the button
            btn = self.palette_buttons[palette_idx][color_idx]
            r, g, b, a = new_color
            
            # Update button style
            brightness = (int(r) * 299 + int(g) * 587 + int(b) * 114) / 1000
            text_color = 'black' if brightness > 128 else 'white'
            
            btn.setStyleSheet(f'''
                QPushButton {{
                    background-color: rgba({int(r)},{int(g)},{int(b)},{int(a)});
                    border: 2px solid #555;
                    color: {text_color};
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
                QPushButton:pressed {{
                    border: 3px solid yellow;
                }}
            ''')
            
            btn.setText(f'#{int(r):02x}{int(g):02x}{int(b):02x}')
            btn.setToolTip(f'#{int(r):02x}{int(g):02x}{int(b):02x}{int(a):02x}')
            
            # Update image preview if this is the current palette
            if palette_idx == self.current_palette_index:
                self.apply_palette_to_image()
                self.update_preview()
                
                # Trigger PMAP refresh
                self.trigger_pmap_refresh()
    
    def paste_color_from_clipboard(self, palette_idx, color_idx):
        """Paste hex color from clipboard"""
        clipboard = QApplication.clipboard()
        hex_text = clipboard.text().strip()
        
        # Remove # if present
        if hex_text.startswith('#'):
            hex_text = hex_text[1:]
        
        # Validate hex format
        if not hex_text:
            QMessageBox.warning(self, 'Warning', 'Clipboard is empty')
            return
        
        try:
            # Parse hex color (supports RGB, RGBA, RRGGBB, RRGGBBAA)
            hex_text = hex_text.upper()
            
            if len(hex_text) == 3:  # RGB short form
                r = int(hex_text[0] * 2, 16)
                g = int(hex_text[1] * 2, 16)
                b = int(hex_text[2] * 2, 16)
                a = 255
            elif len(hex_text) == 4:  # RGBA short form
                r = int(hex_text[0] * 2, 16)
                g = int(hex_text[1] * 2, 16)
                b = int(hex_text[2] * 2, 16)
                a = int(hex_text[3] * 2, 16)
            elif len(hex_text) == 6:  # RRGGBB
                r = int(hex_text[0:2], 16)
                g = int(hex_text[2:4], 16)
                b = int(hex_text[4:6], 16)
                a = 255
            elif len(hex_text) == 8:  # RRGGBBAA
                r = int(hex_text[0:2], 16)
                g = int(hex_text[2:4], 16)
                b = int(hex_text[4:6], 16)
                a = int(hex_text[6:8], 16)
            else:
                raise ValueError("Invalid hex length")
            
            # Save to undo history
            self.save_color_to_history(palette_idx, color_idx)
            
            # Update palette
            new_color = [r, g, b, a]
            self.palettes[palette_idx][color_idx] = new_color
            
            # Update the button
            btn = self.palette_buttons[palette_idx][color_idx]
            
            # Update button style
            brightness = (int(r) * 299 + int(g) * 587 + int(b) * 114) / 1000
            text_color = 'black' if brightness > 128 else 'white'
            
            btn.setStyleSheet(f'''
                QPushButton {{
                    background-color: rgba({int(r)},{int(g)},{int(b)},{int(a)});
                    border: 2px solid #555;
                    color: {text_color};
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
                QPushButton:pressed {{
                    border: 3px solid yellow;
                }}
            ''')
            
            btn.setText(f'#{int(r):02x}{int(g):02x}{int(b):02x}')
            btn.setToolTip(f'#{int(r):02x}{int(g):02x}{int(b):02x}{int(a):02x}')
            
            # Update image preview if this is the current palette
            if palette_idx == self.current_palette_index:
                self.apply_palette_to_image()
                self.update_preview()
                
                # Trigger PMAP refresh
                self.trigger_pmap_refresh()
                
        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, 'Warning', f'Invalid hex color format: {hex_text}\nExpected formats: RGB, RGBA, RRGGBB, or RRGGBBAA')
    
    def show_color_preview(self, idx):
        """Show only the hovered color in the image preview"""
        if self.original_image is None:
            return
        
        # Get the original color to isolate
        original_color = self.original_palette[idx]
        
        # Create isolated image
        isolated_array = np.array(self.original_image).copy()
        height, width = isolated_array.shape[:2]
        
        # Make all pixels transparent except the chosen color
        transparent = np.array([0, 0, 0, 0], dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                pixel = isolated_array[y, x]
                if not np.array_equal(pixel, original_color):
                    isolated_array[y, x] = transparent
        
        # Convert to PIL Image and then to QPixmap
        isolated_image = Image.fromarray(isolated_array, 'RGBA')
        img_data = isolated_image.tobytes('raw', 'RGBA')
        qimage = QImage(img_data, isolated_image.width, isolated_image.height,
                       isolated_image.width * 4, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Update preview with isolated color
        self.image_label.setCurrentPixmap(pixmap)
    
    def hide_color_preview(self):
        """Restore full image preview"""
        if self.image is None:
            return
        
        # Convert current image to QPixmap
        img_data = self.image.tobytes('raw', 'RGBA')
        qimage = QImage(img_data, self.image.width, self.image.height,
                       self.image.width * 4, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Update preview with full image
        self.image_label.setCurrentPixmap(pixmap)
    
    def get_pixel_color_at_pos(self, widget_pos):
        """Get the color at a specific position in the preview widget"""
        if not self.image or not self.image_label.pixmap():
            return None
        
        # Get the displayed pixmap and its position
        pixmap = self.image_label.pixmap()
        label_rect = self.image_label.rect()
        
        # Calculate offset (image might be centered in label)
        offset_x = (label_rect.width() - pixmap.width()) // 2
        offset_y = (label_rect.height() - pixmap.height()) // 2
        
        # Adjust widget position to pixmap coordinates
        pixmap_x = widget_pos.x() - offset_x
        pixmap_y = widget_pos.y() - offset_y
        
        # Check if position is within pixmap bounds
        if pixmap_x < 0 or pixmap_y < 0 or pixmap_x >= pixmap.width() or pixmap_y >= pixmap.height():
            return None
        
        # Convert to original image coordinates (accounting for zoom)
        orig_x = int(pixmap_x / self.image_label.zoom_factor)
        orig_y = int(pixmap_y / self.image_label.zoom_factor)
        
        # Check bounds in original image
        if orig_x < 0 or orig_y < 0 or orig_x >= self.image.width or orig_y >= self.image.height:
            return None
        
        # Get pixel color from current image
        pixel = self.image.getpixel((orig_x, orig_y))
        return pixel
    
    def on_preview_hover(self, pos):
        """Handle hover over preview to underline corresponding palette button"""
        pixel_color = self.get_pixel_color_at_pos(pos)
        if pixel_color is None:
            # Clear all underlines
            self.clear_all_button_underlines()
            return
        
        # Find which palette color this pixel belongs to
        current_palette = self.palettes[self.current_palette_index]
        for idx, palette_color in enumerate(current_palette):
            if tuple(pixel_color) == tuple(palette_color):
                self.underline_button(self.current_palette_index, idx)
                return
        
        # No match found, clear underlines
        self.clear_all_button_underlines()
    
    def on_preview_click(self, pos):
        """Handle click on preview to select color from palette"""
        pixel_color = self.get_pixel_color_at_pos(pos)
        if pixel_color is None:
            return
        
        # Find which palette color this pixel belongs to
        current_palette = self.palettes[self.current_palette_index]
        for idx, palette_color in enumerate(current_palette):
            if tuple(pixel_color) == tuple(palette_color):
                # Trigger edit color dialog
                self.edit_color(self.current_palette_index, idx)
                return
    
    def on_preview_right_click(self, pos):
        """Handle right-click on preview to paste color from clipboard"""
        pixel_color = self.get_pixel_color_at_pos(pos)
        if pixel_color is None:
            return
        
        # Find which palette color this pixel belongs to
        current_palette = self.palettes[self.current_palette_index]
        for idx, palette_color in enumerate(current_palette):
            if tuple(pixel_color) == tuple(palette_color):
                # Paste color from clipboard
                self.paste_color_from_clipboard(self.current_palette_index, idx)
                return
    
    def underline_button(self, palette_idx, color_idx):
        """Underline a specific button's text"""
        # Clear all underlines first
        self.clear_all_button_underlines()
        
        # Set underline on target button
        btn = self.palette_buttons[palette_idx][color_idx]
        font = btn.font()
        font.setUnderline(True)
        btn.setFont(font)
        
        # Update highlighted color display
        color = self.palettes[palette_idx][color_idx]
        r, g, b, a = color
        self.highlighted_color_widget.setStyleSheet(
            f'background-color: rgba({int(r)},{int(g)},{int(b)},{int(a)}); border: 2px solid #555;'
        )
        self.highlighted_color_label.setStyleSheet('border: none; color: white; font-weight: bold;')
        self.highlighted_color_label.setText(f'#{int(r):02x}{int(g):02x}{int(b):02x}{int(a):02x}')
    
    def clear_all_button_underlines(self):
        """Clear underlines from all buttons"""
        for palette_buttons in self.palette_buttons:
            for btn in palette_buttons:
                font = btn.font()
                font.setUnderline(False)
                btn.setFont(font)
        
        # Reset highlighted color display
        self.highlighted_color_widget.setStyleSheet('background-color: transparent; border: 2px solid #555;')
        self.highlighted_color_label.setStyleSheet('border: none; color: #888;')
        self.highlighted_color_label.setText('Hover over a color')
    
    def save_color_to_history(self, palette_idx, color_idx):
        """Save current color to undo history before changing it"""
        if palette_idx >= len(self.palettes) or color_idx >= len(self.palettes[palette_idx]):
            return
        
        old_color = self.palettes[palette_idx][color_idx].copy()
        self.undo_history.append((palette_idx, color_idx, old_color))
        
        # Clear redo history when new change is made
        self.redo_history.clear()
        
        # Limit history size
        if len(self.undo_history) > self.max_undo_history:
            self.undo_history.pop(0)
    
    def undo_color_change(self):
        """Undo the last color change"""
        if not self.undo_history:
            return
        
        # Get last change
        palette_idx, color_idx, old_color = self.undo_history.pop()
        
        # Check if palette and color still exist
        if palette_idx >= len(self.palettes) or color_idx >= len(self.palettes[palette_idx]):
            return
        
        # Save current color to redo history
        current_color = self.palettes[palette_idx][color_idx].copy()
        self.redo_history.append((palette_idx, color_idx, current_color))
        
        # Limit redo history size
        if len(self.redo_history) > self.max_undo_history:
            self.redo_history.pop(0)
        
        # Restore old color
        self.palettes[palette_idx][color_idx] = old_color
        
        # Update button
        btn = self.palette_buttons[palette_idx][color_idx]
        r, g, b, a = old_color
        
        brightness = (int(r) * 299 + int(g) * 587 + int(b) * 114) / 1000
        text_color = 'black' if brightness > 128 else 'white'
        
        btn.setStyleSheet(f'''
            QPushButton {{
                background-color: rgba({int(r)},{int(g)},{int(b)},{int(a)});
                border: 2px solid #555;
                color: {text_color};
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid white;
            }}
            QPushButton:pressed {{
                border: 3px solid yellow;
            }}
        ''')
        
        btn.setText(f'#{int(r):02x}{int(g):02x}{int(b):02x}')
        btn.setToolTip(f'#{int(r):02x}{int(g):02x}{int(b):02x}{int(a):02x}')
        
        # Update image preview if this is the current palette
        if palette_idx == self.current_palette_index:
            self.apply_palette_to_image()
            self.update_preview()
            
            # Trigger PMAP refresh
            self.trigger_pmap_refresh()
    
    def redo_color_change(self):
        """Redo the last undone color change"""
        if not self.redo_history:
            return
        
        # Get last undone change
        palette_idx, color_idx, redo_color = self.redo_history.pop()
        
        # Check if palette and color still exist
        if palette_idx >= len(self.palettes) or color_idx >= len(self.palettes[palette_idx]):
            return
        
        # Save current color to undo history
        current_color = self.palettes[palette_idx][color_idx].copy()
        self.undo_history.append((palette_idx, color_idx, current_color))
        
        # Limit undo history size
        if len(self.undo_history) > self.max_undo_history:
            self.undo_history.pop(0)
        
        # Apply redo color
        self.palettes[palette_idx][color_idx] = redo_color
        
        # Update button
        btn = self.palette_buttons[palette_idx][color_idx]
        r, g, b, a = redo_color
        
        brightness = (int(r) * 299 + int(g) * 587 + int(b) * 114) / 1000
        text_color = 'black' if brightness > 128 else 'white'
        
        btn.setStyleSheet(f'''
            QPushButton {{
                background-color: rgba({int(r)},{int(g)},{int(b)},{int(a)});
                border: 2px solid #555;
                color: {text_color};
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid white;
            }}
            QPushButton:pressed {{
                border: 3px solid yellow;
            }}
        ''')
        
        btn.setText(f'#{int(r):02x}{int(g):02x}{int(b):02x}')
        btn.setToolTip(f'#{int(r):02x}{int(g):02x}{int(b):02x}{int(a):02x}')
        
        # Update image preview if this is the current palette
        if palette_idx == self.current_palette_index:
            self.apply_palette_to_image()
            self.update_preview()
            
            # Trigger PMAP refresh
            self.trigger_pmap_refresh()
    
    def apply_palette_to_image(self):
        """Apply current palette to the image"""
        if self.image_array is None:
            return
        
        # Create new image array
        new_array = self.image_array.copy()
        height, width = new_array.shape[:2]
        
        # Get current palette
        current_palette = self.palettes[self.current_palette_index]
        
        # Replace colors
        for old_color, new_color in zip(self.original_palette, current_palette):
            # Find all pixels with old color
            mask = np.all(new_array == old_color, axis=2)
            # Replace with new color
            new_array[mask] = new_color
        
        # Update image
        self.image = Image.fromarray(new_array.astype(np.uint8), 'RGBA')
    
    def update_preview(self):
        """Update the image preview"""
        if self.image is None:
            return
        
        # Convert PIL Image to QPixmap
        img_data = self.image.tobytes('raw', 'RGBA')
        qimage = QImage(img_data, self.image.width, self.image.height, 
                       self.image.width * 4, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Check if zoom has been applied
        if self.image_label.zoom_factor != 1.0:
            # Preserve zoom level
            self.image_label.setCurrentPixmap(pixmap)
        else:
            # Initial load - fit to available space
            self.image_label.setPixmap(pixmap)
            
            available_width = self.image_label.parent().width() - 20
            available_height = self.image_label.parent().height() - 20
            
            if pixmap.width() > available_width or pixmap.height() > available_height:
                scaled = pixmap.scaled(available_width, available_height, 
                                      Qt.KeepAspectRatio, Qt.FastTransformation)  # Pixelated, no antialiasing
                self.image_label.setFixedSize(scaled.size())
                self.image_label.setPixmap(scaled)
            else:
                self.image_label.setFixedSize(pixmap.size())
    
    def save_image(self):
        """Save the current image"""
        if self.image is None:
            QMessageBox.warning(self, 'Warning', 'No image to save')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Save Image', '', 
            'PNG Files (*.png);;All Files (*)'
        )
        
        if filename:
            try:
                self.image.save(filename)
                QMessageBox.information(self, 'Success', 'Image saved successfully')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to save image: {str(e)}')
    
    def export_palette(self):
        """Export current palette as PNG"""
        if not self.palettes or self.current_palette_index >= len(self.palettes):
            QMessageBox.warning(self, 'Warning', 'No palette to export')
            return
        
        current_palette = self.palettes[self.current_palette_index]
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export Palette', 'palette.png', 
            'PNG Files (*.png);;All Files (*)'
        )
        
        if filename:
            try:
                # Create palette image (1 pixel per color)
                width = len(current_palette)
                palette_img = Image.new('RGBA', (width, 1))
                
                for i, color in enumerate(current_palette):
                    palette_img.putpixel((i, 0), tuple(color))
                
                palette_img.save(filename)
                QMessageBox.information(self, 'Success', f'Palette exported: {width} colors')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to export palette: {str(e)}')
    
    def import_palette(self):
        """Import palette from PNG"""
        if self.image is None:
            QMessageBox.warning(self, 'Warning', 'Open an image first')
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Import Palette', '', 
            'PNG Files (*.png);;All Files (*)'
        )
        
        if filename:
            try:
                # Load palette image
                palette_img = Image.open(filename)
                if palette_img.mode != 'RGBA':
                    palette_img = palette_img.convert('RGBA')
                
                # Read colors from first row
                new_palette = []
                for x in range(palette_img.width):
                    color = palette_img.getpixel((x, 0))
                    new_palette.append(list(color))
                
                current_palette = self.palettes[self.current_palette_index]
                
                # Check if palette size matches
                if len(new_palette) != len(current_palette):
                    QMessageBox.warning(
                        self, 'Warning', 
                        f'Palette size mismatch: expected {len(current_palette)}, got {len(new_palette)}'
                    )
                    return
                
                # Apply new palette to current tab
                self.palettes[self.current_palette_index] = new_palette
                self.update_color_editor()
                self.apply_palette_to_image()
                self.update_preview()
                
                QMessageBox.information(self, 'Success', f'Palette imported: {len(new_palette)} colors')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to import palette: {str(e)}')
    
    def export_positioned(self):
        """Export palette map data as PMAP with unique IDs and pixel positions"""
        if self.original_image is None:
            QMessageBox.warning(self, 'Warning', 'No image loaded')
            return
        
        if not self.palettes or self.current_palette_index >= len(self.palettes):
            QMessageBox.warning(self, 'Warning', 'No palette available')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export Palette Map', 'palette_map.pmap',
            'Palette Map Files (*.pmap);;All Files (*)'
        )
        
        if filename:
            try:
                # Get the original image array for position analysis
                original_array = np.array(self.original_image)
                height, width = original_array.shape[:2]
                
                # Create the positioned data structure
                positioned_data = {}
                
                # Get current palette
                current_palette = self.palettes[self.current_palette_index]
                
                # Process each unique color in the palette
                for palette_idx, palette_color in enumerate(current_palette):
                    # Create unique ID starting from 1
                    unique_id = str(palette_idx + 1)
                    
                    # Find all positions with this color in the original image
                    positions = []
                    
                    # Convert palette color to numpy array for comparison
                    target_color = np.array(palette_color, dtype=np.uint8)
                    
                    # Search through all pixels
                    for y in range(height):
                        for x in range(width):
                            pixel = original_array[y, x]
                            # Check if pixel matches this palette color
                            if np.array_equal(pixel, target_color):
                                positions.append({"x": int(x), "y": int(y)})
                    
                    # Store color info and positions
                    positioned_data[unique_id] = {
                        "hex": f"#{palette_color[0]:02x}{palette_color[1]:02x}{palette_color[2]:02x}{palette_color[3]:02x}",
                        "positions": positions
                    }
                
                # Write JSON file
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(positioned_data, f, indent=2, ensure_ascii=False)
                
                # Calculate total pixels for summary
                total_pixels = sum(len(data["positions"]) for data in positioned_data.values())
                
                QMessageBox.information(
                    self, 'Success', 
                    f'Palette map exported successfully!\n'
                    f'Colors: {len(positioned_data)}\n'
                    f'Total pixels: {total_pixels}'
                )
                
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to export palette map: {str(e)}')
    
    def import_palette_map(self):
        """Import palette map from PMAP file and replace colors in current palette"""
        if not self.original_image:
            QMessageBox.warning(self, 'Warning', 'Load an image first before importing PMAP')
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Import Palette Map', '',
            'Palette Map Files (*.pmap);;JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            try:
                # Load PMAP file
                with open(filename, 'r', encoding='utf-8') as f:
                    pmap_data = json.load(f)
                
                if not pmap_data:
                    QMessageBox.warning(self, 'Warning', 'Palette map file is empty')
                    return
                
                # Generate current PMAP to get position mapping
                current_pmap = self.generate_pmap_data()
                
                if not current_pmap:
                    QMessageBox.warning(self, 'Warning', 'No current palette data available')
                    return
                
                # Extract new colors from imported PMAP
                imported_colors = {}
                for unique_id, color_data in pmap_data.items():
                    if 'hex' not in color_data:
                        QMessageBox.warning(self, 'Warning', f'Invalid format for color ID {unique_id}')
                        return
                    
                    hex_color = color_data['hex']
                    
                    # Parse hex color (remove # if present)
                    if hex_color.startswith('#'):
                        hex_color = hex_color[1:]
                    
                    if len(hex_color) != 8:
                        QMessageBox.warning(self, 'Warning', f'Invalid hex color format: #{hex_color}')
                        return
                    
                    # Convert hex to RGBA
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    a = int(hex_color[6:8], 16)
                    
                    imported_colors[unique_id] = [r, g, b, a]
                
                # Update current palette with imported colors
                if not self.palettes:
                    QMessageBox.warning(self, 'Warning', 'No current palette available')
                    return
                
                # Create new palette tab with updated colors
                new_palette = []
                colors_mapped = 0
                
                # Map imported colors to current palette positions
                for current_id, current_data in current_pmap.items():
                    if current_id in imported_colors:
                        # Use imported color
                        new_palette.append(imported_colors[current_id])
                        colors_mapped += 1
                    else:
                        # Keep original color if no mapping found
                        original_idx = int(current_id) - 1
                        if original_idx < len(self.palettes[self.current_palette_index]):
                            new_palette.append(self.palettes[self.current_palette_index][original_idx])
                        else:
                            new_palette.append([0, 0, 0, 255])  # Default black
                
                # Add any additional imported colors that don't have current mappings
                for imp_id, imp_color in imported_colors.items():
                    if int(imp_id) > len(new_palette):
                        new_palette.append(imp_color)
                
                # Create new palette tab
                self.palettes.append(new_palette)
                self.current_palette_index = len(self.palettes) - 1
                
                # Apply new palette and refresh
                self.apply_palette_to_image()
                self.update_color_editor()
                self.update_preview()
                
                # Trigger PMAP refresh for updated palette
                self.trigger_pmap_refresh()
                
                QMessageBox.information(
                    self, 'Success',
                    f'Palette map applied successfully!\n'
                    f'Colors mapped: {colors_mapped}\n'
                    f'Total colors in palette: {len(new_palette)}\n'
                    f'New palette tab created: Tab {self.current_palette_index + 1}'
                )
                
            except json.JSONDecodeError as e:
                QMessageBox.critical(self, 'Error', f'Invalid JSON format: {str(e)}')
            except KeyError as e:
                QMessageBox.critical(self, 'Error', f'Missing required field: {str(e)}')
            except ValueError as e:
                QMessageBox.critical(self, 'Error', f'Invalid data format: {str(e)}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to import palette map: {str(e)}')
    
    def get_settings_file_path(self):
        """Get the path to the settings.json file - always next to the application script"""
        import os
        import sys
        
        # Get the directory where the main script is located
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller executable
            script_dir = os.path.dirname(sys.executable)
        else:
            # Running as Python script
            script_dir = os.path.dirname(os.path.abspath(__file__))
        
        settings_path = os.path.join(script_dir, 'settings.json')
        
        # Ensure the directory exists (should always exist since script is there)
        os.makedirs(script_dir, exist_ok=True)
        
        return settings_path
    
    def load_recent_files(self):
        """Load recent files from settings.json - always searches next to application script"""
        try:
            import os
            settings_file = self.get_settings_file_path()
            
            print(f"Searching for settings file at: {settings_file}")
            
            if os.path.exists(settings_file):
                print(f"Settings file found, loading recent files...")
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                    self.recent_files = settings_data.get('recent_files', [])
                    print(f"Loaded {len(self.recent_files)} recent files")
            else:
                print("Settings file not found, initializing empty recent files list")
                self.recent_files = []
            
            # Ensure we don't exceed max recent files
            self.recent_files = self.recent_files[:self.max_recent_files]
        except Exception as e:
            print(f"Error loading recent files: {e}")
            self.recent_files = []
    
    def save_recent_files(self):
        """Save recent files to settings.json - always saves next to application script"""
        try:
            import os
            settings_file = self.get_settings_file_path()
            
            print(f"Saving settings to: {settings_file}")
            
            # Load existing settings or create new ones
            settings_data = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings_data = json.load(f)
                    print("Loaded existing settings file")
                except:
                    print("Existing settings file corrupted, creating new one")
                    settings_data = {}
            else:
                print("Creating new settings file")
            
            # Update recent files
            settings_data['recent_files'] = self.recent_files
            
            # Save to file
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully saved {len(self.recent_files)} recent files")
                
        except Exception as e:
            print(f"Error saving recent files: {e}")
    
    def add_recent_file(self, filepath):
        """Add a file to the recent files list"""
        # Remove if already exists
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        # Add to beginning
        self.recent_files.insert(0, filepath)
        
        # Limit to max recent files
        self.recent_files = self.recent_files[:self.max_recent_files]
        
        # Save and update menu
        self.save_recent_files()
        self.update_recent_menu()
    
    def update_recent_menu(self):
        """Update the recent files menu"""
        self.recent_menu.clear()
        
        if not self.recent_files:
            no_recent_action = self.recent_menu.addAction('No recent files')
            no_recent_action.setEnabled(False)
            return
        
        for i, filepath in enumerate(self.recent_files):
            # Create action with filename and number shortcut
            import os
            filename = os.path.basename(filepath)
            action_text = f'&{i+1}. {filename}'
            
            action = self.recent_menu.addAction(action_text)
            if i < 9:  # Only add shortcuts for first 9 items
                action.setShortcut(f'Ctrl+{i+1}')
            
            # Use lambda with default parameter to capture filepath
            action.triggered.connect(lambda checked, path=filepath: self.open_recent_file(path))
        
        # Add separator and clear action
        if self.recent_files:
            self.recent_menu.addSeparator()
            clear_action = self.recent_menu.addAction('&Clear Recent Files')
            clear_action.triggered.connect(self.clear_recent_files)
    
    def open_recent_file(self, filepath):
        """Open a file from recent files list"""
        try:
            import os
            if not os.path.exists(filepath):
                QMessageBox.warning(self, 'Warning', f'File not found: {filepath}')
                # Remove from recent files
                if filepath in self.recent_files:
                    self.recent_files.remove(filepath)
                    self.save_recent_files()
                    self.update_recent_menu()
                return
            
            # Load image with PIL
            self.image = Image.open(filepath)
            
            # Convert to RGBA for consistency
            if self.image.mode != 'RGBA':
                self.image = self.image.convert('RGBA')
            
            # Store original unchanged image
            self.original_image = self.image.copy()
            
            # Extract palette
            self.extract_palette()
            
            # Display image
            self.update_preview()
            
            # Update color editor
            self.update_color_editor()
            
            # Add to recent files (moves to top if already there)
            self.add_recent_file(filepath)
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to open file: {str(e)}')
            # Remove from recent files if it caused an error
            if filepath in self.recent_files:
                self.recent_files.remove(filepath)
                self.save_recent_files()
                self.update_recent_menu()
    
    def clear_recent_files(self):
        """Clear all recent files"""
        self.recent_files.clear()
        self.save_recent_files()
        self.update_recent_menu()
    
    def toggle_pmap_preview(self):
        """Toggle PMAP preview list visibility"""
        self.pmap_preview_visible = not self.pmap_preview_visible
        
        if self.pmap_preview_visible:
            self.splitter.addWidget(self.pmap_list_widget)
            self.pmap_list_widget.show()
            self.update_pmap_preview()
            # Adjust splitter sizes
            sizes = self.splitter.sizes()
            if len(sizes) == 3:
                total = sum(sizes)
                self.splitter.setSizes([int(total * 0.25), int(total * 0.5), int(total * 0.25)])
        else:
            self.pmap_list_widget.hide()
            self.splitter.sizes()
    
    def toggle_pmap_raw(self):
        """Toggle PMAP raw JSON visibility"""
        self.pmap_raw_visible = not self.pmap_raw_visible
        
        if self.pmap_raw_visible:
            self.splitter.addWidget(self.pmap_raw_widget)
            self.pmap_raw_widget.show()
            self.update_pmap_raw()
            # Adjust splitter sizes
            sizes = self.splitter.sizes()
            if len(sizes) >= 3:
                total = sum(sizes)
                if len(sizes) == 3:
                    self.splitter.setSizes([int(total * 0.25), int(total * 0.5), int(total * 0.25)])
                else:  # 4 panels
                    self.splitter.setSizes([int(total * 0.2), int(total * 0.4), int(total * 0.2), int(total * 0.2)])
        else:
            self.pmap_raw_widget.hide()
    
    def update_pmap_preview(self):
        """Update the PMAP preview list (async)"""
        if not self.pmap_preview_visible or not self.original_image:
            return
        
        if not self.palettes or self.current_palette_index >= len(self.palettes):
            return
        
        # Check if we have cached data
        cache_key = self.get_pmap_cache_key()
        if cache_key == self.pmap_cache_key and self.pmap_data_cache:
            self.populate_pmap_list(self.pmap_data_cache)
            return
        
        # Show loading state immediately
        self.pmap_table.setRowCount(1)
        self.pmap_table.setColumnCount(1)
        self.pmap_table.setHorizontalHeaderLabels(['Status'])
        loading_item = QTableWidgetItem("Loading PMAP data...")
        loading_item.setTextAlignment(Qt.AlignCenter)
        self.pmap_table.setItem(0, 0, loading_item)
        
        # Force UI update before starting processing
        QApplication.processEvents()
        
        # Start chunked processing for large images
        image_size = self.original_image.width * self.original_image.height
        if image_size > 50000:  # Use chunked processing for images > 50k pixels
            self.start_chunked_processing()
        else:
            # Use direct processing for small images
            self.request_pmap_update()
    
    def populate_pmap_list(self, pmap_data):
        """Populate the PMAP table with data"""
        if not self.pmap_preview_visible:
            return
        
        # Set number of rows
        self.pmap_table.setRowCount(len(pmap_data))
        
        # Populate table rows
        row = 0
        for unique_id, data in pmap_data.items():
            count = len(data['positions'])
            hex_color = data['hex']
            
            # ID column
            id_item = QTableWidgetItem(unique_id)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.pmap_table.setItem(row, 0, id_item)
            
            # HEX column
            hex_item = QTableWidgetItem(hex_color)
            hex_item.setTextAlignment(Qt.AlignCenter)
            self.pmap_table.setItem(row, 1, hex_item)
            
            # COUNT column
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.pmap_table.setItem(row, 2, count_item)
            
            # Color the row background with the actual color
            try:
                if hex_color.startswith('#') and len(hex_color) == 9:
                    # Create color from hex (without alpha for background)
                    from PyQt5.QtGui import QColor
                    r = int(hex_color[1:3], 16)
                    g = int(hex_color[3:5], 16) 
                    b = int(hex_color[5:7], 16)
                    background_color = QColor(r, g, b, 60)  # Semi-transparent background
                    text_color = QColor(255, 255, 255)  # White text
                    
                    # Apply colors to all cells in the row
                    for col in range(3):
                        item = self.pmap_table.item(row, col)
                        if item:
                            item.setBackground(background_color)
                            item.setForeground(text_color)
            except:
                pass
            
            row += 1
    
    def update_pmap_raw(self):
        """Update the PMAP raw JSON display (async)"""
        if not self.pmap_raw_visible or not self.original_image:
            return
        
        if not self.palettes or self.current_palette_index >= len(self.palettes):
            self.pmap_text.setText("No palette data available")
            return
        
        # Check if we have cached data
        cache_key = self.get_pmap_cache_key()
        if cache_key == self.pmap_cache_key and self.pmap_data_cache:
            # Use chunked JSON generation even for cached data
            self.generate_json_chunked(self.pmap_data_cache)
            return
        
        # Show loading state immediately
        self.pmap_text.setText("Loading PMAP data...")
        
        # Force UI update before starting processing
        QApplication.processEvents()
        
        # Start processing (will use cached result from preview if already computed)
        image_size = self.original_image.width * self.original_image.height
        if image_size > 50000:  # Use chunked processing for images > 50k pixels
            self.start_chunked_processing()
        else:
            # Use direct processing for small images
            self.request_pmap_update()
    
    def generate_pmap_data(self):
        """Generate PMAP data structure for current palette (legacy method)"""
        return self.generate_pmap_data_optimized()
    
    def get_pmap_cache_key(self):
        """Generate a cache key based on current state"""
        if not self.original_image or not self.palettes or self.current_palette_index >= len(self.palettes):
            return None
        
        # Create key from palette colors and image hash
        palette = self.palettes[self.current_palette_index]
        palette_str = str([(c[0], c[1], c[2], c[3]) for c in palette])
        image_hash = hash(self.original_image.tobytes())
        return f"{image_hash}_{hash(palette_str)}"
    
    def request_pmap_update(self):
        """Request deferred PMAP update"""
        if not self.original_image or not self.palettes or self.current_palette_index >= len(self.palettes):
            return
        
        # Delay processing to avoid blocking UI
        self.pmap_update_timer.start(100)  # 100ms delay
    
    def process_pmap_update(self):
        """Process PMAP update in main thread"""
        if not self.original_image or not self.palettes or self.current_palette_index >= len(self.palettes):
            return
        
        try:
            # Generate PMAP data with optimized algorithm
            pmap_data = self.generate_pmap_data_optimized()
            
            # Cache the data
            self.pmap_data_cache = pmap_data
            self.pmap_cache_key = self.get_pmap_cache_key()
            
            # Update UI components
            if self.pmap_preview_visible:
                self.populate_pmap_list(pmap_data)
            
            if self.pmap_raw_visible:
                json_text = json.dumps(pmap_data, indent=2, ensure_ascii=False)
                self.pmap_text.setText(json_text)
                
        except Exception as e:
            print(f"Error processing PMAP data: {e}")
    
    def generate_pmap_data_optimized(self):
        """Generate PMAP data with optimized algorithm"""
        if not self.original_image or not self.palettes:
            return {}
        
        # Get the original image array for position analysis
        original_array = np.array(self.original_image)
        height, width = original_array.shape[:2]
        
        # Create the positioned data structure
        positioned_data = {}
        
        # Get current palette
        current_palette = self.palettes[self.current_palette_index]
        
        # Process each unique color in the palette
        for palette_idx, palette_color in enumerate(current_palette):
            # Create unique ID starting from 1
            unique_id = str(palette_idx + 1)
            
            # Convert palette color to numpy array for comparison
            target_color = np.array(palette_color, dtype=np.uint8)
            
            # Search through all pixels (optimized with numpy)
            mask = np.all(original_array == target_color, axis=2)
            y_indices, x_indices = np.where(mask)
            
            # Convert to list of position dictionaries (limit for very large datasets)
            positions = [{"x": int(x), "y": int(y)} for x, y in zip(x_indices, y_indices)]
            
            # Store color info and positions
            positioned_data[unique_id] = {
                "hex": f"#{palette_color[0]:02x}{palette_color[1]:02x}{palette_color[2]:02x}{palette_color[3]:02x}",
                "positions": positions
            }
        
        return positioned_data
    
    def start_chunked_processing(self):
        """Start chunked processing for large images"""
        if not self.original_image or not self.palettes or self.current_palette_index >= len(self.palettes):
            return
        
        # Stop any current chunked processing
        self.pmap_chunk_timer.stop()
        
        # Initialize processing data
        original_array = np.array(self.original_image)
        current_palette = self.palettes[self.current_palette_index]
        
        self.pmap_processing_data = {
            'original_array': original_array,
            'palette': current_palette,
            'positioned_data': {},
            'total_colors': len(current_palette),
            'processed_colors': 0
        }
        
        self.pmap_current_chunk = 0
        
        # Start processing chunks
        self.pmap_chunk_timer.start(10)  # Process every 10ms
    
    def process_pmap_chunk(self):
        """Process one chunk of PMAP data"""
        if not self.pmap_processing_data:
            return
        
        try:
            data = self.pmap_processing_data
            palette = data['palette']
            
            # Process one color at a time
            if self.pmap_current_chunk < len(palette):
                palette_color = palette[self.pmap_current_chunk]
                unique_id = str(self.pmap_current_chunk + 1)
                
                # Convert palette color to numpy array for comparison
                target_color = np.array(palette_color, dtype=np.uint8)
                
                # Search through all pixels (optimized with numpy)
                mask = np.all(data['original_array'] == target_color, axis=2)
                y_indices, x_indices = np.where(mask)
                
                # Convert to list of position dictionaries
                positions = [{"x": int(x), "y": int(y)} for x, y in zip(x_indices, y_indices)]
                
                # Store color info and positions
                data['positioned_data'][unique_id] = {
                    "hex": f"#{palette_color[0]:02x}{palette_color[1]:02x}{palette_color[2]:02x}{palette_color[3]:02x}",
                    "positions": positions
                }
                
                self.pmap_current_chunk += 1
                
                # Update progress in loading message
                progress = int((self.pmap_current_chunk / len(palette)) * 100)
                
                if self.pmap_preview_visible:
                    self.pmap_table.setRowCount(1)
                    self.pmap_table.setColumnCount(1)
                    self.pmap_table.setHorizontalHeaderLabels(['Status'])
                    loading_item = QTableWidgetItem(f"Processing color {self.pmap_current_chunk}/{len(palette)} ({progress}%)")
                    loading_item.setTextAlignment(Qt.AlignCenter)
                    self.pmap_table.setItem(0, 0, loading_item)
                
                if self.pmap_raw_visible:
                    self.pmap_text.setText(f"Processing color {self.pmap_current_chunk}/{len(palette)} ({progress}%)")
                
                # Allow UI to update
                QApplication.processEvents()
                
            else:
                # Processing complete
                self.pmap_chunk_timer.stop()
                
                # Cache and display results
                pmap_data = data['positioned_data']
                self.pmap_data_cache = pmap_data
                self.pmap_cache_key = self.get_pmap_cache_key()
                
                # Update UI components
                if self.pmap_preview_visible:
                    # Restore proper table structure
                    self.pmap_table.setColumnCount(3)
                    self.pmap_table.setHorizontalHeaderLabels(['ID', 'HEX', 'COUNT'])
                    self.populate_pmap_list(pmap_data)
                
                if self.pmap_raw_visible:
                    # Process JSON generation in chunks for large datasets
                    self.generate_json_chunked(pmap_data)
                
                # Clean up
                self.pmap_processing_data = None
                
        except Exception as e:
            print(f"Error in chunked PMAP processing: {e}")
            self.pmap_chunk_timer.stop()
            self.pmap_processing_data = None
    
    def generate_json_chunked(self, pmap_data):
        """Generate JSON in chunks to prevent UI lag"""
        if not pmap_data:
            self.pmap_text.setText("{}")
            return
        
        # Stop any current JSON processing
        self.json_chunk_timer.stop()
        
        # For small datasets, use direct generation
        total_positions = sum(len(color_data.get('positions', [])) for color_data in pmap_data.values())
        if total_positions < 1000:  # Small dataset
            try:
                json_text = json.dumps(pmap_data, indent=2, ensure_ascii=False)
                self.pmap_text.setText(json_text)
            except Exception as e:
                self.pmap_text.setText(f"Error generating JSON: {e}")
            return
        
        # Large dataset - use chunked processing
        self.pmap_text.setText("Generating JSON...")
        QApplication.processEvents()
        
        # Prepare chunked processing
        self.json_processing_data = {
            'data': pmap_data,
            'keys': list(pmap_data.keys()),
            'total_keys': len(pmap_data)
        }
        self.json_current_chunk = 0
        self.json_result_parts = ["{"]
        
        # Start processing
        self.json_chunk_timer.start(5)  # Process every 5ms for smoother JSON generation
    
    def process_json_chunk(self):
        """Process one chunk of JSON generation"""
        if not self.json_processing_data:
            return
        
        try:
            data = self.json_processing_data
            keys = data['keys']
            pmap_data = data['data']
            
            # Process one color entry at a time
            if self.json_current_chunk < len(keys):
                key = keys[self.json_current_chunk]
                color_data = pmap_data[key]
                
                # Generate JSON for this color entry
                indent = "  "
                entry_json = f'\n{indent}"{key}": {{\n'
                entry_json += f'{indent}{indent}"hex": "{color_data["hex"]}",\n'
                
                # Handle positions - truncate if too many for performance
                positions = color_data.get('positions', [])
                if len(positions) > 500:  # Limit positions for JSON display
                    positions_sample = positions[:500]
                    entry_json += f'{indent}{indent}"positions": [\n'
                    
                    # Add position entries
                    for i, pos in enumerate(positions_sample):
                        entry_json += f'{indent}{indent}{indent}{{"x": {pos["x"]}, "y": {pos["y"]}}}'
                        if i < len(positions_sample) - 1:
                            entry_json += ','
                        entry_json += '\n'
                    
                    entry_json += f'{indent}{indent}],\n'
                    entry_json += f'{indent}{indent}"note": "Showing first 500 of {len(positions)} positions"\n'
                else:
                    # Include all positions
                    entry_json += f'{indent}{indent}"positions": [\n'
                    
                    for i, pos in enumerate(positions):
                        entry_json += f'{indent}{indent}{indent}{{"x": {pos["x"]}, "y": {pos["y"]}}}'
                        if i < len(positions) - 1:
                            entry_json += ','
                        entry_json += '\n'
                    
                    entry_json += f'{indent}{indent}]\n'
                
                entry_json += f'{indent}}}'
                
                # Add comma if not the last entry
                if self.json_current_chunk < len(keys) - 1:
                    entry_json += ','
                
                self.json_result_parts.append(entry_json)
                self.json_current_chunk += 1
                
                # Update progress
                progress = int((self.json_current_chunk / len(keys)) * 100)
                self.pmap_text.setText(f"Generating JSON... {progress}% ({self.json_current_chunk}/{len(keys)} colors)")
                QApplication.processEvents()
                
            else:
                # Processing complete
                self.json_chunk_timer.stop()
                
                # Finalize JSON
                self.json_result_parts.append("\n}")
                json_text = "".join(self.json_result_parts)
                self.pmap_text.setText(json_text)
                
                # Clean up
                self.json_processing_data = None
                self.json_result_parts = []
                
        except Exception as e:
            print(f"Error in chunked JSON processing: {e}")
            self.json_chunk_timer.stop()
            self.json_processing_data = None
            self.pmap_text.setText(f"Error generating JSON: {e}")
    
    def trigger_pmap_refresh(self):
        """Trigger PMAP refresh only when needed"""
        # Clear cache to force regeneration
        self.pmap_data_cache = {}
        self.pmap_cache_key = None
        
        # Update views if visible
        if self.pmap_preview_visible or self.pmap_raw_visible:
            self.update_pmap_preview()
            self.update_pmap_raw()
    
    def close_pmap_preview(self):
        """Close the PMAP preview list"""
        self.pmap_preview_visible = False
        self.pmap_preview_action.setChecked(False)
        self.pmap_list_widget.hide()
        
        # Adjust splitter sizes after closing
        sizes = self.splitter.sizes()
        if len(sizes) > 2:
            # Redistribute space among remaining panels
            remaining_panels = [i for i, size in enumerate(sizes) if self.splitter.widget(i).isVisible()]
            if len(remaining_panels) == 2:
                total = sum(sizes)
                self.splitter.setSizes([int(total * 0.3), int(total * 0.7)])
    
    def close_pmap_raw(self):
        """Close the PMAP raw JSON view"""
        self.pmap_raw_visible = False
        self.pmap_raw_action.setChecked(False)
        self.pmap_raw_widget.hide()
        
        # Adjust splitter sizes after closing
        sizes = self.splitter.sizes()
        if len(sizes) > 2:
            # Redistribute space among remaining panels
            remaining_panels = [i for i, size in enumerate(sizes) if self.splitter.widget(i).isVisible()]
            if len(remaining_panels) == 2:
                total = sum(sizes)
                self.splitter.setSizes([int(total * 0.3), int(total * 0.7)])


def main():
    app = QApplication(sys.argv)
    
    # Enable Ctrl+C to close the application
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # Apply dark theme
    app.setStyle('Fusion')
    dark_palette = app.palette()
    from PyQt5.QtGui import QPalette
    
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    
    app.setPalette(dark_palette)
    
    # Additional stylesheet for better contrast
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a2a2a; 
            border: 1px solid white; 
        }
        QScrollBar:vertical {
            background: #353535;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #666666;
        }
        QScrollBar:horizontal {
            background: #353535;
            height: 12px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #555555;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #666666;
        }
        QMenuBar {
            background-color: #353535;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #2a82da;
        }
        QMenu {
            background-color: #353535;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QMenu::item:selected {
            background-color: #2a82da;
        }
    """)
    
    editor = PaletteEditor()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
