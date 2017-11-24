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
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QTreeWidgetItem
from code_item import CodeItem
from vql_manager_core import *


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
        self.user_data = dict()
        self.setCheckState(0, CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(ITEM_FLAG_ALL)
        self.class_type = Chapter
        self.name = name
        self.setText(0, name)
        self.header = self.make_header(name)
        self.code_items = list()
        self.chapter_items = list()
        self.parent_chapter_name = ''
        self.color = WHITE
        self.gui = GUI_SELECT
        self.selected_child_count = 0
        self.pack()

    # General functions

    def pack(self):
        self.user_data['name'] = self.name
        self.user_data['header'] = self.header
        self.user_data['code_items'] = self.code_items
        self.user_data['chapter_items'] = self.chapter_items
        self.user_data['parent_chapter_name'] = self.parent_chapter_name
        self.user_data['color'] = self.color
        self.user_data['check_state'] = self.checkState(0)
        self.user_data['gui'] = self.gui
        self.user_data['class_type'] = self.class_type
        self.setData(0, Qt.UserRole, self.user_data)
        self.selected_child_count = 0
        for code_item in self.code_items:
            code_item.chapter_name = self.name
            if code_item.is_selected():
                self.selected_child_count += 1
            code_item.pack()
        for chapter in self.chapter_items:
            chapter.parent_chapter_name = self.name
            if chapter.is_selected():
                self.selected_child_count += 1
            chapter.pack()
        self.user_data['selected_child_count'] = self.selected_child_count

    @staticmethod
    def unpack(item):
        item.user_data = item.data(0, Qt.UserRole)
        item.name = item.user_data['name']
        item.header = item.user_data['header']
        item.code_items = item.user_data['code_items']
        item.color = item.user_data['color']
        item.chapter_items = item.user_data['chapter_items']
        item.gui = item.user_data['gui']
        item.class_type = item.user_data['class_type']
        item.selected_child_count = item.user_data['selected_child_count']
        item = QTreeWidgetItem()

        deletes = list()
        for i in range(item.childCount()):
            child = item.child(i)
            class_type = child.data(0, Qt.UserRole)['class_type']
            if class_type == Chapter:
                if (child.childCount() == 0) or (child.checkState == UNCHECKED):
                    deletes.append(child)
            elif class_type == CodeItem:
                if child.checkState == UNCHECKED:
                    deletes.append(child)
            else:
                class_type.unpack(child)
        for child in deletes:
            item.takeChild(item.indexOfChild(child))

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

    def remove_code_item(self, object_name):
        _, code_item = self.get_code_item_by_object_name(object_name)
        index = self.indexOfChild(code_item)
        self.code_items.remove(code_item)
        child = self.takeChild(index)
        del child

    def set_gui(self, gui):
        self.gui = gui
        for chapter in self.chapter_items:
            chapter.set_gui(gui)
        for code_item in self.code_items:
            code_item.set_gui(gui)

    def set_color_based_on_children(self, mode, color=None):
        if color:
            self.set_color(color)
            return

        colors = [translate_colors(code_item.color, to_text=True) for code_item in self.code_items]
        colors.extend([translate_colors(chapter_item.color, to_text=True) for chapter_item in self.chapter_items])
        unique_colors = list(set(colors))
        length = len(unique_colors)
        if length == 0:
            if mode & GUI_SELECT:
                self.set_color(WHITE)
            else:
                self.set_color(RED)
        elif length == 1:
            self.set_color(translate_colors(unique_colors[0], to_text=False))
        else:
            self.set_color(YELLOW)

    def set_color(self, color):
        """
        Set the color
        :param color:
        :type color: QBrush
        :return:
        """
        self.color = color
        self.setForeground(0, color)

    def get_code_item_by_object_name(self, object_name):
        for index, code_item in enumerate(self.code_items):
            if code_item.object_name == object_name:
                return index, code_item
        return None, None

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
