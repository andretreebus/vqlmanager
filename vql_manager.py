#!/usr/bin/python3
# -*- coding: utf-8 -*-

#####################################################
# Denodo VQL Code splitter
# Andre Treebus
#
#####################################################
# Installation:
# Install the needed libraries with pip or with installer
# required libs:
# python3 pip3 install shutil collections PyQt5 qdarkstyle
#

from sys import exit, argv
from PyQt5.QtWidgets import QApplication
from vqlmanagerwindow import VQLManagerWindow
import qdarkstyle


if __name__ == "__main__":
    # Boilerplate python code to start and end the application
    # and allows it to be in a module or library

    app = QApplication(argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = VQLManagerWindow()
    window.show()
    exit(app.exec_())
