#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Denodo VQL Manager

This program shows GUI
to split, select, combine
and compare Denodo .vql files

Dependencies: PyQt5, sys, qdarkstyle and vqlmanager

file: vqlmanagerwindow.py
Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""
__author__ = 'andretreebus@hotmail.com (Andre Treebus)'

# standard library
from sys import exit, argv, version_info
# other libs
from PyQt5.QtWidgets import QApplication
from vqlmanager.vqlmanagerwindow import VQLManagerWindow
from vqlmanager.vql_manager_core import logger
import qdarkstyle

app = None




def main():
    """Main entry point for the application

    Boilerplate python code to start and end the application and allows it to be in a module or library
    :return:
    """
    logger.info("Entering main")
    global app

    if version_info < (3, 6):
        VQLManagerWindow.message_to_user('You need at least Python version 3.6 to run this application.')
        return

    app = QApplication(argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = VQLManagerWindow()
    window.show()
    exit(app.exec())


if __name__ == '__main__':
    main()
