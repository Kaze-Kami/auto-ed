# -*- coding: utf-8 -*-

"""
Simple tool to automatically disable Flight-Assist
in Elite: Dangerous

Reads the status.json and if disables FA if necessary

@author Kami-Kaze
"""

import json
import time

import imgui
from essentials.gui.app import App, AppConfig
from essentials.gui.config import Config
from essentials.io.logging import get_logger
from essentials.utils.git import releases_url, file_url
from essentials.utils.versioning import Version, check_version

from lib.ed import Status
from lib.filesystem import Watchdog
from lib.globals import *

_LOGGER = get_logger('main')

_CONFIG_PATH = 'config.json'
_VERSION_FILE = '.version'
_VERSION_REF_FILE = file_url('Kaze-Kami', 'auto-ed', '.version', branch='main')
_LATEST_RELEASE = releases_url('Kaze-Kami', 'auto-ed', latest=True)


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


class ShipState:
    def __init__(self):
        self.processed = False
        self.flight_assist = False
        self.drive_assist = False
        self.gear = False

        self.in_srv = False
        self.fsd_active = False
        self.docked_or_landed = False


class MyApp(App):
    def __init__(self):
        self.config: MyConfig = Config.load(MyConfig, _CONFIG_PATH, default_config)
        super().__init__(AppConfig(
                width=310,
                height=235,
                title='Auto-ED',
                icon_path='resources/icon-color.png',
                start_minimized=self.config.start_minimized,
                background_color=(0.17, 0.24, 0.31),
        ))

        self.watchdog = Watchdog(ed.BasePath, ed.Files.STATUS, self.on_status_update)

        self.state = ShipState()
        self.was_docked_or_landed = False
        self.last_focused_at = time.time()

        with open(_VERSION_FILE, 'r') as vf:
            self.current_version = Version.parse_version(vf.read())
        self.latest_version = check_version(self.current_version, _VERSION_REF_FILE)

    def update(self):
        # don't do anything if window is not found/focused
        if not win.is_window_focused(win.find_window(WINDOW_NAME)):
            self.last_focused_at = 0
            return
        elif self.last_focused_at == 0:
            self.last_focused_at = time.time()

        # seems ED: struggles if you send commands right away,
        # so we need to wait a bit (50ms) before going ham :)
        focused = time.time() - self.last_focused_at > .05
        if not focused:
            return

        if not self.config.active or self.state.processed:
            return

        if self.config.auto_fa:
            self.check_flight_assist()
        if self.config.auto_da:
            self.check_drive_assist()
        if self.config.auto_gear:
            self.check_gear()
        self.state.processed = True

    def on_status_update(self, status_data: bytes):
        data = json.loads(status_data)
        flags = data['Flags']

        self.state = ShipState()

        self.state.drive_assist = flags & Status.SRV_DRIVE_ASSIST
        self.state.flight_assist = not flags & Status.FLIGHT_ASSIST_OFF
        self.state.gear = flags & Status.GEAR_DOWN

        self.state.in_srv = flags & Status.IN_SRV
        self.state.fsd_active = flags & (Status.FSD_CHARGING | Status.SUPER_CRUISE | Status.FSD_JUMP)
        self.state.docked_or_landed = flags & (Status.DOCKED | Status.LANDED)
        self.was_docked_or_landed |= self.state.docked_or_landed

    def check_flight_assist(self):
        if self.state.in_srv or self.state.docked_or_landed or self.state.fsd_active:
            return

        if self.state.flight_assist:
            _LOGGER.info('Disable Flight assist')
            win.press_key(KEY_FA)

    def check_drive_assist(self):
        if not self.state.in_srv:
            return

        if self.state.drive_assist:
            _LOGGER.info('Disable Drive assist')
            win.press_key(KEY_DA)

    def check_gear(self):
        if not self.state.gear:
            return

        if self.was_docked_or_landed and not self.state.docked_or_landed:
            _LOGGER.info('Retracting gear')
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

        if self.latest_version is not None:
            imgui.push_style_color(imgui.COLOR_TEXT, *red)
            text = "New version available!"
            text_width, _ = imgui.calc_text_size(text)
            imgui.same_line(imgui.get_window_content_region_max().x - text_width)
            imgui.text(text)
            imgui.pop_style_color()

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
        yes_no(self.state.docked_or_landed, 'Docked/Landed')
        yes_no(self.was_docked_or_landed, 'Was Docked/Landed')
        yes_no(self.state.fsd_active, 'FSD Active')
        yes_no(self.state.in_srv, 'In SRV')
        imgui.separator()

        yes_no(self.state.drive_assist, 'Drive Assist', 'Enabled', 'Disabled')
        yes_no(self.state.flight_assist, 'Flight Assist', 'Enabled', 'Disabled')
        yes_no(self.state.gear, 'Gear', 'Extended', 'Retracted')

    def on_start(self):
        self.watchdog.start()

    def on_stop(self):
        self.watchdog.stop()
        Config.save(MyConfig, _CONFIG_PATH, self.config)

    def on_hide(self):
        self.config.start_minimized = True

    def on_show(self):
        self.config.start_minimized = False


def main():
    app = MyApp()
    app.run()


if __name__ == '__main__':
    main()
