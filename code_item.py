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

from vql_manager_core import *
from os import path
from difflib import Differ
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtGui import QBrush


class CodeItem(QTreeWidgetItem):
    """
    CodeItem class represents a .vql file with a single Denodo object
    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget
    Basically a bag for pieces of Denodo code
    """

    diff_engine = Differ()

    def __init__(self, parent, chapter_name, mode, code=None, compare_code=None, preceding=None):
        """
        CodeItem Class
        :param parent:
        :param chapter_name: the chapter name
        :param code: the code related to this denodo object
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
        self.difference = ''
        self.color = WHITE
        self.gui = GUI_SELECT
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
        self.pack(None)

    def set_compare_code(self, compare_code, mode):
        self.mode |= mode
        self.compare_code = compare_code
        self.compare()

    def compare(self):
        if self.code:
            if self.compare_code:
                if self.compare_code == self.code:
                    self.set_color(WHITE)
                else:
                    self.set_color(YELLOW)
                    self.difference = self.get_diff(self.code, self.compare_code)
            else:
                self.set_color(RED)
                self.difference = ''
        else:
            if self.compare_code:
                self.set_color(GREEN)
                self.difference = ''
            else:
                self.suicide()

    def get_diff(self, code, compare_code):
        former_code_split = (code + '\n').splitlines(True)
        next_code_split = (compare_code + '\n').splitlines(True)
        diff = list(self.diff_engine.compare(former_code_split, next_code_split))
        return ''.join(diff)

    def pack(self, color_filter):
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
        self.user_data['difference'] = self.difference
        self.user_data['denodo_folder'] = self.denodo_folder
        self.user_data['gui'] = self.gui
        self.user_data['class_type'] = self.class_type
        self.user_data['selected'] = self.is_selected()
        self.setData(0, Qt.UserRole, self.user_data)

    @staticmethod
    def unpack(item):
        item.user_data = item.data(0, Qt.UserRole)
        item.chapter_name = item.user_data['chapter_name']
        item.object_name = item.user_data['object_name']
        item.code = item.user_data['code']
        item.compare_code = item.user_data['compare_code']
        item.color = item.user_data['color']
        item.difference = item.user_data['difference']
        item.denodo_folder = item.user_data['denodo_folder']
        item.gui = item.user_data['gui']
        item.class_type = item.user_data['class_type']
        item.is_selected = item.user_data['selected']

    def set_gui(self, gui):
        self.gui = gui
        if gui == GUI_SELECT:
            if self.mode & COMP_REPO:
                self.mode -= COMP_REPO
            if self.mode & COMP_FILE:
                self.mode -= COMP_FILE
            self.set_compare_code('', 0)

    def suicide(self):
        self.parent().remove_child(self)

    def get_file_path(self, folder):
        """

        :param folder:
        :return:
        """
        file_name = path.join(folder, self.object_name.replace(' ', '_') + '.vql')
        return file_name

    def is_selected(self):
        """
        Is the object selected
        :return: Boolean
        :rtype: bool
        """
        if self.checkState(0) == CHECKED:
            return True
        else:
            return False

    def tree_reset(self):
        """
        Function for deleting/resetting this item
        :return: nothing
        """
        self.object_name = ''
        self.setText(0, '')
        self.code = ''
        self.compare_code = ''
        self.setData(0, Qt.UserRole, '')
        self.diff_engine = None

    def set_color(self, color):
        """
        Set the color
        :param color:
        :type color: QBrush
        :return:
        """
        self.color = color
        self.setForeground(0, color)

    @staticmethod
    def extract_denodo_folder_name_from_code(chapter_name, code):
        folder_path = ''
        if chapter_name == 'DATASOURCES':
            if code.find('DATASOURCE LDAP') > 0:
                return folder_path
        if chapter_name in ['I18N MAPS', 'DATABASE', 'DATABASE CONFIGURATION', 'TYPES']:
            return folder_path
        if chapter_name == 'FOLDERS':
            start = code.find('\'') + 2
            end = len(code) - 5
            folder_path = code[start:end]
        else:
            start = code.find('FOLDER = \'') + 11
            end = code.find('\'', start)
            folder_path = code[start:end]
        if folder_path:
            folder_path = folder_path.lower()
            return folder_path

    @staticmethod
    def extract_object_name_from_code(chapter_name, code):
        """
        Helper function for the 'parse' function
        The function searches for the Denodo object name to construct a unique file name in the repository
        Each chapter has its own way of extracting the object name

        Warning!!
        With newer versions of Denodo it should be checked if the structure they use is the same

        :param code: string with code relating to one object in Denodo
        :type code: str
        :param chapter_name: string with the name of the chapter it belongs to
        :type chapter_name: str
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
