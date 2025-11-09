"""
ZoomableLabel - Custom QLabel with zoom and pan functionality
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt


class ZoomableLabel(QLabel):
    """Custom QLabel that supports zoom with mouse wheel and middle mouse pan"""
    
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
        """Handle mouse leave to clear status bar and reset dragging"""
        if self.editor:
            # Clear status bar
            if hasattr(self.editor, 'status_bar'):
                self.editor.status_bar.showMessage('Ready')
        
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