"""
PMAP Format Module - Encode/Decode palette map data

PMAP Format Specification:
Line 1: {NUMBER_OF_COLORS}
Following lines: #{HEX} {NUMBER_OF_PIXELS} {X;Y}

Example:
3
#FF0000 5 0;0 1;0 2;0 0;1 1;1
#00FF00 3 2;1 0;2 1;2
#0000FF 2 2;2 0;3
"""


def encode_pmap(image, palette):
    """
    Encode palette map from image and palette
    
    Args:
        image: PIL Image object
        palette: List of RGBA tuples representing colors
    
    Returns:
        str: PMAP formatted string
    """
    # Build color-to-pixels mapping
    color_pixels = {}
    
    for y in range(image.height):
        for x in range(image.width):
            pixel_color = list(image.getpixel((x, y)))
            
            # Find matching palette color
            for i, palette_color in enumerate(palette):
                if pixel_color == list(palette_color):
                    # Convert to hex (RGB only, ignore alpha) with # prefix
                    hex_color = f"#{palette_color[0]:02X}{palette_color[1]:02X}{palette_color[2]:02X}"
                    
                    if hex_color not in color_pixels:
                        color_pixels[hex_color] = []
                    
                    color_pixels[hex_color].append((x, y))
                    break
    
    # Build PMAP string
    lines = []
    lines.append(str(len(color_pixels)))
    
    for hex_color, pixels in color_pixels.items():
        pixel_count = len(pixels)
        pixel_coords = " ".join([f"{x};{y}" for x, y in pixels])
        lines.append(f"{hex_color} {pixel_count} {pixel_coords}")
    
    return "\n".join(lines)


def decode_pmap(pmap_string):
    """
    Decode PMAP formatted string into palette data
    
    Args:
        pmap_string: PMAP formatted string
    
    Returns:
        dict: Dictionary with 'palette' (list of RGBA tuples) and 'pixels' (dict mapping hex to coordinates)
    """
    lines = pmap_string.strip().split('\n')
    
    if len(lines) < 1:
        raise ValueError("Invalid PMAP format: empty data")
    
    try:
        num_colors = int(lines[0])
    except ValueError:
        raise ValueError("Invalid PMAP format: first line must be number of colors")
    
    palette = []
    pixels_map = {}
    
    for i in range(1, num_colors + 1):
        if i >= len(lines):
            raise ValueError(f"Invalid PMAP format: expected {num_colors} color lines, got {i-1}")
        
        line = lines[i]
        parts = line.split(' ', 2)
        
        if len(parts) < 3:
            raise ValueError(f"Invalid PMAP format at line {i+1}: expected #HEX COUNT PIXELS")
        
        hex_color = parts[0]
        pixel_count = int(parts[1])
        pixel_coords_str = parts[2]
        
        # Parse hex color to RGBA (hex_color starts with #)
        if not hex_color.startswith('#') or len(hex_color) != 7:
            raise ValueError(f"Invalid hex color: {hex_color} (must be #RRGGBB)")
        
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        rgba = (r, g, b, 255)
        
        palette.append(rgba)
        
        # Parse pixel coordinates (space-separated X;Y pairs)
        pixels = []
        coord_parts = pixel_coords_str.split(' ')
        
        for coord in coord_parts:
            x, y = coord.split(';')
            pixels.append((int(x), int(y)))
        
        pixels_map[hex_color] = pixels
    
    return {
        'palette': palette,
        'pixels': pixels_map
    }


def get_palette_from_pmap(pmap_string):
    """
    Extract just the palette colors from PMAP string
    
    Args:
        pmap_string: PMAP formatted string
    
    Returns:
        list: List of RGBA tuples
    """
    data = decode_pmap(pmap_string)
    return data['palette']
