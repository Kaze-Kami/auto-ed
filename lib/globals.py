# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""

import os

from lib import ed, win

STATUS_FILE_PATH = os.path.join(ed.BasePath, ed.Files.STATUS)
WINDOW_NAME = ed.WindowName

KEY_FA = win.scan_code(win.VK_F9)
KEY_DA = win.scan_code(win.VK_F10)
KEY_GEAR = win.scan_code(win.VK_F11)
