# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""

import os

from essentials.io.file import join_path
from essentials.io.logging import get_logger
from essentials.utils.git import releases_url, file_url

from lib import ed, win

# ed window name
WINDOW_NAME = ed.WindowName

# key binds
KEY_GLOBAL_MOD = win.scan_code(win.VK_RSHIFT)
KEY_FA = win.scan_code(win.VK_F5)
KEY_DA = win.scan_code(win.VK_F6)
KEY_GEAR = win.scan_code(win.VK_F7)
KEY_LIGHTS = win.scan_code(win.VK_F8)
KEY_NIGHT_VISION = win.scan_code(win.VK_F9)

# logging
LOGGER = get_logger('main')

# versioning
VERSION_FILE = '.version'
VERSION_REF_URL = file_url('Kaze-Kami', 'auto-ed', '.version', branch='main')

# file paths
DATA_DIR = '.data'
CONFIG_FILE = join_path(DATA_DIR, 'config.json')
WAYPOINT_FILE = join_path(DATA_DIR, 'waypoints.json')
WAYPOINT_BACKUP_PATTERN = join_path(DATA_DIR, 'waypoints-backup-%d.json')
LATEST_RELEASE = releases_url('Kaze-Kami', 'auto-ed', latest=True)
STATUS_FILE_PATH = os.path.join(ed.BasePath, ed.Files.STATUS)

# name patterns
WAYPOINT_NAME_PATTERN = 'New Waypoint %d'

# ui stuff
BUTTON_PADDING = 5  # add this to a the calc_text_size of a button's text to get the buttons width
DEFAULT_FUZZY_RATIO = 70

# not present in PyImGui -> taken from imgui source code
ImGuiHoveredFlags_DelayShort = 1 << 12
