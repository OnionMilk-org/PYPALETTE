"""
Image Processor for PyPalette
Handles image loading, palette extraction, and color operations
"""

from PIL import Image
import numpy as np
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


class ImageProcessor:
    """Handles image processing operations for palette editing"""
    
    def __init__(self):
        self.image = None
        self.original_image = None
        self.image_array = None
        self.current_palette = []
    
    def load_image(self, filepath):
        """Load an image from file"""
        try:
            # Load image with PIL
            self.image = Image.open(filepath)
            
            # Convert to RGBA for consistency
            if self.image.mode != 'RGBA':
                self.image = self.image.convert('RGBA')
            
            # Store original unchanged image
            self.original_image = self.image.copy()
            
            return True
            
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
    
    def extract_palette(self):
        """Extract unique colors from the current image"""
        if not self.image:
            return []
        
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
        
        self.current_palette = unique_colors
        return unique_colors
    
    def apply_palette_to_image(self, palette, original_palette=None):
        """Apply a palette to the current image"""
        if not self.original_image or not palette:
            return
        
        try:
            # Convert original to numpy array
            original_array = np.array(self.original_image)
            new_array = original_array.copy()
            
            # Use provided original palette or fall back to stored one
            source_palette = original_palette if original_palette else self.current_palette
            
            # Get original palette if we don't have it
            if not source_palette:
                self.extract_palette()
                source_palette = self.current_palette
            
            # Create mapping from original colors to new colors
            color_map = {}
            for i, original_color in enumerate(source_palette):
                if i < len(palette):
                    color_map[tuple(original_color)] = tuple(palette[i])
            
            # Apply color mapping
            height, width, channels = original_array.shape
            for y in range(height):
                for x in range(width):
                    original_color = tuple(original_array[y, x])
                    if original_color in color_map:
                        new_array[y, x] = color_map[original_color]
            
            # Convert back to PIL Image
            self.image = Image.fromarray(new_array, 'RGBA')
            
        except Exception as e:
            print(f"Error applying palette: {e}")
    
    def get_qpixmap(self):
        """Convert current image to QPixmap for display"""
        if not self.image:
            return None
        
        try:
            # Convert PIL image to bytes
            image_bytes = self.image.tobytes('raw', 'RGBA')
            
            # Create QImage
            qimage = QImage(image_bytes, self.image.width, self.image.height, QImage.Format_RGBA8888)
            
            # Convert to QPixmap
            return QPixmap.fromImage(qimage)
            
        except Exception as e:
            print(f"Error converting to QPixmap: {e}")
            return None
    
    def get_pixel_color_at_pos(self, x, y, zoom_factor=1.0):
        """Get the color of a pixel at the given position"""
        if not self.image:
            return None
        
        try:
            # Adjust coordinates for zoom
            actual_x = int(x / zoom_factor)
            actual_y = int(y / zoom_factor)
            
            # Check bounds
            if (0 <= actual_x < self.image.width and 
                0 <= actual_y < self.image.height):
                return self.image.getpixel((actual_x, actual_y))
            
        except Exception as e:
            print(f"Error getting pixel color: {e}")
        
        return None
    
    def save_image(self, filepath):
        """Save the current image to file"""
        if not self.image:
            return False
        
        try:
            self.image.save(filepath)
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False
    
    def get_image_info(self):
        """Get information about the current image"""
        if not self.image:
            return None
        
        return {
            'width': self.image.width,
            'height': self.image.height,
            'mode': self.image.mode,
            'size_bytes': len(self.image.tobytes()),
            'palette_size': len(self.current_palette) if self.current_palette else 0
        }