#!/usr/bin/env python3
"""
Skyn Data Manager GUI Launcher
Run this script to start the TKINTER GUI for processing single Skyn data files.
"""

import sys
import os

# Add the App directory to the path so we can import SDM modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'App'))

# Import and run the GUI
from App.SDM.sdm_app import main

if __name__ == "__main__":
    main() 