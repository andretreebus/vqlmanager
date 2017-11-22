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
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtGui import QBrush


class CodeItem(QTreeWidgetItem):
    """
    CodeItem class represents a .vql file with a single Denodo object
    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget
    Basically a bag for pieces of Denodo code
    """

    def __init__(self, parent, object_name, code, color, mode):
        """
        Class initializer
        :param parent: reference to the owner of the code, a Chapter object
        :type parent: Chapter
        :param object_name: string the file name of the vql file : not the whole path, just the basename e.g. myview.vql
        :type object_name: str
        :param code: string with the vql code
        :type code: str
        """

        super(CodeItem, self).__init__(parent)

        self.setCheckState(0, CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(ITEM_FLAG_ALL)
        self.object_name = object_name
        self.setText(0, object_name)
        self.code = code
        self.setData(0, Qt.UserRole, code)
        self.color = color
        self.mode = mode
        self.setForeground(0, self.color)
        self.difference = ''
        self.denodo_folder = ''

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

    @staticmethod
    def make_selected_treeview_item(parent, col, text, user_data, color):
        """
        Factory for QTreeWidgetItem instances for the selected_treeview
        They differ a bit from the all_chapter_treeview: no checkboxes etc

        :param parent: The parent of the item, either a QTreeWidget or another QTreeWidgetItem
        :type parent: QTreeWidgetItem
        :param col: column index in the QTreeWidget, always 0
        :type col: int
        :param text: The text shown, a chapter name or a vql filename
        :type text: str
        :param user_data: the code in that vql file
        :type user_data: str
        :param color: the color of the item
        :type color: QBrush
        :return: A fully dressed QTreeWidgetItem instance for the selected_treeview
        :rtype: QTreeWidgetItem
        """

        item = QTreeWidgetItem(parent)
        item.setCheckState(col, CHECKED)
        item.setData(col, Qt.CheckStateRole, QVariant())
        item.setData(col, Qt.UserRole, None)
        item.childIndicatorPolicy = 2
        item.setFlags(ITEM_FLAG_SEL)
        item.setText(col, text)
        item.setData(col, Qt.UserRole, user_data)
        item.setForeground(0, color)
        return item


    def extract_folder(self):
        if not self.code:
            return ''
        code = self.code
        start_index = code.find('FOLDER = \'')
        end_index = code.find('\'', start_index) - 1
        folder = code[start_index:end_index]
        print(folder)