#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
VQLManagerWindow Class
The main window GUI class for the app


file: vqlmanagerwindow.py
Dependencies: os shutil vql_model.py code_item.py vql_manager_core

Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017
"""

from os import path, makedirs, listdir, unlink, rmdir
import subprocess
import sys
from vql_manager_core import *

from PyQt5.QtCore import QSize, QRect, QFileInfo, QTimer, QVariant, QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidgetItemIterator, qApp
from PyQt5.QtWidgets import QGridLayout, QSizePolicy, QHBoxLayout, QWidget, QRadioButton, QButtonGroup
from PyQt5.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PyQt5.QtWidgets import QTextEdit, QStatusBar, QAction, QMenuBar, QFileDialog, QMessageBox
from vql_model import VqlModel
from code_item import CodeItem


class VQLManagerWindow(QMainWindow):
    """
    Main application class for the GUI.
   """
    def __init__(self, parent=None):
        """
        Constructor of the Window Class
        :param parent: The owner/parent of the instance
        :type parent: Qt.Window
        :rtype: nothing
        """

        # initialize main window calling its parent
        super(VQLManagerWindow, self).__init__(parent, Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)  # close children on exit

        # root is the folder from which this file runs
        self._root = QFileInfo(__file__).absolutePath()
        images = self._root + '/images/'

        settings = QSettings(COMPANY, APPLICATION_NAME)  # Todo: remove these in production
        settings.clear()

        self.resize(1200, 800)
        self.setMinimumSize(QSize(860, 440))
        self.setIconSize(QSize(32, 32))
        self.setWindowIcon(QIcon(self._root + '/images/splitter.png'))
        self.setWindowTitle(APPLICATION_NAME)

        select_button_labels = [('All', white), ('Lost', red), ('New', green), ('Same', white), ('Changed', yellow)]
        diff_button_labels = [('Original', white), ('New', green), ('Changes', yellow)]

        # instantiate widgets
        self.mainwidget = QWidget(self, flags=Qt.Widget)
        self.layout = QGridLayout(self.mainwidget)

        # create radio buttons
        self.select_buttons, self.select_buttons_group = self.get_buttons_widget(self.mainwidget, select_button_labels)
        self.diff_buttons, self.diff_buttons_group = self.get_buttons_widget(self.mainwidget, diff_button_labels)

        #create tree widgets VqlModel(self.mainwidget)
        self.all_chapters_treeview = self.create_tree_widget(self.mainwidget, VqlModel, ITEM_FLAG_CHAPTER,
                                                             header='Selection Pane',
                                                             tooltip="")

        self.selected_treeview = self.create_tree_widget(self.mainwidget, QTreeWidget, ITEM_FLAG_SEL,
                                                         header='View Pane',
                                                         tooltip="Selected parts: Click to view source code")

        #create labels
        self.code_text_edit_label = QLabel(self.mainwidget)
        self.mode_label = QLabel(self.mainwidget)
        self.base_repository_label = QLabel(self.mainwidget)
        self.compare_repository_label = QLabel(self.mainwidget)
        self.selection_viewer_label = QLabel(self.mainwidget)

        #create source code view
        self.code_text_edit = QTextEdit(self.mainwidget)

        # create statusbar
        self.statusBar = QStatusBar(self)

        #  Create Actions and Menubar ###############################################################################
        self.open_file_action = QAction(QIcon(images + 'open_file.png'), '&Open File', self)
        self.open_folder_action = QAction(QIcon(images + 'open_repo.png'), 'Open &Repository', self)
        self.export_file_action = QAction(QIcon(images + 'save_file.png'), 'Save As File', self)
        self.export_folder_action = QAction(QIcon(images + 'save_repo.png'), '&Save As Repository', self)
        self.exit_action = QAction(QIcon(images + 'exit.png'), '&Exit', self)

        # Create recent file menu
        self.max_recent_files = 8
        self.recent_file_actions = list()
        self.recent_repository_actions = list()
        self.compare_recent_file_actions = list()
        self.compare_recent_repository_actions = list()

        for i in range(self.max_recent_files):
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(lambda: self.on_open_recent_files(i, BASE_FILE))
            self.recent_file_actions.append(action)

        for i in range(self.max_recent_files):
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(lambda: self.on_open_recent_files(i, BASE_REPO))
            self.recent_repository_actions.append(action)

        for i in range(self.max_recent_files):
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(lambda: self.on_open_recent_files(i, COMP_FILE))
            self.compare_recent_file_actions.append(action)

        for i in range(self.max_recent_files):
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(lambda: self.on_open_recent_files(i, COMP_REPO))
            self.compare_recent_repository_actions.append(action)


        # create compare with File menu
        self.open_compare_file_action = QAction(QIcon(images + 'open_file.png'), '&Open File to Compare', self)
        self.open_compare_folder_action = QAction(QIcon(images + 'open_repo.png'), 'Open &Repository to Compare', self)
        self.denodo_folder_structure_action = QAction(QIcon(images + 'open_repo.png'), 'Denodo Folder Structure', self)

        # Reset everything
        self.reset_action = QAction(QIcon(images + 'reset.png'), 'Reset &Everything', self)
        # create about actions
        self.about_action = QAction("&About", self)
        self.about_qt_action = QAction("About &Qt", self)

        #  Menu
        self.menubar = QMenuBar(self)
        self.filemenu = None
        self.recent_file_separator = None
        self.recent_file_menu = None
        self.recent_repository_separator = None
        self.recent_repository_menu = None

        self.compare_menu = None
        self.compare_recent_file_menu = None
        self.compare_recent_repository_menu = None
        self.compare_recent_repository_separator = None
        self.compare_recent_file_separator = None

        self.help_menu = None

        self.options_menu = None
        self.update_timer = QTimer()

        # Format and setup all widgets
        self.setup_ui()

        # Initialize class properties ###########################################################################

        self.working_folder = ''
        self.base_repository_file = ''
        self.base_repository_folder = ''
        self.compare_repository_file = ''
        self.compare_repository_folder = ''
        self._mode = 0
        self.switch_to_mode(GUI_NONE)
        self.code_show_selector = ORIGINAL_CODE
        self.code_text_edit_cache = None

    @staticmethod
    def create_tree_widget(parent, class_type, flags, header=None, tooltip=None):
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

    def new_tree_data(self):
        # create tree widgets VqlModel(self.mainwidget)
        self.all_chapters_treeview.clear()
        self.selected_treeview.clear()
        self.all_chapters_treeview = self.create_tree_widget(self.mainwidget, VqlModel, ITEM_FLAG_CHAPTER,
                                                             header='Selection Pane',
                                                             tooltip="")

        self.selected_treeview = self.create_tree_widget(self.mainwidget, QTreeWidget, ITEM_FLAG_SEL,
                                                         header='View Pane',
                                                         tooltip="Selected parts: Click to view source code")
    @staticmethod
    def resize_widget(some_widget):
        some_widget.setMinimumSize(QSize(PANE_WIDTH, 0))
        some_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_ui(self):
        """
        Function setup up all widgets
        :return: nothing
        """
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
        self.layout.addWidget(self.mode_label,                0, 0, 1, 1)
        self.layout.addWidget(self.base_repository_label,     1, 0, 1, 1)
        self.layout.addWidget(self.compare_repository_label,  2, 0, 1, 1)
        self.layout.addWidget(self.select_buttons,            3, 0, 1, 1)
        self.layout.addWidget(self.all_chapters_treeview,     4, 0, 4, 1)

        # right pane

        self.layout.addWidget(self.selection_viewer_label,  0, 1, 4, 1)
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
        self.layout.setColumnStretch(1, 1)

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
        # self.reset_action.setShortcut('Ctrl+E')
        self.reset_action.setStatusTip('Reset the application to a clean state')
        self.reset_action.triggered.connect(lambda: self.on_reset(GUI_NONE))

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
        for i in range(self.max_recent_files):
            self.recent_file_menu.addAction(self.recent_file_actions[i])

        self.recent_repository_separator = self.filemenu.addSeparator()
        self.recent_repository_menu = self.filemenu.addMenu('Recent Repositories')
        for i in range(self.max_recent_files):
            self.recent_repository_menu.addAction(self.recent_repository_actions[i])

        self.filemenu.addSeparator()
        self.filemenu.addAction(self.exit_action)

        self.compare_menu = self.menubar.addMenu('&Compare')
        self.compare_menu.addAction(self.open_compare_file_action)
        self.compare_menu.addAction(self.open_compare_folder_action)

        self.compare_recent_file_separator = self.compare_menu.addSeparator()
        self.compare_recent_file_menu = self.compare_menu.addMenu('Recent Files')
        for i in range(self.max_recent_files):
            self.compare_recent_file_menu.addAction(self.recent_file_actions[i])

        self.compare_recent_repository_separator = self.compare_menu.addSeparator()
        self.compare_recent_repository_menu = self.compare_menu.addMenu('Recent Repositories')
        for i in range(self.max_recent_files):
            self.compare_recent_file_menu.addAction(self.recent_repository_actions[i])

        self.options_menu = self.menubar.addMenu('&Options')
        self.options_menu.addAction(self.denodo_folder_structure_action)
        self.options_menu.addSeparator()
        self.options_menu.addAction(self.reset_action)

        self.help_menu = self.menubar.addMenu('&Help')
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.about_qt_action)

        self.update_recent_file_actions()

        # Callbacks Slots and Signals ###########################################################################
        self.all_chapters_treeview.itemChanged.connect(self.on_selection_changed)
        self.selected_treeview.itemClicked.connect(self.on_click_item_selected)

        # Radio buttons
        self.select_buttons_group.buttonClicked.connect(self.on_select_buttons_clicked)
        self.diff_buttons_group.buttonClicked.connect(self.on_diff_buttons_clicked)

        # connect update timer
        self.update_timer.timeout.connect(self.update_tree_widgets)

    def update_recent_file_actions(self):

        settings = QSettings(COMPANY, APPLICATION_NAME)
        files = settings.value('recent_file_list', type=list)
        repositories = settings.value('recent_repositories_list', type=list)

        len_files = len(files)
        len_repositories = len(repositories)
        update_list = [self.recent_file_actions, self.compare_recent_file_actions]

        for i in range(self.max_recent_files):
            if i < len_files:
                text = str(i) + ' ' + path.basename(files[i])
                for actions in update_list:
                    actions[i].setText(text)
                    actions[i].setData(files[i])
                    actions[i].setVisible(True)
                    actions[i].setStatusTip(files[i])
            else:
                for actions in update_list:
                    actions[i].setVisible(False)
        if len_files > 0:
            self.recent_file_separator.setVisible(True)
            self.compare_recent_file_separator.setVisible(True)

        update_list = [self.recent_repository_actions, self.compare_recent_repository_actions]

        for i in range(self.max_recent_files):
            if i < len_repositories:
                text = str(i) + ' ' + path.basename(path.normpath(repositories[i]))
                for actions in update_list:
                    actions[i].setText(text)
                    actions[i].setData(repositories[i])
                    actions[i].setVisible(True)
                    actions[i].setStatusTip(repositories[i])
            else:
                for actions in update_list:
                    actions[i].setVisible(False)

        if len_repositories > 0:
            self.recent_repository_separator.setVisible(True)
            self.compare_recent_repository_separator.setVisible(True)

    def on_open_recent_files(self, index, mode):
        print('index', index)

        if mode & (BASE_FILE | COMP_FILE):
            file_list = 'recent_file_list'
        elif mode & (BASE_REPO | COMP_REPO):
            file_list = 'recent_repository_list'
        else:
            return

        settings = QSettings(COMPANY, APPLICATION_NAME)
        files = settings.value(file_list, type=list)

        if len(files):
            file = files[index]
            print(file)
            self.load_model(file, mode)

    def load_model(self, file, mode):
        if mode & (BASE_FILE | COMP_FILE):
            if path.isfile(file):
                self.load_model_from_file(file, mode)
        elif mode & (BASE_REPO | COMP_REPO):
            if path.isdir(file):
                self.load_model_from_repository(file, mode)

    def on_about_vql_manager(self):
        QMessageBox.about(self, 'About ' + self.windowTitle(), about_text)

    def on_about_qt(self):
        QMessageBox.aboutQt(self, self.windowTitle())

    @staticmethod
    def get_buttons_widget(main_widget, button_list):
        layout = QHBoxLayout()  # layout for the central widget
        widget = QWidget(main_widget)  # central widget
        widget.setLayout(layout)
        group = QButtonGroup(widget)  # Number group
        for i, label_color in enumerate(button_list):
            btn = QRadioButton(label_color[0])
            btn.setStyleSheet("color: " + label_color[1])
            if i == 0:
                btn.setChecked(True)
            group.addButton(btn)
            layout.addWidget(btn, 0, Qt.AlignLeft,)
        return widget, group

    def get_mode(self):
        return self._mode

    def switch_to_mode(self, new_mode):
        """
        This function redresses the window to reflect the new mode

        :param new_mode:
        :return:
        """

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
                    self.base_repository_label.setText('File : ' + self.base_repository_file)
                elif new_mode & BASE_REPO:
                    self.base_repository_label.setText('Repository : ' + self.base_repository_folder)
            self.compare_repository_label.setText('')
        elif new_mode & GUI_COMPARE:
            self.mode_label.setText("View Mode: Compare")
            self.diff_buttons.setHidden(False)
            self.select_buttons.setHidden(False)
            if new_mode & COMP_LOADED:
                if new_mode & COMP_FILE:
                    self.compare_repository_label.setText('File : ' + self.compare_repository_file)
                elif new_mode & COMP_REPO:
                    self.compare_repository_label.setText('Repository : ' + self.compare_repository_folder)
        if new_mode & VQL_VIEW:
            self.denodo_folder_structure_action.setChecked(False)
            self.on_switch_view()

        self.all_chapters_treeview.switch_mode(new_mode)
        self._mode = new_mode
        self.statusBar.showMessage(show_mode(self._mode))

    # Event handlers for opening and saving models

    def on_select_buttons_clicked(self, button):
        # buttons = self.select_buttons.buttons()
        # for myButton in buttons:
        #     if myButton != button:
        #         button.setChecked(False)

        text = button.text()
        tree = self.all_chapters_treeview
        if text == 'All':
            tree.color_filter = None
        elif text == 'Lost':
            tree.color_filter = RED
        elif text == 'New':
            tree.color_filter = GREEN
        elif text == 'Same':
            tree.color_filter = WHITE
        elif text == 'Changed':
            tree.color_filter = YELLOW
        self.update_tree_widgets()

    def on_diff_buttons_clicked(self, button):
        # buttons = self.select_buttons.buttons()
        # for myButton in buttons:
        #     if myButton != button:
        #         button.setChecked(False)

        text = button.text()

        if text == 'Original':
            self.code_show_selector = ORIGINAL_CODE
        elif text == 'New':
            self.code_show_selector = COMPARE_CODE
        elif text == 'Changes':
            self.code_show_selector = DIFF_CODE
        self.show_code_text()

    def on_open(self, new_mode):
        """
        Callback for the Open File menu item
        this function is the starting point for loading a model based on a .vql file or a repository
        :param new_mode: the mode of opening
        :type new_mode: int
        :return: nothing
        """

        current_mode = self.get_mode()

        if new_mode & GUI_SELECT:
            if current_mode & (BASE_LOADED | COMP_LOADED):
                # some base model is open:
                if self.ask_drop_changes():
                    self.on_reset(GUI_NONE)
                    self.switch_to_mode(GUI_NONE)
                    self.on_open(new_mode)  # recurse to the begin
                else:
                    return
            else:  # ok we can load
                if new_mode & BASE_FILE:
                    file = self.ask_file_open()
                    if file:
                        QApplication.setOverrideCursor(Qt.WaitCursor)
                        if self.load_model_from_file(file, BASE_FILE):
                            self.base_repository_file = file
                            new_mode |= BASE_LOADED
                            self.switch_to_mode(new_mode)
                            self.update_tree_widgets()
                            self.working_folder = path.dirname(file)
                            self.add_to_recent_files(file)
                        else:
                            return
                        QApplication.restoreOverrideCursor()
                    else:
                        return
                elif new_mode & BASE_REPO:
                    folder = self.ask_repository_open()
                    if folder:
                        QApplication.setOverrideCursor(Qt.WaitCursor)
                        if self.load_model_from_repository(folder, BASE_REPO):
                            self.base_repository_folder = folder
                            new_mode |= BASE_LOADED
                            self.switch_to_mode(new_mode)
                            self.update_tree_widgets()
                            self.working_folder = folder
                            self.add_to_recent_files(folder)
                        else:
                            return
                        QApplication.restoreOverrideCursor()
                    else:
                        return

        elif new_mode & GUI_COMPARE:
            if current_mode & BASE_LOADED:  # there is a base model
                if current_mode & COMP_LOADED:  # there is a compare going on
                    if self.ask_drop_changes():
                        self.on_reset(GUI_COMPARE)
                        self.on_open(new_mode)  # recurse to the begin
                    else:
                        return
                else:  # ok we can load
                    if new_mode & COMP_FILE:
                        file = self.ask_file_open()
                        if file:
                            QApplication.setOverrideCursor(Qt.WaitCursor)
                            if self.load_model_from_file(file, COMP_FILE):
                                self.compare_repository_file = file
                                current_base_mode = current_mode & (BASE_REPO | BASE_FILE)
                                new_mode |= current_base_mode | COMP_LOADED | BASE_LOADED | COMP_FILE
                                self.switch_to_mode(new_mode)
                                self.update_tree_widgets()
                                self.add_to_recent_files(file)
                            else:
                                return
                            QApplication.restoreOverrideCursor()
                        else:
                            return
                    elif new_mode & COMP_REPO:
                        folder = self.ask_repository_open()
                        if folder:
                            QApplication.setOverrideCursor(Qt.WaitCursor)
                            if self.load_model_from_repository(folder, COMP_REPO):
                                self.compare_repository_folder = folder
                                current_base_mode = current_mode & (BASE_REPO | BASE_FILE)
                                new_mode |= current_base_mode | COMP_LOADED | BASE_LOADED | COMP_REPO
                                self.switch_to_mode(new_mode)
                                self.update_tree_widgets()
                                self.add_to_recent_files(folder)
                            else:
                                return
                            QApplication.restoreOverrideCursor()
                        else:
                            return
            else:
                self.message_to_user("No repository loaded yet")
                return

    def on_save(self, save_mode):
        """
        Callback for the Save to File menu item
        this function is the starting point for saving a model to a .vql file
        :return: nothing
        """
        current_mode = self.get_mode()
        if not current_mode & BASE_LOADED:
            self.message_to_user("No repository loaded yet")
            return

        if save_mode & FILE:
            file = self.ask_file_save()
            if file:
                self.save_model_to_file(file)
        elif save_mode & REPO:
            folder = self.ask_repository_save()
            if folder:
                self.save_model_to_repository(folder)

    def on_reset(self, reset_mode):
        """
        Event handler to reset the model
        :return: nothing
        """
        app_path = path.normpath(self._root + '/vql_manager.py')
        try:
            subprocess.Popen([sys.executable, app_path])
        except OSError as exception:
            print('ERROR: could not restart application:')
            print('  %s' % str(exception))
        else:
            qApp.quit()

    def on_selection_changed(self, item, *_):
        """
        Event handler for changes of the selection in the all_chapters_treeview (VqlModel)
        :param item: The item that changed in the all_chapters_treeview
        :type item: QTreeWidgetItem
        :param _: not used
        :return: nothing
        """
        self.all_chapters_treeview.changed = True
        self.update_timer.start(100)

    def on_click_item_selected(self, item, col):
        """
        Event handler for looking up code in the code pane
        :param item: The CodeItem clicked on the Selection Tree
        :type item: QTreeWidgetItem
        :param col: The column --always zero, we only use 1 column in tree widgets
        :type col: int
        :return: Nothing
        """

        if item:
            item_data = item.data(col, Qt.UserRole)
            if item_data['class_type'] == CodeItem:
                cache = dict()
                cache['object_name'] = item_data['object_name']
                cache['code'] = item_data['code']
                cache['compare_code'] = item_data['compare_code']
                cache['difference'] = item_data['difference']
                self.code_text_edit_cache = cache
                self.show_code_text()
            else:
                self.code_text_edit_cache = None

    def show_code_text(self):
        if self.code_text_edit_cache:
            # convenience names
            item_data = self.code_text_edit_cache
            selector = self.code_show_selector
            put_text = self.code_text_edit.setHtml
            set_title = self.code_text_edit_label.setText
            object_name = item_data['object_name']

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
                    html_code = self.format_source_code(object_name, item_data['difference'], selector)
                    set_title("Differences : " + object_name)
            put_text(html_code)

    def add_to_recent_files(self, file):
        settings = QSettings(COMPANY, APPLICATION_NAME)
        if path.isfile(file):
            settings_list = 'recent_file_list'
        elif path.isdir(file):
            settings_list = 'recent_repository_list'
        else:
            return

        files = settings.value(settings_list, type=list)
        if file in files:
            files.remove(file)
        files = [file] + files
        if len(files) > self.max_recent_files:
            files = files[:self.max_recent_files]
        settings.setValue(settings_list, files)
        self.update_recent_file_actions()

    @staticmethod
    def format_source_code(object_name, raw_code, code_type):
        if not raw_code:
            return ''

        html = ''
        if code_type & (ORIGINAL_CODE | COMPARE_CODE):
            code = raw_code.replace('\n', '<br />')
            code = code.replace('    ', ' &nbsp; &nbsp; &nbsp; &nbsp; ')

            for word in RESERVED_WORDS:
                code = code.replace(' ' + word + ' ', ' <strong>' + word + '</strong> ')  # rude method here
            code = code.replace('<br />', '<br />\n')

            body = '<p style="color:' + white + '">' + code + '</p>'
            body = body.replace(object_name, '<font color="' + red + '">' + object_name + '</font>')
            html = doc_template(object_name, body)
            # print(html)

        elif code_type & DIFF_CODE:
            return raw_code

        return html

    def on_switch_view(self):
        if self._mode & BASE_LOADED:
            if self.denodo_folder_structure_action.isChecked():
                self.denodo_folder_structure_action.setText('Switch to VQL View')
                self.all_chapters_treeview.change_view(DENODO_VIEW, self._mode)
            else:
                self.denodo_folder_structure_action.setText('Switch to DENODO View')
                self.all_chapters_treeview.change_view(VQL_VIEW, self._mode)
            self.update_tree_widgets()

    # dialogs for opening and saving

    def ask_file_open(self):
        """
        Function to ask which file to open to via a dialog
        it also checks if the file exists and has a .vql extension
        :return: filepath
        :rtype: str
        """

        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setDefaultSuffix('vql')
        dialog.setWindowTitle("Select single VQL file")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
        if self.working_folder:
            open_path = self.working_folder
        else:
            open_path = path.curdir
        filename, _ = dialog.getOpenFileName(self, "Save File", open_path,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)",
                                             options=QFileDialog.DontResolveSymlinks)
        if not filename:
            return ''
        filename = str(filename)
        filename = path.normpath(filename)

        if not path.isfile(filename):
            self.message_to_user("File does not exist")
            return ''

        if not filename[-4:] == '.vql':
            self.message_to_user("This file has the wrong extenion")
            return ''

        return filename

    def ask_repository_open(self):
        """
        Function to ask which folder to open via a dialog
        it also checks if all files mentioned in the part.log files exist
        :return: the folder path
        :rtype: str
        """
        if self.working_folder:
            open_path = self.working_folder
        else:
            open_path = path.curdir
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setWindowTitle("Select Folder")
        dialog.setViewMode(QFileDialog.List)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        folder = dialog.getExistingDirectory(self, "Open Directory", open_path)

        if not folder:
            return ''

        folder = str(folder)
        folder = path.normpath(folder)

        if not path.isdir(folder):
            self.message_to_user("No folder found")
            return ''

        possible_folders = [name.replace(' ', '_') for name in CHAPTER_NAMES]
        matching_folders = set(possible_folders) & set(listdir(folder))

        if len(matching_folders) == 0:
            self.message_to_user("No sub folders found")
            return ''

        # part_logger = list()
        for sub_folder in matching_folders:
            part_file_to_check = path.join(folder, sub_folder, 'part.log')
            if path.isfile(part_file_to_check):
                file = self.read_file(part_file_to_check)
                part_logger = file.split('\n')
                for file_to_check in part_logger:
                    if file_to_check:
                        if not path.isfile(file_to_check):
                            self.message_to_user("File: " + file_to_check +
                                                 " not found. Make sure your repository is not corrupt")
                            return ''
            else:
                self.message_to_user("Part.log file: " + part_file_to_check +
                                     " not found. Make sure your repository is not corrupt")
                return ''
        return folder

    def ask_repository_save(self):
        """
        Function to ask which folder to save to via a dialog
        it also checks if the folder is empty and may be overwritten
        :return: Boolean if success: chapter_folder is set
        :rtype: bool
        """
        if self.working_folder:
            open_path = self.working_folder
        else:
            open_path = path.curdir
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        # dialog.setDefaultSuffix('vql')
        # dialog.setWindowTitle("Select single VQL file")
        dialog.setFileMode(QFileDialog.Directory)
        # dialog.setViewMode(QFileDialog.Detail)
        folder = dialog.getExistingDirectory(self, "Save to Repository", open_path)

        # folder = self.ask_folder()

        if not folder:
            return ''

        folder = path.normpath(folder)

        if not path.isdir(folder):
            try:
                makedirs(folder)
                return folder
            except OSError as e:
                self.error_message_box('Error', 'Error creating folder', e)
                return ''

        if listdir(folder):
            if self.ask_overwrite():
                self.clear_export_folder(folder)
                return folder
            else:
                return ''

        return folder

    def ask_file_save(self):
        """
        Function to ask which file to save to via a dialog
        it also checks if the file may be overwritten
        :return: Boolean if success; vql_file is set
        :rtype: bool
        """
        if self.working_folder:
            open_path = self.working_folder
        else:
            open_path = path.curdir
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        dialog.setDefaultSuffix('vql')
        dialog.setFileMode(QFileDialog.AnyFile)
        filename, _ = dialog.getSaveFileName(self, "Save File", open_path,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)")

        if not filename:  # not cancel pressed
            return ''

        filename = str(filename)
        filename = path.normpath(filename)

        if not ('.' in filename):
            filename = filename + '.vql'

        if path.isfile(filename):
            if self.ask_overwrite():
                unlink(filename)
                return filename
            else:
                return ''
        else:
            return filename

    # General purpose dialogs

    def message_to_user(self, message):
        """
        General Messagebox
        :return: nothing
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("You got a message!")
        msg.setIcon(QMessageBox.Question)
        msg.setText("<strong>" + message + "<strong>")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)
        msg.exec()

    def ask_overwrite(self):
        """
        General Messagebox to warn/ask for files to be overwritten
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

    def ask_drop_changes(self):
        """
        General Messagebox to warn/ask if made changes can be dropped
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

    def error_message_box(self, title, text, e):
        """
        General messagebox if an error happened
        :param title: Title of dialog window
        :type title: str
        :param text: Main text of dialog window
        :type text: str
        :param e: the error text generated by python
        :type e: OSError
        :return: nothing
        """
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setIcon(QMessageBox.Critical)
        msg.setText("<strong>An error has occurred!<strong>")
        msg.setInformativeText(text)
        msg.setDetailedText(e)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)
        msg.exec()

    # Helper function for io to disk

    def remove_dir(self, base_folder):
        """

        :param base_folder:
        :return:
        """
        for the_path in (path.join(base_folder, file) for file in listdir(base_folder)):
            if path.isdir(the_path):
                self.remove_dir(the_path)
            else:
                unlink(the_path)
        rmdir(base_folder)

    def clear_export_folder(self, folder):
        """
        Removes all files in a repository
        :param folder: The folder
        :type folder: str
        :return: nothing
        """
        for a_file in listdir(folder):
            file_path = path.join(folder, a_file)
            try:
                if path.isfile(file_path):
                    unlink(file_path)
                elif path.isdir(file_path):
                    self.remove_dir(file_path)
            except OSError as e:
                self.error_message_box("Error", "An error occurred during the removal of files in the folder: "
                                       + self.base_repository_folder, e)

    def read_file(self, file):
        """
        General function to read in a file
        :param file: The path to the file
        :type file: str
        :return: The contents of the file as string
        :rtype: str
        """
        content = None
        try:
            with open(path.normpath(file), 'r') as f:
                content = f.read(content)
        except OSError as e:
            self.error_message_box("Error", "An error occurred during reading of file: " + file, e)
        return content

    def write_file(self, file, content):
        """
        General function to write a file to disk
        :param file: the path where the file should be written to
        :type file: str
        :param content: The content to be written as string
        :type content: str
        :return: Boolean on success
        :rtype: bool
        """
        ok = False
        try:
            with open(path.normpath(file), 'x') as f:
                f.write(content)
                ok = True
        except OSError as e:
            self.error_message_box("Error", "An error occurred during writing of file: " + file, e)
        return ok

    def read_vql_folder(self, folder):
        """
        Helper function to the load_model_from_folder function
        This function actually reads all files in the repository and loads the contents in the all_chapters_treeview
        :param folder: The base folder of the repository
        :return: nothing
        """
        tree = self.all_chapters_treeview
        tree.set_base_folder(folder)
        content = PROP_QUOTE
        for chapter_name, chapter in tree.chapters.items():
            content += chapter.header
            part_log_filepath, _ = chapter.get_part_log()

            if path.isfile(part_log_filepath):
                part_logs = self.read_file(part_log_filepath).split('\n')
                for file in part_logs:
                    filepath = file
                    if path.isfile(filepath):
                        content += self.read_file(filepath)
        return content

    # Saving and loading models

    def load_model_from_file(self, file, mode):
        """
        Function to load a single .vql file into the VqlModel instance: all_chapters_treeview
        via its parse function. This function is called after all checks have been done
        :return: nothing
        """

        # if not file:
        #     self.message_to_user("No file found")
        #     return False

        self.statusBar.showMessage("Loading model")
        # mode = self.get_mode()
        tree = self.all_chapters_treeview
        content = self.read_file(file)

        if content:
            tree.blockSignals(True)
            tree.parse(content, mode)
            self.update_tree_widgets()
            tree.blockSignals(False)
        self.statusBar.showMessage("Ready")
        return True

    def load_model_from_repository(self, folder, mode):
        """
        Function to load a repository folder structure into the VqlModel instance: all_chapters_treeview
        via the read_vql_folder function. This function is called after all checks have been done
        :return: nothing
        """

        tree = self.all_chapters_treeview
        self.statusBar.showMessage("Loading model")

        content = PROP_QUOTE
        for chapter in tree.chapters:
            content += chapter.header
            part_log_filepath, _ = chapter.get_part_log(folder)
            if path.isfile(part_log_filepath):
                part_logs = self.read_file(part_log_filepath).split('\n')
                files = [self.read_file(file) for file in part_logs if path.isfile(file)]
                content += ''.join(files)

        # content = self.read_vql_folder(folder)
        if content:
            tree.blockSignals(True)
            tree.parse(content, mode)
            self.update_tree_widgets()
            tree.blockSignals(False)
        else:
            self.statusBar.showMessage("Load Failed")
            return False
        self.statusBar.showMessage("Ready")
        return True

    def save_model_to_file(self, file):
        """
        Function to save the single .vql file
        :return: Boolean on success
        :rtype: bool
        """
        self.statusBar.showMessage("Saving")
        tree = self.all_chapters_treeview
        if path.isfile(file):
            try:
                unlink(file)
            except OSError as e:
                self.error_message_box("Error", "An error occurred during removal of file : " + file, e)
                self.statusBar.showMessage("Save error")
                tree.blockSignals(False)
                return False
        tree.blockSignals(True)
        content = tree.get_code_as_file(selected=True)
        tree.blockSignals(False)
        if content:
            if self.write_file(file, content):
                self.statusBar.showMessage("Ready")
                return True
            else:
                self.statusBar.showMessage("Save error")
                return False

    def save_model_to_repository(self, folder):
        """
        Function to save the model selection to a repository
        The files are written to chapter_folder
        :return: Boolean on success
        :rtype: bool
        """
        self.statusBar.showMessage("Saving")

        if not folder:
            self.statusBar.showMessage("Save Error")
            return False

        tree = self.all_chapters_treeview
        tree.blockSignals(True)

        for part_log_filepath, part_log_content in tree.get_part_logs(folder):

            sub_folder, file = path.split(part_log_filepath)
            try:
                makedirs(sub_folder)
            except OSError as e:
                self.statusBar.showMessage("Save Error")
                self.error_message_box("Error", "An error occurred during creation of the folders in : "
                                       + sub_folder, e)
                return False

            if not part_log_content:
                self.statusBar.showMessage("Save Error")
                return False

            if not part_log_filepath:
                self.statusBar.showMessage("Save Error")
                return False

            if not self.write_file(part_log_filepath, part_log_content):
                self.statusBar.showMessage("Save Error")
                return False
        for file_path, content in tree.get_selected_code_files(folder):
            if not content:
                self.statusBar.showMessage("Save Error")
                return False
            if not file_path:
                self.statusBar.showMessage("Save Error")
                return False
            if not self.write_file(path.normpath(file_path), content):
                self.statusBar.showMessage("Save Error")
                return False

        tree.blockSignals(False)

        self.statusBar.showMessage("Ready")
        return True

    def update_tree_widgets(self):
        """
        Builds/sets new content of the selected_treeview after the selection in the all_chapters_treeview is changed
        This function copies the selected items and leaves out the chapters that are empty
        The updates are timed.
        When big changes are made (when whole chapters are unselected) the function is not redrawing the screen to often
        :return: nothing
        """
        # stop the update timer
        self.update_timer.stop()
        # store former "blocked" indicator
        blocked = self.all_chapters_treeview.signalsBlocked()

        # block signals while updating
        self.all_chapters_treeview.blockSignals(True)

        # convenience pointer names
        col = 0
        tree_sel = self.selected_treeview
        root_sel = tree_sel.invisibleRootItem()
        # root_sel.setFlags(ITEM_FLAG_SEL)

        tree_all = self.all_chapters_treeview
        root_all = tree_all.invisibleRootItem()
        tree_sel.clear()
        tree_all.pack()
        root_sel.addChildren(root_all.clone().takeChildren())
        VqlModel.unpack(tree_sel)

        # # itemIterator traverses over every node
        item_iterator = QTreeWidgetItemIterator(tree_sel)
        while item_iterator.value():
            item = item_iterator.value()
            item.setData(col, Qt.CheckStateRole, QVariant())
            item_iterator += 1
        self.all_chapters_treeview.blockSignals(blocked)
