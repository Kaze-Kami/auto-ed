# -*- coding: utf-8 -*-

"""
Script to set up key binds for Auto-ED

TODO: Alter game config files directly:
    - arg: config-name

    -> copy config to <config-name>-auto-ed and overwrite needed key binds
@author Kami-Kaze
"""

import time
from msvcrt import getch

from lib.globals import *


def main():
    # script to set up key binds
    print('-------- SETUP --------')
    print('Open key bind settings and open the "Input dialog" for given key bind')
    print('I recommend binding it as secondary binding')
    print('Once the "Input dialog" is open, continue here')
    print()

    def set_bind(name: str, key):
        print(f'> {name}')
        input('Press enter to continue... then re-focus ED')
        while True:
            # wait for ed to get focus
            print('Waiting for ED to get focus')
            while not win.is_window_focused(win.find_window(WINDOW_NAME)):
                time.sleep(.25)

            print('Setting key bind')
            time.sleep(.5)
            win.press_key(key, KEY_GLOBAL_MOD)
            print('Press enter to continue or anything else to repeat...')
            if getch() == b'\r':
                break

    set_bind('Flight Assist (Toggle)', KEY_FA)
    set_bind('Drive Assist (Toggle)', KEY_DA)
    set_bind('Landing Gear', KEY_GEAR)
    set_bind('Lights', KEY_LIGHTS)
    set_bind('Night Vision', KEY_NIGHT_VISION)
    print('Setup complete')
    print('Remember to save your ED settings')


if __name__ == '__main__':
    main()
