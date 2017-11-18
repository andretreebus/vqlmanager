#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Chapter Class
Class representing the categories (chapters)
related to the construction of
one Denodo objects

The class holds (as its parent) data of
all code pieces related to the chapter

This class is inherited from QTreeWidgetItem
for showing itself in a QTreeWidget

file: code_item.py
Dependencies: os PyQt5 vql_manager_core.py

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""

from os import path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QTreeWidgetItem
from code_item import CodeItem
from vql_manager_core import VqlConstants as Vql


class Chapter(QTreeWidgetItem):
    """
    Chapter class represents a group of Denodo objects of the same kind
    For example: a BASEVIEW or a ASSOCIATION etc
    The Chapter class also represents a folder in the repository
    The Chapter class is the owner/parent of the CodeItems
    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget
    """

    def __init__(self, parent, name):
        """
        Initializer of the class objects
        :param parent: reference to the parent or owner, this should be a VqlModel class (QTreeWidget)
        :type parent: VqlModel
        :param name: string name of the chapter
        :type name: str
        """
        super(Chapter, self).__init__(parent)
        self.setCheckState(0, Vql.CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(Vql.ITEM_FLAG_ALL)
        self.name = name
        self.setText(0, name)
        self.setData(0, Qt.UserRole, 'chapter')
        self.header = self._header(name)

        self._base_folder = None
        self._sub_folder = None

        self.code_items = list()

    def set_base_folder(self, base_folder):
        """
        Function sets the base folder of the repository
        :param base_folder: string path to the folder
        :type base_folder: str
        :return: nothing
        """
        if base_folder:
            self._base_folder = base_folder
            self._sub_folder = path.join(base_folder, str.replace(self.name, ' ', '_'))
            for code_item in self.code_items:
                code_item.set_sub_folder(self._sub_folder)
        else:
            self._base_folder = None

    def _get_code_as_file(self, selected):
        """
        Function returns the combined Denodo code from a whole chapter.
        This function does not add a chapter header
        :return: string with code content
        :rtype: str
        """
        code = ''
        if selected:
            if self.is_selected():
                for code_item in self.code_items:
                    code += code_item.get_code_as_file(selected)
            else:
                for code_item in self.code_items:
                    code += code_item.get_code_as_file(selected)
        return code

    @staticmethod
    def _header(chapter_name):
        """
        Constructs a string that can be used to identify chapters in a Denodo exported databse file
        :param chapter_name: string with Chapter name
        :type chapter_name: str
        :return: The chapter Header
        :rtype: str
        """
        chapter_header = '# #######################################\n# ' \
                         + chapter_name + '\n# #######################################\n'
        return chapter_header

    def add_code_item(self, file_name, code, color):
        """
        Function to construct and store a CodeItem in this Chapter
        :param file_name: string of the code item's file name
        :type file_name: str
        :param code: string with code content of the code item
        :type code: str
        :param color: the color of the item
        :type color: QBrush
        :return: nothing

        """
        code_item = CodeItem(self, file_name, code, color)
        self.code_items.append(code_item)

    def get_part_log(self):
        """
        Function returning two values: the file path for the part.log file and its content as a string
        The content is a list of file paths pointing to the code items in this chapter
        The part.log files are used in a repository to ensure the same order of execution
        Only the selected code items are included
        :return: Two values, a file path and the content of the part.log file of this chapter
        :rtype: str, str
        """
        part_log = list()
        for code_item in self.code_items:
            if code_item.is_selected:
                part_log.append(code_item.get_file_path())
        part_log_filepath = path.join(self._sub_folder, 'part') + '.log'
        part_log_content = '\n'.join(part_log)
        return part_log_filepath, part_log_content

    def get_code_as_file(self, selected):
        """
        Function returns the combined Denodo code from a whole chapter.
        This function adds a chapter header
        :return: string with code content
        :rtype: str
        """

        if selected:
            if self.is_selected():
                code = self._get_code_as_file(selected)
                if code:
                    return self.header + code
        else:
            code = self._get_code_as_file(selected)
            if code:
                return self.header + code

    def is_selected(self):
        """
        Function returns if the chapter is selected or has some code items selected (tri state)
        :return: Boolean
        :rtype: bool
        """
        if self.checkState(0) in (Vql.PART_STATE, Vql.CHECKED) and len(self.code_items) > 0:
            return True
        else:
            return False

    def selected_items(self):
        """
        Generator for looping over selected code items
        :return: Iterator
        :rtype: CodeItem
        """
        for code_item in self.code_items:
            if code_item.is_selected():
                yield code_item

    def tree_reset(self):
        """
        Function for deleting/resetting this chapter
        :return: nothing
        """
        for code_item in self.code_items:
            code_item.tree_reset()

        self.code_items = list()
        _ = self.takeChildren()
        self._base_folder = None
        self._sub_folder = None
