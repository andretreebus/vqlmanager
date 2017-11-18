#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Denodo VQL Manager

This program shows GUI
to split, select, combine
and compare Denodo .vql files

Dependencies: shutil collections PyQt5 qdarkstyle and vqlmanagerwindow.py

file: vqlmanagerwindow.py
Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""

from sys import exit, argv
from PyQt5.QtWidgets import QApplication
from vqlmanagerwindow import VQLManagerWindow
import qdarkstyle

app = None


def main():
    # Boilerplate python code to start and end the application
    # and allows it to be in a module or library
    global app

    app = QApplication(argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = VQLManagerWindow()
    window.show()
    exit(app.exec())


if __name__ == '__main__':
    # Boilerplate python code to start and end the application
    # and allows it to be in a module or library
    main()
