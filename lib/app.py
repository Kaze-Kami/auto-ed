# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""

import json
import time
from collections import defaultdict

import imgui
from attrs import define
from essentials.gui.app import App, AppConfig
from essentials.gui.config import Config
from essentials.io.file import open_or_create
from essentials.utils.versioning import Version, check_version
from fuzzywuzzy.fuzz import partial_ratio
from prefixed import Float

from lib.ed import Status
from lib.filesystem import Watchdog
from lib.globals import *
from lib.ship_state import ShipState
from lib.util import find_first_available
from lib.waypoint import Waypoint, calculate_bearing, calculate_distance


@define
class UiState:
    automation: bool = True
    waypoint_manager: bool = True
    waypoints: bool = True


@define
class MyConfig(Config):
    start_minimized: bool = False
    floating: bool = False
    window_position: (float, float) = (100, 100)
    active: bool = True
    auto_fa: bool = True
    auto_da: bool = True
    auto_gear: bool = True
    auto_lights: bool = False
    auto_night_vision: bool = False
    waypoint_filter: str = ''
    fuzzy_ratio: float = DEFAULT_FUZZY_RATIO
    seconds_to_average: int = DEFAULT_SECONDS_TO_AVERAGE
    show_planet_names: bool = True
    group_by_planet: bool = True
    filter_current_planet: bool = True


class MyApp(App):
    def __init__(self):
        self.config: MyConfig = Config.load_or_defaults(MyConfig, CONFIG_FILE, backup_suffix='.backup_%Y%m%d')
        super().__init__(AppConfig(
                width=500,
                height=300,
                title='Auto-ED',
                icon_path='resources/icon-color.ico',
                start_minimized=self.config.start_minimized,
        ))

        # additional window setup
        self.window.position = self.config.window_position
        self.window.floating = self.config.floating
        self.window.background_color = (.1, .1, .1, 1.)

        self.watchdog = Watchdog(ed.BasePath, ed.Files.STATUS, self.on_status_update)

        self.state = ShipState()
        self.was_docked_or_landed = False
        self.last_focused_at = time.time()

        with open_or_create(VERSION_FILE, 'r', '0.0.0') as vf:
            self.current_version = Version.parse_version(vf.read())
        self.latest_version = check_version(self.current_version, VERSION_REF_URL)

        # ensure data dir exists
        os.makedirs(DATA_DIR, exist_ok=True)

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

        # eta related
        self._last_status_update: float or None = None
        self.recent_average_velocity: float or None = None

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
        if self.config.auto_lights:
            self.check_lights()
        if self.config.auto_night_vision:
            self.check_night_vision()

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

        self.state.lights = flags & Status.LIGHTS_ON
        self.state.night_vision = flags & Status.NIGHT_VISION

        self.has_position = flags & Status.HAS_LAT_LONG
        if self.has_position:
            last_position = self.position
            self.position = data['Latitude'], data['Longitude']
            self.heading = data['Heading']
            self.planet_radius = data['PlanetRadius']
            self.altitude = data['Altitude']
            planet_name = data['BodyName']

            if planet_name != self.planet_name:
                self.planet_name = planet_name
                self._filter_waypoints()

            # update eta tracking stats
            t1 = time.time()
            if (t0 := self._last_status_update) is not None:
                dt = t1 - t0
                dx = calculate_distance(self.position, last_position, self.planet_radius + self.altitude)
                v = dx / dt

                if self.recent_average_velocity is None:
                    self.recent_average_velocity = v
                else:
                    k = max(min(dt / self.config.seconds_to_average, 1.0), 0.0)
                    self.recent_average_velocity = self.recent_average_velocity * (1.0 - k) + v * k

            self._last_status_update = t1

        else:
            self.position = 0.0, 0.0
            self.heading = 0.0
            self.planet_radius = 0.0
            self.altitude = 0.0
            self.planet_name = ''

            # reset eta tracking stats
            self.recent_average_velocity = None
            self._last_status_update = None

    def check_flight_assist(self):
        if self.state.in_srv or self.state.docked_or_landed or self.state.fsd_active:
            return

        if self.state.flight_assist:
            LOGGER.debug('Disable Flight assist')
            win.press_key(KEY_FA, KEY_GLOBAL_MOD)

    def check_drive_assist(self):
        if not self.state.in_srv:
            return

        if self.state.drive_assist:
            LOGGER.debug('Disable Drive assist')
            win.press_key(KEY_DA, KEY_GLOBAL_MOD)

    def check_gear(self):
        if not self.state.gear:
            return

        if self.was_docked_or_landed and not self.state.docked_or_landed:
            LOGGER.debug('Retracting gear')
            self.was_docked_or_landed = False
            win.press_key(KEY_GEAR, KEY_GLOBAL_MOD)

    def check_lights(self):
        if self.state.lights:
            return

        # todo: not sure when one can toggle lights
        if not self.state.fsd_active:
            LOGGER.debug('Enable lights')
            win.press_key(KEY_LIGHTS, KEY_GLOBAL_MOD)

    def check_night_vision(self):
        if self.state.night_vision:
            return

        # todo: not sure when one can toggle night vision either
        if not self.state.fsd_active:
            LOGGER.debug('Enable lights')
            win.press_key(KEY_NIGHT_VISION, KEY_GLOBAL_MOD)

    def render(self):
        # --                      HELPERS                      -- #
        indent = 4.0
        red = (0.90, 0.49, 0.13)
        green = (0.18, 0.80, 0.44)
        gray = (0.58, 0.65, 0.65)

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

        def right_button(text: str, id: str = None) -> bool:
            text_width, _ = imgui.calc_text_size(text)
            item_width = text_width + BUTTON_PADDING
            imgui.same_line(imgui.get_window_content_region_max().x - item_width)
            if id is not None:
                text = f'{text}##{id}'
            r = imgui.button(text)
            return r

        def right_text(text: str):
            text_width, _ = imgui.calc_text_size(text)
            imgui.same_line(imgui.get_window_content_region_max().x - text_width)
            imgui.text(text)

        def waypoint_name(waypoint: Waypoint, show_planet_name: bool, prefix: str = ''):
            # name
            text = f'{prefix}{waypoint.name}'

            if show_planet_name:
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

            can_target = not self.has_position or self.planet_name == waypoint.planet

            if not can_target:
                imgui.push_style_color(imgui.COLOR_BUTTON, *gray)
                imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *gray)
                imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *gray)

            if imgui.button(f'Target##{waypoint.id}') and can_target:
                if is_active:
                    self.current_waypoint = None
                else:
                    self.current_waypoint = waypoint

            if not can_target:
                imgui.pop_style_color(3)
                if imgui.is_item_hovered(ImGuiHoveredFlags_DelayShort):
                    imgui.begin_tooltip()
                    imgui.text('Not on current planet')
                    imgui.end_tooltip()

            if is_active:
                imgui.pop_style_color()

            # name
            imgui.same_line()
            waypoint_name(waypoint, self.config.show_planet_names and not (self.config.group_by_planet or self.config.filter_current_planet))

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

        # --                      MAIN UI                      -- #

        # Main menu bar
        imgui.begin_menu_bar()
        if imgui.begin_menu('File'):
            # floating entry
            click, floating = imgui.menu_item('Floating', None, self.config.floating)
            if click:
                self.config.floating = self.window.floating = floating

            # exit entry
            click, _ = imgui.menu_item('Exit', None)
            if click:
                self.exit()

            imgui.end_menu()
        imgui.end_menu_bar()

        # status button
        yes_no(win.find_window(WINDOW_NAME), 'Elite Running')

        # version info
        if self.latest_version is not None:
            imgui.push_style_color(imgui.COLOR_TEXT, *red)
            right_text('New version available!')
            imgui.pop_style_color()
        else:
            right_text(f'Version {self.current_version} ')

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
                imgui.same_line()
                self.config.auto_lights = colored_switch('Lights', self.config.auto_lights)
                imgui.same_line()
                self.config.auto_night_vision = colored_switch('Night Vision', self.config.auto_night_vision)
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
                yes_no(self.state.lights, 'Lights', 'On', 'Off')
                yes_no(self.state.night_vision, 'Night vision', 'On', 'Off')

        # waypoint manager
        with collapsing_header('Waypoint Manager') as open:
            if open:
                if self.current_waypoint is not None:
                    bearing_text = '[Unavailable]'
                    distance_text = '[Unavailable]'
                    if self.has_position and self.current_waypoint.planet == self.planet_name:
                        bearing = calculate_bearing(self.position, self.current_waypoint)

                        alt_distance = calculate_distance(self.position, self.current_waypoint.position, self.planet_radius + self.altitude)
                        surf_distance = calculate_distance(self.position, self.current_waypoint.position, self.planet_radius)

                        eta = 'N/A'
                        if (v := self.recent_average_velocity) is not None and 0.0 < v:
                            eta = f'{alt_distance / v:.0f}s'

                        bearing_text = f'{bearing:.1f}° (ETA: {eta})'
                        distance_text = f'{Float(alt_distance):.2h}m ({Float(surf_distance):.2h}m on surface)'

                    waypoint_name(self.current_waypoint, self.config.show_planet_names and not self.config.filter_current_planet, prefix='Target: ')

                    if self.current_waypoint is not None:
                        imgui.same_line()
                        if right_button('Unset'):
                            self.current_waypoint = None

                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Bearing: {bearing_text}')
                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Distance: {distance_text}')
                else:
                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Target: [No Target]')

                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Bearing: [No Target]')

                    imgui.align_text_to_frame_padding()
                    imgui.text(f'Distance: [No Target]')

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
                            if imgui.button('Reset##fuzzy_ratio'):
                                ratio_change = True
                                self.config.fuzzy_ratio = DEFAULT_FUZZY_RATIO

                            seconds_change, self.config.seconds_to_average = imgui.input_int('Average velocity over (s)', self.config.seconds_to_average, 1)
                            imgui.same_line(0, 30)
                            if imgui.button('Reset##seconds_to_average'):
                                seconds_change = True
                                self.config.seconds_to_average = DEFAULT_SECONDS_TO_AVERAGE

                            if seconds_change and self.config.seconds_to_average < 1:
                                self.config.seconds_to_average = 1

                            planet_change, self.config.filter_current_planet = imgui.checkbox('Filter current planet', self.config.filter_current_planet)

                            _, self.config.show_planet_names = imgui.checkbox('Show planet names', self.config.show_planet_names)

                            if not self.config.filter_current_planet:
                                _, self.config.group_by_planet = imgui.checkbox('Group by planet', self.config.group_by_planet)

                            change |= ratio_change | planet_change | seconds_change
                            imgui.end_popup()

                        if change:
                            self._filter_waypoints()

                        imgui.separator()

                        if self.config.filter_current_planet or not self.config.group_by_planet:
                            waypoints = sorted(self.filtered_waypoints, key=lambda x: x.name)
                            empty = 0 == len(waypoints)

                            for waypoint in waypoints:
                                waypoint_panel(waypoint)
                        else:
                            planet_waypoints = dict(self.filtered_waypoints_by_planet)
                            empty = 0 == len(planet_waypoints)

                            for planet in sorted(planet_waypoints):
                                if imgui.tree_node(planet):
                                    for waypoint in sorted(planet_waypoints[planet], key=lambda x: x.name):
                                        waypoint_panel(waypoint)
                                    imgui.tree_pop()

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

    def on_move(self, pos: (int, int)):
        self.config.window_position = pos

    def get_additional_imgui_flags(self) -> int:
        return imgui.WINDOW_MENU_BAR

    def _filter_waypoints(self):
        self.filtered_waypoints = list(filter(self._filter_waypoint, self.waypoints))
        self.filtered_waypoints_by_planet.clear()

        for waypoint in self.filtered_waypoints:
            self.filtered_waypoints_by_planet[waypoint.planet].append(waypoint)

    def _filter_waypoint(self, waypoint: Waypoint) -> bool:
        if self.config.filter_current_planet and self.has_position:
            if self.planet_name != waypoint.planet:
                return False

        if self.config.waypoint_filter == '':
            return True

        r = partial_ratio(self.config.waypoint_filter.lower(), f'{waypoint.name} {waypoint.planet}'.lower())
        return self.config.fuzzy_ratio <= r
