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
__author__ = 'andretreebus@hotmail.com (Andre Treebus)'

# standard library
from pathlib import Path
# other libs
from PyQt5.QtWidgets import QWidget, QTreeWidget
from vqlmanager.chapter import Chapter
from vqlmanager.code_item import CodeItem
from vqlmanager.vql_manager_core import *

class VqlModel(QTreeWidget):
    """VqlModel class represents all objects in a Denodo database.

    The VqlModel class also represents a Repository file structure.
    The Chapter class is the owner/parent of the Chapter instances.
    It inherits from QTreeWidget, so it can display in a QMainWindow or QWidget.
    In this application it is instanced as: all_chapter_treeview.
    The purpose of this class is to make GUI based selections.
    """

    def __init__(self, parent: Union[QWidget, None]):
        """Constructor of the class.

        Mostly setting the stage for the behavior of the QTreeWidget.

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
        # changed is a boolean indicating a change in selection was made
        self.changed = False
        # mode of operation: see mode variable flags in vql_manager_core
        self.mode = GUI_NONE
        # storage_list to store items for different views
        self.storage_list = list()
        # view stores the current view
        self.view = VQL_VIEW
        # denodo_root is a reference to the root item of the denodo view
        self.denodo_root = Chapter(None, 'root')
        # color_filter used to filter items
        self.color_filter = None

    def pack(self):
        """Packs all data of the tree into UserData of the QTreeWidgetItems.

        :return: None
        :rtype: None
        """
        for chapter in self.chapters:
            chapter.pack(self.color_filter)

    @staticmethod
    def unpack(tree: QTreeWidget):
        """Unpacks the data from QtreeWidgetItem's Userdata.

        It also prunes the tree on checked items only with children
        :param tree: The QtreeWidget to work on
        :type tree: QtreeWidget
        :return: None
        :rtype: None
        """
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

    def _add_chapters(self, chapter_names: List[str]):
        """Method that adds a chapter to the chapter list for every name given.

        :param chapter_names: list of chapter_names of type string
        :type chapter_names: list
        :return: None
        :rtype: None
        """
        for chapter_name in chapter_names:
            chapter = Chapter(self.root, chapter_name)
            self.chapters.append(chapter)

    def get_code_items(self, chapter_list=None)->Tuple[Chapter, CodeItem]:
        """Generator to loop all code items.

        Optionally a list with chapter names may be given as a filter.
        Only chapter names in the lis are then included.

        :param chapter_list: Optional list with chapter names
        :type chapter_list: list
        :return: Yields a tuple of chapter and code_item
        :rtype: Tuple[Chapter, CodeItem]
        """
        if chapter_list:
            chapters = (chapter for chapter in self.chapters if chapter.name in chapter_list)
        else:
            chapters = (chapter for chapter in self.chapters)

        for chapter in chapters:
            for code_item in chapter.code_items:
                yield (chapter, code_item)

    def get_code_as_file(self, selected: bool)->str:
        """Function that puts the code content in a single .vql file of all checked/selected items.
        :param selected: Only selected items or not
        :type selected: bool
        :return: string of code content
        :rtype: str
        """

        code = [chapter.get_code_as_file(selected) for chapter in self.chapters]
        return PROP_QUOTE + '\n'.join(code)

    def get_part_logs(self, folder: Path):
        """Gives all part.log data.

        With log file names (key) and their content (values).
        The content is a list of paths to the code items in a chapter.
        This function is used to create a repository.

        :param folder: The folder to save the repo to
        :type folder: Path
        :return: Iterator with filepaths and content
        :rtype: generator of tuples: part_log_filepath, part_log_content
        """
        result = (chapter.get_part_log(folder) for chapter in self.chapters if chapter.is_selected())
        return result

    def get_selected_code_files(self, folder: Path)->List[Tuple[Path, str]]:
        """Function for looping over all selected code items in the model.

        This function is used to write the repository
        :param folder: the proposed folder for storage
        :type folder: Path
        :return: an iterator with two unpacked values: filepath and code content
        :rtype: list(tuple(Path, str))
        """

        item_path_code = list()
        for chapter in self.chapters:
            items = chapter.selected_items()
            chapter_folder = folder / chapter.name
            for code_item in items:
                item_path = code_item.get_file_path(chapter_folder)
                item_code = code_item.code
                item_path_code.append((item_path, item_code))
        return item_path_code

    def get_chapter_by_name(self, chapter_name: str)->Chapter:
        """Function that returns a chapter from the 'chapters' list by its name.

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

    def switch_mode(self, new_mode: int):
        """Method to switch mode on the tree item, sets appropriate headers and tooltips.

        :param new_mode: The new mode
        :type new_mode: int
        :return: None
        """

        if new_mode & GUI_NONE:
            self.setHeaderLabel('')
            self.setToolTip('No model loaded, Open a file or repository')
        if new_mode & GUI_SELECT:
            self.setHeaderLabel('Selection Pane')
            self.setToolTip('Check the parts you like to select')
        elif new_mode & GUI_COMPARE:
            self.setHeaderLabel('Compare Pane')
            self.setToolTip('Select items')
            self.setToolTipDuration(1000)

    async def parse(self, file_content: str, mode: int):
        """Method that parses the denodo export file.

        It analyzes it to construct/fill the VqlModel tree.

        :param file_content: String with the denodo file
        :type file_content: str
        :param mode: the application mode, selecting or comparing
        :param mode: int
        :return: None
        :rtype: None
        """
        logger.debug('Start parsing data.')
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
                    code_item.set_color(RED)
            for chapter in self.chapters:
                chapter.set_gui(gui)
                chapter.set_color_based_on_children(gui, color=WHITE)
                if chapter.childCount() == 0:
                    chapter.setCheckState(0, UNCHECKED)

        elif gui & GUI_COMPARE:
            for _, code_item in self.get_code_items():
                if code_item.color == RED:
                    code_item.setCheckState(0, UNCHECKED)
            for chapter in self.chapters:
                chapter.set_gui(gui)
                chapter.set_color_based_on_children(gui)
                if chapter.childCount() == 0:
                    chapter.setCheckState(0, UNCHECKED)

        logger.debug('Finished parsing data.')

    def get_dependencies(self, gui: int):
        """Method with nifty code to extract en fill direct dependencies.

        Per code object upon other objects based on their vql code.
        :param gui: mode flag selector indicating what code is done
        :type gui: int
        :return: None
        :rtype: None
        """

        # place holder in search strings that is unlikely in the code
        place_holder = '%&*&__&*&%'

        # helper function
        def find_dependencies(_code_objects, _underlying_code_objects, _search_template):
            """
            Function finds and adds the direct dependencies of code objects
            in the lower-cased code of underlying objects.
            Basically it looks for the code_item's object name in the code of the underlying objects
            via a particular search string per chapter type
            :param _code_objects: a list of tuples (code object, object name, code)
            :type _code_objects: list(tuple(CodeItem, str, str))
            :param _underlying_code_objects: a list of tuples (code object, object name, code) of underlying objects
            :type _underlying_code_objects: list(tuple(CodeItem, str, str))
            :param _search_template: a template for the search string in which the object names can be put
            :type _search_template: str
            :return: None
            :rtype: None
            """

            for code_object, code_object_name, code in _code_objects:
                for other_code_item, other_name, other_code in _underlying_code_objects:
                    search_string = _search_template.replace(place_holder, other_name)
                    if not code.find(search_string) == -1:
                        if gui & GUI_SELECT:
                            code_object.dependencies.append(other_code_item)
                        elif gui & GUI_COMPARE:
                            code_object.compare_dependencies.append(other_code_item)

        # helper function
        def code_items_lower(_code_object_chapter_name):
            """
            Returns a list of code items with their code and object names in lower case of a particular chapter
            :param _code_object_chapter_name: the chapter name
            :type _code_object_chapter_name: str
            :return: the requested list of tuples
            :rtype: list(tuple(CodeItem, str, str))
            """
            items = None
            if gui & GUI_SELECT:
                items = [(code_item, code_item.object_name.lower(), code_item.code.lower())
                         for code_item in self.get_chapter_by_name(_code_object_chapter_name).code_items]
            elif gui & GUI_COMPARE:
                items = [(code_item, code_item.object_name.lower(), code_item.compare_code.lower())
                         for code_item in self.get_chapter_by_name(_code_object_chapter_name).code_items]
            return items

        # construct the searches in a list of tuples:
        # 1 the items analysed
        # 2 the underlying items
        # 3 the search string template

        searches = list()
        searches.append(('WRAPPERS', 'DATASOURCES', f"datasourcename={place_holder}"))
        searches.append(('BASE VIEWS', 'WRAPPERS', f"wrapper (jdbc {place_holder})"))
        searches.append(('BASE VIEWS', 'WRAPPERS', f"wrapper (df ' {place_holder})"))
        searches.append(('BASE VIEWS', 'WRAPPERS', f"wrapper (ldap {place_holder})"))
        searches.append(('VIEWS', 'BASE VIEWS', f"from {place_holder}"))
        searches.append(('VIEWS', 'VIEWS', f"from {place_holder}"))
        searches.append(('ASSOCIATIONS', 'VIEWS', f" {place_holder} "))

        # perform the searches and store dependencies
        for chapter_name, underlying_chapter_name, search_template in searches:
            code_objects = code_items_lower(chapter_name)
            underlying_code_objects = code_items_lower(underlying_chapter_name)
            find_dependencies(code_objects, underlying_code_objects, search_template)

    def get_dependees(self, gui: int):
        """Method that fills the code item's dependees list.

        Only direct dependees (objects that depend on this object) are stored.
        :param gui: The mode flag of operation
        :type gui: int
        :return: None
        :rtype: None
        """

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
                if gui & GUI_SELECT:
                    item_dependency.dependees.append(item)
                elif gui & GUI_COMPARE:
                    item_dependency.compare_dependees.append(item)

            dependees = self.unique_list(dependees)

            if gui & GUI_SELECT:
                item.dependencies = dependencies
                item.dependees = dependees
            elif gui & GUI_COMPARE:
                item.compare_dependencies = dependencies
                item.compare_dependees = dependees

    @staticmethod
    def unique_list(_list: list):
        """Function that turns a list into a list with unique items.

        Keeping the sort order.

        :param _list: the list to make unique
        :type _list: list
        :return: the list made unique
        :rtype: list
        """
        new_list = list()
        for item in _list:
            if item not in new_list:
                new_list.append(item)
        return new_list

    def change_view(self, mode: int)->bool:
        """Method that swaps the tree items from VQL View to Denodo file structure view and back.

        The actual switch is done in switch_view function.
        This function handles the surrounding aspects.

        :param mode: the mode flag with bits for the new view either VQL_VIEW or DENODO_VIEW
        :type mode: int
        :return: Success or not
        :rtype: bool
        """

        gui = mode & (GUI_NONE | GUI_SELECT | GUI_COMPARE)
        if self.view & mode:
            return True

        if mode & VQL_VIEW:
            if self.storage_list:
                self.switch_view()
                self.view = VQL_VIEW
                return True
            else:
                # build a VQL_View
                pass
        elif mode & DENODO_VIEW:
            if self.storage_list:
                self.switch_view()
                self.view = DENODO_VIEW
                return True
            else:
                # build denodo view
                if self.build_denodo_view(gui):
                    self.change_view(mode)
        return False

    def switch_view(self):
        """Method to switch view between VQL or Denodo file structure.

        Store the children of the root item of the tree widget
        and replace them with the stored ones.
        :return: None
        :rtype: None
        """

        temp = self.root.takeChildren()
        self.root.addChildren(self.storage_list)
        self.storage_list = temp

    def build_denodo_view(self, gui: int)->bool:
        """Method that builds up the Denodo folder structure.

        Using chapter items as folders and adds code_items as children.
        This structure is stored in the storage list
        and shown when the view is switched.
        :param gui: flag to indicate compare or normal select operations
        :type gui: int
        :return: Success or not
        :rtype: bool
        """

        folders = dict()
        self.pack()
        # get the list of folders and all code items in them
        for chapter, code_item in self.get_code_items():
            if code_item.denodo_folder not in folders.keys():
                folders[code_item.denodo_folder] = list()
                folders[code_item.denodo_folder].append(code_item)
            else:
                folders[code_item.denodo_folder].append(code_item)

        temp_widget = VqlModel(None)
        temp_root = temp_widget.denodo_root

        old_depth = 1
        parent_item = temp_root
        folder_item = None
        for folder, code_items in folders.items():
            if folder:
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
            else:
                return False

        self.storage_list = temp_root.takeChildren()
        return True

    def remove_compare(self):
        """Method to remove compare code .

        It resets the items as if still in the GUI_SELECT state.
        :return: None
        :rtype: None
        """
        for _, item in self.get_code_items():
            item.remove_compare()
