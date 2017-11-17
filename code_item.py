#!/usr/bin/python3
# -*- coding: utf-8 -*-

from os import path
from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtGui import QBrush, QColor


class CodeItem(QTreeWidgetItem):
    """
    CodeItem class represents a .vql file with a single Denodo object
    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget
    Basically a bag for pieces of Denodo code
    """
    PART_STATE = Qt.PartiallyChecked
    CHECKED = Qt.Checked
    UNCHECKED = Qt.Unchecked

    RED = QBrush(QColor("#ff4444"))
    GREEN = QBrush(QColor("#44ff44"))
    YELLOW = QBrush(QColor("#ffff44"))
    WHITE = QBrush(QColor("#cccccc"))
    ITEM_FLAG_ALL = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsTristate
    ITEM_FLAG_SEL = Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def __init__(self, parent, object_name, code, color=None):
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

        self.setCheckState(0, CodeItem.CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(CodeItem.ITEM_FLAG_ALL)
        self.object_name = object_name
        self.setText(0, object_name)
        self._code = code
        self.setData(0, Qt.UserRole, code)
        self._sub_folder = None
        self.color = CodeItem.WHITE
        if color:
            self.setForeground(0, color)
        else:
            self.setForeground(0, self.color)

    def set_sub_folder(self, sub_folder):
        """
        Set the folder where this codeItem resides
        :param sub_folder: string with file path
        :type sub_folder:str
        :return: nothing
        """
        self._sub_folder = sub_folder

    def get_file_path(self):
        """
        Function returns the whole file path
        :return: string file path
        :rtype: str
        """
        return path.join(self._sub_folder, self.object_name)

    def get_code(self):
        """
        Function returning the code
        :return: string code content
        :rtype: str
        """
        return self._code

    def get_code_as_file(self, selected):
        """
        Function returns code if selected
        :return: string code content
        :rtype: str
        """
        if selected:
            if self.is_selected:
                return self._code
        else:
            return self._code

    def is_selected(self):
        """
        Is the object selected
        :return: Boolean
        :rtype: bool
        """
        if self.checkState(0) == CodeItem.CHECKED:
            return True
        else:
            CodeItem.changed = True
            return False

    def tree_reset(self):
        """
        Function for deleting/resetting this item
        :return: nothing
        """
        self.object_name = None
        self.setText(0, '')
        self._code = None
        self.setData(0, Qt.UserRole, '')
        self._sub_folder = None

    def set_color(self, color):
        """
        Set the color
        :param color:
        :type color: QBrush
        :return:
        """
        self.color = color
        self.setForeground(0, color)

    def get_color(self):
        """
        Returns the color of the item
        :return: QBrush
        :rtype: QBrush
        """
        return self.color

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
        item.setCheckState(col, CodeItem.CHECKED)
        item.setData(col, Qt.CheckStateRole, QVariant())
        item.childIndicatorPolicy = 2
        item.setFlags(CodeItem.ITEM_FLAG_SEL)
        item.setText(col, text)
        item.setData(col, Qt.UserRole, user_data)
        item.setForeground(0, color)
        return item
