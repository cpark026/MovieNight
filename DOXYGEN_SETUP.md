# Setting Up Doxygen for MovieNight Documentation

## Quick Start

### Prerequisites Installation

#### Windows (using Chocolatey)
If you have Chocolatey installed:
```powershell
choco install doxygen graphviz
```

If you don't have Chocolatey, install it first or download directly:
- **Doxygen**: https://www.doxygen.nl/download.html
- **Graphviz**: https://graphviz.org/download/

#### macOS (using Homebrew)
```bash
brew install doxygen graphviz
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install doxygen graphviz
```

### Generate Documentation

Once Doxygen and Graphviz are installed:

```powershell
python generate_docs.py
```

This will:
1. ✓ Verify Doxygen installation
2. ✓ Verify Graphviz installation (for diagrams)
3. ✓ Generate HTML documentation
4. ✓ Create flow diagrams for all functions
5. ✓ Open documentation in your browser

### Output Location

Documentation will be generated in: `doxygen_output/html/index.html`

## What You'll Get

### Flow Diagrams
- **Call Graphs**: Shows what each function calls
- **Caller Graphs**: Shows what functions call each function
- **UML Diagrams**: Class and structure relationships

### For model.py Specifically
You'll see detailed diagrams for:
- `get_recommendations()` - Main recommendation engine flow
- `get_recommendations_for_last_added()` - Last-added movie recommendations
- `get_recommendations_by_most_common_genre()` - Genre-based recommendations
- `get_user_profile()` - User profile aggregation
- All helper functions with their relationships

### Documentation Features
- Syntax-highlighted source code
- Interactive call/caller graphs
- Tree view of all modules and functions
- Search functionality
- Cross-referenced documentation
- Parameter and return value documentation

## Manual Generation

If you prefer to run Doxygen directly:

```powershell
doxygen Doxyfile
```

Then open: `doxygen_output/html/index.html`

## Customization

The `Doxyfile` can be customized for:
- Different output formats (HTML, LaTeX, RTF, etc.)
- Including/excluding specific files
- Diagram depth and complexity
- Documentation style and appearance

Key settings in Doxyfile:
- `CALL_GRAPH = YES` - Generate call graphs
- `CALLER_GRAPH = YES` - Generate caller graphs
- `EXTRACT_ALL = YES` - Document all members
- `HAVE_DOT = YES` - Use Graphviz for diagrams

## Troubleshooting

### "doxygen: command not found"
- Doxygen not installed or not in PATH
- Run installation commands above
- Or add Doxygen to your system PATH

### Diagrams not generating
- Graphviz not installed
- Run: `choco install graphviz` (Windows)
- Or see installation instructions above

### Permission denied on generate_docs.py
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Next Steps

1. Install Doxygen and Graphviz
2. Run `python generate_docs.py`
3. Open `doxygen_output/html/index.html` in your browser
4. Explore the call graphs and documentation for model.py
