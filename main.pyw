# -*- coding: utf-8 -*-

"""
Simple tool to automatically disable Flight-Assist
in Elite: Dangerous

Reads the status.json and if disables FA if necessary

@author Kami-Kaze
"""

import json
import time
from collections import defaultdict

import imgui
from essentials.gui.app import App, AppConfig
from essentials.gui.config import Config
from essentials.io.file import open_or_create
from essentials.utils.versioning import Version, check_version
from fuzzywuzzy.fuzz import partial_ratio

from lib.ed import Status
from lib.filesystem import Watchdog
from lib.globals import *
from lib.util import find_first_available
from lib.waypoint import Waypoint, calculate_bearing, calculate_distance


class MyConfig(Config):
    def __init__(self,
                 start_minimized: bool, active: bool,
                 auto_fa: bool, auto_da: bool, auto_gear: bool,
                 waypoint_filter: str, fuzzy_ratio: int,
                 show_planet_names: bool, group_by_planet: bool,
                 ):
        super().__init__()
        self.start_minimized = start_minimized
        self.active = active
        self.auto_fa = auto_fa
        self.auto_da = auto_da
        self.auto_gear = auto_gear
        self.waypoint_filter = waypoint_filter
        self.fuzzy_ratio = fuzzy_ratio
        self.show_planet_names = show_planet_names
        self.group_by_planet = group_by_planet


def default_config():
    return MyConfig(
            start_minimized=False,
            auto_fa=True,
            auto_da=True,
            auto_gear=True,
            active=True,
            waypoint_filter='',
            fuzzy_ratio=DEFAULT_FUZZY_RATIO,
            show_planet_names=True,
            group_by_planet=True,
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
        self.config: MyConfig = Config.load(MyConfig, CONFIG_FILE, default_config)
        super().__init__(AppConfig(
                width=500,
                height=300,
                title='Auto-ED',
                icon_path='resources/icon-color.png',
                resizable=True,
                start_minimized=self.config.start_minimized,
                background_color=(0.17, 0.24, 0.31),
        ))

        self.watchdog = Watchdog(ed.BasePath, ed.Files.STATUS, self.on_status_update)

        self.state = ShipState()
        self.was_docked_or_landed = False
        self.last_focused_at = time.time()

        with open_or_create(VERSION_FILE, 'r', '0.0.0') as vf:
            self.current_version = Version.parse_version(vf.read())
        self.latest_version = check_version(self.current_version, VERSION_REF_URL)

        with open_or_create(WAYPOINT_FILE, 'r', '[]') as wpf:
            try:
                self.waypoints = json.load(wpf, object_hook=Waypoint.from_json)
            except Exception:
                p = find_first_available(WAYPOINT_BACKUP_PATTERN, lambda p: os.path.exists(p))
                LOGGER.error(f'Failed to read waypoints file! A backup has been saved to {p}')
                with open(p, 'w') as backup:
                    backup.write(wpf.read())
                self.waypoints = []

        self.has_position = False
        self.position = 0.0, 0.0
        self.heading = 0.0
        self.planet_name = ''
        self.planet_radius = 0.0
        self.altitude = 0.0

        self.current_waypoint = None

        self.filtered_waypoints = list()
        self.filtered_waypoints_by_planet = defaultdict(lambda: [])
        self._filter_waypoints()

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

        self.has_position = flags & Status.HAS_LAT_LONG
        if self.has_position:
            self.position = data['Latitude'], data['Longitude']
            self.heading = data['Heading']
            self.planet_radius = data['PlanetRadius']
            self.altitude = data['Altitude']
            self.planet_name = data['BodyName']
        else:
            self.position = 0.0, 0.0
            self.heading = 0.0
            self.planet_radius = 0.0
            self.altitude = 0.0
            self.planet_name = ''

        # todo: 1) wing beacon
        # todo: 2) lights & night vision

    def check_flight_assist(self):
        if self.state.in_srv or self.state.docked_or_landed or self.state.fsd_active:
            return

        if self.state.flight_assist:
            LOGGER.info('Disable Flight assist')
            win.press_key(KEY_FA)

    def check_drive_assist(self):
        if not self.state.in_srv:
            return

        if self.state.drive_assist:
            LOGGER.info('Disable Drive assist')
            win.press_key(KEY_DA)

    def check_gear(self):
        if not self.state.gear:
            return

        if self.was_docked_or_landed and not self.state.docked_or_landed:
            LOGGER.info('Retracting gear')
            self.was_docked_or_landed = False
            win.press_key(KEY_GEAR)

    def render(self):
        indent = 4.0
        red = (0.90, 0.49, 0.13)
        green = (0.18, 0.80, 0.44)

        def collapsing_header(title: str):
            class _Helper:
                def __enter__(self):
                    r, _ = imgui.collapsing_header(title)
                    imgui.indent(indent)
                    return r

                def __exit__(self, exc_type, exc_val, exc_tb):
                    imgui.unindent(indent)

            return _Helper()

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

        # automation tools
        with collapsing_header('Automation') as open:
            if open:
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

        def right_button(text: str, id: str = None) -> bool:
            text_width, _ = imgui.calc_text_size(text)
            item_width = text_width + BUTTON_PADDING
            imgui.same_line(imgui.get_window_content_region_max().x - item_width)
            if id is not None:
                text = f'{text}##{id}'
            r = imgui.button(text)
            return r

        def waypoint_name(waypoint: Waypoint, prefix: str = ''):
            # name
            text = f'{prefix}{waypoint.name}'

            if self.config.show_planet_names:
                text = f'{text} ({waypoint.planet})'

            imgui.align_text_to_frame_padding()
            imgui.text(text)

            # position
            if imgui.is_item_hovered(ImGuiHoveredFlags_DelayShort):
                imgui.begin_tooltip()
                imgui.align_text_to_frame_padding()
                imgui.text(f'Planet: {waypoint.planet}')
                imgui.text(f'Position: {waypoint.lat:.4f}, {waypoint.lon:.4f}')
                imgui.end_tooltip()

        def waypoint_panel(waypoint: Waypoint):
            # target button
            is_active = self.current_waypoint == waypoint

            if is_active:
                imgui.push_style_color(imgui.COLOR_BUTTON, *green)

            if imgui.button(f'Target##{waypoint.id}'):
                if is_active:
                    self.current_waypoint = None
                else:
                    self.current_waypoint = waypoint

            if is_active:
                imgui.pop_style_color()

            # name
            imgui.same_line()
            waypoint_name(waypoint)

            # edit button
            popup_name = f'edit_waypoint_{waypoint.id}'
            imgui.same_line()
            if right_button(f'Edit', waypoint.id):
                imgui.open_popup(popup_name)

            change = False
            if imgui.begin_popup(popup_name):
                imgui.text('Edit Waypoint')
                imgui.separator()
                imgui.text(f'ID: {waypoint.id}')
                # name
                change_name, waypoint.name = imgui.input_text(f'Name##{popup_name}', waypoint.name, 250)
                # lat/lon
                change_pos, (waypoint.lat, waypoint.lon) = imgui.input_float2('Position', waypoint.lat, waypoint.lon)

                # delete button
                imgui.push_style_color(imgui.COLOR_BUTTON, 0.90, 0.49, 0.13)
                imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.75, 0.22, 0.17)

                if imgui.button(f'Delete Waypoint##{waypoint.id}'):
                    imgui.close_current_popup()
                    self.waypoints.remove(waypoint)
                    self._filter_waypoints()
                    if self.current_waypoint == waypoint:
                        self.current_waypoint = None

                imgui.pop_style_color(2)

                change |= change_name | change_pos
                imgui.end_popup()

            if change:
                self._filter_waypoints()

        # waypoint manager
        with collapsing_header('Waypoint Manager') as open:
            if open:
                if self.current_waypoint is not None:
                    if self.has_position:
                        bearing = calculate_bearing(self.position, self.current_waypoint)
                        distance = calculate_distance(self.position, self.current_waypoint, self.planet_radius)
                        imgui.align_text_to_frame_padding()
                        imgui.text(f'Bearing: {bearing:.1f}° ({distance:.0f} m on surface)')

                    waypoint_name(self.current_waypoint, prefix='Target: ')
                else:
                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Bearing: [No Target]')

                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Target: [No Target]')

                if self.current_waypoint is not None:
                    imgui.same_line()
                    if right_button('Unset'):
                        self.current_waypoint = None

                if self.has_position:
                    lat, lon = self.position
                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Current position: {lat:.4f}, {lon:.4f}')
                    imgui.same_line()
                    if right_button('Save'):
                        name = find_first_available(WAYPOINT_NAME_PATTERN, lambda name: any(p.name == name for p in self.waypoints))
                        self.waypoints.append(Waypoint.from_position(name, self.planet_name, lat, lon))
                        self._filter_waypoints()
                else:
                    imgui.align_text_to_frame_padding()
                    imgui.text('Current position: [No Reading]')

                # waypoint list
                imgui.separator()
                with collapsing_header('Waypoints') as open:
                    if open:
                        change, self.config.waypoint_filter = imgui.input_text('##waypoint_filter', self.config.waypoint_filter, 200)

                        imgui.same_line()
                        if imgui.button('Reset'):
                            self.config.waypoint_filter = ''
                            change = True

                        imgui.same_line()
                        if right_button('Settings'):
                            imgui.open_popup('manager_settings')

                        if imgui.begin_popup('manager_settings'):
                            ratio_change, self.config.fuzzy_ratio = imgui.slider_int('Fuzzy Ratio', self.config.fuzzy_ratio, 0, 100)

                            imgui.same_line(0, 30)
                            if imgui.button('Reset##ratio_reset'):
                                ratio_change = True
                                self.config.fuzzy_ratio = DEFAULT_FUZZY_RATIO

                            _, self.config.show_planet_names = imgui.checkbox('Show planet names', self.config.show_planet_names)

                            if self.config.show_planet_names:
                                self.config.group_by_planet = False
                            else:
                                _, self.config.group_by_planet = imgui.checkbox('Group by planet', self.config.group_by_planet)

                            change |= ratio_change
                            imgui.end_popup()

                        if change:
                            self._filter_waypoints()

                        imgui.separator()

                        if self.config.group_by_planet:
                            planet_waypoints = dict(self.filtered_waypoints_by_planet)
                            empty = 0 == len(planet_waypoints)

                            for (planet, waypoints) in planet_waypoints.items():
                                if imgui.tree_node(planet):
                                    for waypoint in waypoints:
                                        waypoint_panel(waypoint)
                                    imgui.tree_pop()
                        else:
                            waypoints = self.filtered_waypoints
                            empty = 0 == len(waypoints)

                            for waypoint in waypoints:
                                waypoint_panel(waypoint)

                        if empty:
                            imgui.text('No waypoints found')

    def on_start(self):
        self.watchdog.start()

    def on_stop(self):
        self.watchdog.stop()
        Config.save(MyConfig, CONFIG_FILE, self.config)
        with open(WAYPOINT_FILE, 'w') as wpf:
            json.dump(self.waypoints, wpf, default=lambda x: x.__dict__)

    def on_hide(self):
        self.config.start_minimized = True

    def on_show(self):
        self.config.start_minimized = False

    def _filter_waypoints(self):
        self.filtered_waypoints = list(filter(self._filter_waypoint, self.waypoints))
        self.filtered_waypoints_by_planet.clear()

        for waypoint in self.filtered_waypoints:
            self.filtered_waypoints_by_planet[waypoint.planet].append(waypoint)

    def _filter_waypoint(self, waypoint: Waypoint) -> bool:
        if self.config.waypoint_filter == '':
            return True

        r = partial_ratio(waypoint.text, self.config.waypoint_filter)
        LOGGER.debug(f'ratio({waypoint.text.lower()}, {self.config.waypoint_filter.lower()}) = {r}')
        return self.config.fuzzy_ratio <= r


def main():
    app = MyApp()
    app.run()


if __name__ == '__main__':
    main()
