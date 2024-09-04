import sys
import os

# Determine the base path depending on whether the script is bundled by PyInstaller
if getattr(sys, 'frozen', False):
    # If bundled, use sys._MEIPASS as the base path
    base_path = sys._MEIPASS
else:
    # If running normally, use the current directory
    base_path = os.path.abspath(os.path.dirname(__file__))

# Append the directory containing your modules to sys.path
print(base_path)
sys.path.append(base_path)

from sdm_user_interface import SkynDataManagerApp

SkynDataManagerApp()