#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
CodeItem Class
Class representing the code pieces
related to the construction of
one Denodo object

The class holds data of
Denodo object names
and their vql code

This class is inherited from QTreeWidgetItem
for showing itself in a QTreeWidget

file: code_item.py
Dependencies: os PyQt5 vql_manager_core.py

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""
__author__ = 'andretreebus@hotmail.com (Andre Treebus)'

# standard library
from pathlib import Path
# other libs
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtGui import QBrush
from vqlmanager.vql_manager_core import *


class CodeItem(QTreeWidgetItem):
    """CodeItem class represents a .vql file with a single Denodo object.

    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget.
    Basically a bag for pieces of Denodo code.
    """
    def __init__(self, parent: QTreeWidgetItem, chapter_name: str, mode: int,
                 code=None, compare_code=None, preceding=None):
        """CodeItem Class constructor.

        :param parent: The object owning this object
        :type parent: Chapter
        :param chapter_name: the chapter name
        :type chapter_name: str
        :param mode: the mode flag
        :type mode: int
        :param code: optional: the code related to this denodo object
        ::type code: str
        :param code: optional: the other code related to this denodo object for comparisons
        ::type code: str
        :param preceding: the CodeItem after which this code item is placed in the tree
        :type preceding: CodeItem
        """

        if preceding:
            super(CodeItem, self).__init__(parent, preceding, 0)
        else:
            super(CodeItem, self).__init__(parent)
        self.user_data = dict()
        self.setCheckState(0, CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(ITEM_FLAG_CODE_ITEM)  # from parent
        self.class_type = CodeItem
        self.chapter_name = chapter_name
        self.mode = mode
        self.code = code
        self.compare_code = compare_code
        self.object_name = ''
        self.denodo_folder = ''
        self.color = WHITE
        self.set_color(WHITE)
        self.gui = GUI_SELECT
        self.dependencies = list()
        self.dependees = list()
        self.compare_dependencies = list()
        self.compare_dependees = list()

        if code:
            self.object_name = self.extract_object_name_from_code(self.chapter_name, self.code)
            self.denodo_folder = self.extract_denodo_folder_name_from_code(self.chapter_name, self.code)

        if compare_code:
            self.object_name = self.extract_object_name_from_code(self.chapter_name, self.compare_code)
            self.denodo_folder = self.extract_denodo_folder_name_from_code(self.chapter_name, self.compare_code)
            self.set_compare_code(compare_code, mode)

        if self.object_name:
            self.setText(0, self.object_name)

        if mode & (COMP_FILE | COMP_REPO):
            self.compare()
        self.pack(WHITE)
        logger.debug(f">>>> CodeItem: {self.object_name if self.object_name else '_'} created.")

    def set_compare_code(self, compare_code: str, mode: int):
        """Setter for the compare mode and code.

        :param compare_code: the other code
        :type compare_code: str
        :param mode: new mode
        :type mode: int
        :return: None
        :rtype: None
        """
        self.mode |= mode
        self.compare_code = compare_code
        self.compare()

    def compare(self):
        """Compare the code and sets color to the item itself.

        White = unchanged; Red = lost; Green = new; Yellow = changed
        :return: None
        :rtype: None
        """
        if self.code:
            if self.compare_code:
                if self.compare_code == self.code:
                    self.set_color(WHITE)
                else:
                    self.set_color(YELLOW)
            else:
                if self.mode & GUI_COMPARE:
                    self.set_color(RED)
                else:
                    self.set_color(RED) if self.dependees else self.set_color(WHITE)
        else:
            if self.compare_code:
                self.set_color(GREEN)
            else:
                # code item with identity crisis
                self.suicide()

    @staticmethod
    def get_diff(code: str, compare_code: str)->str:
        """Supplies the code edit widget with html for the comparison.

        The main intel of this function is supplied by the global instance of the diff_match_patch.py engine
        maintained on Google. Here the engine is used on the two code pieces and a patch is calculated
        the patch is again inserted in the prettyHtml function of the engine and modded a bit
        The colors are similar to the usage in this tool
        to get new code (compare_code) from old code (code), remove red, add green

        :param code: the original code
        :type code: str
        :param compare_code: the new code
        :type compare_code: str
        :return: html representation of teh difference
        :rtype: str
        """
        def format_code(_code: str)->str:
            """
            Formats a code piece as html
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            _code = _code.replace('<br>', '<br />\n')
            _code = _code.replace('&para;', '')
            _code = _code.replace('    ', ' &nbsp; &nbsp; &nbsp; &nbsp; ')
            return _code

        def format_code2(_code: str)->str:
            """
            Formats a code piece as html
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            _code = _code.replace('\n', '<br />\n')
            _code = _code.replace('    ', ' &nbsp; &nbsp; &nbsp; &nbsp; ')
            return _code

        def set_green(_code: str)->str:
            """
            Formats a code piece as html to set it green
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            return '<span>' + new_diff_ins_indicator + _code + '</ins></span>'

        def set_red(_code: str)->str:
            """
            Formats a code piece as html to set it red
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            return '<span>' + new_diff_del_indicator + _code + '</del></span>'

        diff_ins_indicator = '<ins style="background:#e6ffe6;">'
        diff_del_indicator = '<del style="background:#ffe6e6;">'
        new_diff_ins_indicator = '<ins style="color:' + green + ';">'
        new_diff_del_indicator = '<del style="color:' + red + ';">'
        diff_html = ''
        if code:
            if compare_code:
                diff = diff_engine.diff_main(code, compare_code)
                diff_html = format_code(diff_engine.diff_prettyHtml(diff))
                diff_html = diff_html.replace(diff_ins_indicator, new_diff_ins_indicator)
                diff_html = diff_html.replace(diff_del_indicator, new_diff_del_indicator)
            else:
                diff_html = format_code2(set_red(code))
        else:
            if compare_code:
                diff_html = format_code2(set_green(compare_code))

        return diff_html

    def pack(self, color_filter: QBrush):
        """Packs and filters this code item object.

        Used before it gets cloned.
        The clone function only supports QTreeWidgetItem data,
        so we survive in the standard data(Qt.UserRole) in a dictionary.

        :param color_filter: The color that is selected
        :type color_filter: QBrush
        :return: None
        :rtype: None
        """
        if color_filter:
            if not self.color == color_filter:
                self.setHidden(True)
            else:
                self.setHidden(False)
        else:
            self.setHidden(False)

        self.user_data['chapter_name'] = self.chapter_name
        self.user_data['object_name'] = self.object_name
        self.user_data['code'] = self.code
        self.user_data['compare_code'] = self.compare_code
        self.user_data['color'] = self.color
        self.user_data['denodo_folder'] = self.denodo_folder
        self.user_data['gui'] = self.gui
        self.user_data['class_type'] = self.class_type
        self.user_data['selected'] = self.is_selected()
        self.user_data['hidden'] = self.isHidden()
        self.setData(0, Qt.UserRole, self.user_data)

    @staticmethod
    def unpack(item: QTreeWidgetItem):
        """Unpacks and filters this code item.

        Used after it has been cloned and packed.
        The clone function only supports QTreeWidgetItem data,
        so we survive in the standard data member data.(Qt.UserRole)
        in a dictionary. This is a static member to unpack
        the resulting QTreeWidgetItem after cloning.

        :param item: item to be unpacked
        :type item: QTreeWidgetItem
        :return: None
        :rtype: None
        """

        item.user_data = item.data(0, Qt.UserRole)
        item.chapter_name = item.user_data['chapter_name']
        item.object_name = item.user_data['object_name']
        item.code = item.user_data['code']
        item.compare_code = item.user_data['compare_code']
        item.color = item.user_data['color']
        item.denodo_folder = item.user_data['denodo_folder']
        item.gui = item.user_data['gui']
        item.class_type = item.user_data['class_type']
        item.is_selected = item.user_data['selected']
        item.setHidden(item.user_data['hidden'])

    def set_gui(self, gui: int):
        """Sets the gui type flag.

        This function also resets the compare mode if it was there.

        :param gui: mode flag
        :type gui: int
        :return: None
        :rtype: None
        """

        self.gui = gui
        if gui == GUI_SELECT:
            if self.mode & COMP_REPO:
                self.mode -= COMP_REPO
            if self.mode & COMP_FILE:
                self.mode -= COMP_FILE
            self.set_compare_code('', self.mode | GUI_SELECT)

    def suicide(self):
        """Asks dad to shoot you.

        Item gets pruned from the tree.
        :return: None
        :rtype: None
        """
        self.parent().remove_child(self)

    def get_file_path(self, folder: Path)->Path:
        """Get the file path for this code item.

        This function changes and slash, forward and backward into an underscore
        Warning: this can potentially be dangerous if two uniquely named objects
         turn out to have the same name after turning slashes to underscores.

        :param folder: the folder in which code item resides
        :type folder: Path
        :return: Path
        """

        file_name = folder / (self.object_name.replace('/', '_').replace('\\', '_') + '.vql')
        return file_name

    def is_selected(self)->bool:
        """Is the object selected.

        :return: Boolean
        :rtype: bool
        """
        if self.checkState(0) == CHECKED:
            return True
        else:
            return False

    def set_color(self, color: QBrush):
        """Set the color.

        :param color:
        :type color: QBrush
        :return: None
        :rtype: None
        """

        self.color = color
        self.setForeground(0, color)

    def remove_compare(self):
        """Function reverts the loading of compare code.

        :return: None
        :rtype: None
        """

        if self.compare_code:
            if not self.code:
                self.suicide()
        if self.code:
            self.set_gui(GUI_SELECT)
            self.set_color(WHITE) if self.dependees else self.set_color(RED)
            if self.compare_code:
                self.denodo_folder = self.extract_denodo_folder_name_from_code(self.chapter_name, self.code)

    @staticmethod
    def extract_denodo_folder_name_from_code(chapter_name: str, code: str)->Union[Path, None]:
        """Extracts the denodo folder name from code.

        :param chapter_name: Type of denodo object
        :type chapter_name: str
        :param code: the code to create the object
        :type code: str
        :return: The denodo path
        :rtype: Union[Path, None]
        """
        if chapter_name == 'DATASOURCES' and code.find('DATASOURCE LDAP') > -1:
                folder_path = ''
        elif chapter_name in ['I18N MAPS', 'DATABASE', 'DATABASE CONFIGURATION', 'TYPES']:
            folder_path = ''
        elif chapter_name == 'FOLDERS':
            start = code.find('\'') + 2
            end = len(code) - 5
            folder_path = code[start:end]
        else:
            start = code.find('FOLDER = \'') + 11
            end = code.find('\'', start)
            folder_path = code[start:end]

        if folder_path:
            folder_path = Path(folder_path.lower())
        else:
            folder_path = None
        return folder_path

    @staticmethod
    def extract_object_name_from_code(chapter_name: str, code: str)->str:
        """Searches for the Denodo object name.

        Helper function for the 'parse' function
        The function constructs a unique object name in its code
        Each chapter has its own way of extracting the object name

        Warning: With newer versions of Denodo it should be checked if the structure they use is the same

        :param chapter_name: string with the name of the chapter it belongs to
        :type chapter_name: str
        :param code: string with code relating to one object in Denodo
        :type code: str
        :return: string with the filename
        :rtype: str
        """

        def get_last_word(line):
            """
            Helper function for the extract_filename function
            :param line: string, one line of code (the first line)
            :type line: str
            :return: string with the last word on the line
            :rtype: str
            """
            line_reversed = line.strip()[::-1]
            last_space = line_reversed.find(' ')
            last_word = line_reversed[0:last_space][::-1]
            return last_word.strip()

        object_name = ''

        # Object names are on the first line of the code item
        first_line = code[0:code.find("\n")]

        if chapter_name == 'I18N MAPS':
            object_name = get_last_word(first_line[0:-2])
        elif chapter_name == 'DATABASE':
            object_name = first_line.split()[4]
        elif chapter_name == 'FOLDERS':
            object_name = first_line[27:-3]
        elif chapter_name == 'LISTENERS JMS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'DATASOURCES':
            object_name = get_last_word(first_line)
        elif chapter_name == 'WRAPPERS':
            object_name = get_last_word(first_line)
        elif chapter_name == 'STORED PROCEDURES':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'TYPES':
            object_name = first_line.split()[4]
        elif chapter_name == 'MAPS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'BASE VIEWS':
            object_name = first_line.split()[4]
        elif chapter_name == 'VIEWS':
            split = first_line.split(' ')
            if split[3] == 'INTERFACE':
                object_name = split[5]
            else:
                object_name = split[4]
        elif chapter_name == 'ASSOCIATIONS':
            object_name = first_line.split()[4]
        elif chapter_name == 'WEBSERVICES':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WIDGETS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WEBCONTAINER WEB SERVICE DEPLOYMENTS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WEBCONTAINER WIDGET DEPLOYMENTS':
            pass  # Todo: we don't use these kind of objects in Denodo

        return object_name
