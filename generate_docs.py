#!/usr/bin/env python3
"""
Script to generate Doxygen documentation with flow diagrams for the MovieNight project.

This script:
1. Checks for Doxygen installation
2. Generates HTML documentation with flow diagrams
3. Opens the generated documentation in a browser

Usage:
    python generate_docs.py

Requirements:
    - Doxygen (must be installed on system)
    - Graphviz (must be installed on system for diagram generation)
    - doxypypy (Python package for improved Python parsing)
"""

import subprocess
import os
import sys
import webbrowser
from pathlib import Path


def check_doxygen_installed():
    """Check if Doxygen is installed on the system."""
    try:
        result = subprocess.run(['doxygen', '--version'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            print(f"✓ Doxygen found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    return False


def check_graphviz_installed():
    """Check if Graphviz is installed (needed for diagram generation)."""
    try:
        result = subprocess.run(['dot', '-V'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            print(f"✓ Graphviz found: {result.stderr.strip()}")
            return True
    except FileNotFoundError:
        pass
    return False


def generate_documentation():
    """Run Doxygen to generate documentation."""
    doxyfile_path = Path('Doxyfile')
    
    if not doxyfile_path.exists():
        print("✗ Error: Doxyfile not found in current directory")
        return False
    
    print("\n🔄 Generating documentation with Doxygen...")
    try:
        result = subprocess.run(['doxygen', 'Doxyfile'],
                              capture_output=True,
                              text=True)
        
        if result.returncode == 0:
            print("✓ Documentation generated successfully!")
            return True
        else:
            print(f"✗ Doxygen error:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error running Doxygen: {e}")
        return False


def open_documentation():
    """Open the generated documentation in default browser."""
    html_index = Path('doxygen_output/html/index.html')
    
    if html_index.exists():
        print(f"\n📖 Opening documentation at: {html_index.absolute()}")
        webbrowser.open(f'file://{html_index.absolute()}')
        return True
    else:
        print("✗ Documentation HTML not found")
        return False


def main():
    """Main function to orchestrate documentation generation."""
    print("=" * 60)
    print("MovieNight Documentation Generator")
    print("=" * 60)
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    doxygen_ok = check_doxygen_installed()
    graphviz_ok = check_graphviz_installed()
    
    if not doxygen_ok:
        print("\n✗ Doxygen is not installed!")
        print("\n📥 Installation instructions:")
        print("  Windows: choco install doxygen graphviz")
        print("  macOS:   brew install doxygen graphviz")
        print("  Linux:   sudo apt-get install doxygen graphviz")
        sys.exit(1)
    
    if not graphviz_ok:
        print("\n⚠️  Warning: Graphviz not found. Flow diagrams won't be generated.")
        print("Install Graphviz for better diagram generation:")
        print("  Windows: choco install graphviz")
        print("  macOS:   brew install graphviz")
        print("  Linux:   sudo apt-get install graphviz")
    
    # Generate documentation
    if not generate_documentation():
        sys.exit(1)
    
    # Open in browser
    print("\n" + "=" * 60)
    open_documentation()
    print("=" * 60)
    print("\n✓ Documentation generation complete!")
    print("\nGenerated files are in: doxygen_output/html/")
    print("\nKey diagrams to look for:")
    print("  - Call graphs for each function")
    print("  - Caller graphs showing function relationships")
    print("  - Class hierarchies and relationships")


if __name__ == '__main__':
    main()
