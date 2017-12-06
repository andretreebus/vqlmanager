#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
VQL_Constants and globals
Several shared objects in the VQL Manager app

file: vql_manager_core.py
Dependencies: PyQt5, pathlib, vqlmanager, logging

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""
__author__ = "andretreebus@hotmail.com (Andre Treebus)"

# standard library
import logging
from pathlib import Path
from typing import Iterator, List, Tuple, Union, Sized, Tuple, Generator
# other libs
from PyQt5.QtCore import Qt, QObject, Q_FLAGS
from PyQt5.QtGui import QBrush, QColor
from vqlmanager.diff_match_patch import diff_match_patch

# registry data
COMPANY = "www.erasmusmc.nl"
APPLICATION_NAME = "VQL Manager"

# setup logger
LOGGING_LEVEL = logging.DEBUG
LOGGING_FORMAT = "%(levelname)s %(asctime)s - %(message)s "
script_path = Path(__file__).parent.resolve()
log_filename = script_path / "log" / "vql_manager.log"
log_dir = log_filename.parent
if not log_dir.is_dir():
    try:
        log_dir.mkdir()
    except (OSError, IOError) as e:
        print("Could not create log directory: " + str(log_filename.parent))

if not log_filename.is_file():
    try:
        log_filename.touch()
    except (OSError, IOError) as e:
        print("Could not create logfile: " + str(log_filename))

logging.basicConfig(filename=log_filename, level=LOGGING_LEVEL, format=LOGGING_FORMAT, filemode="w")
logger = logging.getLogger("vql_manager")

# class VqlConstants(QObject):
# convenience names for class constants
# checkbox option in the tree widgets
PART_STATE = Qt.PartiallyChecked
CHECKED = Qt.Checked
UNCHECKED = Qt.Unchecked

# Hint for the width of the tree widgets
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
ITEM_FLAG_ALL = Qt.ItemIsEnabled
ITEM_FLAG_CHAPTER = Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsTristate
ITEM_FLAG_CODE_ITEM = Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
ITEM_FLAG_SEL = Qt.ItemIsSelectable | Qt.ItemIsEnabled


LOG_FILE_NAME = "part.log"

# main chapter names as used in Denodo code
CHAPTER_NAMES = ["I18N MAPS", "DATABASE", "FOLDERS", "LISTENERS JMS", "DATASOURCES", "WRAPPERS",
                 "STORED PROCEDURES", "TYPES", "MAPS", "BASE VIEWS", "VIEWS", "ASSOCIATIONS",
                 "WEBSERVICES", "WIDGETS", "WEBCONTAINER WEB SERVICE DEPLOYMENTS",
                 "WEBCONTAINER WIDGET DEPLOYMENTS"]

# the delimiter use to separate chapters into CodeItems
DELIMITER = "CREATE OR REPLACE"

# Start quote of the Denodo script
PROP_QUOTE = "# REQUIRES-PROPERTIES-FILE - # Do not remove this comment!\n#\n"


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


# class SourceType(QObject):
#     FILE = 1 << 10
#     REPO = 1 << 11

class SourceType(QObject):
    FILE = ModelState.BASE_FILE | ModelState.COMP_FILE
    REPO = ModelState.BASE_REPO | ModelState.COMP_REPO


class ViewType(QObject):
    VQL_VIEW = 1 << 12
    DENODO_VIEW = 1 << 13


class CodeView(QObject):
    ORIGINAL_CODE = 1 << 14
    COMPARE_CODE = 1 << 15
    DIFF_CODE = 1 << 16


Q_FLAGS(GuiType)
Q_FLAGS(ModelState)
Q_FLAGS(SourceType)
Q_FLAGS(ViewType)
Q_FLAGS(CodeView)

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

ORIGINAL_CODE = CodeView.ORIGINAL_CODE
COMPARE_CODE = CodeView.COMPARE_CODE
DIFF_CODE = CodeView.DIFF_CODE


def translate_colors(item_color: Union[str, QBrush], to_text=True)->Union[str, QBrush]:
    """
    Function for translating item QBrush objects for strings
    This is needed because the set function does not accept unhashable items
    :param item_color: the object to be translated
    :type item_color: str or QBrush
    :param to_text: indicator for the direction of the tranlation
    :type to_text: bool
    :return: Translated value
    :rtype: QBrush or str
    """
    color = None
    if to_text:
        if item_color == RED:
            color = red
        elif item_color == GREEN:
            color = green
        elif item_color == YELLOW:
            color = yellow
        elif item_color == WHITE:
            color = white
    else:
        if item_color == red:
            color = RED
        elif item_color == green:
            color = GREEN
        elif item_color == yellow:
            color = YELLOW
        elif item_color == white:
            color = WHITE
    return color


def show_mode(mode: int)->str:
    """Returns debug info string to logger.

    :param mode: the mode to show
    :type mode: int
    :return: a human readable string with flags
    :rtype: str
    """
    gui_types = {GUI_NONE: "GUI_NONE", GUI_SELECT: "GUI_SELECT", GUI_COMPARE: "GUI_COMPARE"}
    model_states = {BASE_FILE: "BASE_FILE", BASE_REPO: "BASE_REPO", COMP_FILE: "COMP_FILE", COMP_REPO: "COMP_REPO",
                    BASE_LOADED: "BASE_LOADED", COMP_LOADED: "COMP_LOADED"}
    source_types = {FILE: "FILE", REPO: "REPO"}

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

    return " : ".join(mode_txt)


def get_reserved_words()->Iterator[Sized]:
    """Returns a list (Iterator) over the Denodo reserved words.


    :return: the list as Iterator
    :rtype: Iterator[Sized]
    """
    words = ["ADD", "AS", "ANY", "OPT", "OR", "CREATE", "VIEW", "NULL", "ALTER", "NOT", "FROM", "AND", "SELECT",
             "WHEN", "JOIN", "IS", "ON", "LEFT", "CASE", "TABLE", "WHERE", "DEFAULT", "OFF", "JDBC", "INNER", "OF",
             "ZERO", "NOS", "UNION", "DF", "DISTINCT", "ASC", "FULL", "FALSE", "DESC", "BASE", "DATABASE", "TRUE",
             "ALL", "CONTEXT", "CONNECT", "LDAP", "WITH", "SWAP", "ARN", "BOTH", "CALL", "CROSS", "CURRENT_DATE",
             "CURRENT_TIMESTAMP", "CUSTOM", "DROP", "EXISTS", "FETCH", "FLATTEN", "GRANT", "GROUP BY", "GS", "HASH",
             "HAVING", "HTML", "IF", "INTERSECT", "INTO", "LEADING", "LIMIT", "MERGE", "MINUS", "MY", "NATURAL",
             "NESTED", "OBL", "ODBC", "OFFSET", "ONE", "ORDER BY", "ORDERED", "PRIVILEGES", "READ", "REVERSEORDER",
             "REVOKE", "RIGHT", "ROW", "TO", "TRACE", "TRAILING", "USER", "USING", "WRITE", "WS"]

    words.append(DELIMITER)
    words.extend(CHAPTER_NAMES)
    reserved_words = reversed(sorted(words, key=len))
    return reserved_words


RECENT_FILES = "recent_file_list"
RECENT_REPOSITORIES = "recent_repositories_list"
MAX_RECENT_FILES = 8

# <link rel="stylesheet" type="text/css" href="mystyle.css">


def doc_template(object_name: str, body: str)->str:
    """
    Returns a html page
    :param object_name: name of the object
    :param body: body of the page
    :return: the page
    """
    doc = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>""" + object_name + """</title>
    <meta name="description" content="Denodo code part">
  </head>
  <body>""" + body + """</body>
</html>
"""
    return doc


about_text = """
VQL Manager was created by Erasmus MC Rotterdam The Netherlands 2017.
This application is open source software.
Questions and remarks should be sent to: andretreebus@hotmail.com
"""

diff_engine = diff_match_patch()
diff_engine.Diff_Timeout = 2
diff_engine.Match_Threshold = 0.0
diff_engine.Patch_DeleteThreshold = 0.0
diff_engine.Match_MaxBits = 0