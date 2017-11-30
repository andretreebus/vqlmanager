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
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QTreeWidget, QAbstractItemView, QTreeWidgetItem
from chapter import Chapter
from code_item import CodeItem
from collections import OrderedDict


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

        # chapters are stored in a list of Chapters inherited from QTreeWidgetItem
        self.chapters = list()

        # initialize by adding empty chapters
        self._add_chapters(CHAPTER_NAMES)
        self.changed = False
        self.mode = GUI_NONE
        self.storage_list = list()
        self.view = VQL_VIEW
        self.denodo_root = Chapter(None, 'root')
        self.color_filter = None

    def pack(self):
        for chapter in self.chapters:
            chapter.pack(self.color_filter)

    @staticmethod
    def unpack(tree):
        deletes = list()
        for i in range(tree.topLevelItemCount()):
            child = tree.topLevelItem(i)
            if (child.childCount() == 0) or (child.checkState(0) == UNCHECKED):
                deletes.append(child)
            else:
                item_class = child.data(0, Qt.UserRole)['class_type']
                item_class.unpack(child)
        for child in reversed(deletes):
            tree.takeTopLevelItem(tree.indexOfTopLevelItem(child))

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

    def get_code_items(self, chapter_list=None):
        if chapter_list:
            chapters = (chapter for chapter in self.chapters if chapter.name in chapter_list)
        else:
            chapters = (chapter for chapter in self.chapters)

        for chapter in chapters:
            for code_item in chapter.code_items:
                yield (chapter, code_item)

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

    async def parse(self, file_content, mode):
        """
        Generator of parsed pieces of the vql file per Denodo object
        :param file_content: the file to parse
        :type file_content: str
        :param mode: the application mode, selecting or comparing
        :param mode: int
        :return: yields the following components: chapter_name, object_name, object_code, is_already_in_model, is_same
        """

        self.changed = False
        gui = GUI_NONE

        if mode & (BASE_FILE | BASE_REPO):
            gui = GUI_SELECT
        elif mode & (COMP_FILE | COMP_REPO):
            gui = GUI_COMPARE
            # set all items to red, indicating they are lost.. this will later change if not
            for _, code_item in self.get_code_items():
                code_item.set_compare_code('', mode)

        # remove possible crab above first chapter
        for chapter in self.chapters:
            start_index = file_content.find(chapter.header)
            if not start_index == -1:
                file_content = file_content[start_index:]
                break

        # construct a list with indices where chapters start
        indices = list()
        for chapter in self.chapters:
            start_string_index = file_content.find(chapter.header)
            if start_string_index == -1:
                continue
            indices.append((chapter, start_string_index))
        indices.append(('', len(file_content)))

        # extract data from the file
        # zip the indices shifted one item to get start and end of the chapter code
        for start_tuple, end_tuple in zip(indices[:-1], indices[1:]):
            index = 0
            chapter, start = start_tuple
            next_chapter, end = end_tuple
            if start == -1:
                continue
            chapter_part = file_content[start:end]   # << contains chapter code
            chapter_objects = chapter_part.split(DELIMITER)[1:]  # split on CREATE OR REPLACE
            for chapter_object in chapter_objects:
                code = DELIMITER + chapter_object  # << put back the delimiter
                object_name = CodeItem.extract_object_name_from_code(chapter.name, code)  # extract object name
                if not object_name:
                    continue
                if gui == GUI_SELECT:
                    # add the code item to the chapter
                    chapter.code_items.append(CodeItem(chapter, chapter.name, mode, code=code))

                elif mode & (COMP_FILE | COMP_REPO):   # COMPARE case
                    # Check if item exists, and where
                    i, existing_item = chapter.get_code_item_by_object_name(object_name)
                    if existing_item:
                        existing_item.set_compare_code(code, mode)  # set the new mode en code
                        index = i
                    else:  # code object does not yet exist
                        index_child = chapter.child(index)
                        # add the new object under the indexed child
                        chapter.code_items.insert(index,
                                                  CodeItem(chapter, chapter.name, mode,
                                                           compare_code=code, preceding=index_child))
                        index += 1

        self.get_dependencies(gui)
        self.get_dependees(gui)

        # formatting the tree items
        if gui & GUI_SELECT:
            for _, code_item in self.get_code_items():
                if code_item.dependees:
                    code_item.set_color = RED

        if gui & GUI_COMPARE:
            for _, code_item in self.get_code_items():
                if code_item.color == RED:
                    code_item.setCheckState(0, UNCHECKED)
            for chapter in self.chapters:
                chapter.set_gui(gui)
                chapter.set_color_based_on_children(gui)
                if chapter.childCount() == 0:
                    chapter.setCheckState(0, UNCHECKED)

    def get_dependencies(self, gui):

        other_name_place_holder = '%&*&__&*&%'

        def find_dependencies(_code_objects, _underlying_code_objects, _search_template, _gui):
            for code_object, code_object_name, code in _code_objects:
                for other_code_item, other_name, other_code in _underlying_code_objects:
                    search_string = _search_template.replace(other_name_place_holder, other_name)
                    if not code.find(search_string) == -1:
                        if _gui & GUI_SELECT:
                            code_object.dependencies.append(other_code_item)
                        elif _gui & GUI_COMPARE:
                            code_object.compare_dependencies.append(other_code_item)

        def code_items_lower(_code_object_chapter_name, _gui):
            items = None
            if _gui & GUI_SELECT:
                items = [(code_item, code_item.object_name.lower(), code_item.code.lower())
                         for code_item in self.get_chapter_by_name(_code_object_chapter_name).code_items]
            elif _gui & GUI_COMPARE:
                items = [(code_item, code_item.object_name.lower(), code_item.compare_code.lower())
                         for code_item in self.get_chapter_by_name(_code_object_chapter_name).code_items]
            return items

        searches = list()
        searches.append(('WRAPPERS', 'DATASOURCES', 'datasourcename=' + other_name_place_holder))
        searches.append(('BASE VIEWS', 'WRAPPERS', 'wrapper (jdbc ' + other_name_place_holder + ')'))
        searches.append(('BASE VIEWS', 'WRAPPERS', 'wrapper (df ' + other_name_place_holder + ')'))
        searches.append(('BASE VIEWS', 'WRAPPERS', 'wrapper (ldap ' + other_name_place_holder + ')'))
        searches.append(('VIEWS', 'BASE VIEWS', 'from ' + other_name_place_holder))
        searches.append(('VIEWS', 'VIEWS', 'from ' + other_name_place_holder))
        searches.append(('ASSOCIATIONS', 'VIEWS', ' ' + other_name_place_holder + ' '))

        for code_object_chapter_name, underlying_code_object_chapter_name, search_template in searches:
            code_objects = code_items_lower(code_object_chapter_name, gui)
            underlying_code_objects = code_items_lower(underlying_code_object_chapter_name, gui)

            find_dependencies(code_objects, underlying_code_objects, search_template, gui)

    def get_dependees(self, gui):

        for chapter, item in self.get_code_items():
            # make unique
            dependencies = None
            dependees = None

            if gui & GUI_SELECT:
                dependencies = item.dependencies
                dependees = item.dependees
            elif gui & GUI_COMPARE:
                dependencies = item.compare_dependencies
                dependees = item.compare_dependees

            dependencies = self.unique_list(dependencies)

            # remove item itself (maybe from a join on itself)
            if item in dependencies:
                dependencies.remove(item)

            # construct list of dependees, of which this item is a parent
            for item_dependency in dependencies:
                item_dependency.dependees.append(item)

            dependees = self.unique_list(dependees)

            if gui & GUI_SELECT:
                item.dependencies = dependencies
                item.dependees = dependees
            elif gui & GUI_COMPARE:
                item.compare_dependencies = dependencies
                item.compare_dependees = dependees

    @staticmethod
    def unique_list(_list):
        new_list = list()
        for item in _list:
            if item not in new_list:
                new_list.append(item)
        return new_list

    def change_view(self, new_view, mode):
        gui = mode & (GUI_NONE | GUI_SELECT | GUI_COMPARE)
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
                self.build_denodo_view(gui)
                self.change_view(new_view, gui)

    def switch_view(self):
        temp = self.root.takeChildren()
        self.root.addChildren(self.storage_list)
        self.storage_list = temp

    def build_denodo_view(self, gui):
        folders = OrderedDict()
        self.pack()
        # get the list of folders and all code items in them
        for chapter, code_item in self.get_code_items():
            if code_item.denodo_folder not in folders.keys():
                folders[code_item.denodo_folder] = list()
                folders[code_item.denodo_folder].append(code_item)
            else:
                folders[code_item.denodo_folder].append(code_item)

        # Todo: if the folders contain paths that have no parents yet an error occurs
        # Todo: example: /source/presentatie_laag/vma
        # Todo: without the vql file mentioning /source, /source/presentatie_laag

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
            if parent_item is not temp_root:
                parent_item.chapter_items.append(folder_item)
                folder_item.gui = parent_item.gui
            old_depth = new_depth

            for code_item in code_items:
                item = CodeItem(folder_item, code_item.chapter_name, code_item.mode,
                                code=code_item.code, compare_code=code_item.compare_code)

                folder_item.code_items.append(item)

                item.setCheckState(0, code_item.checkState(0))
            folder_item.set_gui(gui)
            folder_item.set_color_based_on_children(gui)

        self.storage_list = temp_root.takeChildren()

    def remove_compare(self):
        for _, item in self.get_code_items():
            item.remove_compare()
