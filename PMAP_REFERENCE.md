# PMAP Format Reference

## Overview

The **PMAP (Palette Map)** format is a text-based file format designed for storing color palette information along with precise pixel position data from images. It provides a structured way to map unique colors to their exact locations within an image, enabling precise color analysis and manipulation.

## File Extension

- **Standard extension**: `.pmap`

## Purpose and Applications

### Primary Uses
- **Color-to-position mapping**: Store exact pixel coordinates for each unique color
- **Image reconstruction**: Recreate images from color and position data
- **Palette analysis**: Analyze color distribution and usage patterns
- **Color replacement workflows**: Enable precise color substitution operations

### Workflow Integration
- **Embedded in PNG**: Automatic embedding as metadata in PNG files
- **Standalone files**: Export/import as separate `.pmap` files
- **Cross-platform compatibility**: Plain text format ensures universal support

## Format Specification

### Structure Overview

The PMAP format uses a simple text structure:

```
{NUMBER_OF_COLORS}
#{HEX_COLOR} {PIXEL_COUNT} {X;Y} {X;Y} {X;Y} ...
#{HEX_COLOR} {PIXEL_COUNT} {X;Y} {X;Y} ...
...
```

### Line-by-Line Breakdown

#### Line 1: Color Count
```
{NUMBER_OF_COLORS}
```
- **Type**: Integer
- **Purpose**: Specifies the total number of unique colors in the palette
- **Range**: 1 to theoretical maximum (limited by image size)

#### Subsequent Lines: Color Data
```
#{HEX_COLOR} {PIXEL_COUNT} {X;Y} {X;Y} {X;Y} ...
```

**Components:**
1. **HEX_COLOR**: 6-character hexadecimal color code with `#` prefix
   - Format: `#RRGGBB`
   - Example: `#FF0000` (red), `#00FF00` (green), `#0000FF` (blue)
   - Case: Uppercase recommended

2. **PIXEL_COUNT**: Number of pixels with this color
   - Type: Integer
   - Must match the actual number of coordinate pairs that follow

3. **Coordinate Pairs**: Space-separated `X;Y` positions
   - Format: `X;Y` where X and Y are integers
   - Separator: Semicolon (`;`) between X and Y coordinates
   - Delimiter: Space between coordinate pairs
   - Coordinate system: (0,0) at top-left, X increases right, Y increases down

## Examples

### Simple Example
```
3
#FF0000 2 0;0 1;0
#00FF00 1 0;1
#0000FF 3 1;1 2;0 2;1
```

**Interpretation:**
- 3 unique colors
- Red (`#FF0000`): 2 pixels at (0,0) and (1,0)
- Green (`#00FF00`): 1 pixel at (0,1)
- Blue (`#0000FF`): 3 pixels at (1,1), (2,0), and (2,1)

### Complex Example
```
5
#FFFFFF 156 0;0 1;0 2;0 3;0 4;0 5;0 6;0 7;0 8;0 9;0 0;1 1;1 2;1 3;1 4;1 5;1 6;1 7;1 8;1 9;1
#000000 89 10;0 11;0 12;0 13;0 14;0 15;0 16;0 17;0 18;0 19;0 10;1 11;1 12;1 13;1 14;1
#FF0000 23 0;2 1;2 2;2 3;2 4;2 5;2 6;2 7;2 8;2 9;2 10;2 11;2 12;2
#00FF00 45 0;3 1;3 2;3 3;3 4;3 5;3 6;3 7;3 8;3 9;3 10;3 11;3 12;3 13;3 14;3
#0000FF 67 0;4 1;4 2;4 3;4 4;4 5;4 6;4 7;4 8;4 9;4 10;4 11;4 12;4 13;4 14;4 15;4
```

## Technical Details

### Coordinate System
- **Origin**: Top-left corner (0, 0)
- **X-axis**: Increases from left to right
- **Y-axis**: Increases from top to bottom
- **Units**: Pixels (integer coordinates only)
- **Bounds**: 0 ≤ X < image_width, 0 ≤ Y < image_height

### Color Representation
- **Format**: Hexadecimal RGB
- **Alpha channel**: Not stored (assumed opaque)
- **Bit depth**: 8 bits per channel (24-bit total)
- **Case sensitivity**: Case-insensitive parsing, uppercase preferred

### File Encoding
- **Character encoding**: UTF-8
- **Line endings**: Platform-independent (CR, LF, or CRLF supported)
- **Whitespace**: Spaces used as delimiters, no tabs
- **Comments**: Not supported

## Implementation Notes

### Parsing Algorithm
```python
def parse_pmap(pmap_content):
    lines = pmap_content.strip().split('\n')
    
    # Parse color count
    num_colors = int(lines[0])
    
    # Parse each color entry
    for i in range(1, num_colors + 1):
        parts = lines[i].split(' ', 2)
        hex_color = parts[0]  # #RRGGBB
        pixel_count = int(parts[1])
        
        # Parse coordinates
        coord_string = parts[2]
        coordinates = []
        for coord in coord_string.split(' '):
            x, y = coord.split(';')
            coordinates.append((int(x), int(y)))
```

### Generation Algorithm
```python
def generate_pmap(image, palette):
    color_positions = {}
    
    # Scan image and collect positions for each color
    for y in range(image.height):
        for x in range(image.width):
            pixel_color = image.getpixel((x, y))
            hex_color = f"#{pixel_color[0]:02X}{pixel_color[1]:02X}{pixel_color[2]:02X}"
            
            if hex_color not in color_positions:
                color_positions[hex_color] = []
            color_positions[hex_color].append((x, y))
    
    # Generate PMAP string
    lines = [str(len(color_positions))]
    
    for hex_color, positions in color_positions.items():
        coord_string = ' '.join([f"{x};{y}" for x, y in positions])
        lines.append(f"{hex_color} {len(positions)} {coord_string}")
    
    return '\n'.join(lines)
```

## Validation Rules

### Format Validation
1. **Line 1**: Must be a valid integer > 0
2. **Color lines**: Must match the count specified in line 1
3. **Hex colors**: Must be valid 6-character hex codes with `#` prefix
4. **Pixel counts**: Must match the actual number of coordinate pairs
5. **Coordinates**: Must be valid integers separated by semicolons

### Content Validation
1. **No duplicate coordinates**: Each (X,Y) pair should appear only once
2. **Valid bounds**: All coordinates must be within reasonable image dimensions
3. **Color consistency**: Each color should appear in only one palette entry

### Error Handling
Common parsing errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid color count | Non-integer first line | Check first line format |
| Mismatched pixel count | Count doesn't match coordinates | Verify coordinate list |
| Invalid hex color | Malformed color code | Check `#RRGGBB` format |
| Invalid coordinates | Non-integer or missing semicolon | Verify `X;Y` format |

## Performance Considerations

### File Size
- **Overhead**: ~20 bytes per color entry (hex code + count)
- **Coordinates**: ~8 bytes per pixel position (`X;Y `)
- **Compression**: Text format compresses well with gzip/zip

### Memory Usage
- **Loading**: Entire file loaded into memory during parsing
- **Processing**: O(n) where n = total number of pixels
- **Storage**: ~16 bytes per coordinate pair in memory (integer tuples)

### Optimization Tips
1. **Large images**: Consider tiling or region-based processing
2. **Many colors**: Use streaming parsers for memory efficiency
3. **Compression**: Apply text compression for storage/transmission

## Use Cases

### Image Analysis
```python
# Count colors and their frequencies
def analyze_palette(pmap_file):
    data = parse_pmap(open(pmap_file).read())
    for color, positions in data.items():
        print(f"Color {color}: {len(positions)} pixels")
```

### Color Replacement
```python
# Replace one color with another
def replace_color(pmap_data, old_color, new_color):
    if old_color in pmap_data:
        positions = pmap_data.pop(old_color)
        pmap_data[new_color] = positions
```

### Region Analysis
```python
# Find colors in a specific region
def colors_in_region(pmap_data, x1, y1, x2, y2):
    region_colors = {}
    for color, positions in pmap_data.items():
        region_positions = [
            (x, y) for x, y in positions 
            if x1 <= x <= x2 and y1 <= y <= y2
        ]
        if region_positions:
            region_colors[color] = region_positions
    return region_colors
```

## Integration with PyPalette

### Embedded PNG Storage
PyPalette automatically embeds PMAP data in PNG files as text chunks:
- **Chunk name**: `PMAP`
- **Content**: Raw PMAP format string
- **Encoding**: UTF-8 text
- **Compatibility**: Standard PNG readers ignore unknown chunks

### Export Options
1. **Standalone PMAP**: Save as `.pmap` file
2. **Embedded PNG**: Save image with PMAP metadata

### Import Capabilities
1. **Direct PMAP**: Load `.pmap` files directly
2. **PNG extraction**: Extract PMAP from PNG metadata
3. **Palette reconstruction**: Rebuild image from PMAP data

## Version History

### Current Version (1.0)
- Basic PMAP format specification
- RGB color support (no alpha)
- Integer coordinate system
- Text-based format

### Future Considerations
- **Alpha channel support**: Extend to `#RRGGBBAA` format
- **Compression**: Binary format for large files
- **Metadata**: Additional image properties (dimensions, creation date)
- **Hierarchical palettes**: Support for palette inheritance

## Compatibility

### Supported Platforms
- **Windows**: Full support
- **macOS**: Compatible (line ending agnostic)
- **Linux**: Compatible (UTF-8 standard)

### External Tools
- **Text editors**: Any UTF-8 capable editor
- **Custom parsers**: Requires PMAP-aware software for processing
- **Image tools**: Requires PMAP-aware software

## Best Practices

### File Management
1. **Naming**: Use descriptive names (`image_name.pmap`)
2. **Organization**: Store alongside source images
3. **Backup**: Include in version control systems
4. **Documentation**: Comment purpose in file metadata

### Performance
1. **Large files**: Consider splitting into regions
2. **Frequent access**: Cache parsed data in memory
3. **Network transfer**: Compress before transmission
4. **Processing**: Use streaming for memory-constrained environments

### Quality Assurance
1. **Validation**: Always validate format before processing
2. **Testing**: Verify round-trip accuracy (image → PMAP → image)
3. **Error handling**: Implement graceful failure modes
4. **Logging**: Track parsing errors and warnings

---

*PMAP Format Reference - Version 1.0*  
*Part of PyPalette Dynamic Palette Editor*  
*Repository: https://github.com/OnionMilk-org/PYPALETTE*  
*For more information, visit: https://onionmilk.org*