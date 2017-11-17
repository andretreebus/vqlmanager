from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor


class VQL_Constants(object):
    # convenience names for class constants
    # checkbox option in the tree widgets
    PART_STATE = Qt.PartiallyChecked
    CHECKED = Qt.Checked
    UNCHECKED = Qt.Unchecked

    # Hint for the width of the tree wigets
    PANE_WIDTH = 300

    # application modes
    # modes
    SELECT = 1 << 1
    COMPARE = 1 << 2
    BASE_MODEL_FILE = 1 << 3
    BASE_MODEL_REPO = 1 << 4
    COMP_MODEL_FILE = 1 << 5
    COMP_MODEL_REPO = 1 << 6
    BASE_MODEL_LOADED = 1 << 7
    COMP_MODEL_LOADED = 1 << 8

    # colors used
    RED = QBrush(QColor("#ff4444"))
    GREEN = QBrush(QColor("#44ff44"))
    YELLOW = QBrush(QColor("#ffff44"))
    WHITE = QBrush(QColor("#cccccc"))

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

    # Width hint on screen
    PANE_WIDTH = 300

    # Start quote of the Denodo script
    PROP_QUOTE = '# REQUIRES-PROPERTIES-FILE - # Do not remove this comment!\n#\n'
