# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""

from typing import Callable


def find_first_available(pattern: str, in_use_predicate: Callable[[str], bool]) -> str:
    """
    Finds first available integer where in_use_predicate(pattern % number) == false
    """
    i = 0
    while in_use_predicate(p := pattern % i):
        i += 1
    return p
