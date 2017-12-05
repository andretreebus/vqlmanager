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
Dependencies: PyQt5 vql_manager

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""
__author__ = 'andretreebus@hotmail.com (Andre Treebus)'

# other libs
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QTreeWidgetItem
from vqlmanager.code_item import CodeItem
from vqlmanager.vql_manager_core import *


class Chapter(QTreeWidgetItem):
    """Chapter class represents a group of Denodo objects of the same kind.

    For example: a BASEVIEW or a ASSOCIATION etc.
    The Chapter class also represents a folder in the repository.
    The Chapter class is the owner/parent of the CodeItems.
    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget.
    """

    def __init__(self, parent, name):
        """Initializer of the class objects

        :param parent: reference to the parent or owner, this should be a VqlModel class (QTreeWidget)
        :type parent: VqlModel
        :param name: string name of the chapter
        :type name: str
        """

        super(Chapter, self).__init__(parent)
        self.user_data = dict()
        self.setCheckState(0, CHECKED)
        self.childIndicatorPolicy = 2
        self.setFlags(ITEM_FLAG_CHAPTER)
        self.class_type = Chapter
        self.name = name
        self.setText(0, name)
        self.header = self.make_header(name)
        self.code_items = list()
        self.chapter_items = list()
        self.parent_chapter_name = ''
        self.color = None
        self.set_color(WHITE)
        self.gui = GUI_SELECT
        self.pack(WHITE)
        logger.debug(f">> Chapter: {self.name} created.")

    # General functions

    def pack(self, color_filter):
        """Packs and filters this chapter object and its code_item children.

        Used before it gets cloned.
        The clone function only supports QTreeWidgetItem data,
        so we survive in the standard data(Qt.UserRole) in a dictionary.

        :param color_filter: The color that is selected
        :type color_filter: QBrush
        :return: None
        :rtype: None
        """

        self.user_data['name'] = self.name
        self.user_data['header'] = self.header
        self.user_data['code_items'] = self.code_items
        self.user_data['chapter_items'] = self.chapter_items
        self.user_data['parent_chapter_name'] = self.parent_chapter_name
        self.user_data['color'] = self.color
        self.user_data['gui'] = self.gui
        self.user_data['class_type'] = self.class_type
        self.user_data['selected'] = self.is_selected()
        self.user_data['expanded'] = self.isExpanded()
        for code_item in self.code_items:
            code_item.chapter_name = self.name
            code_item.pack(color_filter)
        for chapter in self.chapter_items:
            chapter.parent_chapter_name = self.name
            chapter.pack(color_filter)
        self.set_color_based_on_children(self.gui)
        self.setData(0, Qt.UserRole, self.user_data)

    @staticmethod
    def unpack(item):
        """Unpacks and filters this chapter object and its code_item children.

        Used after it has been cloned and packed,
        The clone function only supports QTreeWidgetItem data,
        so we survive in the standard data member data.(Qt.UserRole)
        in a dictionary
        This is a static member to unpack the resulting QTreeWidgetItem after cloning

        :param item: item to be unpacked
        :type item: QTreeWidgetItem
        :return: None
        :rtype: None
        """

        item.user_data = item.data(0, Qt.UserRole)
        item.name = item.user_data['name']
        item.header = item.user_data['header']
        item.code_items = item.user_data['code_items']
        item.color = item.user_data['color']
        item.chapter_items = item.user_data['chapter_items']
        item.gui = item.user_data['gui']
        item.class_type = item.user_data['class_type']
        item.is_selected = item.user_data['selected']
        item.setExpanded(item.user_data['expanded'])
        deletes = list()
        for i in range(item.childCount()):
            child = item.child(i)
            if child.checkState(0) == UNCHECKED:
                deletes.append(child)
        for child in reversed(deletes):
            item.takeChild(item.indexOfChild(child))

        deletes = list()
        for i in range(item.childCount()):
            child = item.child(i)
            item_class = child.data(0, Qt.UserRole)['class_type']
            if child.childCount() == 0 and not item_class == CodeItem:
                deletes.append(child)
        for child in reversed(deletes):
            item.takeChild(item.indexOfChild(child))

        for i in range(item.childCount()):
            child = item.child(i)
            item_class = child.data(0, Qt.UserRole)['class_type']
            item_class.unpack(child)

    @staticmethod
    def make_header(chapter_name):
        """Constructs a string that can be used to identify chapters in a Denodo exported database file.

        :param chapter_name: string with Chapter name
        :type chapter_name: str
        :return: The chapter Header
        :rtype: str
        """
        chapter_header = '# #######################################\n# ' \
                         + chapter_name + '\n# #######################################\n'
        return chapter_header

    def set_gui(self, gui):
        """Sets the Gui type (GUI_SELECT GUI_COMPARE) on the chapter and its children.

        :param gui: the new GUI type
        :type gui: int
        :return:None
        :rtype: None
        """
        self.gui = gui
        for chapter in self.chapter_items:
            chapter.set_gui(gui)
        for code_item in self.code_items:
            code_item.set_gui(gui)

    def set_color_based_on_children(self, mode, color=None):
        """Sets the color of chapters based on the non hidden children.

        :param mode: the mode of the gui
        :type mode: int
        :param color: Optional parameter to set the color only
        :type color: QBrush
        :return: None
        :rtype: None
        """
        if color:
            self.set_color(color)
            return

        colors = [translate_colors(code_item.color, to_text=True)
                  for code_item in self.code_items if not code_item.isHidden()]
        colors.extend([translate_colors(chapter_item.color, to_text=True)
                       for chapter_item in self.chapter_items if not chapter_item.isHidden()])
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
        """Set the color of this item.

        :param color:
        :type color: QBrush
        :return:
        """
        self.color = color
        self.setForeground(0, color)

    def get_code_item_by_object_name(self, object_name):
        """Returns a tuple of a code item child and the index it has.

        :param object_name: The object name of the CodeItem
        :type object_name: str
        :return: The tuple of index and code item object itself
        :rtype: tuple(int, CodeItem)
        """
        if object_name:
            for index, code_item in enumerate(self.code_items):
                if code_item:
                    if code_item.object_name == object_name:
                        return index, code_item
        return 0, None

    def is_selected(self):
        """Function returns if the chapter is selected or has some code items selected (tri state).

        :return: Boolean
        :rtype: bool
        """
        if self.checkState(0) in (PART_STATE, CHECKED) and len(self.code_items) > 0:
            return True
        else:
            return False

    # export functions
    # to file
    def get_code_as_file(self, selected):
        """Returns the combined Denodo code for a whole chapter.

        This function adds a chapter header, and only selected code items

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
    def get_part_log(self, base_path):
        """Returns data to write the part.log files.

        Returning two values: the file path for the part.log file and its content as a string.
        The content is a list of file paths pointing to the code items in this chapter.
        The part.log files are used in a repository to ensure the same order of execution.
        Only the selected code items are included.

        :param: base_path: The base folder for the repo
        :type: Path
        :return: Two values, a file path and the content of the part.log file of this chapter
        :rtype: tuple Path, str
        """
        folder = base_path / self.name
        part_log_filepath = folder / LOG_FILE_NAME
        part_log = [str(code_item.get_file_path(folder)) for code_item in self.code_items if code_item.is_selected()]
        part_log_content = '\n'.join(part_log)
        return part_log_filepath, part_log_content

    def selected_items(self):
        """Function for looping over selected code items.

        :return: list with items
        :rtype: list(CodeItem)
        """
        items = list()
        for code_item in self.code_items:
            if code_item.is_selected():
                items.append(code_item)
        return items
