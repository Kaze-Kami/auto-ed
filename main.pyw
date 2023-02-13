# -*- coding: utf-8 -*-

"""
Simple tool to automatically disable Flight-Assist
in Elite: Dangerous

Reads the status.json and if disables FA if necessary

@author Kami-Kaze
"""

import json

import imgui
from essentials.gui.app import App, AppConfig
from essentials.gui.config import Config
from essentials.io.logging import get_logger

from lib.ed import Status
from lib.filesystem import Watchdog
from lib.globals import *

_LOGGER = get_logger('main')

_CONFIG_PATH = 'config.json'


class MyConfig(Config):
    def __init__(self, start_minimized: bool, active: bool, auto_fa: bool, auto_da: bool, auto_gear: bool):
        super().__init__()
        self.start_minimized = start_minimized
        self.active = active
        self.auto_fa = auto_fa
        self.auto_da = auto_da
        self.auto_gear = auto_gear


def default_config():
    return MyConfig(
            start_minimized=False,
            auto_fa=True,
            auto_da=True,
            auto_gear=True,
            active=True
    )


class MyApp(App):
    def __init__(self):
        self.config = Config.load(MyConfig, _CONFIG_PATH, default_config)
        super().__init__(AppConfig(
                width=330,
                height=210,
                title='Auto-ED',
                icon_path='resources/icon-color.png',
                start_minimized=self.config.start_minimized,
                background_color=(0.17, 0.24, 0.31),
        ))

        self.watchdog = Watchdog(ed.BasePath, ed.Files.STATUS, self.on_status_update)

        self.flight_assist = False
        self.drive_assist = False
        self.gear = False

        self.in_srv = False
        self.fsd_active = False
        self.was_docked_or_landed = False
        self.docked_or_landed = False

    def update(self):
        if not self.config.active:
            return

        # don't do anything if window is not found/focused
        if not win.is_window_focused(win.find_window(WINDOW_NAME)):
            return

        if self.config.auto_fa:
            self.check_flight_assist()
        if self.config.auto_da:
            self.check_drive_assist()
        if self.config.auto_gear:
            self.check_gear()

    def on_status_update(self, status_data: bytes):
        data = json.loads(status_data)
        flags = data['Flags']

        self.drive_assist = flags & Status.SRV_DRIVE_ASSIST
        self.flight_assist = not flags & Status.FLIGHT_ASSIST_OFF
        self.gear = flags & Status.GEAR_DOWN

        self.in_srv = flags & Status.IN_SRV
        self.fsd_active = flags & (Status.FSD_CHARGING | Status.SUPER_CRUISE | Status.FSD_JUMP)
        self.was_docked_or_landed |= self.docked_or_landed
        self.docked_or_landed = flags & (Status.DOCKED | Status.LANDED)

    def check_flight_assist(self):
        if self.in_srv or self.docked_or_landed or self.fsd_active:
            return

        if self.flight_assist:
            _LOGGER.info('Disable Flight assist')
            self.flight_assist = False
            win.press_key(KEY_FA)

    def check_drive_assist(self):
        if not self.in_srv:
            return

        if self.drive_assist:
            _LOGGER.info('Disable Drive assist')
            self.drive_assist = False
            win.press_key(KEY_DA)

    def check_gear(self):
        if not self.gear:
            return

        if self.was_docked_or_landed and not self.docked_or_landed:
            _LOGGER.info('Retracting gear')
            self.gear = False
            self.was_docked_or_landed = False
            win.press_key(KEY_GEAR)

    def render(self):
        red = (0.90, 0.49, 0.13)
        green = (0.18, 0.80, 0.44)

        def yes_no(prop: bool, name: str, yes: str = 'Yes', no: str = 'No'):
            color = green if prop else red
            text = yes if prop else no
            imgui.align_text_to_frame_padding()
            imgui.text(f'{name}:')
            imgui.same_line()
            imgui.push_style_color(imgui.COLOR_BUTTON, *color)
            imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *color)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *color)
            imgui.button(text)
            imgui.pop_style_color(3)

        def colored_switch(text, status):
            imgui.push_style_color(imgui.COLOR_BUTTON, *(green if status else red))
            r = imgui.button(text)
            imgui.pop_style_color()
            return not status if r else status

        yes_no(win.find_window(WINDOW_NAME), 'Elite Running')
        imgui.separator()
        self.config.active = colored_switch('Active', self.config.active)
        imgui.same_line()
        self.config.auto_fa = colored_switch('Flight Assist', self.config.auto_fa)
        imgui.same_line()
        self.config.auto_da = colored_switch('Drive Assist', self.config.auto_da)
        imgui.same_line()
        self.config.auto_gear = colored_switch('Gear', self.config.auto_gear)
        imgui.separator()

        # debug ui I guess
        yes_no(self.docked_or_landed, 'Docked/Landed')
        yes_no(self.fsd_active, 'FSD Active')
        yes_no(self.in_srv, 'In SRV')
        imgui.separator()

        yes_no(self.drive_assist, 'Drive Assist', 'Enabled', 'Disabled')
        yes_no(self.flight_assist, 'Flight Assist', 'Enabled', 'Disabled')
        yes_no(self.gear, 'Gear', 'Extended', 'Retracted')

    def on_start(self):
        self.watchdog.start()

    def on_stop(self):
        self.watchdog.stop()
        Config.save(MyConfig, _CONFIG_PATH, self.config)


def main():
    app = MyApp()
    app.run()


if __name__ == '__main__':
    main()
