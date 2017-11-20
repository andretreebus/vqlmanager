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
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QTreeWidget
from chapter import Chapter


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

        # chapters must be ordered, so no normal dict here
        # keys   : string with the chapter_name
        # values : the Chapter objects
        # self.chapters = OrderedDict()
        self.chapters = list()

        # initialize by adding empty chapters
        self._add_chapters(CHAPTER_NAMES)
        self.changed = False
        self.mode = GUI_NONE

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

    def add_code_part(self, chapter, object_name, code, color, mode):
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
        code = [chapter get_code(selected) for chapter in self.chapters]
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
        return ((code_item.get_file_path(folder), code_item.code)
                for code_item in (chapter.code_items for chapter in self.chapters if chapter.is_selected()))

    def get_chapter_by_name(self, chapter_name):
        for chapter in self.chapters:
            if chapter.name == chapter_name:
                return chapter

    # def selected_items(self, mode):
    #     """
    #     Generator for looping over all selected code items in the model
    #     This function is used to write the repository
    #     :return: an iterator with 2 unpacked values: a boolean indicator if the file is a Chapter object
    #     :rtype: bool, QTreeWidgetItem
    #     If not, it is a CodeItem object.
    #     The second value is the item itself
    #     """
    #     for chapter in self.chapters:
    #         if not chapter.is_selected():
    #             continue
    #
    #         if mode & GUI_SELECT:
    #             yield True, chapter
    #             for code_item in chapter.code_items:
    #                 if code_item.is_selected():
    #                     yield False, code_item
    #         elif mode & GUI_COMPARE:
    #             items = list()
    #             for code_item in chapter.code_items:
    #                 if code_item.is_selected():   # and not code_item.get_color() == WHITE:
    #                     items.append(code_item)
    #             if items:
    #                 yield True, chapter
    #                 for item in items:
    #                     yield False, item
    @staticmethod
    def compare(chapter, object_name, object_code):
        color = GREEN
        for code_item in chapter.code_items:
            if code_item.object_name == object_name:
                color = YELLOW
                if code_item.get_code() == object_code:
                    color = WHITE
        return color

    # @staticmethod
    # def add_compared_part(chapter, object_name, object_code):
    #     color = self.compare(chapter, object_name, object_code)
    #     return (object_name, object_code, color)

    def switch_mode(self, new_mode):
        if new_mode & GUI_NONE:
            self.setHeaderLabel('')
            self.setToolTip('No model loaded, Open a file or repository')
        if new_mode & GUI_SELECT:
            self.setHeaderLabel('Selection Pane')
            self.setToolTip('Check the parts you like to select')
        elif new_mode & GUI_COMPARE:
            self.setHeaderLabel('Compare Pane')
            tip = '<span style=\"background-color:white;\">Same Object</span></br>' \
                '<span style=\"background-color:red;\">Removed Object</span></br>' \
                '<span style=\"background-color:green;\">New Object</span></br>' \
                '<span style=\"background-color:yellow;\">Code Change</span>'
            self.setToolTip(tip)
            # self.setToolTip('White:No change; Red:Lost; Green:New; Yellow:Changed')

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
                object_code = [(self.extract_object_name(chapter_name, code), code) for code in object_codes]

                if mode & (COMP_FILE | COMP_REPO):
                    to_add = [[name, code, self.compare(chapter, name, code)] for name, code in object_code]
                    new_objects = [name for name, code, color in to_add]
                    for item in chapter.code_items:
                        if item.object_name not in new_objects:
                            item.set_color(RED)
                    for name, code, color in to_add:
                        self.add_code_part(chapter, name, code, color, mode)
                elif mode & (BASE_FILE | BASE_REPO):
                    for name, code in object_code:
                        self.add_code_part(chapter, name, code, WHITE, mode)

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
