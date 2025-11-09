# PyPalette - Dynamic Palette Editor

A simple tool for color replacement in images with palette saving capabilities. Load an image, edit its colors, and save your palette changes.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![License](https://img.shields.io/badge/license-Open%20Source-blue.svg)
![Vibe](https://img.shields.io/badge/vibe-coded-ff69b4.svg)

## 🎨 Features

### Core Functionality
- **Real-time palette editing** with instant visual feedback
- **Automatic color extraction** from loaded images
- **Multiple palette management** with tabbed interface
- **Precision color replacement** maintaining image quality
- **Zoom and pan** capabilities (0.1x to 10x zoom)

### File Format Support
- **Image formats**: PNG, JPG, JPEG, BMP, GIF (not animated)
- **Palette export/import**: PNG palette strips
- **PMAP format**: Custom palette mapping format
- **Embedded PMAP**: Automatic embedding in PNG files for seamless workflow

### Advanced Features
- **Undo/Redo system** with up to 50 operation history
- **Clipboard integration** for color pasting (hex, RGB, RGBA)
- **Smart directory memory** for different operations
- **Color hover preview** in image and palette
- **PMAP preview panel** with detailed color statistics
- **Multi-palette workflow** with easy tab switching

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/OnionMilk-org/PYPALETTE.git
   cd PYPALETTE
   ```

2. **Install dependencies:**
   ```bash
   # Using the provided batch file (Windows)
   install_requirements.bat
   
   # Or manually with pip
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   # Using the launcher (Windows)
   start_palette_editor.bat
   
   # Or directly with Python
   python main.py
   ```

### Building Standalone Executable (Optional)

If you want a standalone `.exe` file:

```bash
# Basic compilation
compile.bat

# Advanced compilation with optimizations
compile_advanced.bat
```

The compiled executable will be created in the `build/` directory and can run without Python installed.

### Basic Usage

1. **Load an image**: `Ctrl+O` or File → Open
2. **Edit colors**: Click any color in the palette panel
3. **Save your work**: `Ctrl+S` saves with embedded palette data
4. **Export palette**: Use File → Export Palette Map for sharing

## 📋 Interface Overview

### Main Components

#### Color Editor Panel (Left)
- **Palette tabs**: Switch between multiple color schemes (1-9 keys)
- **Color buttons**: buttons showing hex codes
- **New Palette**: Duplicate current palette for variations

#### Image Preview (Center)
- **Zoomable display**: Mouse wheel zoom, middle-click pan
- **Real-time updates**: Instant color change visualization
- **Pixel-perfect editing**: No antialiasing for precise work
- **Color information**: Hover shows coordinates and color values

#### PMAP Preview Panel (Optional)
- **Color statistics**: ID, hex codes, pixel counts
- **Interactive preview**: Hover to highlight colors in image
- **Toggle visibility**: F1 or View menu

### Key Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open Image |
| `Ctrl+S` | Save Image (with embedded PMAP) |
| `Ctrl+Z/Y` | Undo/Redo |
| `Ctrl+E` | Export Palette Map |
| `Ctrl+M` | Import Palette Map |
| `1-9` | Switch Palette Tabs |
| `F1` | Toggle PMAP Preview |

### Mouse Operations

#### Color Buttons
- **Left Click**: Open color picker dialog
- **Right Click**: Paste color from clipboard

#### Image Preview
- **Mouse Wheel**: Zoom in/out
- **Middle Mouse + Drag**: Pan image
- **Left Click**: Edit clicked pixel's color
- **Right Click**: Paste clipboard color to pixel

## 🗂️ File Formats

### PMAP (Palette Map) Format
Custom text format storing:
- Color count and hex values
- Precise pixel coordinates for each color
- Complete image reconstruction data

```
3
#FF0000 5 0;0 1;0 2;0 0;1 1;1
#00FF00 3 2;1 0;2 1;2
#0000FF 2 2;2 0;3
```

Format: `{COLOR_COUNT}` on first line, then `#{HEX} {PIXEL_COUNT} {X;Y} {X;Y}...` for each color.

See [PMAP_REFERENCE.md](PMAP_REFERENCE.md) for detailed specification.

### Embedded PMAP in PNG
- Automatic embedding when saving PNG files
- Seamless loading of palette data with images
- Maintains standard PNG compatibility

## 🏗️ Project Structure

```
PYPALETTE/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── settings.json             # User preferences and recent files
├── 
├── core/
│   └── image_processor.py    # Image loading and processing
├── ui/
│   ├── palette_editor_ui.py  # Main application interface
│   └── zoomable_label.py     # Custom zoomable image widget
├── io/
│   └── pmap_format.py        # PMAP encoding/decoding
├── utils/
│   ├── color_utils.py        # Color manipulation utilities
│   └── settings.py           # Settings management
└── build/
    ├── PyPalette.spec        # PyInstaller configuration
    └── compile scripts       # Build automation
```

## 🛠️ Development

### Requirements
- Python 3.7+
- PyQt5 5.15+
- Pillow (PIL) 8.3+
- NumPy 1.21+

### Building Executable
```bash
# Compile to standalone executable
compile.bat               # Basic compilation
compile_advanced.bat      # Advanced with optimizations
```

### Architecture
- **Modular design**: Separated concerns across core, UI, IO, and utils
- **Event-driven**: PyQt5 signal/slot architecture
- **Settings persistence**: JSON-based configuration management
- **Memory efficient**: Smart image handling and palette management

## 📚 Use Cases

### Game Development
- **Sprite recoloring**: Quick palette swaps for character variants
- **Asset management**: Consistent color schemes across game assets
- **Pixel art editing**: Precise control for retro-style graphics

### Digital Art
- **Color exploration**: Multiple palette variations of artwork
- **Batch processing**: Consistent color changes across image sets
- **Color analysis**: Statistical breakdown of color usage

### Technical Applications
- **Image analysis**: Color distribution and positioning data
- **Color mapping**: Precise color transformations with coordinate tracking
- **Quality assurance**: Pixel-perfect color verification

## 🤝 Contributing

Contributions are welcome! Areas for enhancement:
- Additional image format support
- Batch processing capabilities  
- Color harmony tools
- Plugin system architecture

## 📄 License

Open Source - See license file for details.

## 🔗 Links

- **Author**: [onionmilk.org](https://onionmilk.org)
- **Repository**: [https://github.com/OnionMilk-org/PYPALETTE](https://github.com/OnionMilk-org/PYPALETTE)

## 🤖 Development Credits

This tool was created with the assistance of AI coding tools:
- **GitHub Copilot** in Visual Studio Code for code generation and completion
- **Claude Sonnet 4** for architecture design and problem-solving

This was an experiment on how I could co-work with AI tools, in conslusion: it's a pain. But it's good enough for primitive tools.