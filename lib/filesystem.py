# -*- coding: utf-8 -*-

"""

@author Kami-Kaze
"""
import io
import os
from typing import Callable

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


class Handler(PatternMatchingEventHandler):
    def __init__(self, path: str, file: str, callback: Callable[[bytes], None], ignore_empty: bool = True):
        super().__init__({file})
        self.path = os.path.join(path, file)
        self.ignore_empty = ignore_empty
        self.callback = callback
        self.file: io.FileIO = None

    def on_modified(self, *_):
        self.file.seek(0)
        raw_json = self.file.read()
        if not raw_json and self.ignore_empty:
            return

        self.callback(raw_json)

    def open(self):
        self.file = open(self.path)
        self.on_modified()

    def close(self):
        self.file.close()


class Watchdog:
    def __init__(self, path: str, file: str, on_change: Callable[[bytes], None], ignore_empty: bool = True):
        self.observer = Observer()
        self.handler = Handler(path, file, on_change, ignore_empty)
        self.observer.schedule(self.handler, path, recursive=False)

    def start(self):
        self.handler.open()
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.handler.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
