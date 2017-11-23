#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
VqlModel Class
Overloaded QTreeWidget Class
Holds the model data for the VQL Manager app
Also functions as the view on the window

file: vql_model.py
Dependencies: PyQt5, collections, vql_manager_core.py, chapter.py

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""

from vql_manager_core import *
from PyQt5.QtCore import Qt, QBuffer, QIODevice
from PyQt5.QtGui import QBrush, QPixmap
from PyQt5.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem
from chapter import Chapter
from code_item import CodeItem
# from difflib import Differ
from _collections import OrderedDict


class VqlModel(QTreeWidget):
    """
    VqlModel class represents all objects in a Denodo database
    For example: ddp
    The VqlModel class also represents a Repository file structure
    The Chapter class is the owner/parent of the Chapter instances
    It inherits from QTreeWidget, so it can display in a QMainWindow or QWidget
    In this application it is instanced as: all_chapter_treeview
    The purpose of this class is to make GUI based selections
    """

    def __init__(self, parent):
        """
        Constructor of the class
        Mostly setting the stage for the display behavior of the QTreeWidget
        :param parent: the object holding this instance, a central widget of the QMainWindow
        :type parent: QWidget
        """
        super(VqlModel, self).__init__(parent)

        # custom class variables #########################
        # root is the first/parent node for all QTreeWidgetItem children
        self.root = self.invisibleRootItem()

        # chapters are stored in a list of Chapters inherrited from QTreeWidgetItem
        self.chapters = list()

        # initialize by adding empty chapters
        self._add_chapters(CHAPTER_NAMES)
        self.changed = False
        self.mode = GUI_NONE
        self.diff_engine = Differ()
        self.storage_list = list()
        self.view = VQL_VIEW
        self.denodo_root = Chapter(None, 'root')



    def _add_chapters(self, chapter_names):
        """
        Adds chapters to the dict
        :param chapter_names: list of chapter_names of type string
        :type chapter_names: list
        :return: nothing
        """
        for chapter_name in chapter_names:
            chapter = Chapter(self.root, chapter_name)
            self.chapters.append(chapter)

    def get_code_items(self):
        for chapter in self.chapters:
            for code_item in chapter.code_items:
                yield (chapter, code_item)

    @staticmethod
    def add_code_part(chapter, object_name, code, color, mode):
        """
        Adds a CodeItem to a chapter
        :param chapter: string chapter name, key in the chapters dictionary
        :type chapter: Chapter
        :param object_name: string file_name of the bit of code in the repository
        :type object_name: str
        :param code: string actual Denodo code for one Denodo object
        :type code: str
        :param color: the color of the item
        :type color: QBrush
        :param mode: the context type of code part, subset of modes
        :type mode: int
        :return: nothing
        """

        # chapter = self.chapters[chapter_name]
        chapter.add_code_item(object_name, code, color, mode)

    def get_code_as_file(self, selected):
        """
        Generates the code content for a single .vql file of all checked items
        :return: string of code content
        :rtype: str
        """
        code = [chapter.get_code_as_file(selected) for chapter in self.chapters]
        return PROP_QUOTE + '\n'.join(code)

    def get_part_logs(self, folder):
        """
        Generator with log file names (key) and their content (values)
        The content is a list of paths to the code items in a chapter
        This function is used to create a repository
        :return: Iterator with filepaths and content
        :rtype: generator of tuples: part_log_filepath, part_log_content
        """
        result = (chapter.get_part_log(folder) for chapter in self.chapters if chapter.is_selected())
        return result

    def get_selected_code_files(self, folder):
        """
        Generator for looping over all selected code items in the model
        This function is used to write the repository
        :return: an iterator with two unpacked values: filepath and code content
        :rtype: str, str
        """

        item_path_code = list()
        for chapter in self.chapters:
            items = chapter.selected_items()
            for code_item in items:
                item_path = code_item.get_file_path(chapter.get_file_path(folder))
                item_code = code_item.code
                item_path_code.append((item_path, item_code))
        return item_path_code

    def get_chapter_by_name(self, chapter_name):
        """
        Helper function: returns a chapter from the 'chapters' list by its name
        :param chapter_name: the name of the particular chapter requested
        :type chapter_name: str
        :return: A single chapter
        :rtype: Chapter
        """
        chapter = None
        for chapter in self.chapters:
            if chapter.name == chapter_name:
                break
        return chapter



    # def object_compare(self, chapter, object_name, object_code):
    #     """
    #     Function returns the color of an compare item, based on the following rules:
    #     green: the item is new
    #     yellow: the item is changed
    #     white: the item is the same
    #     :param chapter: the chapter of the item
    #     :param object_name: the name of the Denodo object to be compared
    #     :param object_code: the code of the Denodo object to be compared
    #     :return: the color and the diff
    #     :rtype: QBrush str
    #     """
    #
    #     color = GREEN
    #     for code_item in chapter.code_items:
    #         if code_item.object_name == object_name:
    #             if code_item.code == object_code:
    #                 color = WHITE
    #             else:
    #                 color = YELLOW
    #                 code_item.difference = self.get_diff(code_item.code, object_code)
    #     return color

    def switch_mode(self, new_mode):
        if new_mode & GUI_NONE:
            self.setHeaderLabel('')
            self.setToolTip('No model loaded, Open a file or repository')
        if new_mode & GUI_SELECT:
            self.setHeaderLabel('Selection Pane')
            self.setToolTip('Check the parts you like to select')
        elif new_mode & GUI_COMPARE:
            self.setHeaderLabel('Compare Pane')
            pix_map = QPixmap('images/tooltip.png')
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            pix_map.save(buffer, "PNG", quality=100)
            image = bytes(buffer.data().toBase64()).decode()
            html = '<img src="data:image/png;base64,{}">'.format(image)
            self.setToolTip(html)
            self.setToolTipDuration(1000)

    def parse(self, file_content, mode):
        """
        Generator of parsed pieces of the vql file per Denodo object
        :param file_content: the file to parse
        :type file_content: str
        :param mode: the application mode, selecting or comparing
        :param mode: int
        :return: yields the following components: chapter_name, object_name, object_code, is_already_in_model, is_same
        """

        self.changed = False
        indices = [[chapter.name, file_content.find(chapter.header)] for chapter in self.chapters]
        indices.append(['', len(file_content)])
        chapter_parts = [[start[0], file_content[start[1]:end[1]]]  # extract chapter_name and the content code
                         for start, end in zip(indices[:-1], indices[1:])  # loop over the indices, and those shifted
                         if start[1] > 0]  # if found

        for chapter_name, chapter_part in chapter_parts:
            chapter = self.get_chapter_by_name(chapter_name)
            if chapter:
                object_codes = (DELIMITER + code for code in chapter_part.split(DELIMITER)[1:])

                if mode & (BASE_FILE | BASE_REPO):
                    chapter.code_items = [CodeItem(chapter, chapter.name, code=code) for code in object_codes]
                if mode & (COMP_FILE | COMP_REPO):
                    new_objects = ((CodeItem.extract_object_name_from_code(chapter.name, code), code)
                                   for code in object_codes)
                    for new_object_name, code in new_objects:
                        code_item = chapter.get_code_item_by_object_name(new_object_name)
                        if code_item:
                            code_item.set_compare_code(code)
                        else:
                            code_items = (CodeItem(chapter, chapter.name, compare_code=code) for code in object_codes)
                            for code_item in code_items:
                                chapter.code_items.append(code_item)

        #self.sort(mode) Todo this

    def tree_reset(self):
        """
        Function resets the whole model
        :return: nothing
        """

        for chapter in self.chapters:
            chapter.tree_reset()

        self.chapters = list()
        # root is the first/parent node for all QTreeWidgetItem children
        self.root = self.invisibleRootItem()
        self.clear()
        # initialize by adding empty chapters
        self._add_chapters(CHAPTER_NAMES)

        # base_folder for storing as a repository
        # self.set_base_folder('')
        self.changed = False

        # self.setHeaderLabel('Selection')

    def sort(self, mode):
        if mode & (COMP_FILE | COMP_REPO):
            for chapter in self.chapters:
                chapter.sort()

    def tree_reset_compare(self):
        """
        Reset of compare tree items
        :return:
        """
        pass

    @staticmethod
    def update_colors(tree, mode):
        """
        Update the colors of the two tree objects
        :param tree: Reference to the QTreeWidget
        :type tree: QTreeWidget
        :param mode: Reference to the current mode
        :type mode: int
        :return: nothing
        """

        def update_chapter_colors():
            """
            Helper function for the update_colors function
            this function figures out the colors of the chapter items and sets them
            :return: nothing
            """

            children = (chapter_item.child(j) for j in range(chapter_item.childCount()))
            child_colors = (translate_colors(child.data(0, Qt.ForegroundRole), to_text=True) for child in children)
            unique_colors_in_chapter = {color for color in child_colors}

            length = len(unique_colors_in_chapter)
            if length == 0:  # no items found, so these are items not found in the new items
                if mode & COMP_LOADED:
                    chapter_color = RED
                else:
                    chapter_color = WHITE
            elif length == 1:  # all items the same color , use that color
                chapter_color = translate_colors(list(unique_colors_in_chapter)[0], to_text=False)
            else:
                chapter_color = YELLOW
            chapter_item.setForeground(0, chapter_color)

        root_item = tree.invisibleRootItem()
        for i in range(root_item.childCount()):
            chapter_item = root_item.child(i)
            update_chapter_colors()

    def change_view(self, new_view):
        if not self.mode & BASE_LOADED:
            return

        if self.view & new_view:
            return

        if new_view == VQL_VIEW:
            if self.storage_list:
                self.switch_view()
                self.view = VQL_VIEW
            else:
                # build a VQL_View
                pass
        elif new_view & DENODO_VIEW:
            if self.storage_list:
                self.switch_view()
                self.view = DENODO_VIEW
            else:
                # build denodo view
                self.build_denodo_view()
                self.change_view(new_view)

    def switch_view(self):
        temp = self.root.takeChildren()
        self.root.addChildren(self.storage_list)
        self.storage_list = temp

    def build_denodo_view(self):
        def extract_folder_names_from_code(_items):
            _folders = OrderedDict()
            folder_names = ((code_item, code_item.extract_denodo_folder_name_from_code(chapter)) for chapter, code_item in _items)

            for code_item, _folder in folder_names:
                if _folder:
                    code_item.denodo_folder = _folder
                    _folders[_folder] = list()

            for chapter, code_item in _items:
                if not chapter.name == 'FOLDERS':
                    if code_item.denodo_folder:
                        _folders[code_item.denodo_folder].append(code_item)
            return _folders

        items = [(chapter, code_item) for chapter, code_item in self.get_code_items()]
        folders = extract_folder_names_from_code(items)

        if not folders:
            return

        # print(folders.keys())

        temp_widget = VqlModel(None)
        temp_root = temp_widget.denodo_root

        old_depth = 1
        parent_item = temp_root
        folder_item = None
        for folder, code_items in folders.items():
            folder_split = folder.split('/')
            last_folder = folder_split[-1]
            new_depth = len(folder_split)
            if new_depth == 1:
                parent_item = temp_root
            else:
                if new_depth > old_depth:
                    parent_item = folder_item
            folder_item = Chapter(parent_item, last_folder)
            old_depth = new_depth
            for code_item in code_items:
                item = folder_item.add_code_item(code_item.object_name, code_item.code, code_item.color, code_item.mode)
                item.setCheckState(0, code_item.checkState(0))
        self.storage_list = temp_root.takeChildren()
