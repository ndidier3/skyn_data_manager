from sys import platform

def get_font_size(type):
  if platform == "linux" or platform == "linux2":
    return 16 if type == 'header' else 13
  elif platform == "darwin":
    return 16 if type == 'header' else 13
  elif platform == "win32":
    return 14 if type == 'header' else 11
