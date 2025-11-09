"""
Palette Editor UI - Main application window and interface
"""

import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QColorDialog, 
                             QScrollArea, QFileDialog, QMessageBox, QSplitter,
                             QTabWidget, QListWidget, QListWidgetItem, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QApplication, QProgressBar)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPalette
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import numpy as np
import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo

# Import our modular components
from .zoomable_label import ZoomableLabel
from core.image_processor import ImageProcessor
from utils.settings import SettingsManager
from utils.color_utils import *


class PaletteEditor(QMainWindow):
    """Main palette editor application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.image_processor = ImageProcessor()
        self.settings_manager = SettingsManager()
        
        # UI state
        self.palettes = []  # List of palettes, each palette is a list of colors
        self.current_palette_index = 0
        self.palette_buttons = []
        self.palette_grids = []
        self.original_palette = []  # Original extracted colors for hover preview
        
        # History for undo/redo
        self.undo_history = []
        self.redo_history = []
        self.max_undo_history = 50
        
        # PMAP preview widgets
        self.pmap_list_widget = None
        self.pmap_table = None
        
        # Load settings
        self.settings_manager.load_settings()
        
        # Initialize UI
        self.initUI()
    
    @property
    def image(self):
        """Get current image from processor"""
        return self.image_processor.image
    
    @property
    def original_image(self):
        """Get original image from processor"""
        return self.image_processor.original_image
    
    @property
    def recent_files(self):
        """Get recent files from settings"""
        return self.settings_manager.get_recent_files()
    
    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle('PyPalette - Dynamic Palette Editor')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        central_widget_layout = QVBoxLayout(central_widget)
        central_widget_layout.addWidget(main_splitter)
        
        # Create left panel (color editor)
        self.color_editor_widget = self.create_color_editor()
        main_splitter.addWidget(self.color_editor_widget)
        
        # Create right panel (image preview)
        self.image_preview_widget = self.create_image_preview()
        main_splitter.addWidget(self.image_preview_widget)
        
        # Create PMAP preview widgets (initially hidden)
        self.create_pmap_widgets(main_splitter)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 800])
        
        # Create status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Basic file operations
        open_action = file_menu.addAction('&Open')
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_image)
        
        save_action = file_menu.addAction('&Save')
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_image)
        
        file_menu.addSeparator()
        
        # Palette operations
        export_palette_action = file_menu.addAction('Export &Palette PNG')
        export_palette_action.setShortcut('Ctrl+Shift+P')
        export_palette_action.triggered.connect(self.export_palette)
        
        import_palette_action = file_menu.addAction('&Import Palette PNG')
        import_palette_action.setShortcut('Ctrl+Shift+I')
        import_palette_action.triggered.connect(self.import_palette)
        
        file_menu.addSeparator()
        
        # PMAP operations
        export_pmap_action = file_menu.addAction('Export Palette &Map')
        export_pmap_action.setShortcut('Ctrl+E')
        export_pmap_action.triggered.connect(self.export_positioned)
        
        import_pmap_action = file_menu.addAction('Import Palette Ma&p')
        import_pmap_action.setShortcut('Ctrl+M')
        import_pmap_action.triggered.connect(self.import_palette_map)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('E&xit')
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu('&Edit')
        
        undo_action = edit_menu.addAction('&Undo')
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.undo_color_change)
        
        redo_action = edit_menu.addAction('&Redo')
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.redo_color_change)
        
        # View menu
        view_menu = menubar.addMenu('&View')
        
        zoom_in_action = view_menu.addAction('Zoom &In')
        zoom_in_action.setShortcut('Ctrl++')
        zoom_in_action.triggered.connect(self.zoom_in)
        
        zoom_out_action = view_menu.addAction('Zoom &Out')
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(self.zoom_out)
        
        zoom_reset_action = view_menu.addAction('&Reset Zoom')
        zoom_reset_action.setShortcut('Ctrl+0')
        zoom_reset_action.triggered.connect(self.zoom_reset)
        
        view_menu.addSeparator()
        
        fit_action = view_menu.addAction('&Fit to Window')
        fit_action.setShortcut('Ctrl+F')
        fit_action.triggered.connect(self.fit_to_window)
        
        view_menu.addSeparator()
        
        self.pmap_preview_action = view_menu.addAction('PMAP &Preview')
        self.pmap_preview_action.setShortcut('F1')
        self.pmap_preview_action.setCheckable(True)
        self.pmap_preview_action.triggered.connect(self.toggle_pmap_preview)
        
        # Recent files menu
        self.recent_menu = menubar.addMenu('&Recent')
        self.update_recent_menu()
        
        # About menu
        about_menu = menubar.addMenu('&About')
        
        author_action = about_menu.addAction('&Author Website')
        author_action.triggered.connect(self.open_author_website)
        
        controls_action = about_menu.addAction('&Controls')
        controls_action.setShortcut('F1')
        controls_action.triggered.connect(self.show_controls_window)
        
        about_menu.addSeparator()
        
        version_action = about_menu.addAction('&Version')
        version_action.triggered.connect(self.show_version_info)
    
    def create_color_editor(self):
        """Create the color editor panel"""
        editor_widget = QWidget()
        editor_widget.setFixedWidth(240)  # Fixed width for 3 columns (70px * 3 + 5px spacing * 2 + margins)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(5, 5, 5, 5)  # Minimal margins
        editor_layout.setSpacing(5)  # Minimal spacing
        
        # Title and controls
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel('Palette Colors')
        title.setStyleSheet('font-size: 16px; font-weight: bold; padding: 5px;')
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
        self.palette_tabs.setToolTip("Use keys 1-9 to switch between palette tabs")
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
        editor_widget.setLayout(editor_layout)
        
        # Store reference for width calculations
        self.color_editor = editor_widget
        
        return editor_widget
    
    def create_image_preview(self):
        """Create the image preview panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Image Preview")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # Scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        # Zoomable image label
        self.image_label = ZoomableLabel()
        self.image_label.editor = self  # Set reference for callbacks
        self.image_label.scroll_area = self.scroll_area
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        return widget
    
    def create_pmap_widgets(self, parent_splitter):
        """Create PMAP preview widgets (initially hidden)"""
        from PyQt5.QtWidgets import QTableWidget, QHeaderView
        
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
        self.pmap_table.setAlternatingRowColors(False)
        self.pmap_table.verticalHeader().setVisible(False)
        self.pmap_table.setMouseTracking(True)
        
        # Install event filter to detect mouse leave
        self.pmap_table.viewport().installEventFilter(self)
        
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
        
        # Add to splitter
        parent_splitter.addWidget(self.pmap_list_widget)
    
    def toggle_pmap_preview(self, checked):
        """Toggle PMAP preview visibility"""
        if checked:
            self.show_pmap_preview()
        else:
            self.close_pmap_preview()
    
    def show_pmap_preview(self):
        """Show PMAP preview with current palette data"""
        if not self.palettes or not self.image:
            QMessageBox.warning(self, 'Warning', 'No palette or image loaded')
            self.pmap_preview_action.setChecked(False)
            return
        
        # Get current palette
        current_palette = self.palettes[self.current_palette_index]
        
        # Count pixels for each color
        from collections import Counter
        import numpy as np
        
        image_array = np.array(self.image)
        pixels = image_array.reshape(-1, 4)
        
        # Count occurrences
        color_counts = Counter()
        for pixel in pixels:
            color_tuple = tuple(pixel)
            color_counts[color_tuple] += 1
        
        # Clear and populate table
        self.pmap_table.setRowCount(0)
        self.pmap_table.setRowCount(len(current_palette))
        
        for idx, color in enumerate(current_palette):
            color_tuple = tuple(color)
            count = color_counts.get(color_tuple, 0)
            
            # ID column
            id_item = QTableWidgetItem(str(idx + 1))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.pmap_table.setItem(idx, 0, id_item)
            
            # HEX column
            hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            hex_item = QTableWidgetItem(hex_color.upper())
            hex_item.setTextAlignment(Qt.AlignCenter)
            self.pmap_table.setItem(idx, 1, hex_item)
            
            # COUNT column
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.pmap_table.setItem(idx, 2, count_item)
        
        # Connect hover events (disconnect first to avoid duplicates)
        try:
            self.pmap_table.cellEntered.disconnect()
        except:
            pass
        self.pmap_table.cellEntered.connect(self.on_pmap_cell_hover)
        
        self.pmap_list_widget.show()
    
    def close_pmap_preview(self):
        """Close PMAP preview"""
        self.pmap_list_widget.hide()
        self.pmap_preview_action.setChecked(False)
    
    def on_pmap_cell_hover(self, row, column):
        """Handle hover over PMAP table row - show color preview"""
        if row >= 0 and row < len(self.palettes[self.current_palette_index]):
            # Show color preview for this palette index
            self.show_color_preview(row)
    
    def eventFilter(self, obj, event):
        """Event filter to detect mouse leave from PMAP table"""
        from PyQt5.QtCore import QEvent
        if obj == self.pmap_table.viewport() and event.type() == QEvent.Leave:
            # Restore normal image when mouse leaves table
            self.update_preview()
        return super().eventFilter(obj, event)
    
    # Placeholder methods - these will be implemented with full functionality
    def open_image(self):
        """Open an image file"""
        # Get the last used directory for opening images
        last_dir = self.settings_manager.get_last_directory('open_image')
        
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open Image', last_dir, 
            'Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)'
        )
        
        if filename:
            if self.image_processor.load_image(filename):
                # Check for embedded PMAP in PNG files
                if filename.lower().endswith('.png'):
                    try:
                        img = Image.open(filename)
                        if 'PMAP' in img.text:
                            # Ask user if they want to load the embedded PMAP
                            reply = QMessageBox.question(
                                self, 'Embedded PMAP Found',
                                'This PNG file contains an embedded palette map (PMAP).\n\n'
                                'Do you want to load it?',
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes
                            )
                            
                            if reply == QMessageBox.Yes:
                                import os
                                parent_dir = os.path.dirname(os.path.dirname(__file__))
                                pmap_module_path = os.path.join(parent_dir, 'io', 'pmap_format.py')
                                spec = __import__('importlib.util').util.spec_from_file_location("pmap_format", pmap_module_path)
                                pmap_module = __import__('importlib.util').util.module_from_spec(spec)
                                spec.loader.exec_module(pmap_module)
                                get_palette_from_pmap = pmap_module.get_palette_from_pmap
                                
                                # Decode PMAP using new format
                                pmap_string = img.text['PMAP']
                                palette = get_palette_from_pmap(pmap_string)
                                
                                # Restore palette
                                self.palettes = [palette]
                                self.current_palette_index = 0
                                self.original_palette = palette.copy()
                                
                                self.update_color_editor()
                                self.update_preview()
                                self.update_pmap_preview()
                                self.fit_to_window()
                                self.statusBar().showMessage(f'Loaded embedded PMAP with {len(palette)} colors', 3000)
                                self.settings_manager.add_recent_file(filename)
                                self.update_recent_menu()
                                return
                    except Exception as e:
                        # If PMAP loading fails, fall through to normal extraction
                        print(f"Failed to load embedded PMAP: {e}")
                
                # Normal extraction if no PMAP or user declined
                self.extract_palette()
                self.update_preview()
                self.update_color_editor()
                self.fit_to_window()
                self.settings_manager.add_recent_file(filename)
                self.update_recent_menu()
            else:
                QMessageBox.critical(self, 'Error', 'Failed to open image')
    
    def save_image(self):
        """Save the current image with embedded PMAP for PNG files"""
        if not self.image:
            QMessageBox.warning(self, 'Warning', 'No image to save')
            return
        
        # Get the last used directory for saving images
        last_dir = self.settings_manager.get_last_directory('save_image')
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Save Image', last_dir, 
            'PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)'
        )
        
        if filename:
            # For PNG files, save with embedded PMAP if palette exists
            if filename.lower().endswith('.png') and self.palettes and self.palettes[self.current_palette_index]:
                try:
                    import sys
                    import os
                    parent_dir = os.path.dirname(os.path.dirname(__file__))
                    pmap_module_path = os.path.join(parent_dir, 'io', 'pmap_format.py')
                    spec = __import__('importlib.util').util.spec_from_file_location("pmap_format", pmap_module_path)
                    pmap_module = __import__('importlib.util').util.module_from_spec(spec)
                    spec.loader.exec_module(pmap_module)
                    encode_pmap = pmap_module.encode_pmap
                    import tempfile
                    import shutil
                    
                    # Encode PMAP using new format
                    current_palette = self.palettes[self.current_palette_index]
                    pmap_string = encode_pmap(self.image, current_palette)
                    
                    # Save image first to temporary file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_filename = temp_file.name
                        self.image.save(temp_filename, "PNG")
                    
                    # Reload and add PMAP at the end
                    from PIL import Image
                    img_with_pmap = Image.open(temp_filename)
                    pnginfo = PngInfo()
                    pnginfo.add_text("PMAP", pmap_string)
                    img_with_pmap.save(filename, "PNG", pnginfo=pnginfo)
                    
                    # Clean up temp file
                    import os
                    os.unlink(temp_filename)
                    
                    self.settings_manager.save_last_directory('save_image', filename)
                    self.statusBar().showMessage(f'Image saved with embedded PMAP', 3000)
                    
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to save image: {str(e)}')
            else:
                # For non-PNG files or when no palette, use regular save
                if self.image_processor.save_image(filename):
                    # Remember the directory for future saves
                    self.settings_manager.save_last_directory('save_image', filename)
                else:
                    QMessageBox.critical(self, 'Error', 'Failed to save image')
    
    def extract_palette(self):
        """Extract palette from the current image"""
        if not self.image:
            return
        
        palette = self.image_processor.extract_palette()
        if palette:
            self.palettes = [palette]
            self.current_palette_index = 0
            self.original_palette = palette.copy()  # Store original palette for hover preview
    
    def update_preview(self):
        """Update the image preview"""
        pixmap = self.image_processor.get_qpixmap()
        if pixmap:
            self.image_label.setCurrentPixmap(pixmap)
    
    def update_color_editor(self):
        """Update the color editor display"""
        if not self.palettes:
            return
        
        # Clear existing tabs and button references
        self.palette_tabs.clear()
        self.palette_buttons.clear()
        self.palette_grids.clear()
        
        # Create a tab for each palette
        for palette_idx, palette in enumerate(self.palettes):
            tab_widget = self.create_palette_tab(palette_idx, palette)
            tab_name = str(palette_idx + 1)  # Just the tab number
            self.palette_tabs.addTab(tab_widget, tab_name)
        
        # Set current tab
        if self.current_palette_index < self.palette_tabs.count():
            self.palette_tabs.setCurrentIndex(self.current_palette_index)
    
    def create_palette_tab(self, palette_idx, palette):
        """Create a tab widget for a single palette"""
        tab_widget = QWidget()
        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        tab_layout.setSpacing(0)  # Remove spacing
        
        # Scroll area for palette colors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        palette_container = QWidget()
        palette_layout = QVBoxLayout()
        palette_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        palette_layout.setSpacing(0)  # Remove spacing
        
        # Create grid layout for color buttons
        from PyQt5.QtWidgets import QGridLayout
        grid_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        grid_layout.setSpacing(5)
        grid_widget.setLayout(grid_layout)
        
        # Fixed 3 columns layout
        columns = 3
        
        # Add color buttons in grid
        buttons_for_this_palette = []
        for idx, color in enumerate(palette):
            color_btn = self.create_color_button(palette_idx, idx, color)
            row = idx // columns
            col = idx % columns
            grid_layout.addWidget(color_btn, row, col)
            buttons_for_this_palette.append(color_btn)
        
        # Store buttons for this palette
        while len(self.palette_buttons) <= palette_idx:
            self.palette_buttons.append([])
        self.palette_buttons[palette_idx] = buttons_for_this_palette
        
        # Store grid layout reference
        while len(self.palette_grids) <= palette_idx:
            self.palette_grids.append((None, -1))
        self.palette_grids[palette_idx] = (grid_layout, palette_idx)
        
        palette_layout.addWidget(grid_widget)
        palette_layout.addStretch()
        palette_container.setLayout(palette_layout)
        scroll.setWidget(palette_container)
        
        tab_layout.addWidget(scroll)
        tab_widget.setLayout(tab_layout)
        
        return tab_widget
    
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
        
        btn.clicked.connect(lambda checked, p_idx=palette_idx, c_idx=color_idx: self.edit_color(p_idx, c_idx))
        
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
    
    def create_new_palette(self):
        """Create new palette tab by duplicating current one"""
        if not self.palettes:
            return
        
        # Duplicate current palette
        current_palette = self.palettes[self.current_palette_index]
        new_palette = [color.copy() for color in current_palette]
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
    
    def show_color_preview(self, idx):
        """Show only the hovered color in the image preview"""
        if self.original_image is None or not self.original_palette:
            return
        
        # Get the original color to isolate
        if idx >= len(self.original_palette):
            return
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
        from PIL import Image
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
    
    def paste_color_from_clipboard(self, palette_idx, color_idx):
        """Paste color from clipboard (right-click functionality)"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            
            # Try to parse color from clipboard
            from utils.color_utils import parse_color_from_clipboard
            parsed_color = parse_color_from_clipboard(text)
            
            if parsed_color:
                # Save to undo history
                self.save_color_to_history(palette_idx, color_idx)
                
                # Update palette
                self.palettes[palette_idx][color_idx] = list(parsed_color)
                
                # Update UI
                self.update_color_editor()
                self.apply_palette_to_image()
                self.update_preview()
            else:
                QMessageBox.warning(self, 'Invalid Color', f'Could not parse color from: {text}')
                
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to paste color: {str(e)}')
    
    def edit_color(self, palette_idx, color_idx):
        """Edit a color in the palette"""
        if palette_idx >= len(self.palettes) or color_idx >= len(self.palettes[palette_idx]):
            return
        
        current_color = self.palettes[palette_idx][color_idx]
        
        # Create color dialog
        color_dialog = QColorDialog()
        initial_color = QColor(current_color[0], current_color[1], current_color[2])
        if len(current_color) > 3:
            initial_color.setAlpha(current_color[3])
        
        color_dialog.setCurrentColor(initial_color)
        
        if color_dialog.exec_() == QColorDialog.Accepted:
            new_color = color_dialog.currentColor()
            
            # Save to undo history
            self.save_color_to_history(palette_idx, color_idx)
            
            # Update palette
            self.palettes[palette_idx][color_idx] = [
                new_color.red(), 
                new_color.green(), 
                new_color.blue(), 
                new_color.alpha()
            ]
            
            # Update UI
            self.update_color_editor()
            self.apply_palette_to_image()
            self.update_preview()
    
    def delete_color(self, palette_idx, color_idx):
        """Delete a color from the palette"""
        if palette_idx >= len(self.palettes) or color_idx >= len(self.palettes[palette_idx]):
            return
        
        # Confirm deletion
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                   f'Delete color #{color_idx + 1}?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Remove color from palette
            del self.palettes[palette_idx][color_idx]
            
            # Update UI
            self.update_color_editor()
            self.apply_palette_to_image()
            self.update_preview()
    
    def apply_palette_to_image(self):
        """Apply the current palette to the image"""
        if self.palettes and self.current_palette_index < len(self.palettes):
            current_palette = self.palettes[self.current_palette_index]
            # Pass both original and new palette for proper color mapping
            self.image_processor.apply_palette_to_image(current_palette, self.original_palette)
    
    def update_recent_menu(self):
        """Update the recent files menu"""
        self.recent_menu.clear()
        
        for filepath in self.recent_files:
            action = self.recent_menu.addAction(filepath)
            action.triggered.connect(lambda checked, path=filepath: self.open_recent_file(path))
    
    def open_recent_file(self, filepath):
        """Open a recent file"""
        import os
        
        # Check if file exists
        if not os.path.exists(filepath):
            QMessageBox.critical(
                self, 'Error', 
                f'File not found:\n{filepath}\n\nThis file will be removed from the recent files list.'
            )
            # Remove from recent files list
            self.settings_manager.remove_recent_file(filepath)
            self.update_recent_menu()
            return
        
        if self.image_processor.load_image(filepath):
            # Check for embedded PMAP in PNG files
            if filepath.lower().endswith('.png'):
                try:
                    img = Image.open(filepath)
                    if 'PMAP' in img.text:
                        # Ask user if they want to load the embedded PMAP
                        reply = QMessageBox.question(
                            self, 'Embedded PMAP Found',
                            'This PNG file contains an embedded palette map (PMAP).\n\n'
                            'Do you want to load it?',
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )
                        
                        if reply == QMessageBox.Yes:
                            import os
                            parent_dir = os.path.dirname(os.path.dirname(__file__))
                            pmap_module_path = os.path.join(parent_dir, 'io', 'pmap_format.py')
                            spec = __import__('importlib.util').util.spec_from_file_location("pmap_format", pmap_module_path)
                            pmap_module = __import__('importlib.util').util.module_from_spec(spec)
                            spec.loader.exec_module(pmap_module)
                            get_palette_from_pmap = pmap_module.get_palette_from_pmap
                            
                            # Decode PMAP using new format
                            pmap_string = img.text['PMAP']
                            palette = get_palette_from_pmap(pmap_string)
                            
                            # Restore palette
                            self.palettes = [palette]
                            self.current_palette_index = 0
                            self.original_palette = palette.copy()
                            
                            self.update_color_editor()
                            self.update_preview()
                            self.update_pmap_preview()
                            self.fit_to_window()
                            self.statusBar().showMessage(f'Loaded embedded PMAP with {len(palette)} colors', 3000)
                            self.settings_manager.save_last_directory('open_image', filepath)
                            return
                except Exception as e:
                    # If PMAP loading fails, fall through to normal extraction
                    print(f"Failed to load embedded PMAP: {e}")
            
            # Normal extraction if no PMAP or user declined
            self.extract_palette()
            self.update_preview()
            self.update_color_editor()
            self.fit_to_window()
            # Remember the directory when opening recent files
            self.settings_manager.save_last_directory('open_image', filepath)
        else:
            QMessageBox.critical(self, 'Error', f'Failed to open {filepath}')
    
    def export_palette(self):
        """Export current palette as PNG"""
        if not self.palettes or not self.palettes[self.current_palette_index]:
            QMessageBox.warning(self, 'Warning', 'No palette to export')
            return
        
        # Get the last used directory for exporting palettes
        last_dir = self.settings_manager.get_last_directory('export_palette')
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export Palette', last_dir, 
            'PNG Files (*.png);;All Files (*)'
        )
        
        if filename:
            try:
                # Create palette image - each color is a 1x1 pixel
                current_palette = self.palettes[self.current_palette_index]
                palette_width = len(current_palette)
                
                # Create a PIL image for the palette
                from PIL import Image
                palette_image = Image.new('RGBA', (palette_width, 1))
                
                for i, color in enumerate(current_palette):
                    palette_image.putpixel((i, 0), tuple(color))
                
                # Save the palette
                palette_image.save(filename)
                
                # Remember the directory
                self.settings_manager.save_last_directory('export_palette', filename)
                
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to export palette: {str(e)}')
    
    def import_palette(self):
        """Import palette from PNG"""
        # Get the last used directory for importing palettes
        last_dir = self.settings_manager.get_last_directory('import_palette')
        
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Import Palette', last_dir, 
            'PNG Files (*.png);;All Files (*)'
        )
        
        if filename:
            try:
                from PIL import Image
                
                # Load palette image
                palette_image = Image.open(filename)
                
                # Convert to RGBA
                if palette_image.mode != 'RGBA':
                    palette_image = palette_image.convert('RGBA')
                
                # Extract colors from first row
                imported_palette = []
                for x in range(palette_image.width):
                    color = palette_image.getpixel((x, 0))
                    imported_palette.append(list(color))
                
                # Add as new palette
                self.palettes.append(imported_palette)
                self.current_palette_index = len(self.palettes) - 1
                
                # Update UI
                self.update_color_editor()
                
                # Remember the directory
                self.settings_manager.save_last_directory('import_palette', filename)
                
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to import palette: {str(e)}')
    
    def export_positioned(self):
        """Export PMAP (Palette Map) with color IDs and positions"""
        if not self.image or not self.palettes:
            QMessageBox.warning(self, 'Warning', 'No image or palette to export')
            return
        
        # Get the last used directory for exporting PMAP
        last_dir = self.settings_manager.get_last_directory('export_pmap')
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export Palette Map', last_dir, 
            'Palette Map Files (*.pmap);;JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            try:
                import os
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                pmap_module_path = os.path.join(parent_dir, 'io', 'pmap_format.py')
                spec = __import__('importlib.util').util.spec_from_file_location("pmap_format", pmap_module_path)
                pmap_module = __import__('importlib.util').util.module_from_spec(spec)
                spec.loader.exec_module(pmap_module)
                encode_pmap = pmap_module.encode_pmap
                
                current_palette = self.palettes[self.current_palette_index]
                
                # Encode PMAP using new format
                pmap_string = encode_pmap(self.image, current_palette)
                
                # Save to file
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(pmap_string)
                
                # Remember the directory
                self.settings_manager.save_last_directory('export_pmap', filename)
                
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to export PMAP: {str(e)}')
    
    def import_palette_map(self):
        """Import PMAP (Palette Map) file"""
        # Get the last used directory for importing PMAP
        last_dir = self.settings_manager.get_last_directory('import_pmap')
        
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Import Palette Map', last_dir, 
            'Palette Map Files (*.pmap);;All Files (*)'
        )
        
        if filename:
            try:
                import os
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                pmap_module_path = os.path.join(parent_dir, 'io', 'pmap_format.py')
                spec = __import__('importlib.util').util.spec_from_file_location("pmap_format", pmap_module_path)
                pmap_module = __import__('importlib.util').util.module_from_spec(spec)
                spec.loader.exec_module(pmap_module)
                decode_pmap = pmap_module.decode_pmap
                from PIL import Image
                
                # Load PMAP data
                with open(filename, 'r', encoding='utf-8') as f:
                    pmap_string = f.read()
                
                # Decode PMAP using new format
                pmap_data = decode_pmap(pmap_string)
                imported_palette = pmap_data['palette']
                pixels_map = pmap_data['pixels']
                
                # Determine image dimensions from pixel coordinates
                max_x = 0
                max_y = 0
                for hex_color, pixels in pixels_map.items():
                    for x, y in pixels:
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
                
                width = max_x + 1
                height = max_y + 1
                
                # Create new image from PMAP data
                new_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                
                # Place pixels using the palette and pixel map
                for hex_color, pixels in pixels_map.items():
                    # Find matching color in palette
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    rgba = (r, g, b, 255)
                    
                    for x, y in pixels:
                        if 0 <= x < width and 0 <= y < height:
                            new_image.putpixel((x, y), rgba)
                
                # Set as current image and palette
                self.image_processor.image = new_image
                self.image_processor.original_image = new_image.copy()
                
                if imported_palette:
                    self.palettes = [imported_palette]
                    self.current_palette_index = 0
                    self.original_palette = imported_palette.copy()  # Store for hover preview
                
                # Update UI
                self.update_preview()
                self.update_color_editor()
                
                # Remember the directory
                self.settings_manager.save_last_directory('import_pmap', filename)
                
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to import PMAP: {str(e)}')
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        key = event.key()
        
        # Check for number keys 1-9 to switch palette tabs
        if Qt.Key_1 <= key <= Qt.Key_9:
            tab_index = key - Qt.Key_1  # Convert to 0-based index
            if tab_index < self.palette_tabs.count():
                self.palette_tabs.setCurrentIndex(tab_index)
                return
        
        # Call parent for other keys
        super().keyPressEvent(event)
    
    def recalculate_palette_layouts(self):
        """Recalculate the grid layout for all palette tabs"""
        if not hasattr(self, 'palette_tabs') or not hasattr(self, 'palettes'):
            return
        
        # Fixed 3 columns layout - no dynamic calculation needed
        new_columns = 3
        
        # Update all palette tab layouts
        for palette_idx in range(len(self.palettes)):
            if palette_idx < len(self.palette_grids):
                grid_layout, _ = self.palette_grids[palette_idx]
                if grid_layout and palette_idx < len(self.palette_buttons):
                    self.update_grid_layout(grid_layout, palette_idx, new_columns)
    
    def update_grid_layout(self, grid_layout, palette_idx, new_columns):
        """Update a specific grid layout with new column count"""
        if palette_idx >= len(self.palette_buttons):
            return
        
        buttons = self.palette_buttons[palette_idx]
        
        # Remove all widgets from grid
        while grid_layout.count():
            child = grid_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        # Re-add buttons with new column layout
        for idx, button in enumerate(buttons):
            row = idx // new_columns
            col = idx % new_columns
            grid_layout.addWidget(button, row, col)
    
    def on_preview_hover(self, pos):
        """Handle hover over preview to show color info in status bar"""
        pixel_color = self.get_pixel_color_at_pos(pos)
        if pixel_color is None:
            # Clear status bar
            self.status_bar.showMessage('Ready')
            return
        
        # Get image coordinates (accounting for zoom)
        if self.image_label and self.image_label.pixmap():
            # Convert widget position to image coordinates
            pixmap_size = self.image_label.pixmap().size()
            image_x = int(pos.x() / self.image_label.zoom_factor)
            image_y = int(pos.y() / self.image_label.zoom_factor)
            
            # Format color as hex
            r, g, b = pixel_color[:3]
            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            
            # Find palette index if it matches
            palette_info = ""
            if self.palettes and self.current_palette_index < len(self.palettes):
                current_palette = self.palettes[self.current_palette_index]
                for idx, palette_color in enumerate(current_palette):
                    if tuple(pixel_color) == tuple(palette_color):
                        palette_info = f" | Palette Color #{idx + 1}"
                        break
            
            # Update status bar with color info
            status_msg = f"Pos: ({image_x}, {image_y}) | RGB: ({r}, {g}, {b}) | Hex: {hex_color}{palette_info}"
            self.status_bar.showMessage(status_msg)
    
    def on_preview_click(self, pos):
        """Handle click on preview to select color from palette"""
        pixel_color = self.get_pixel_color_at_pos(pos)
        if pixel_color is None:
            return
        
        # Find which palette color this pixel belongs to
        if not self.palettes or self.current_palette_index >= len(self.palettes):
            return
        
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
        if not self.palettes or self.current_palette_index >= len(self.palettes):
            return
        
        current_palette = self.palettes[self.current_palette_index]
        for idx, palette_color in enumerate(current_palette):
            if tuple(pixel_color) == tuple(palette_color):
                # Paste color from clipboard
                self.paste_color_from_clipboard(self.current_palette_index, idx)
                return
    
    def clear_all_button_underlines(self):
        """Clear underlines from all palette buttons"""
        for palette_buttons in self.palette_buttons:
            for btn in palette_buttons:
                # Reset button style to remove underline
                current_style = btn.styleSheet()
                # Remove any text-decoration lines
                lines = current_style.split('\n')
                new_lines = []
                for line in lines:
                    if 'text-decoration' not in line.lower():
                        new_lines.append(line)
                btn.setStyleSheet('\n'.join(new_lines))
    
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
        return list(pixel) if len(pixel) == 4 else list(pixel) + [255]
    
    def underline_button(self, palette_idx, color_idx):
        """Underline a specific button's text"""
        # Clear all underlines first
        self.clear_all_button_underlines()
        
        # Add underline to the specified button
        if (palette_idx < len(self.palette_buttons) and 
            color_idx < len(self.palette_buttons[palette_idx])):
            
            btn = self.palette_buttons[palette_idx][color_idx]
            current_style = btn.styleSheet()
            
            # Add text-decoration underline
            if 'text-decoration' not in current_style.lower():
                # Insert before the last closing brace
                if current_style.strip().endswith('}'):
                    # Find the last QPushButton block
                    lines = current_style.split('\n')
                    new_lines = []
                    for i, line in enumerate(lines):
                        new_lines.append(line)
                        if line.strip() == 'QPushButton {' and i < len(lines) - 1:
                            # Look for the closing brace of this block
                            for j in range(i + 1, len(lines)):
                                if lines[j].strip() == '}':
                                    # Insert text-decoration before the closing brace
                                    lines.insert(j, '                text-decoration: underline;')
                                    break
                            break
                    btn.setStyleSheet('\n'.join(lines))
                else:
                    btn.setStyleSheet(current_style + '\nQPushButton { text-decoration: underline; }')
    
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
        
        # Update UI
        self.update_color_editor()
        self.apply_palette_to_image()
        self.update_preview()
    
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
        
        # Update UI
        self.update_color_editor()
        self.apply_palette_to_image()
        self.update_preview()
    
    def open_author_website(self):
        """Open author website in default browser"""
        import webbrowser
        webbrowser.open('https://onionmilk.org/')
    
    def show_controls_window(self):
        """Display a window with all controls, shortcuts and mouse operations"""
        from PyQt5.QtWidgets import QDialog, QScrollArea, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle('PyPalette Controls')
        dialog.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout()
        
        # Create scrollable text area
        scroll = QScrollArea()
        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setStyleSheet('''
            QTextEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                padding: 10px;
            }
        ''')
        
        controls_text = """
<h2 style="color: #4a9eff;">PyPalette Controls & Shortcuts</h2>

<h3 style="color: #66bb6a;">🎹 Keyboard Shortcuts</h3>
<table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
<tr><td><b>Ctrl+O</b></td><td>Open Image</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save Image</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>Undo Color Change</td></tr>
<tr><td><b>Ctrl+Y</b></td><td>Redo Color Change</td></tr>
<tr><td><b>Ctrl+Shift+P</b></td><td>Export Palette PNG</td></tr>
<tr><td><b>Ctrl+Shift+I</b></td><td>Import Palette PNG</td></tr>
<tr><td><b>Ctrl+E</b></td><td>Export Palette Map (PMAP)</td></tr>
<tr><td><b>Ctrl+M</b></td><td>Import Palette Map (PMAP)</td></tr>
<tr><td><b>1-9</b></td><td>Switch Between Palette Tabs</td></tr>
<tr><td><b>F1</b></td><td>Show This Controls Window</td></tr>
<tr><td><b>Alt+F4</b></td><td>Exit Application</td></tr>
</table>

<h3 style="color: #66bb6a;">🖱️ Mouse Operations</h3>

<h4 style="color: #ffa726;">Color Buttons:</h4>
<ul>
<li><b>Left Click:</b> Edit color with color picker dialog</li>
<li><b>Right Click:</b> Paste color from clipboard (supports hex, RGB, RGBA)</li>
</ul>

<h4 style="color: #ffa726;">Image Preview:</h4>
<ul>
<li><b>Mouse Wheel:</b> Zoom in/out (0.1x to 10x)</li>
<li><b>Middle Mouse + Drag:</b> Pan around image when zoomed</li>
<li><b>Hover:</b> Status bar shows color information and coordinates</li>
<li><b>Left Click:</b> Edit the color at clicked pixel</li>
<li><b>Right Click:</b> Paste clipboard color to clicked pixel's color</li>
</ul>

<h4 style="color: #ffa726;">Palette Tabs:</h4>
<ul>
<li><b>Left Click:</b> Switch to palette tab</li>
<li><b>Close Button (×):</b> Remove palette tab</li>
<li><b>+ New Palette:</b> Duplicate current palette</li>
</ul>

<h3 style="color: #66bb6a;">🎨 Color Operations</h3>
<ul>
<li><b>Palette Extraction:</b> Automatically extracts unique colors from loaded images</li>
<li><b>Real-time Preview:</b> Color changes instantly update the image</li>
<li><b>Multiple Palettes:</b> Create and switch between different color variations</li>
<li><b>Clipboard Support:</b> Paste colors in formats: #RRGGBB, #RRGGBBAA, rgb(r,g,b), rgba(r,g,b,a)</li>
</ul>

<h3 style="color: #66bb6a;">💾 File Operations</h3>
<ul>
<li><b>Smart Directory Memory:</b> Remembers last used folder for each operation type</li>
<li><b>Multiple Formats:</b> Supports PNG, JPG, JPEG, BMP, GIF</li>
<li><b>Palette Export/Import:</b> Save/load palettes as PNG files</li>
<li><b>PMAP Files:</b> Export/import complete color position maps as JSON</li>
<li><b>Recent Files:</b> Quick access to recently opened images</li>
</ul>

<h3 style="color: #66bb6a;">⚡ Advanced Features</h3>
<ul>
<li><b>Undo/Redo:</b> Full history tracking of color changes (up to 50 operations)</li>
<li><b>Progress Indicators:</b> Real-time feedback during PMAP processing</li>
<li><b>Status Bar:</b> Real-time color and position info when hovering over preview</li>
<li><b>Fixed 3-Column Layout:</b> Consistent palette button arrangement</li>
<li><b>Pixelated Zoom:</b> No antialiasing for precise pixel-level editing</li>
</ul>

<p style="color: #888; font-size: 10px; margin-top: 20px;">
PyPalette - Dynamic Palette Editor<br>
Sophisticated image palette manipulation with real-time preview
</p>
        """
        
        text_widget.setHtml(controls_text)
        
        # Make text widget expand to fill available space
        scroll.setWidget(text_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)  # stretch factor of 1 to take all available space
        
        # Close button
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn, 0)  # stretch factor of 0 to keep minimum size
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def show_version_info(self):
        """Display version information and package versions"""
        try:
            # Get package versions
            import PyQt5.Qt
            import PIL
            import numpy
            import json
            import sys
            
            # Get PyQt5 version properly
            pyqt5_version = PyQt5.Qt.PYQT_VERSION_STR
            pil_version = getattr(PIL, '__version__', 'Unknown')
            numpy_version = getattr(numpy, '__version__', 'Unknown')
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            
            # Get application version from QApplication
            from PyQt5.QtWidgets import QApplication
            app_version = QApplication.applicationVersion()
            
            version_text = f"""PyPalette - Dynamic Palette Editor
            
🎨 Application Version: {app_version}
🐍 Python Version: {python_version}

📦 Package Versions:
• PyQt5: {pyqt5_version}
• Pillow (PIL): {pil_version}  
• NumPy: {numpy_version}
• JSON: Built-in

🏗️ Architecture: Modular Design
✨ Features: Complete feature parity with backup
🚀 Status: Production Ready

Author: onionmilk.org
License: Open Source"""
            
            QMessageBox.information(self, 'PyPalette Version Info', version_text)
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to get version info: {str(e)}')
    
    def zoom_in(self):
        """Zoom in the image preview"""
        if self.image_label and self.image_label.current_pixmap:
            self.image_label.zoom_factor *= 1.2
            self.image_label.zoom_factor = min(self.image_label.zoom_factor, 10.0)
            self.image_label.setCurrentPixmap(self.image_label.current_pixmap)
    
    def zoom_out(self):
        """Zoom out the image preview"""
        if self.image_label and self.image_label.current_pixmap:
            self.image_label.zoom_factor *= 0.8
            self.image_label.zoom_factor = max(self.image_label.zoom_factor, 0.1)
            self.image_label.setCurrentPixmap(self.image_label.current_pixmap)
    
    def zoom_reset(self):
        """Reset zoom to 100%"""
        if self.image_label and self.image_label.current_pixmap:
            self.image_label.zoom_factor = 1.0
            self.image_label.setCurrentPixmap(self.image_label.current_pixmap)
    
    def fit_to_window(self):
        """Fit image to window size"""
        if self.image_label and self.image_label.current_pixmap and self.scroll_area:
            # Get available space
            viewport_size = self.scroll_area.viewport().size()
            pixmap_size = self.image_label.current_pixmap.size()
            
            # Calculate zoom to fit
            width_ratio = viewport_size.width() / pixmap_size.width()
            height_ratio = viewport_size.height() / pixmap_size.height()
            fit_zoom = min(width_ratio, height_ratio) * 0.95  # 95% to leave some margin
            
            # Apply zoom
            self.image_label.zoom_factor = max(0.1, min(fit_zoom, 10.0))
            self.image_label.setCurrentPixmap(self.image_label.current_pixmap)
