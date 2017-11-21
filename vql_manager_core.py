#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
VQL_Constants Class
Several shared objects in the VQL Manager app

file: vql_manager_core.py
Dependencies: PyQt5

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""

from PyQt5.QtCore import Qt, QObject, Q_FLAGS
from PyQt5.QtGui import QBrush, QColor


# class VqlConstants(QObject):
# convenience names for class constants
# checkbox option in the tree widgets
PART_STATE = Qt.PartiallyChecked
CHECKED = Qt.Checked
UNCHECKED = Qt.Unchecked

# Hint for the width of the tree wigets
PANE_WIDTH = 300

# # application modes en flags

# colors used
red = "#ff4444"
green = "#44ff44"
yellow = "#ffff44"
white = "#cccccc"

RED = QBrush(QColor(red))
GREEN = QBrush(QColor(green))
YELLOW = QBrush(QColor(yellow))
WHITE = QBrush(QColor(white))

# item flags for the all_chapters and selection tree widget items
ITEM_FLAG_ALL = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsTristate
ITEM_FLAG_SEL = Qt.ItemIsSelectable | Qt.ItemIsEnabled

# main chapter names as used in Denodo code
CHAPTER_NAMES = ['I18N MAPS', 'DATABASE', 'FOLDERS', 'LISTENERS JMS', 'DATASOURCES', 'WRAPPERS',
                 'STORED PROCEDURES', 'TYPES', 'MAPS', 'BASE VIEWS', 'VIEWS', 'ASSOCIATIONS',
                 'WEBSERVICES', 'WIDGETS', 'WEBCONTAINER WEB SERVICE DEPLOYMENTS',
                 'WEBCONTAINER WIDGET DEPLOYMENTS']

# the delimiter use to separate chapters into CodeItems
DELIMITER = "CREATE OR REPLACE"

# Start quote of the Denodo script
PROP_QUOTE = '# REQUIRES-PROPERTIES-FILE - # Do not remove this comment!\n#\n'


# app_state flags
class GuiType(QObject):
    GUI_NONE = 1 << 1                  # initial or reset mode
    GUI_SELECT = 1 << 2           # gui set to selection mode
    GUI_COMPARE = 1 << 3          # gui set to compare, with a base model and a compare model


class ModelState(QObject):
    BASE_FILE = 1 << 4        # indicate that the base model is a single file
    BASE_REPO = 1 << 5        # indicate that the base model is a repository (folder structure)
    COMP_FILE = 1 << 6        # indicate that the base model is a single file
    COMP_REPO = 1 << 7        # indicate that the base model is a repository (folder structure)
    BASE_LOADED = 1 << 8      # indicate that the base model is loaded
    COMP_LOADED = 1 << 9      # indicate that the compare model is loaded


class SourceType(QObject):
    FILE = 1 << 10
    REPO = 1 << 11

class ViewType:
    VQL_VIEW = 1 << 12
    DENODO_VIEW = 1 << 13



Q_FLAGS(GuiType)
Q_FLAGS(ModelState)
Q_FLAGS(SourceType)

GUI_NONE = GuiType.GUI_NONE
GUI_SELECT = GuiType.GUI_SELECT
GUI_COMPARE = GuiType.GUI_COMPARE

BASE_FILE = ModelState.BASE_FILE
BASE_REPO = ModelState.BASE_REPO
COMP_FILE = ModelState.COMP_FILE
COMP_REPO = ModelState.COMP_REPO
BASE_LOADED = ModelState.BASE_LOADED
COMP_LOADED = ModelState.COMP_LOADED

FILE = SourceType.FILE
REPO = SourceType.REPO

VQL_VIEW = ViewType.VQL_VIEW
DENODO_VIEW = ViewType.DENODO_VIEW


def show_mode(mode):
    """

    :param mode:
    :return:
    """
    gui_types = {GUI_NONE: 'GUI_NONE', GUI_SELECT: 'GUI_SELECT', GUI_COMPARE: 'GUI_COMPARE'}
    model_states = {BASE_FILE: 'BASE_FILE', BASE_REPO: 'BASE_REPO', COMP_FILE: 'COMP_FILE', COMP_REPO: 'COMP_REPO',
                    BASE_LOADED: 'BASE_LOADED', COMP_LOADED: 'COMP_LOADED'}
    source_types = {FILE: 'FILE', REPO: 'REPO'}

    mode_txt = list()

    for num, name in gui_types.items():
        if mode & num:
            mode_txt.append(name)

    for num, name in model_states.items():
        if mode & num:
            mode_txt.append(name)

    for num, name in source_types.items():
        if mode & num:
            mode_txt.append(name)

    return ' : '.join(mode_txt)


def get_reserved_words():
    with open('denodo_reserved_words.txt') as f:
        return [word.strip() for word in f.readlines()]


RESERVED_WORDS = get_reserved_words()
