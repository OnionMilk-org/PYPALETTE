"""
Color Utilities for PyPalette
Helper functions for color operations and conversions
"""

from PyQt5.QtGui import QColor
import numpy as np


def rgba_to_qcolor(rgba):
    """Convert RGBA tuple to QColor"""
    if len(rgba) == 3:
        return QColor(rgba[0], rgba[1], rgba[2])
    else:
        return QColor(rgba[0], rgba[1], rgba[2], rgba[3])


def qcolor_to_rgba(qcolor):
    """Convert QColor to RGBA tuple"""
    return (qcolor.red(), qcolor.green(), qcolor.blue(), qcolor.alpha())


def color_distance(color1, color2):
    """Calculate Euclidean distance between two RGBA colors"""
    r1, g1, b1, a1 = color1
    r2, g2, b2, a2 = color2
    
    return np.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2 + (a1 - a2)**2)


def find_closest_color(target_color, color_palette):
    """Find the closest color in a palette to the target color"""
    if not color_palette:
        return None, -1
    
    min_distance = float('inf')
    closest_color = None
    closest_index = -1
    
    for i, palette_color in enumerate(color_palette):
        distance = color_distance(target_color, palette_color)
        if distance < min_distance:
            min_distance = distance
            closest_color = palette_color
            closest_index = i
    
    return closest_color, closest_index


def parse_color_from_clipboard(clipboard_text):
    """Parse color from clipboard text in various formats"""
    text = clipboard_text.strip().lower()
    
    try:
        # Try hex format (#RRGGBB, #RRGGBBAA, RRGGBB, or RRGGBBAA)
        hex_color = text[1:] if text.startswith('#') else text
        
        # Check if it's a valid hex string (only hex characters)
        if all(c in '0123456789abcdef' for c in hex_color):
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return (r, g, b, 255)
            elif len(hex_color) == 8:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                a = int(hex_color[6:8], 16)
                return (r, g, b, a)
        
        # Try RGB/RGBA format
        if 'rgb' in text:
            # Remove 'rgb(' or 'rgba(' and ')'
            text = text.replace('rgba(', '').replace('rgb(', '').replace(')', '')
            values = [int(x.strip()) for x in text.split(',')]
            
            if len(values) == 3:
                return (values[0], values[1], values[2], 255)
            elif len(values) == 4:
                return (values[0], values[1], values[2], values[3])
        
        # Try comma-separated values
        values = [int(x.strip()) for x in text.split(',')]
        if len(values) == 3:
            return (values[0], values[1], values[2], 255)
        elif len(values) == 4:
            return (values[0], values[1], values[2], values[3])
    
    except (ValueError, IndexError):
        pass
    
    return None


def format_color_as_hex(rgba_color):
    """Format RGBA color as hex string"""
    r, g, b, a = rgba_color
    if a == 255:
        return f"#{r:02x}{g:02x}{b:02x}"
    else:
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"


def format_color_as_rgba(rgba_color):
    """Format RGBA color as string"""
    r, g, b, a = rgba_color
    if a == 255:
        return f"rgb({r}, {g}, {b})"
    else:
        return f"rgba({r}, {g}, {b}, {a})"


def is_color_similar(color1, color2, threshold=5):
    """Check if two colors are similar within a threshold"""
    return color_distance(color1, color2) <= threshold


def generate_color_id(index):
    """Generate a color ID starting from 1"""
    return index + 1