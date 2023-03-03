# -*- coding: utf-8 -*-

"""
Simple tool to automatically disable Flight-Assist
in Elite: Dangerous -- at least that's what it used to be

Reads the status.json and if disables FA if necessary

@author Kami-Kaze
"""

from lib.app import MyApp


def main():
    app = MyApp()
    app.run()


if __name__ == '__main__':
    main()
