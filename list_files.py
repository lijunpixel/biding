#!/usr/bin/env python3
"""
File Lister Script
Reads and displays all files/folders in the current directory with details.
"""

import os
from pathlib import Path
from datetime import datetime


def list_directory(path: str = ".") -> None:
    """
    List all files and folders in the specified directory.
    
    Args:
        path: Directory path to list (default: current directory)
    """
    try:
        directory = Path(path).resolve()
        
        if not directory.exists():
            print(f"[ERROR] Directory '{path}' does not exist")
            return
        
        print(f"\n[DIRECTORY] Contents of: {directory}")
        print(f"{'='*80}")
        
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        
        if not items:
            print("(empty directory)")
            return
        
        for item in items:
            # Determine icon
            icon = "[DIR]" if item.is_dir() else "[FILE]"
            
            # Get file size
            if item.is_file():
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024**2:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/(1024**2):.1f}MB"
            else:
                size_str = "-"
            
            # Get modification time
            mod_time = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            
            # Format output
            name = item.name + ("/" if item.is_dir() else "")
            print(f"{icon} {name:<40} {size_str:>10}  {mod_time}")
        
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    # List current directory
    list_directory()
    
    # Optionally list a specific directory if provided as argument
    import sys
    if len(sys.argv) > 1:
        print("\n" + "="*80)
        list_directory(sys.argv[1])
