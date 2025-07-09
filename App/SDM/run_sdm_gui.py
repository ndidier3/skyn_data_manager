#!/usr/bin/env python3
"""
Skyn Data Manager GUI Launcher
Run this script to start the TKINTER GUI for processing single Skyn data files.
"""

import sys
import os

# Get the workspace root (2 levels up from this script)
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(os.path.dirname(script_dir))

# Add the workspace root to the path so we can import App.SDM modules
sys.path.insert(0, workspace_root)

# Import and run the GUI
from App.SDM.sdm_app import main

if __name__ == "__main__":
    main() 