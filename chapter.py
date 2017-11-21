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
# from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QTreeWidgetItem
from code_item import CodeItem
from vql_manager_core import *
from difflib import Differ

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
        self.setCheckState(0, CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(ITEM_FLAG_ALL)
        self.name = name
        self.setText(0, name)
        self.setData(0, Qt.UserRole, 'chapter')
        self.header = self.make_header(name)
        self.code_items = list()

    # General functions
    @staticmethod
    def make_header(chapter_name):
        """
        Constructs a string that can be used to identify chapters in a Denodo exported database file
        :param chapter_name: string with Chapter name
        :type chapter_name: str
        :return: The chapter Header
        :rtype: str
        """
        chapter_header = '# #######################################\n# ' \
                         + chapter_name + '\n# #######################################\n'
        return chapter_header

    def is_selected(self):
        """
        Function returns if the chapter is selected or has some code items selected (tri state)
        :return: Boolean
        :rtype: bool
        """
        if self.checkState(0) in (PART_STATE, CHECKED) and len(self.code_items) > 0:
            return True
        else:
            return False

    def get_file_path(self, folder):
        return path.normpath(path.join(folder, self.name.replace(' ', '_')))

    def tree_reset(self):
        """
        Function for deleting/resetting this chapter
        :return: nothing
        """
        for code_item in self.code_items:
            code_item.tree_reset()

        self.code_items = list()
        _ = self.takeChildren()

    def sort(self):
        """
        Sorts and filters the selection tree view
        :return:
        """

        children = self.takeChildren()
        base_children = [child for child in children if child.mode & (BASE_FILE | BASE_REPO)]
        base_child_object_names = [child.object_name for child in children if child.mode & (BASE_FILE | BASE_REPO)]
        comp_children = [child for child in children if child.mode & (COMP_FILE | COMP_REPO)]
        index = 0
        for comp_child in comp_children:
            if comp_child.color == WHITE:
                index = base_child_object_names.index(comp_child.object_name)

            elif comp_child.color == YELLOW:
                index = base_child_object_names.index(comp_child.object_name) + 1
                base_children.insert(index, comp_child)
                base_child_object_names.insert(index, comp_child.object_name)

            if comp_child.color == GREEN:
                base_children.insert(index + 1, comp_child)
                base_child_object_names.insert(index + 1, comp_child.object_name)

        for i, child in enumerate(base_children):
            if child.color == YELLOW:
                former_child = base_children[i-1]
                former_child.setCheckState(0, UNCHECKED)
            if child.color == RED:
                child.setCheckState(0, UNCHECKED)
        self.addChildren(base_children)

    # import functions
    def add_code_item(self, object_name, code, color, mode):
        """
        Function to construct and store a CodeItem in this Chapter
        :param object_name: string of the code item's file name
        :type object_name: str
        :param code: string with code content of the code item
        :type code: str
        :param color: the color of the item
        :type color: QBrush
        :param mode: the color of the item
        :type mode: int
        :return: nothing

        """

        code_item = CodeItem(self, object_name, code, color, mode)
        self.code_items.append(code_item)

    # export functions
    # to file
    def get_code_as_file(self, selected):
        """
        Function returns the combined Denodo code from a whole chapter.
        This function does not add a chapter header
        :param selected: Indicator is True if only selected items are requested
        :type selected: bool
        :return: string with code content
        :rtype: str
        """
        if selected and self.is_selected():
            code = [code_item.code for code_item in self.code_items if code_item.is_selected()]
        else:
            code = [code_item.code for code_item in self.code_items]
        return self.header + '\n'.join(code)

    # to repository
    def get_part_log(self, folder):
        """
        Function returning two values: the file path for the part.log file and its content as a string
        The content is a list of file paths pointing to the code items in this chapter
        The part.log files are used in a repository to ensure the same order of execution
        Only the selected code items are included
        :return: Two values, a file path and the content of the part.log file of this chapter
        :rtype: str, str
        """

        sub_folder = self.get_file_path(folder)
        part_log_filepath = path.normpath(path.join(sub_folder, 'part.log'))
        part_log = [code_item.get_file_path(sub_folder) for code_item in self.code_items if code_item.is_selected()]
        part_log_content = '\n'.join(part_log)
        return part_log_filepath, part_log_content

    def selected_items(self):
        """
        Generator for looping over selected code items
        :return: Iterator
        :rtype: CodeItem
        """
        items = list()
        for code_item in self.code_items:
            if code_item.is_selected():
                items.append(code_item)
        return items
