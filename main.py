#!/usr/bin/env python3
"""
PyPalette - Dynamic Palette Editor
Main entry point for the modular palette editor application
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Import the main editor class (will be created)
from ui.palette_editor_ui import PaletteEditor


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName('PyPalette')
    app.setApplicationVersion('1.0')
    
    # Set application style
    app.setStyle('Fusion')
    
    # Apply dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QPushButton {
            background-color: #404040;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #353535;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #353535;
        }
        QTabBar::tab {
            background-color: #404040;
            color: #ffffff;
            padding: 8px 16px;
            margin: 1px;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        QTabBar::tab:selected {
            background-color: #2a82da;
        }
        QTabBar::tab:hover {
            background-color: #505050;
        }
        QScrollArea {
            border: 1px solid #555555;
            background-color: #353535;
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
        QTableWidget {
            background-color: #353535;
            color: #ffffff;
            gridline-color: #555555;
        }
        QHeaderView::section {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QTextEdit {
            background-color: #353535;
            color: #ffffff;
            border: 1px solid #555555;
        }
    """)
    
    # Create and show the main editor
    editor = PaletteEditor()
    editor.show()
    
    # Start the application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()