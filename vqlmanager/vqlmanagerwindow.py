#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
VQLManagerWindow Class
The main window GUI class for the application

file: vqlmanagerwindow.py
Dependencies: vqlmanager, PyQt5

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""
__author__ = 'andretreebus@hotmail.com (Andre Treebus)'

# standard library
from pathlib import Path
import subprocess
import sys
import asyncio
from functools import partial
# other libs
from PyQt5.QtCore import QSize, QRect, QFileInfo, QTimer, QVariant, QSettings, QPoint
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidgetItemIterator, qApp, QMenu
from PyQt5.QtWidgets import QGridLayout, QSizePolicy, QHBoxLayout, QWidget, QRadioButton, QButtonGroup
from PyQt5.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PyQt5.QtWidgets import QTextEdit, QStatusBar, QAction, QMenuBar, QFileDialog, QMessageBox, QScrollArea
from vqlmanager.vql_manager_core import *
from vqlmanager.vql_model import VqlModel
from vqlmanager.code_item import CodeItem
from vqlmanager.chapter import Chapter


class DependencyViewer(QWidget):
    """
    Dependency viewer: a window to investigate code objects that are dependent
    on the currently selected, right mouse clicked item in the selection tree view
    """
    def __init__(self, mode: int, code_item: CodeItem, pos: QPoint, parent=None):
        """
        Class Constructor
        :param mode: either GUI_SELECT or GUI_COMPARE
        :param code_item: the code item whose dependees are shown
        :param pos: pos of the window
        :param parent: parent object for this window
        """

        def recurse(n_recurses, _mode: int, _code_item: CodeItem, _child: QTreeWidgetItem):
            """

            :param n_recurses:
            :param _mode:
            :param _code_item:
            :param _child:
            :return:
            """
            n_recurses += 1
            if n_recurses > 100:
                return
            _child.setText(0, _code_item.chapter_name[:-1] + ' : ' + _code_item.object_name)
            dependees = None
            if _mode & GUI_SELECT:
                dependees = _code_item.dependees
            elif _mode & GUI_COMPARE:
                dependees = _code_item.compare_dependees
            for _code_item1 in dependees:
                _child1 = _code_item1.clone()
                _child1.setText(0, _code_item1.chapter_name[:-1] + ' : ' + _code_item1.object_name)
                _child.addChild(_child1)
                recurse(n_recurses, _mode, _code_item1, _child1)

        super(DependencyViewer, self).__init__(parent)
        # self.setGeometry(300, 400)
        self.resize(400, 400)
        self.move(pos)
        self.setMinimumSize(QSize(180, 240))
        if mode & GUI_SELECT:
            self.setWindowTitle('Depencency Viewer')
        elif mode & GUI_COMPARE:
            self.setWindowTitle('Depencency Viewer Compare Code')

        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        layout = QGridLayout(self)

        root_node = code_item.clone()
        header = 'Dependencies on ' + code_item.object_name
        self.dependency_tree = VQLManagerWindow.create_tree_widget(self, QTreeWidget, ITEM_FLAG_SEL, header=header)
        scroll = QScrollArea()
        scroll.setWidget(self.dependency_tree)
        recurse(0, mode, code_item, root_node)
        children = root_node.takeChildren()
        if children:
            self.dependency_tree.addTopLevelItems(children)
        else:
            non_item = QTreeWidgetItem()
            non_item.setText(0, 'None')
            self.dependency_tree.addTopLevelItem(non_item)

        # self.dependency_tree.addTopLevelItem(root_node)
        self.dependency_tree.expandAll()
        VQLManagerWindow.remove_checkboxes(self.dependency_tree)
        layout.addWidget(self.dependency_tree, 0,0)
        self.setLayout(layout)

    @staticmethod
    def get_viewer(mode: int, code_item: CodeItem, pos: QPoint, parent=None):
        """
        Returns the dependency viewer
        :param mode: the mode
        :param code_item: the code item whose depedees are shown
        :param pos: position of the code_item
        :param parent: parent
        :return: None
        """
        viewer = DependencyViewer(mode, code_item, pos, parent)
        result = viewer.show()
        return result


class VQLManagerWindow(QMainWindow):
    """
    Main Gui Class.
    """
    def __init__(self, parent=None):
        """
        Constructor of the Window Class
        :param parent: The owner/parent of the instance
        :type parent: Qt.Window
        :rtype: None
        """
        logger.info("Start Window creation")
        # initialize main window calling its parent
        super(VQLManagerWindow, self).__init__(parent, Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)  # close children on exit
        # root is the folder from which this file runs
        self._root = Path(QFileInfo(__file__).absolutePath())
        images = self._root / 'images'

        self.resize(1200, 800)
        self.setMinimumSize(QSize(860, 440))
        self.setIconSize(QSize(32, 32))
        self.setWindowIcon(QIcon(str(images / 'splitter.png')))
        self.setWindowTitle(APPLICATION_NAME)

        self.select_button_labels = {'All': white, 'Lost': red, 'New': green, 'Same': white, 'Changed': yellow}
        self.diff_button_labels = {'Original': white, 'New': green, 'Changes': yellow}

        # instantiate widgets
        self.mainwidget = QWidget(self, flags=Qt.Widget)
        self.layout = QGridLayout(self.mainwidget)

        # create radio buttons
        self.select_buttons, self.select_buttons_group = \
            self.get_buttons_widget(self.mainwidget, self.select_button_labels)
        self.diff_buttons, self.diff_buttons_group = \
            self.get_buttons_widget(self.mainwidget, self.diff_button_labels)

        # create tree widgets VqlModel(self.mainwidget)
        self.all_chapters_treeview = self.create_tree_widget(self.mainwidget, VqlModel, ITEM_FLAG_CHAPTER,
                                                             header='Selection Pane',
                                                             tooltip="")

        self.selected_treeview = self.create_tree_widget(self.mainwidget, QTreeWidget, ITEM_FLAG_SEL,
                                                         header='View Pane',
                                                         tooltip="Selected parts: Click to view source code")

        # create labels
        self.code_text_edit_label = QLabel(self.mainwidget)
        self.mode_label = QLabel(self.mainwidget)
        self.base_repository_label = QLabel(self.mainwidget)
        self.compare_repository_label = QLabel(self.mainwidget)
        self.selection_viewer_label = QLabel(self.mainwidget)

        # create source code view
        self.code_text_edit = QTextEdit(self.mainwidget)

        # create statusbar
        self.statusBar = QStatusBar(self)

        #  Create Actions and Menubar ###############################################################################
        self.open_file_action = QAction(QIcon(str(images / 'open_file.png')), '&Open File', self)
        self.open_folder_action = QAction(QIcon(str(images / 'open_repo.png')), 'Open &Repository', self)
        self.export_file_action = QAction(QIcon(str(images / 'save_file.png')), 'Save As File', self)
        self.export_folder_action = QAction(QIcon(str(images / 'save_repo.png')), '&Save As Repository', self)
        self.exit_action = QAction(QIcon(str(images / 'exit.png')), '&Exit', self)

        # Create recent file menu
        self.recent_file_actions = list()
        self.recent_repository_actions = list()
        self.compare_recent_file_actions = list()
        self.compare_recent_repository_actions = list()

        for i in range(MAX_RECENT_FILES):
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_SELECT | BASE_FILE))
            self.recent_file_actions.append(action)
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_SELECT | BASE_REPO))
            self.recent_repository_actions.append(action)
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_COMPARE | COMP_FILE))
            self.compare_recent_file_actions.append(action)
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_COMPARE | COMP_REPO))
            self.compare_recent_repository_actions.append(action)

        # create compare with File menu
        self.open_compare_file_action = \
            QAction(QIcon(str(images / 'open_file.png')), '&Open File to Compare', self)
        self.open_compare_folder_action = \
            QAction(QIcon(str(images / 'open_repo.png')), 'Open &Repository to Compare', self)
        self.denodo_folder_structure_action = \
            QAction(QIcon(str(images / 'open_repo.png')), 'Denodo Folder Structure', self)

        # Reset everything
        self.reset_action = QAction(QIcon(str(images / 'reset.png')), 'Reset &Everything', self)
        # create about actions
        self.about_action = QAction("&About", self)
        self.about_qt_action = QAction("About &Qt", self)

        # Menu
        self.menubar = QMenuBar(self)
        self.filemenu = QMenu()
        self.recent_file_separator = None
        self.recent_file_menu = QMenu()
        self.recent_repository_separator = None
        self.recent_repository_menu = QMenu()

        self.compare_menu = QMenu()
        self.compare_recent_file_menu = QMenu()
        self.compare_recent_repository_menu = QMenu()
        self.compare_recent_repository_separator = None
        self.compare_recent_file_separator = QMenu()

        self.help_menu = QMenu()

        self.options_menu = QMenu()
        self.update_timer = QTimer()

        self.all_chapters_treeview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.all_chapters_treeview.customContextMenuRequested.connect(self.on_right_click)

        # Format and setup all widgets
        self.setup_ui()

        # Initialize class properties ###########################################################################

        self.working_folder = None
        self.base_repository_file = None
        self.base_repository_folder = None
        self.compare_repository_file = None
        self.compare_repository_folder = None

        self._mode = 0

        self.switch_to_mode(GUI_NONE)
        self.code_show_selector = ORIGINAL_CODE
        self.code_text_edit_cache = None
        logger.info("Finished Window creation")

    @staticmethod
    def create_tree_widget(parent: QWidget, class_type, flags: int, header=None, tooltip=None)\
            ->Union[VqlModel, QTreeWidget]:
        """Factory for instances of a QTreeWidget or VqlModel

        :param parent: The parent of the widget, in which it is placed
        :type parent: QWidget
        :param class_type: Either a QTreeWidget or an inherited VqlModel
        :type class_type: class
        :param flags: the flags on the QTreeWidget
        :type flags: int
        :param header: The header of the widget
        :type header: str
        :param tooltip: Initial tooltip
        :type tooltip: str
        :return: the TreeWidget created
        :rtype: VqlModel or QTreeWidget
        """
        tree_widget = class_type(parent)
        tree_widget.invisibleRootItem().setFlags(flags)
        tree_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree_widget.setSelectionMode(QAbstractItemView.NoSelection)
        tree_widget.setUniformRowHeights(True)
        if header:
            tree_widget.setHeaderLabel(header)
        if tooltip:
            tree_widget.setToolTip(tooltip)
        tree_widget.setToolTipDuration(2000)
        tree_widget.setColumnCount(1)
        return tree_widget

    def new_tree_data(self, mode: int)->int:
        """Function resets the data in the trees so the are new and shiny.

        :param mode: Flags
        :type mode: int
        :return: the new mode
        :rtype: int
        """

        new_mode = GUI_NONE
        if mode & GUI_NONE:
            self.all_chapters_treeview.clear()
            self.selected_treeview.clear()
            self.all_chapters_treeview = self.create_tree_widget(
                self.mainwidget, VqlModel, ITEM_FLAG_CHAPTER, header='Selection Pane', tooltip="")

            self.selected_treeview = self.create_tree_widget(
                self.mainwidget, QTreeWidget, ITEM_FLAG_SEL, header='View Pane',
                tooltip="Selected parts: Click to view source code")
            new_mode = GUI_NONE

        elif mode & GUI_SELECT:
            self.all_chapters_treeview.remove_compare()
            strip_list = [GUI_COMPARE, COMP_REPO, COMP_FILE, COMP_LOADED]
            new_mode = self.mode_strip(self.get_mode(), strip_list)
        return new_mode

    @staticmethod
    def mode_strip(mode: int, strip_list: List[int])->int:
        """Removes flags in the strip_list from the mode flag.

        Normally this is done with mode = mode & ~flag , but since python has not unsigned integers we use subtract
        :param mode: the mode flags
        :type mode: int
        :param strip_list: the flag to remove
        :type strip_list: list(int)
        :return: an new mode without stripped flags
        :rtype: int
        """
        for constant in strip_list:
            if mode & constant:
                mode -= constant
        return mode

    @staticmethod
    def resize_widget(some_widget: QWidget):
        """Sets size policy on the widget

        :param some_widget: a widget
        :type some_widget: QWidget
        :return: None
        :rtype: None
        """
        some_widget.setMinimumSize(QSize(PANE_WIDTH, 0))
        some_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_ui(self):
        """Function setup up all widgets

        :return: None
        :rtype: None
        """
        logger.debug("Start setup window ui")
        self.layout.setContentsMargins(23, 23, 23, 23)
        self.layout.setSpacing(8)

        # Add Widgets ####################################################################################

        self.resize_widget(self.all_chapters_treeview)
        self.resize_widget(self.selected_treeview)
        self.resize_widget(self.code_text_edit_label)
        self.resize_widget(self.mode_label)
        self.resize_widget(self.selection_viewer_label)
        self.resize_widget(self.compare_repository_label)
        self.resize_widget(self.base_repository_label)
        self.resize_widget(self.code_text_edit)
        self.resize_widget(self.select_buttons)
        self.resize_widget(self.diff_buttons)

        self.select_buttons.setHidden(True)
        self.diff_buttons.setHidden(True)
        self.code_text_edit.setLineWrapMode(0)
        self.code_text_edit.setReadOnly(True)
        self.code_text_edit.setText("non selected")
        self.code_text_edit_label.setText("Command:")

        #  Layout ################################################################################
        # left pane
        self.layout.addWidget(self.mode_label,                0, 0, 1, 2)
        self.layout.addWidget(self.base_repository_label,     1, 0, 1, 2)
        self.layout.addWidget(self.compare_repository_label,  2, 0, 1, 2)
        self.layout.addWidget(self.select_buttons,            3, 0, 1, 1)
        self.layout.addWidget(self.all_chapters_treeview,     4, 0, 4, 1)

        # right pane

        self.layout.addWidget(self.selection_viewer_label,  3, 1, 1, 1)
        self.layout.addWidget(self.selected_treeview,       4, 1, 1, 1)
        self.layout.addWidget(self.code_text_edit_label, 5, 1, 1, 1)
        self.layout.addWidget(self.diff_buttons,            6, 1, 1, 1)
        self.layout.addWidget(self.code_text_edit, 7, 1, 1, 1)

        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)
        self.layout.setRowStretch(3, 1)

        self.layout.setRowStretch(4, 12)
        self.layout.setRowStretch(5, 1)
        self.layout.setRowStretch(6, 1)
        self.layout.setRowStretch(7, 12)

        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 2)

        self.statusBar.setMinimumSize(QSize(0, 20))
        self.statusBar.showMessage("Ready")
        self.setStatusBar(self.statusBar)

        # Parent mainWidget to the QMainWindow
        self.setCentralWidget(self.mainwidget)

        #  Actions and Menubar ###############################################################################
        # Open File
        self.open_file_action.setShortcut('Ctrl+O')
        self.open_file_action.setStatusTip('Open Single VQL File')
        self.open_file_action.triggered.connect(lambda: self.on_open(GUI_SELECT | BASE_FILE))

        # Open Repository
        self.open_folder_action.setShortcut('Ctrl+R')
        self.open_folder_action.setStatusTip('Open a repository containing folders with separate vql scripts')
        self.open_folder_action.triggered.connect(lambda: self.on_open(GUI_SELECT | BASE_REPO))

        # Save As File
        self.export_file_action.setStatusTip('Save selection to a repository file')
        self.export_file_action.triggered.connect(lambda: self.on_save(FILE))

        # Save As Repository
        self.export_folder_action.setShortcut('Ctrl+S')
        self.export_folder_action.setStatusTip('Save selection to a repository folder')
        self.export_folder_action.triggered.connect(lambda: self.on_save(REPO))

        # Exit App
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.setStatusTip('Exit application')
        self.exit_action.triggered.connect(QApplication.quit)

        # Compare with File
        self.open_compare_file_action.setShortcut('Ctrl+O')
        self.open_compare_file_action.setStatusTip('Open Single VQL File')
        self.open_compare_file_action.triggered.connect(lambda: self.on_open(GUI_COMPARE | COMP_FILE))

        # Compare with Folder
        self.open_compare_folder_action.setShortcut('Ctrl+R')
        self.open_compare_folder_action.setStatusTip('Open a repository containing folders with separate vql scripts')
        self.open_compare_folder_action.triggered.connect(lambda: self.on_open(GUI_COMPARE | COMP_REPO))

        self.denodo_folder_structure_action.setShortcut('Ctrl+D')
        self.denodo_folder_structure_action.setStatusTip('Switch to DENODO View')
        self.denodo_folder_structure_action.setCheckable(True)
        self.denodo_folder_structure_action.triggered.connect(self.on_switch_view)

        # Reset everything
        self.reset_action.setStatusTip('Reset the application to a clean state')
        self.reset_action.triggered.connect(lambda: self.on_reset())

        self.about_action.setStatusTip("Show the application's About box")
        self.about_action.triggered.connect(self.on_about_vql_manager)
        self.about_qt_action.setStatusTip("Show the Qt library's About box")
        self.about_qt_action.triggered.connect(self.on_about_qt)

        #  Menu
        self.menubar.setGeometry(QRect(0, 0, 1200, 23))

        self.filemenu = self.menubar.addMenu('&File')
        self.filemenu.addAction(self.open_file_action)
        self.filemenu.addAction(self.open_folder_action)
        self.filemenu.addAction(self.export_file_action)
        self.filemenu.addAction(self.export_folder_action)

        self.recent_file_separator = self.filemenu.addSeparator()
        self.recent_file_menu = self.filemenu.addMenu('Recent Files')
        for i in range(MAX_RECENT_FILES):
            self.recent_file_menu.addAction(self.recent_file_actions[i])

        self.recent_repository_separator = self.filemenu.addSeparator()
        self.recent_repository_menu = self.filemenu.addMenu('Recent Repositories')
        for i in range(MAX_RECENT_FILES):
            self.recent_repository_menu.addAction(self.recent_repository_actions[i])

        self.filemenu.addSeparator()
        self.filemenu.addAction(self.exit_action)

        self.compare_menu = self.menubar.addMenu('&Compare')
        self.compare_menu.addAction(self.open_compare_file_action)
        self.compare_menu.addAction(self.open_compare_folder_action)

        self.compare_recent_file_separator = self.compare_menu.addSeparator()
        self.compare_recent_file_menu = self.compare_menu.addMenu('Recent Files')
        for i in range(MAX_RECENT_FILES):
            self.compare_recent_file_menu.addAction(self.compare_recent_file_actions[i])

        self.compare_recent_repository_separator = self.compare_menu.addSeparator()
        self.compare_recent_repository_menu = self.compare_menu.addMenu('Recent Repositories')
        for i in range(MAX_RECENT_FILES):
            self.compare_recent_repository_menu.addAction(self.compare_recent_repository_actions[i])

        self.update_recent_file_actions()

        self.options_menu = self.menubar.addMenu('&Options')
        self.options_menu.addAction(self.denodo_folder_structure_action)
        self.options_menu.addSeparator()
        self.options_menu.addAction(self.reset_action)

        self.help_menu = self.menubar.addMenu('&Help')
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.about_qt_action)

        # Callbacks Slots and Signals #####################################################
        self.all_chapters_treeview.itemChanged.connect(self.on_selection_changed)
        self.selected_treeview.itemClicked.connect(self.on_click_item_selected)

        # Radio buttons
        self.select_buttons_group.buttonClicked.connect(self.on_select_buttons_clicked)
        self.diff_buttons_group.buttonClicked.connect(self.on_diff_buttons_clicked)

        # connect update timer
        self.update_timer.timeout.connect(self.update_tree_widgets)
        logger.debug("Finished setup window ui")

    def update_recent_file_actions(self):
        """Upates the Action objects in the menu to reflect the recent file storage.

        :return: None
        :rtype: None
        """
        settings = QSettings(COMPANY, APPLICATION_NAME)
        files = settings.value(RECENT_FILES, type=list)
        repositories = settings.value(RECENT_REPOSITORIES, type=list)

        len_files = len(files)
        len_repositories = len(repositories)

        menus = [self.recent_file_actions, self.compare_recent_file_actions]
        for actions in menus:
            for i in range(MAX_RECENT_FILES):
                if i < len_files:
                    file = Path(files[i])
                    text = str(i + 1) + ': ' + str(file.name)
                    actions[i].setText(text)
                    actions[i].setData(file)
                    actions[i].setVisible(True)
                    actions[i].setStatusTip(str(file))
                else:
                    actions[i].setVisible(False)

        menus = [self.recent_repository_actions, self.compare_recent_repository_actions]
        for actions in menus:
            for i in range(MAX_RECENT_FILES):
                if i < len_repositories:
                    repository = Path(repositories[i])
                    text = str(i + 1) + ': ' + str(repository.name)
                    actions[i].setText(text)
                    actions[i].setData(repository)
                    actions[i].setVisible(True)
                    actions[i].setStatusTip(str(repository))
                else:
                    actions[i].setVisible(False)

        if len_files > 0:
            self.recent_file_separator.setVisible(True)
            self.compare_recent_file_separator.setVisible(True)
        else:
            self.recent_file_separator.setVisible(False)
            self.compare_recent_file_separator.setVisible(False)

        if len_repositories > 0:
            self.recent_repository_separator.setVisible(True)
            self.compare_recent_repository_separator.setVisible(True)
        else:
            self.recent_repository_separator.setVisible(False)
            self.compare_recent_repository_separator.setVisible(False)

    def get_all_dependees(self, item: CodeItem, items=list())->List[CodeItem]:
        """Recursive function to gather all the items that are dependent on this one.

        :param item: a CodeItem object
        :type item: CodeItem
        :param items: the list of dependees
        :type items: list(CodeItems)
        :return: the list of dependees
        :rtype: list(CodeItems)
        """
        for item in item.dependees:
            items.append(item)
            self.get_all_dependees(item, items)
        else:
            return items

    @staticmethod
    def get_buttons_widget(main_widget: QWidget, button_dict: dict)->Tuple[QWidget, QButtonGroup]:
        """Constructs a series of related radio buttons used to filter CodeItems.

        :param main_widget: the parent widget
        :type main_widget: QWidget
        :param button_dict: A dict with names and colors
        :type button_dict: dict
        :return: A tuple of widget and the group its in
        :rtype: tuple(Qwidget, QWidgetGroup)
        """
        layout = QHBoxLayout()  # layout for the central widget
        widget = QWidget(main_widget)  # central widget
        widget.setLayout(layout)
        group = QButtonGroup(widget)  # Number group
        first_button = True
        for text, label_color in button_dict.items():
            btn = QRadioButton(text)
            btn.setStyleSheet("color: " + label_color)
            if first_button:
                btn.setChecked(True)
                first_button = False
            group.addButton(btn)
            layout.addWidget(btn, 0, Qt.AlignLeft)
        return widget, group

    def get_mode(self)->int:
        """Getter for the mode flag

        :return: the current mode
        :rtype: int
        """
        return self._mode

    def switch_to_mode(self, new_mode: int):
        """Redresses the window to reflect the new mode
        :param new_mode: the new mode
        :return: None
        :rtype: None
        """
        logger.debug("Starting setting mode: " + show_mode(new_mode))
        if new_mode & GUI_NONE or new_mode == 0:
            self.mode_label.setText('View Mode: None')
            self.base_repository_label.setText('No file loaded')
            self.compare_repository_label.setText('')
            self.all_chapters_treeview.setHeaderLabel('Selection Pane')
        elif new_mode & GUI_SELECT:
            self.mode_label.setText("View Mode: Selection")
            self.diff_buttons.setHidden(True)
            self.select_buttons.setHidden(True)
            if new_mode & BASE_LOADED:
                if new_mode & BASE_FILE:
                    self.base_repository_label.setText('File : ' + str(self.base_repository_file))
                elif new_mode & BASE_REPO:
                    self.base_repository_label.setText('Repository : ' + str(self.base_repository_folder))
            self.compare_repository_label.setText('')
        elif new_mode & GUI_COMPARE:
            self.mode_label.setText("View Mode: Compare")
            self.diff_buttons.setHidden(False)
            self.select_buttons.setHidden(False)
            if new_mode & COMP_LOADED:
                if new_mode & COMP_FILE:
                    self.compare_repository_label.setText('File : ' + str(self.compare_repository_file))
                elif new_mode & COMP_REPO:
                    self.compare_repository_label.setText('Repository : ' + str(self.compare_repository_folder))
        if new_mode & VQL_VIEW:
            self.denodo_folder_structure_action.setChecked(False)
            self.on_switch_view()

        self.all_chapters_treeview.switch_mode(new_mode)
        self._mode = new_mode
        # self.statusBar.showMessage(show_mode(self._mode))
        logger.debug("Finished setting mode: " + show_mode(self._mode))

    # Event handlers for opening and saving models

    def on_open_recent_files(self, index: int, mode: int):
        """Event handler for the click on a recent files menu item.

        This function collects the data from the OS storage about the recent file/repo list
        and initiates a loading process.

        :param index: Index of the menu item clicked
        :type index: int
        :param mode: mode flag of the application
        :type: int
        :return: None
        :rtype: None
        """

        if mode & FILE:
            file_list = RECENT_FILES
        elif mode & REPO:
            file_list = RECENT_REPOSITORIES
        else:
            return

        settings = QSettings(COMPANY, APPLICATION_NAME)
        files = settings.value(file_list, type=list)

        if files:
            file = files[index]
            self.on_open(mode, file)

    def on_select_buttons_clicked(self, button: QRadioButton):
        """Event handler for the radio buttons in the left pane.

        To filter the VqlModel tree based on color of the items.
        :param button: the button clicked
        :type button: QRadioButton
        :return: None
        :rtype: None
        """
        if button.text() == 'All':
            color = None
        else:
            color = translate_colors(self.select_button_labels[button.text()], to_text=False)
        self.all_chapters_treeview.color_filter = color
        self.update_tree_widgets()

    def on_diff_buttons_clicked(self, button: QRadioButton):
        """Event handler for the radio buttons in the right pane.

        To filter the view in the code edit widget.
        :param button: the button clicked
        :type button: QRadioButton
        :return: None
        :rtype: None
        """

        text = button.text()
        if text == 'Original':
            self.code_show_selector = ORIGINAL_CODE
        elif text == 'New':
            self.code_show_selector = COMPARE_CODE
        elif text == 'Changes':
            self.code_show_selector = DIFF_CODE
        self.show_code_text()

    def on_open(self, new_mode: int, load_path=None):
        """Event handler Open File menu items and Compare open items.

        This function is the starting point for loading a model based on a .vql file or a repository
        :param new_mode: the mode of opening
        :type new_mode: int
        :param load_path: optional parameter for loading from a recent file list
        :type load_path: Path
        :return: None
        :rtype: None
        """
        logger.info(f"Open file or repository {load_path if load_path else ''} in mode: {show_mode(new_mode)} mode.")
        file = None
        folder = None

        if load_path:
            if new_mode & FILE:
                    file = Path(load_path)
            elif new_mode & REPO:
                    folder = Path(load_path)
            else:
                return

        current_mode = self.get_mode()

        if new_mode & GUI_SELECT:
            if current_mode & (BASE_LOADED | COMP_LOADED):
                # some base model is open:
                if self.ask_drop_changes():
                    self.switch_to_mode(self.new_tree_data(GUI_NONE))
                    self.on_open(new_mode)  # recurse to the begin
                else:
                    return
            else:  # ok we can load
                if new_mode & BASE_FILE:
                    if not file:
                        file = self.ask_file_open()
                    if file:
                        self.run(self.load_model_from_file(file, BASE_FILE | GUI_SELECT))
                elif new_mode & BASE_REPO:
                    if not folder:
                        folder = self.ask_repository_open()
                    if folder:
                        self.run(self.load_model_from_repository(folder, BASE_REPO | GUI_SELECT))

        elif new_mode & GUI_COMPARE:
            if not current_mode & BASE_LOADED:  # there is a base model
                self.message_to_user("No repository loaded yet")
                return

            if current_mode & COMP_LOADED:  # there is a compare going on
                if self.ask_drop_changes():
                    self.switch_to_mode(self.new_tree_data(GUI_SELECT))
                    self.on_open(new_mode)  # recurse to the begin
                else:
                    return
            else:  # ok we can load
                if new_mode & COMP_FILE:
                    if not file:
                        file = self.ask_file_open()
                    if file:
                        self.run(self.load_model_from_file(file, COMP_FILE | GUI_COMPARE))
                elif new_mode & COMP_REPO:
                    if not folder:
                        folder = self.ask_repository_open()
                    if folder:
                        self.run(self.load_model_from_repository(folder, COMP_REPO | GUI_COMPARE))
        logger.info("File or repository loaded.")

    def on_right_click(self, pos: QPoint):
        """Event handler for the right click event on the all_chapter_treeview widget.

        :param pos: position of the click
        :return: None
        :rtype: None
        """
        if pos:
            item = self.all_chapters_treeview.itemAt(pos)
            if item.class_type == CodeItem:
                if self._mode & GUI_SELECT:
                    DependencyViewer.get_viewer(self._mode, item, pos, self)
                elif self._mode & GUI_COMPARE:
                    if item.compare_code:
                        DependencyViewer.get_viewer(self._mode, item, pos, self)
                    else:
                        self.message_to_user('This item does not exist in the new (compare) code base')

    @staticmethod
    def run(task):
        """Function to start asynchronous tasks.

        :param task: A future function to be ran
        :return: None
        :rtype: None
        """

        if task:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(task)
            loop.close()

    def on_save(self, save_mode: int):
        """Event handler for the Save to File or Save to Repository menu items.

        This function is the starting point for saving a model to a .vql file or repository.
        Only selected items in the base model are saved!

        :return: None
        :rtype: None
        """
        logger.info(f"Saving file or repository in {show_mode(save_mode)} mode.")
        current_mode = self.get_mode()
        if not current_mode & BASE_LOADED:
            self.message_to_user("No repository loaded yet")
            return

        if save_mode & FILE:
            file = self.ask_file_save()
            if file:
                self.run(self.save_model_to_file(file))
                logger.info(f"{file} saved.")
        elif save_mode & REPO:
            folder = self.ask_repository_save()
            if folder:
                self.run(self.save_model_to_repository(folder))
                logger.info(f"{folder} saved.")

    def on_reset(self):
        """Event handler to reset everything.

        This function actually restarts the whole application in a new process.
        Also the recent files and repositories are reset.

        :return: None
        :rtype: None
        """
        logger.info('Application restart.')
        settings = QSettings(COMPANY, APPLICATION_NAME)
        settings.clear()

        app_path = self._root / 'vql_manager.py'
        try:
            subprocess.Popen([sys.executable, app_path])
        except OSError as exception:
            print('ERROR: could not restart application:')
            print('  %s' % str(exception))
        else:
            qApp.quit()

    def on_selection_changed(self, item: Union[Chapter, CodeItem], *_):
        """Event handler for changes of the selection (check boxes) in the all_chapters_treeview (VqlModel).

        :param item: The item that changed in the all_chapters_treeview
        :type item: QTreeWidgetItem
        :param _: not used
        :return: None
        :rtype: None
        """
        def sel(_item: Union[Chapter, CodeItem])->bool:
            """
            if an item is selected
            :param _item: the item
            :return:
            """
            return False if _item.checkState(0) == UNCHECKED else True

        logger.debug('Item clicked on Selection Pane: ' + item.text(0))
        mode = self.get_mode()

        if mode & GUI_SELECT:
            if item.class_type == CodeItem:
                if not sel(item):
                    if any([sel(dependee) for dependee in item.dependees]):
                        self.message_to_user('This item has other items that are dependent on it.')

        elif mode & GUI_COMPARE:
            if item.class_type == CodeItem:
                if sel(item):
                    if not item.compare_code:
                        item.compare_code = item.code
                        items = {code_item.object_name for code_item in item.dependencies}
                        dependencies_not_met = [item for item in items if not item.compare_code or not sel(item)]
                        if any(dependencies_not_met):
                            self.message_to_user('This item has dependencies not met. '
                                                 'Check these: ' + '; '.join(dependencies_not_met))
                else:
                    dependees_orphaned = [sel(dependee) for dependee in item.compare_dependees]
                    if any(dependees_orphaned):
                        self.message_to_user('This item has other items that are dependent on it.'
                                             'Check these: ' + '; '.join(dependees_orphaned))

        self.all_chapters_treeview.changed = True
        self.update_timer.start(100)

    def on_click_item_selected(self, item: QTreeWidgetItem, col: int):
        """Event handler for looking up code in the View Pane (code item clicked).

        :param item: The CodeItem clicked on the Selection Tree
        :type item: QTreeWidgetItem
        :param col: The column --always zero, we only use 1 column in tree widgets
        :type col: int
        :return: None
        :rtype: None
        """

        if item:
            item_data = item.data(col, Qt.UserRole)
            if item_data['class_type'] == CodeItem:
                logger.debug('CodeItem clicked on View Pane: ' + item.text(0))
                cache = dict()
                cache['object_name'] = item_data['object_name']
                cache['code'] = item_data['code']
                cache['compare_code'] = item_data['compare_code']
                self.code_text_edit_cache = cache
                self.show_code_text()
            else:
                self.code_text_edit_cache = None

    def on_about_vql_manager(self):
        """Event handler for the click on the About menu item in the help menu.

        :return: None
        :rtype: None
        """
        QMessageBox.about(self, 'About ' + self.windowTitle(), about_text)

    def on_about_qt(self):
        """Event handler for the click on the About Qt menu item in the help menu.

        It uses the boilerplate Qt about box
        :return: None
        :rtype: None
        """
        QMessageBox.aboutQt(self, self.windowTitle())

    @staticmethod
    def format_source_code(object_name: str, raw_code: str, code_type: int)->str:
        """Creates html for the code edit widget to view the source code.

        :param object_name: Name of the CodeItem
        :type object_name: str
        :param raw_code: the raw code string
        :type raw_code: str
        :param code_type: and indicator what code is formatted either ORIGINAL_CODE or COMPARE_CODE or DIFF_CODE
        :return: the constructed html
        :rtype: str
        """
        if not raw_code:
            return ''

        html = ''
        if code_type & (ORIGINAL_CODE | COMPARE_CODE):
            code = raw_code.replace('\n', '<br />')
            code = code.replace('    ', ' &nbsp; &nbsp; &nbsp; &nbsp; ')

            for word in get_reserved_words():
                code = code.replace(' ' + word + ' ', ' <strong>' + word + '</strong> ')  # rude method here
            code = code.replace('<br />', '<br />\n')

            body = '<p style="color:' + white + '">' + code + '</p>'
            body = body.replace(object_name, '<font color="' + red + '">' + object_name + '</font>')
            html = doc_template(object_name, body)

        elif code_type & DIFF_CODE:
            html = doc_template(object_name, raw_code)
        return html

    def on_switch_view(self):
        """Event handler for the click on the menu item to switch between VQL view or Denodo view.

        :return: None
        :rtype: None
        """

        if self._mode & BASE_LOADED:
            if self.denodo_folder_structure_action.isChecked():
                if self.all_chapters_treeview.change_view(self._mode | DENODO_VIEW):
                    self.denodo_folder_structure_action.setText('Switch to VQL View')
                    logger.debug('Switching to Denodo View')
                else:
                    self.message_to_user('Denodo view not possible. Missing folders in the code.')
                    self.denodo_folder_structure_action.setChecked(False)
                    logger.debug('Switch to Denodo View aborted')
            else:
                logger.debug('Switching to VQL View')
                self.denodo_folder_structure_action.setText('Switch to DENODO View')
                self.all_chapters_treeview.change_view(self._mode | VQL_VIEW)
            self.update_tree_widgets()

    # dialogs for opening and saving

    def ask_file_open(self)->Union[Path, None]:
        """Asks user which file to open to via a dialog.

        :return: filepath
        :rtype: Path
        """
        logger.info('Asking file to open.')
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setDefaultSuffix('vql')
        dialog.setWindowTitle("Select single VQL file")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)

        open_path = str(self.working_folder if self.working_folder else Path.cwd())

        filename, _ = dialog.getOpenFileName(self, "Save File", open_path,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)",
                                             options=QFileDialog.DontResolveSymlinks)
        if not filename:
            return None

        filename = Path(str(filename))

        if not filename.exists():
            self.message_to_user("File does not exist")
            return None

        if not filename.suffix == '.vql':
            self.message_to_user("This file has the wrong extension")
            return None

        logger.info('Got: ' + str(filename))
        return filename

    def ask_repository_open(self)->Union[Path, None]:
        """Asks user which repository (folder) to open via a dialog.

        :return: the folder path
        :rtype: Path
        """
        logger.info('Asking repository to open.')
        open_path = str(self.working_folder if self.working_folder else Path.cwd())

        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setWindowTitle("Select Folder")
        dialog.setViewMode(QFileDialog.List)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        folder = dialog.getExistingDirectory(self, "Open Directory", open_path)

        if not folder:
            return None
        folder = Path(str(folder))
        if not folder.is_dir():
            self.message_to_user("No folder found")
            return None
        logger.info('Got:' + str(folder))
        return folder

    def ask_repository_save(self)->Union[Path, None]:
        """Asks user which folder to save to via a dialog.

        If the folder exists, then asks if overwrite is allowed.

        :return: Folder to store the repository
        :rtype: Path
        """
        logger.info('Asking repository to save.')
        open_path = str(self.working_folder if self.working_folder else Path.cwd())
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        dialog.setFileMode(QFileDialog.Directory)
        folder = dialog.getExistingDirectory(self, "Save to Repository", open_path)

        if not folder:
            return None
        folder = Path(str(folder))

        if not folder.is_dir():
            try:
                folder.mkdir(parents=True)
                return folder
            except OSError as error:
                self.error_message_box('Error', 'Error creating folder', str(error))
                return None

        if any([item_path.exists() for item_path, _
                in self.all_chapters_treeview.get_selected_code_files(self.get_mode(), folder)]):
            if not self.ask_overwrite():
                return None
        logger.info('Got:' + str(folder))
        return folder

    def ask_file_save(self)->Union[Path, None]:
        """Asks which file to save to via a dialog.

        It also checks if the file may be overwritten

        :return: the file path of the file to be written
        :rtype: Path
        """
        logger.info('Asking file to save.')
        open_path = str(self.working_folder if self.working_folder else Path.cwd())
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        dialog.setDefaultSuffix('vql')
        dialog.setFileMode(QFileDialog.AnyFile)
        filename, _ = dialog.getSaveFileName(self, "Save File", open_path,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)")

        if not filename:
            return None  # not cancel pressed
        filename = Path(str(filename))
        filename = filename if filename.suffix else filename.with_suffix('.vql')

        if filename.is_file():
            if not self.ask_overwrite():
                return None
            else:
                filename.unlink()
        logger.info('Got:' + str(filename))
        return filename

    # General purpose dialogs

    def message_to_user(self, message: str):
        """General Messagebox functionality.

        :return: None
        :rtype: None
        """
        logger.debug('Message to user: ' + message)
        msg = QMessageBox(self)
        msg.setWindowTitle("You got a message!")
        msg.setIcon(QMessageBox.Question)
        msg.setText("<strong>" + message + "<strong>")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)
        msg.exec()

    def ask_overwrite(self)->bool:
        """General Messagebox to warn/ask for files to be overwritten.

        :return: Boolean if allowed
        :rtype: bool
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Warning")
        msg.setIcon(QMessageBox.Question)
        msg.setText("<strong>Overwrite File(s)?<strong>")
        msg.setInformativeText("Do you want to overwrite current file(s)?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        if msg.exec() == QMessageBox.Yes:
            return True
        else:
            return False

    def ask_drop_changes(self)->bool:
        """General Messagebox to warn/ask if made changes can be dropped.

        :return: Boolean if allowed
        :rtype: bool
        """
        if not self.all_chapters_treeview.changed:
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle("Warning")
        msg.setIcon(QMessageBox.Question)
        msg.setText("<strong>Drop the changes?<strong>")
        msg.setInformativeText("You are opening another repository,"
                               " that will discard any changes you made?"
                               "Click OK to proceed, and drop the changes.")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Cancel)
        if msg.exec() == QMessageBox.Ok:
            return True
        else:
            return False

    def error_message_box(self, title: str, text: str, error: str):
        """General messagebox if an error happened.

        :param title: Title of dialog window
        :type title: str
        :param text: Main text of dialog window
        :type text: str
        :param error: the error text generated by python
        :type error: str
        :return: None
        :rtype: None
        """
        logger.error(title + str(error))
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setIcon(QMessageBox.Critical)
        msg.setText("<strong>An error has occurred!<strong>")
        msg.setInformativeText(text)
        msg.setDetailedText(error)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)
        msg.exec()

    # Helper function for io to disk

    async def read_file(self, file: Path)->str:
        """General function to read in a file

        :param file: The path to the file
        :type file: Path
        :return: The contents of the file as string
        :rtype: str
        """
        logger.debug('Reading: ' + str(file))
        content = None
        try:
            with file.open() as f:
                content = f.read()
        except (OSError, IOError) as error:
            self.error_message_box("Error", "An error occurred during reading of file: " + str(file), str(error))
        if content:
            logger.debug(f"{str(file)} with {len(content)} characters read.")
        return content

    async def write_file(self, file: Path, content: str)->bool:
        """General function to write a file to disk

        :param file: the path where the file should be written to
        :type file: Path
        :param content: The content to be written as string
        :type content: str
        :return: Boolean on success
        :rtype: bool
        """
        logger.debug('Saving: ' + str(file))
        if file.is_file():
            try:
                file.unlink()
            except (OSError, IOError) as error:
                self.error_message_box("Error", "An error occurred during removal of file : " + str(file), str(error))
                self.statusBar.showMessage("Save error")
                return False

        try:
            with file.open(mode='x') as f:
                written = f.write(content)
                logger.debug(f"Saved {written} characters to {str(file)}")
                return True
        except (OSError, IOError) as error:
            self.error_message_box("Error", "An error occurred during writing of file: " + str(file), str(error))
            return False

    # Saving and loading models

    async def load_model_from_file(self, file: Path, new_mode: int):
        """Loads a single .vql file into the VqlModel instance.

        :param file: path of the file to bew loaded in
        :type file: Path
        :param new_mode: either BASE_FILE or COMP_FILE
        :type new_mode: int
        :return: None
        :rtype: None
        """
        logger.debug(f"Loading model from file in {show_mode(new_mode)} mode")
        self.statusBar.showMessage("Loading model from file.")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        tree = self.all_chapters_treeview
        content = await self.read_file(file)
        current_mode = self.get_mode()

        if content:
            tree.blockSignals(True)
            await tree.parse(content, new_mode)
            self.update_tree_widgets()
            tree.blockSignals(False)
        self.statusBar.showMessage("Ready")

        if new_mode & BASE_FILE:
            self.base_repository_file = file
            new_mode |= BASE_LOADED
        elif new_mode & COMP_FILE:
            self.compare_repository_file = file

            current_base_mode = current_mode & (BASE_REPO | BASE_FILE)
            new_mode |= current_base_mode | COMP_LOADED | BASE_LOADED | COMP_FILE

        self.switch_to_mode(new_mode)
        self.update_tree_widgets()
        self.working_folder = file.resolve().parent
        self.add_to_recent_files(file, FILE)
        QApplication.restoreOverrideCursor()
        logger.debug(f"Loading model from file finished.")

    async def load_model_from_repository(self, folder: Path, new_mode: int):
        """Loads a repository folder structure into the VqlModel instance.

        :param folder: the folder containing the repository
        :type folder: Path
        :param new_mode: flag indication BASE_REPO or COMP_REPO
        :return: None
        :rtype: None
        """
        logger.debug(f"Loading model from repository in {show_mode(new_mode)} mode")

        self.statusBar.showMessage("Loading model")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        existing_folders = {sub_folder for sub_folder in folder.iterdir()}
        possible_folders = {folder / sub_folder for sub_folder in CHAPTER_NAMES}
        matching_folders = existing_folders & possible_folders
        if not matching_folders:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            message = "No repository found. Did not find any matching sub folders."
            self.message_to_user(message)
            self.statusBar.showMessage(message)
            return

        part_files = [folder / sub_folder / LOG_FILE_NAME
                      for sub_folder in CHAPTER_NAMES if folder / sub_folder in matching_folders]
        non_existing_part_files = [str(part_file) for part_file in part_files if not part_file.is_file()]
        existing_part_files = [part_file for part_file in part_files if part_file.is_file()]
        if non_existing_part_files:
            missing = ', '.join(non_existing_part_files)
            self.message_to_user(f"{LOG_FILE_NAME} file(s): {missing} not found. "
                                 f"Make sure your repository is not corrupt")

        all_code_files = list()
        for part_file in existing_part_files:
            file_content = await self.read_file(part_file)
            code_files = [Path(code_file) for code_file in file_content.split('\n')]
            non_existing_code_files = [str(code_file) for code_file in code_files if not code_file.is_file()]
            if non_existing_code_files:
                missing = ', '.join(non_existing_code_files)
                self.message_to_user(f"Code file(s): {missing} not found. Make sure your repository is not corrupt")
            existing_code_files = [(str(code_file.parent.name), code_file)
                                   for code_file in code_files if code_file.is_file()]
            all_code_files.extend(existing_code_files)

        tree = self.all_chapters_treeview
        content = PROP_QUOTE
        for chapter in tree.chapters:
            content += chapter.header
            files = [file for chapter_name, file in all_code_files if chapter_name == chapter.name]
            for file in files:
                content += await self.read_file(file)

        current_mode = self.get_mode()

        if content:
            tree.blockSignals(True)
            await tree.parse(content, new_mode)
            self.update_tree_widgets()
            tree.blockSignals(False)
        else:
            self.statusBar.showMessage("Load Failed")
            QApplication.restoreOverrideCursor()
            return

        if new_mode & BASE_REPO:
            self.base_repository_folder = folder
            new_mode |= BASE_LOADED
        elif new_mode & COMP_REPO:
            self.compare_repository_folder = folder
            current_base_mode = current_mode & (BASE_REPO | BASE_FILE)
            new_mode |= current_base_mode | COMP_LOADED | BASE_LOADED | COMP_REPO

        self.switch_to_mode(new_mode)
        self.working_folder = folder
        self.update_tree_widgets()
        self.add_to_recent_files(folder, REPO)
        QApplication.restoreOverrideCursor()
        self.statusBar.showMessage("Model Loaded")
        logger.debug(f"Repository loaded with new mode {show_mode(self._mode)}")

    async def save_model_to_file(self, file: Path)->bool:
        """Saves the single .vql file.

        :param file: the file!
        :type file: Path
        :return: boolean on success
        :rtype: bool
        """

        logger.debug(f"Saving model to file in {file} in mode: {show_mode(self.get_mode())}")
        tree = self.all_chapters_treeview

        self.statusBar.showMessage("Saving")
        tree.blockSignals(True)
        content = tree.get_code_as_file(self.get_mode(), selected=True)
        tree.blockSignals(False)
        if content:
            if await self.write_file(file, content):
                self.statusBar.showMessage("Ready")
                logger.debug("Saved OK")
                return True
            else:
                self.statusBar.showMessage("Save error")
                logger.debug("Not Saved")
                return False

    async def save_model_to_repository(self, folder: Path)->bool:
        """Saves the model selection to a repository.

        The files are written to chapter_folders
        :param folder: The folder to write the repository
        :type folder: Path
        :return: boolean on success
        :rtype bool
        """
        logger.debug(f"Saving model to repository in folder {folder} in mode: {show_mode(self.get_mode())}")
        self.statusBar.showMessage("Saving")
        if not folder:
            self.statusBar.showMessage("Save Error")
            return False

        tree = self.all_chapters_treeview
        tree.blockSignals(True)

        for part_log_filepath, part_log_content in tree.get_part_logs(folder):

            if not part_log_content:
                self.statusBar.showMessage("Save Error")
                return False

            if not part_log_filepath:
                self.statusBar.showMessage("Save Error")
                return False

            sub_folder = part_log_filepath.parent
            if not sub_folder.is_dir():
                try:
                    logger.debug("Creating Directory.")
                    sub_folder.mkdir(parents=True)
                except (OSError, IOError) as error:
                    self.statusBar.showMessage("Save Error")
                    self.error_message_box("Error", "An error occurred during creation of the folders in : "
                                           + sub_folder, str(error))
                    return False

            if not await self.write_file(part_log_filepath, part_log_content):
                self.statusBar.showMessage("Save Error")
                logger.debug("Saved not OK")
                return False

        for file_path, content in tree.get_selected_code_files(self.get_mode(), folder):
            if not content:
                self.statusBar.showMessage("Save Error")
                logger.debug("Saved not OK")
                return False
            if not file_path:
                self.statusBar.showMessage("Save Error")
                logger.debug("Saved not OK")
                return False
            if not await self.write_file(file_path, content):
                self.statusBar.showMessage("Save Error")
                logger.debug("Saved not OK")
                return False

        tree.blockSignals(False)
        self.statusBar.showMessage("Ready")
        logger.debug("Saved OK")
        return True

    def add_to_recent_files(self, file_path: Path, mode: int):
        """Function adds a file path to the OS storage of recent files.

        :param file_path: The path to add
        :type file_path: Path
        :param mode: selector flag either REPO or FILE
        :type mode: int
        :return: None
        :rtype: None
        """
        logger.debug(f"Adding {file_path} to recent file list in {show_mode(mode)} mode")
        settings = QSettings(COMPANY, APPLICATION_NAME)

        if not settings:
            logger.debug("No resent file settings found.")
            return

        if mode & FILE:
            settings_list = RECENT_FILES
        elif mode & REPO:
            settings_list = RECENT_REPOSITORIES
        else:
            return

        paths = settings.value(settings_list, type=list)
        file = str(file_path)
        if file in paths:
            paths.remove(file)
        paths = [file] + paths
        if len(paths) > MAX_RECENT_FILES:
            paths = paths[:MAX_RECENT_FILES]
        settings.setValue(settings_list, paths)

        self.update_recent_file_actions()
        logger.debug("Path added to recent files or folders.")

    def show_code_text(self):
        """Shows the code of the clicked CodeItem in the Code edit widget.

        :return: None
        :rtype: None
        """

        if self.code_text_edit_cache:
            # convenience names
            item_data = self.code_text_edit_cache
            selector = self.code_show_selector
            put_text = self.code_text_edit.setHtml
            set_title = self.code_text_edit_label.setText
            object_name = item_data['object_name']
            html_code = ''
            if self._mode & GUI_SELECT:
                html_code = self.format_source_code(object_name, item_data['code'], selector)
                set_title("Code: " + object_name)
            elif self._mode & GUI_COMPARE:

                if selector & ORIGINAL_CODE:
                    html_code = self.format_source_code(object_name, item_data['code'], selector)
                    set_title("Original Code: " + object_name)
                elif selector & COMPARE_CODE:
                    html_code = self.format_source_code(object_name, item_data['compare_code'], selector)
                    set_title("New Code: " + object_name)
                elif selector & DIFF_CODE:
                    difference = CodeItem.get_diff(item_data['code'], item_data['compare_code'])
                    html_code = self.format_source_code(object_name, difference, selector)
                    set_title("Differences : " + object_name)
            put_text(html_code)

    def update_tree_widgets(self):
        """Builds/sets new content of the selected_treeview

        Like a screen update.
        Used after the selection in the all_chapters_treeview is changed
        This function copies the selected items and leaves out the chapters that are empty
        The updates are timed because when big changes are made (when whole chapters are unselected)
        the function should not redraw the screen to often.

        :return: None
        :rtype: None
        """
        logger.debug('Update_tree_widgets')
        # stop the update timer
        self.update_timer.stop()
        # store former "blocked" indicator
        blocked = self.all_chapters_treeview.signalsBlocked()

        # block signals while updating
        self.all_chapters_treeview.blockSignals(True)

        # convenience pointer names
        tree_sel = self.selected_treeview
        root_sel = tree_sel.invisibleRootItem()

        tree_all = self.all_chapters_treeview
        root_all = tree_all.invisibleRootItem()
        tree_sel.clear()
        tree_all.pack()
        root_sel.addChildren(root_all.clone().takeChildren())
        VqlModel.unpack(tree_sel)

        # # itemIterator traverses over every node
        self.remove_checkboxes(tree_sel)
        self.all_chapters_treeview.blockSignals(blocked)

    @staticmethod
    def remove_checkboxes(tree: QTreeWidget):
        """

        :param tree:
        :return:
        """
        item_iterator = QTreeWidgetItemIterator(tree)
        while item_iterator.value():
            item = item_iterator.value()
            item.setData(0, Qt.CheckStateRole, QVariant())
            item_iterator += 1
