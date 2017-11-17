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

from collections import OrderedDict
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QWidget
# from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QTreeWidget
from chapter import Chapter
from vql_manager_core import VqlConstants as Vql


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
        # self.setColumnCount(1)
        # self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.setSelectionMode(QAbstractItemView.NoSelection)
        # self.setIconSize(QSize(16, 16))
        # self.setUniformRowHeights(True)
        # self.setHeaderLabel('No file selected')
        # self.setToolTip("Select code parts: Right mouse click")
        # self.setToolTipDuration(2000)
        # self.setIconSize(QSize(16, 16))
        # self.setColumnCount(1)
        # self.setMinimumSize(QSize(VQL.PANE_WIDTH, 0))
        # self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # custom class variables #########################
        # root is the first/parent node for all QTreeWidgetItem children
        self.root = self.invisibleRootItem()

        # base_folder for storing as a repository
        self._base_folder = None

        # chapters must be ordered, so no normal dict here
        # keys   : string with the chapter_name
        # values : the Chapter objects
        self.chapters = OrderedDict()

        # initialize by adding empty chapters
        self._add_chapters(Vql.CHAPTER_NAMES)
        self.changed = False
        self.new_objects = list()
        self.to_add = list()

        self.view_mode = 0
        self.base_model_path = ''
        self.base_model_type = ''
        self.compare_model_path = ''
        self.compare_model_type = ''

    def set_base_folder(self, base_folder):
        """
        Sets the repository base folder
        :param base_folder: string repository path
        :type base_folder:str
        :return: nothing
        """
        if base_folder:
            self._base_folder = base_folder
            for chapter_name, chapter in self.chapters.items():
                chapter.set_base_folder(base_folder)
        else:
            self._base_folder = ''

    def _add_chapters(self, chapter_names):
        """
        Adds chapters to the dict
        :param chapter_names: list of chapter_names of type string
        :type chapter_names: list
        :return: nothing
        """
        for chapter_name in chapter_names:
            chapter = Chapter(self.root, chapter_name)
            self.chapters[chapter_name] = chapter

    def add_code_part(self, chapter_name, object_name, code, color):
        """
        Adds a CodeItem to a chapter
        :param chapter_name: string chapter name, key in the chapters dictionary
        :type chapter_name: str
        :param object_name: string file_name of the bit of code in the repository
        :type object_name: str
        :param code: string actual Denodo code for one Denodo object
        :type code: str
        :param color: the color of the item
        :type color: QBrush
        :return: nothing
        """

        chapter = self.chapters[chapter_name]
        chapter.add_code_item(object_name, code, color)

    def get_code_as_file(self, selected):
        """
        Generates the code content for a single .vql file of all checked items
        :return: string of code content
        :rtype: str
        """
        code = ''
        code += VqlModel.PROP_QUOTE
        for chapter_name, chapter in self.chapters.items():
            code += chapter.get_code_as_file(selected)
        return code

    def get_part_logs(self):
        """
        Generator with log file names (key) and their content (values)
        The content is a list of paths to the code items in a chapter
        This function is used to create a repository
        :return: Iterator with filepaths and content
        :rtype: str, str
        """
        for chapter_name, chapter in self.chapters.items():
            if chapter.is_selected and chapter.childCount() > 0:
                part_log_filepath, part_log_content = chapter.get_part_log()
                yield part_log_filepath, part_log_content

    def get_selected_code_files(self):
        """
        Generator for looping over all selected code items in the model
        This function is used to write the repository
        :return: an iterator with two unpacked values: filepath and code content
        :rtype: str, str
        """
        for chapter_name, chapter in self.chapters.items():
            if chapter.is_selected():
                for code_item in chapter.code_items:
                    if code_item.is_selected():
                        yield code_item.get_file_path(), code_item.get_code()

    def selected_items(self, mode):
        """
        Generator for looping over all selected code items in the model
        This function is used to write the repository
        :return: an iterator with 2 unpacked values: a boolean indicator if the file is a Chapter object
        :rtype: bool, QTreeWidgetItem
        If not, it is a CodeItem object.
        The second value is the item itself
        """
        for chapter_name, chapter in self.chapters.items():
            if not chapter.is_selected():
                continue

            if mode & VqlModel.SELECT:
                yield True, chapter
                for code_item in chapter.code_items:
                    if code_item.is_selected():
                        yield False, code_item
            elif mode & VqlModel.COMPARE:
                items = list()
                for code_item in chapter.code_items:
                    if code_item.is_selected():
                        if not code_item.get_color() == Vql.WHITE:
                            items.append(code_item)
                if items:
                    yield True, chapter
                    for item in items:
                        yield False, item

    def parse(self, file_content, mode):
        """
        Generator of parsed pieces of the vql file per Denodo object
        :param file_content: the file to parse
        :type file_content: str
        :param mode: the application mode, selecting or comparing
        :param mode: int
        :return: yields the following components: chapter_name, object_name, object_code, is_already_in_model, is_same
        """

        length = len(file_content)
        if mode & VqlModel.SELECT:
            self.changed = False
            self.tree_reset()
            # self.setHeaderLabel('Selection')
        elif mode & VqlModel.COMPARE:
            self.tree_reset_compare()
            self.new_objects = list()
            self.to_add = list()
            # self.setHeaderLabel('Difference')

        indices = [[chapter_name, file_content.find(chapter.header)]
                   for chapter_name, chapter in self.chapters.items()]

        indices.append(['', length])

        chapter_parts = [[start[0], file_content[start[1]:end[1]]]
                         for start, end in zip(indices[:-1], indices[1:])
                         if start[1] > 0]

        for chapter_name, chapter_part in chapter_parts:
            object_codes = [VqlModel.DELIMITER + code for code in chapter_part.split(VqlModel.DELIMITER)[1:]]
            object_code = [(self.extract_object_name(chapter_name, code), code) for code in object_codes]
            for object_name, object_code in object_code:
                if mode == VqlModel.SELECT:
                    self.add_code_part(chapter_name, object_name, object_code, Vql.WHITE)
                else:
                    self.add_compared_part(chapter_name, object_name, object_code)

        if mode == VqlModel.COMPARE:
            self.check_deleted_items()
            for chapter_name, object_name, object_code, color in self.to_add:
                self.add_code_part(chapter_name, object_name, object_code, color)

    def check_deleted_items(self):
        """

        :return:
        """
        # all items in the model that are not in model2
        for chapter_name, chapter in self.chapters.items():
            for item in chapter.code_items:
                if item.object_name not in self.new_objects:
                    item.set_color(Vql.RED)

    def compare(self, chapter_name, object_name, object_code):
        """

        :param chapter_name:
        :param object_name:
        :param object_code:
        :return:
        """
        is_already_in_model = False
        is_same = False
        chapter = self.chapters[chapter_name]
        for code_item in chapter.code_items:
            if code_item.object_name == object_name:
                is_already_in_model = True
                if code_item.get_code() == object_code:
                    is_same = True
        return is_already_in_model, is_same

    def add_compared_part(self, chapter_name, object_name, object_code):
        """

        :param chapter_name:
        :param object_name:
        :param object_code:
        :return:
        """
        self.new_objects.append(object_name)
        is_already_in_model, is_same = self.compare(chapter_name, object_name, object_code)
        if is_already_in_model:
            if is_same:   # object not changed
                pass
            else:      # object changed
                self.to_add.append((chapter_name, object_name, object_code, Vql.YELLOW))
        else:   # object is new item
            self.to_add.append((chapter_name, object_name, object_code, Vql.GREEN))

    def tree_reset(self):
        """
        Function resets the whole model
        :return: nothing
        """

        for chapter in self.chapters.values():
            chapter.tree_reset()

        self.chapters = OrderedDict()
        # root is the first/parent node for all QTreeWidgetItem children
        self.root = self.invisibleRootItem()
        self.clear()
        # initialize by adding empty chapters
        self._add_chapters(VqlModel.CHAPTER_NAMES)

        # base_folder for storing as a repository
        self.set_base_folder('')
        self.changed = False

        self.setHeaderLabel('Selection')

    def tree_reset_compare(self):
        """
        Reset of compare tree items
        :return:
        """
        pass

    @staticmethod
    def extract_object_name(chapter_name, command):
        """
        Helper function for the 'parse' function
        The function searches for the Denodo object name to construct a unique file name in the repository
        Each chapter has its own way of extracting the object name

        Warning!!
        With newer versions of Denodo it should be checked if the structure they use is the same

        :param command: string with code relating to one object in Denodo
        :type command: str
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

        filename = ''

        # Object names are on the first line of the code item
        first_line = command[0:command.find("\n")]

        if chapter_name == 'I18N MAPS':
            filename = get_last_word(first_line[0:-2])
        elif chapter_name == 'DATABASE':
            pass  # Todo: we don't use export vql files that span multiple databases in Denodo
        elif chapter_name == 'FOLDERS':
            filename = first_line[27:-3].replace(' ', '_').replace('/', '_')
        elif chapter_name == 'LISTENERS JMS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'DATASOURCES':
            filename = get_last_word(first_line)
        elif chapter_name == 'WRAPPERS':
            filename = get_last_word(first_line)
        elif chapter_name == 'STORED PROCEDURES':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'TYPES':
            filename = first_line.split()[4]
        elif chapter_name == 'MAPS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'BASE VIEWS':
            filename = first_line.split()[4]
        elif chapter_name == 'VIEWS':
            split = first_line.split(' ')
            if split[3] == 'INTERFACE':
                filename = split[5]
            else:
                filename = split[4]
        elif chapter_name == 'ASSOCIATIONS':
            filename = first_line.split()[4]
        elif chapter_name == 'WEBSERVICES':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WIDGETS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WEBCONTAINER WEB SERVICE DEPLOYMENTS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WEBCONTAINER WIDGET DEPLOYMENTS':
            pass  # Todo: we don't use these kind of objects in Denodo
        return filename

    @staticmethod
    def update_colors(tree):
        """
        Update the colors of the two tree objects
        :param tree: Reference to the QTreeWidget
        :type tree: QTreeWidget
        :return: nothing
        """

        def translate_colors(item_color, to_text):
            """
            Function for translating item QBrush objects for strings
            This is needed because the set function does not accept unhashable items
            :param item_color: the object to be translated
            :type item_color: str or QBrush
            :param to_text: indicator for the direction of the tranlation
            :type to_text: bool
            :return: Translated value
            :rtype: QBrush or str
            """
            color = None
            if to_text:
                if item_color == Vql.RED:
                    color = 'red'
                elif item_color == Vql.GREEN:
                    color = 'green'
                elif item_color == Vql.YELLOW:
                    color = 'yellow'
                elif item_color == Vql.WHITE:
                    color = 'white'
            else:
                if item_color == 'red':
                    color = Vql.RED
                elif item_color == 'green':
                    color = Vql.GREEN
                elif item_color == 'yellow':
                    color = Vql.YELLOW
                elif item_color == 'white':
                    color = Vql.WHITE
            return color

        def update_chapter_colors(local_chapter_item):
            """
            Helper function for the update_colors function
            this function figures out the colors of the chapter items and sets them
            :param local_chapter_item: the chapter item
            :type local_chapter_item: QTreeWidgetItem
            :return: nothing
            """
            unique_colors_in_chapter = set()
            children = (local_chapter_item.child(j) for j in range(local_chapter_item.childCount()))
            child_colors = [translate_colors(child.data(0, Qt.ForegroundRole), True) for child in children]
            for color in child_colors:
                unique_colors_in_chapter.add(color)

            length = len(unique_colors_in_chapter)
            if length == 0:
                chapter_color = Vql.RED
            elif length == 1:
                chapter_color = translate_colors(list(unique_colors_in_chapter)[0], False)
            else:
                chapter_color = Vql.YELLOW
            local_chapter_item.setForeground(0, chapter_color)

        root_item = tree.invisibleRootItem()
        for i in range(root_item.childCount()):
            chapter_item = root_item.child(i)
            update_chapter_colors(chapter_item)
