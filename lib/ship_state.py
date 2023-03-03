# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""


class ShipState:
    def __init__(self):
        self.processed = False
        self.flight_assist = False
        self.drive_assist = False
        self.gear = False

        self.in_srv = False
        self.fsd_active = False
        self.docked_or_landed = False

        self.lights = False
        self.night_vision = False
