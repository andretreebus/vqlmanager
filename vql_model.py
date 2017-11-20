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
from collections import OrderedDict
# from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QWidget
# from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QTreeWidget
from chapter import Chapter
# from vql_manager_core import VqlConstants as Vql


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

        # base_folder for storing as a repository
        self._base_folder = None

        # chapters must be ordered, so no normal dict here
        # keys   : string with the chapter_name
        # values : the Chapter objects
        self.chapters = OrderedDict()

        # initialize by adding empty chapters
        self._add_chapters(CHAPTER_NAMES)
        self.changed = False

        self.view_mode = 0
        # self.base_model_path = ''
        # self.base_model_type = ''
        # self.compare_model_path = ''
        # self.compare_model_type = ''

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

        code = PROP_QUOTE
        for chapter_name, chapter in self.chapters.items():
            chapter_code = chapter.get_code_as_file(selected)
            if chapter_code:
                code += chapter_code
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

            if mode & GUI_SELECT:
                yield True, chapter
                for code_item in chapter.code_items:
                    if code_item.is_selected():
                        yield False, code_item
            elif mode & GUI_COMPARE:
                items = list()
                for code_item in chapter.code_items:
                    if code_item.is_selected(): # and not code_item.get_color() == WHITE:
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

        def add_compared_part():
            def compare():
                local_is_already_in_model = False
                local_is_same = False
                for code_item in chapter.code_items:
                    if code_item.object_name == object_name:
                        local_is_already_in_model = True
                        if code_item.get_code() == object_code:
                            local_is_same = True
                return local_is_already_in_model, local_is_same

            new_objects.append(object_name)
            is_already_in_model, is_same = compare()
            if is_already_in_model:
                if is_same:  # object not changed
                    pass
                else:  # object changed
                    to_add.append((object_name, object_code, YELLOW))
            else:  # object is new item
                to_add.append((object_name, object_code, GREEN))

        length = len(file_content)
        if mode & (BASE_FILE | BASE_REPO):
            self.changed = False
            self.setHeaderLabel('Selection')
        elif mode & (COMP_FILE | COMP_REPO):
            self.setHeaderLabel('White: No change; Red: Lost; Green: New; Yellow: Changed')

        indices = [[chapter_name, file_content.find(chapter.header)]
                   for chapter_name, chapter in self.chapters.items()]

        indices.append(['', length])

        chapter_parts = [[start[0], file_content[start[1]:end[1]]]
                         for start, end in zip(indices[:-1], indices[1:])
                         if start[1] > 0]

        for chapter_name, chapter_part in chapter_parts:
            new_objects = list()
            to_add = list()
            chapter = self.chapters[chapter_name]
            object_codes = [DELIMITER + code for code in chapter_part.split(DELIMITER)[1:]]
            object_code = [(self.extract_object_name(chapter_name, code), code) for code in object_codes]

            for object_name, object_code in object_code:
                if mode & (COMP_FILE | COMP_REPO):
                    add_compared_part()
                elif mode & (BASE_FILE | BASE_REPO):
                    self.add_code_part(chapter_name, object_name, object_code, WHITE)

            if mode & (COMP_FILE | COMP_REPO):
                for item in chapter.code_items:
                    if item.object_name not in new_objects:
                        item.set_color(RED)

                for object_name, object_code, color in to_add:
                    self.add_code_part(chapter_name, object_name, object_code, color)

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
        self._add_chapters(CHAPTER_NAMES)

        # base_folder for storing as a repository
        self.set_base_folder('')
        self.changed = False

        # self.setHeaderLabel('Selection')

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
            :param chapter_item: the chapter item
            :return: nothing
            """

            def translate_colors(item_color, to_text=True):
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
                    if item_color == RED:
                        color = 'red'
                    elif item_color == GREEN:
                        color = 'green'
                    elif item_color == YELLOW:
                        color = 'yellow'
                    elif item_color == WHITE:
                        color = 'white'
                else:
                    if item_color == 'red':
                        color = RED
                    elif item_color == 'green':
                        color = GREEN
                    elif item_color == 'yellow':
                        color = YELLOW
                    elif item_color == 'white':
                        color = WHITE
                return color
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
