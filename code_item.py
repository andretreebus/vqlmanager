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

# from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtGui import QBrush


class CodeItem(QTreeWidgetItem):
    """
    CodeItem class represents a .vql file with a single Denodo object
    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget
    Basically a bag for pieces of Denodo code
    """

    diff_engine = Differ()

    def __init__(self, parent, chapter_name, code=None, compare_code=None):
        """
        CodeItem Class
        :param parent:
        :param chapter_name: the chapter name
        :param code: the code related to this denodo object
        """

        super(CodeItem, self).__init__(parent)
        self.user_data = dict()
        self.setCheckState(0, CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(ITEM_FLAG_ALL)

        self.chapter_name = chapter_name
        # self.mode = mode
        self.code = code
        self.compare_code = ''
        self.object_name = ''
        self.denodo_folder = ''
        self.diff_engine = None
        if code:
            self.object_name = self.extract_object_name_from_code(chapter_name, code)
            self.denodo_folder = self.extract_denodo_folder_name_from_code(chapter_name, code)
        elif compare_code:
            self.object_name = self.extract_object_name_from_code(chapter_name, compare_code)
            self.denodo_folder = self.extract_denodo_folder_name_from_code(chapter_name, compare_code)
            self.set_compare_code(compare_code)

        if self.object_name:
            self.setText(0, self.object_name)

        self.difference = ''
        self.color = WHITE
        self.compare()
        self.pack()

    def set_compare_code(self, compare_code):
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
        else:
            if self.compare_code:
                self.set_color(GREEN)
            else:
                self.set_color(WHITE)

    def get_diff(self, code, compare_code):
        former_code_split = (code + '\n').splitlines(True)
        next_code_split = (compare_code + '\n').splitlines(True)
        diff = list(self.diff_engine.compare(former_code_split, next_code_split))
        return ''.join(diff)

    def pack(self):
        self.user_data['chapter_name'] = self.chapter_name
        self.user_data['code'] = self.code
        self.user_data['compare_code'] = self.compare_code
        self.user_data['color'] = self.color
        self.user_data['difference'] = self.difference
        self.user_data['denodo_folder'] = self.denodo_folder
        self.user_data['check_state'] = self.checkState(0)
        self.setData(0, Qt.UserRole, self.user_data)

    def unpack(self):
        self.user_data = self.data(0, Qt.UserRole)

        self.chapter_name = self.user_data['chapter_name']
        self.code = self.user_data['code']
        self.compare_code = self.user_data['compare_code']
        self.color = self.user_data['color']
        self.difference = self.user_data['difference']
        self.denodo_folder = self.user_data['denodo_folder']

        self.setData(0, Qt.EditRole, self.object_name)
        self.setData(0, Qt.ForegroundRole, self.color)
        self.setData(0, Qt.CheckStateRole, self.user_data['check_state'])

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
        self.setData(0, Qt.UserRole, '')

    def set_color(self, color):
        """
        Set the color
        :param color:
        :type color: QBrush
        :return:
        """
        self.color = color
        self.setForeground(0, color)

    # @staticmethod
    # def make_selected_treeview_item(parent, col, text, user_data, color):
    #     """
    #     Factory for QTreeWidgetItem instances for the selected_treeview
    #     They differ a bit from the all_chapter_treeview: no checkboxes etc
    #
    #     :param parent: The parent of the item, either a QTreeWidget or another QTreeWidgetItem
    #     :type parent: QTreeWidgetItem
    #     :param col: column index in the QTreeWidget, always 0
    #     :type col: int
    #     :param text: The text shown, a chapter name or a vql filename
    #     :type text: str
    #     :param user_data: the code in that vql file
    #     :type user_data: str
    #     :param color: the color of the item
    #     :type color: QBrush
    #     :return: A fully dressed QTreeWidgetItem instance for the selected_treeview
    #     :rtype: QTreeWidgetItem
    #     """
    #
    #     item = QTreeWidgetItem(parent)
    #     item.setCheckState(col, CHECKED)
    #     item.setData(col, Qt.CheckStateRole, QVariant())
    #     # item.setData(col, Qt.UserRole, None)
    #     item.childIndicatorPolicy = 2
    #     item.setFlags(ITEM_FLAG_SEL)
    #     item.setText(col, text)
    #     item.setData(col, Qt.UserRole, user_data)
    #     item.setForeground(0, color)
    #     return item

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
            object_name = first_line[27:-3].replace(' ', '_').replace('/', '_')
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
