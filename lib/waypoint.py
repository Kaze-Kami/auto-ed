# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""
import math
import uuid
from dataclasses import dataclass


@dataclass
class Waypoint:
    id: str
    name: str
    planet: str
    lat: float
    lon: float

    @property
    def text(self):
        return f'{self.name} ({self.planet})'

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Waypoint):
            return self.id == o.id
        return super().__eq__(o)

    @staticmethod
    def from_json(args):
        return Waypoint(**args)

    @staticmethod
    def from_position(name: str, planet: str, lat: float, long: float):
        id = str(uuid.uuid4())
        return Waypoint(id, name, planet, lat, long)


def radians(lat: float, lon: float):
    return math.radians(lat), math.radians(lon)


def calculate_bearing(position: tuple[float, float], target: Waypoint) -> float:
    """
    @param position: current position
    @param target: target waypoint
    @return: bearing towards p in °

    thanks @ https://mapscaping.com/how-to-calculate-bearing-between-two-coordinates/
    """
    # Convert latitude and longitude to radians
    lat1, lon1 = radians(*position)
    lat2, lon2 = radians(target.lat, target.lon)

    # Calculate the bearing
    bearing = math.atan2(
            math.sin(lon2 - lon1) * math.cos(lat2),
            math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    )

    # Convert the bearing to degrees
    bearing = math.degrees(bearing)

    # Make sure the bearing is positive
    bearing = (bearing + 360) % 360

    return bearing


def calculate_distance(position: tuple[float, float], target: Waypoint, planet_radius) -> float:
    """
    Calculate distance between to points of (lat, long) on surface of planet with given radius

    @return: distance on surface from position to target in meters

    thanks @ https://stackoverflow.com/a/27943/10330869
    """

    # Convert latitude and longitude to radians
    lat1, lon1 = radians(*position)
    lat2, lon2 = radians(target.lat, target.lon)

    d_lat, d_lon = lat2 - lat1, lon2 - lon1

    # sin(dLat / 2) ^ 2 + cos(lat1) * cos(lat2) * sin(dLon / 2) ^ 2
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c * planet_radius
