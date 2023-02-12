# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""
import os
from enum import IntFlag


def _bit(pos: int) -> int:
    return 1 << pos


class Status(IntFlag):
    """
    Flags used in status.json
    Each flag is indicated by the bit value in the
    'Flags' field of the status json at given position
    """
    DOCKED = _bit(0)
    LANDED = _bit(1)
    GEAR_DOWN = _bit(2)
    SHIELDS_UP = _bit(3)
    SUPER_CRUISE = _bit(4)
    FLIGHT_ASSIST_OFF = _bit(5)
    HARDPOINTS_DEPLOYED = _bit(6)
    IN_WING = _bit(7)
    LIGHTS_ON = _bit(8)
    CARGO_SCOOP_DEPLOYED = _bit(9)
    SILENT_RUNNING = _bit(10)
    SCOOPING_FUEL = _bit(11)
    SRV_HAND_BREAK_ON = _bit(12)
    SRV_USING_TURRET_VIEW = _bit(13)
    SRV_CLOSE_TO_SHIP = _bit(14)
    SRV_DRIVE_ASSIST = _bit(15)
    FSD_MASS_LOCKED = _bit(16)
    FSD_CHARGING = _bit(17)
    FSD_COOLDOWN = _bit(18)
    LOW_FUEL = _bit(19)
    OVER_HEATING = _bit(20)
    HAS_LAT_LONG = _bit(21)
    IS_IN_DANGER = _bit(22)
    BEING_INTERDICTED = _bit(23)
    IN_MAIN_SHIP = _bit(24)
    IN_FIGHTER = _bit(25)
    IN_SRV = _bit(26)
    HUD_IN_ANALYSIS_MODE = _bit(27)
    NIGHT_VISION = _bit(28)
    ALTITUDE_FROM_AVERAGE_RADIUS = _bit(29)
    FSD_JUMP = _bit(30)
    SRV_HIGH_BEAM = _bit(31)


# noinspection SpellCheckingInspection
class Files:
    STATUS = "Status.json"
    SHIP_YARD = "Shipjard.json"
    SHIP_LOCKER = "ShipLocker.json"
    OUTFITTING = "Outfittin.json"
    NAV_ROUTE = "NavRoute.json"
    MODULE_INFO = "ModulesInfo.json"
    MARKET = "Market.json"
    CARGO = "Cargo.json"
    BACKPACK = "Backpack.json"


BasePath = os.path.join(os.getenv('USERPROFILE'), r'Saved Games\Frontier Developments\Elite Dangerous')
WindowName = "Elite - Dangerous (CLIENT)"
