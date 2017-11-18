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

from os import path, makedirs, listdir, unlink
from shutil import rmtree

from PyQt5.QtCore import Qt, QSize, QRect, QFileInfo, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QGridLayout, QSizePolicy
from PyQt5.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PyQt5.QtWidgets import QTextEdit, QStatusBar, QAction, QMenuBar, QFileDialog, QMessageBox
from vql_model import VqlModel
from code_item import CodeItem
from vql_manager_core import VqlConstants as Vql

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
        self.tick = 0
        # root is the folder from which this file runs
        self._root = QFileInfo(__file__).absolutePath()

        # initialize main window calling its parent
        super(VQLManagerWindow, self).__init__(parent, Qt.Window)

        # instanciate widgets
        self.mainwidget = QWidget(self, flags=Qt.Widget)
        self.layout = QGridLayout(self.mainwidget)
        self.all_chapters_treeview = VqlModel(self.mainwidget)
        self.selected_treeview = QTreeWidget(self.mainwidget)
        self.command_text_edit_label = QLabel(self.mainwidget)

        self.mode_label = QLabel(self.mainwidget)
        self.base_repository_label = QLabel(self.mainwidget)
        self.compare_repository_label = QLabel(self.mainwidget)

        self.selection_viewer_label = QLabel(self.mainwidget)
        self.command_txtEdit = QTextEdit(self.mainwidget)
        self.statusBar = QStatusBar(self)

        #  Actions and Menubar ###############################################################################
        self.open_file_action = QAction(QIcon(self._root + '/images/open_file.png'), '&Open File', self)
        self.open_folder_action = QAction(QIcon(self._root + '/images/open_repo.png'), 'Open &Repository', self)
        self.export_file_action = QAction(QIcon(self._root + '/images/save_file.png'), 'Save As File', self)
        self.export_folder_action = QAction(QIcon(self._root + '/images/save_repo.png'), '&Save As Repository', self)
        self.exit_action = QAction(QIcon(self._root + '/images/exit.png'), '&Exit', self)

        # Add/Construct menus
        self.menubar = QMenuBar(self)

        # Compare with File
        self.open_compare_file_action = QAction(QIcon(self._root + '/images/open_file.png'),
                                                '&Open File to Compare', self)
        # Compare with Folder
        self.open_compare_folder_action = QAction(QIcon(self._root + '/images/open_repo.png'),
                                                  'Open &Repository to Compare', self)
        # Reset everything
        self.reset_action = QAction(QIcon(self._root + '/images/reset.png'), 'Reset &Everything', self)

        #  Menu
        self.menubar = QMenuBar(self)
        self.filemenu = None
        self.tool_menu = None

        self.update_timer = QTimer()

        # Format and setup all widgets
        self.setup_ui()

        # CallbacksL Slots and Signals ###########################################################################
        self.all_chapters_treeview.itemChanged.connect(self.on_selection_changed)
        self.selected_treeview.itemClicked.connect(self.on_click_item_selected)

        # connect update timer
        self.update_timer.timeout.connect(self.update_tree_widgets)

        # Initialize class properties ###########################################################################
        self.base_repository_file = ''
        self.base_repository_folder = ''
        self.compare_repository_file = ''
        self.compare_repository_folder = ''

        self._mode = Vql.NONE
        self.switch_to_mode(self._mode)

        self.switch_to_mode(Vql.SELECT | Vql.BASE_MODEL_FILE)
        file = '/home/andre/PycharmProjects/vql/data/db.vql'
        if self.load_model_from_file(file):
            self.base_repository_file = file
            self.switch_to_mode(Vql.SELECT | Vql.BASE_MODEL_FILE | Vql.BASE_MODEL_LOADED)

    def setup_ui(self):
        """
        Function setup up all widgets
        :return: nothing
        """

        def set_size(some_widget):
            some_widget.setMinimumSize(QSize(Vql.PANE_WIDTH, 0))
            some_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.resize(1200, 800)
        self.setMinimumSize(QSize(860, 440))
        self.setMaximumSize(QSize(1920, 1080))
        self.setIconSize(QSize(32, 32))
        self.setWindowIcon(QIcon(self._root + '/images/splitter.png'))
        self.setWindowTitle("VQL Manager")

        # initialize mainwidget and layout
        self.layout.setContentsMargins(23, 23, 23, 23)
        self.layout.setSpacing(8)

        # Add Widgets ####################################################################################
        self.all_chapters_treeview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.all_chapters_treeview.setSelectionMode(QAbstractItemView.NoSelection)
        self.all_chapters_treeview.setIconSize(QSize(16, 16))
        self.all_chapters_treeview.setUniformRowHeights(True)
        self.all_chapters_treeview.setHeaderLabel('No file selected')
        # self.all_chapters_treeview.setToolTip("Select code parts: Right mouse click")
        # self.all_chapters_treeview.setToolTipDuration(2000)
        self.all_chapters_treeview.setIconSize(QSize(16, 16))
        self.all_chapters_treeview.setColumnCount(1)
        set_size(self.all_chapters_treeview)

        self.selected_treeview = QTreeWidget(self.mainwidget)
        self.selected_treeview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.selected_treeview.setSelectionMode(QAbstractItemView.NoSelection)
        self.selected_treeview.setUniformRowHeights(True)
        self.selected_treeview.setHeaderLabel('Selection Pane')
        self.selected_treeview.setToolTip("Selected parts: Click to view source code")
        self.selected_treeview.setToolTipDuration(2000)
        self.selected_treeview.setIconSize(QSize(16, 16))
        self.selected_treeview.setColumnCount(1)
        set_size(self.selected_treeview)

        self.command_text_edit_label.setText("Command:")

        set_size(self.command_text_edit_label)
        set_size(self.mode_label)
        set_size(self.selection_viewer_label)
        set_size(self.compare_repository_label)
        set_size(self.base_repository_label)

        self.command_txtEdit.setAcceptRichText(False)
        self.command_txtEdit.setLineWrapMode(0)
        self.command_txtEdit.setReadOnly(True)
        self.command_txtEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.command_txtEdit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.command_txtEdit.setText("non selected")
        set_size(self.command_txtEdit)

        #  Layout ################################################################################
        # left pane
        self.layout.addWidget(self.mode_label,                0, 0, 1, 1)
        self.layout.addWidget(self.base_repository_label, 1, 0, 1, 1)
        self.layout.addWidget(self.compare_repository_label, 2, 0, 1, 1)
        self.layout.addWidget(self.all_chapters_treeview,     3, 0, 3, 1)

        # right pane

        self.layout.addWidget(self.selection_viewer_label,  0, 1, 3, 1)
        self.layout.addWidget(self.selected_treeview,       3, 1)
        self.layout.addWidget(self.command_text_edit_label, 4, 1)
        self.layout.addWidget(self.command_txtEdit,         5, 1)

        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)
        self.layout.setRowStretch(3, 10)
        self.layout.setRowStretch(4, 1)
        self.layout.setRowStretch(5, 10)

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
        self.open_file_action.triggered.connect(lambda: self.on_open(Vql.SELECT | Vql.BASE_MODEL_FILE))

        # Open Repository
        self.open_folder_action.setShortcut('Ctrl+R')
        self.open_folder_action.setStatusTip('Open a repository containing folders with separate vql scripts')
        self.open_folder_action.triggered.connect(lambda: self.on_open(Vql.SELECT | Vql.BASE_MODEL_REPO))

        # Save As File
        self.export_file_action.setStatusTip('Save selection to a repository file')
        self.export_file_action.triggered.connect(lambda: self.on_save(Vql.FILE))

        # Save As Repository
        self.export_folder_action.setShortcut('Ctrl+S')
        self.export_folder_action.setStatusTip('Save selection to a repository folder')
        self.export_folder_action.triggered.connect(lambda: self.on_save(Vql.REPO))

        # Exit App
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.setStatusTip('Exit application')
        self.exit_action.triggered.connect(QApplication.quit)

        # Compare with File
        self.open_compare_file_action.setShortcut('Ctrl+O')
        self.open_compare_file_action.setStatusTip('Open Single VQL File')
        self.open_compare_file_action.triggered.connect(
            lambda: self.on_open(Vql.COMPARE & Vql.COMP_MODEL_FILE))

        # Compare with Folder
        self.open_compare_folder_action.setShortcut('Ctrl+R')
        self.open_compare_folder_action.setStatusTip('Open a repository containing folders with separate vql scripts')
        self.open_compare_folder_action.triggered.connect(
            lambda: self.on_open(Vql.COMPARE & Vql.COMP_MODEL_REPO))

        # Reset everything
        # self.reset_action.setShortcut('Ctrl+E')
        self.reset_action.setStatusTip('Reset the application to a clean state')
        self.reset_action.triggered.connect(self.on_reset)

        #  Menu

        self.menubar.setGeometry(QRect(0, 0, 1200, 23))

        self.filemenu = self.menubar.addMenu('&File')
        self.filemenu.addAction(self.open_file_action)
        self.filemenu.addAction(self.open_folder_action)
        self.filemenu.addAction(self.export_file_action)
        self.filemenu.addAction(self.export_folder_action)
        self.filemenu.addSeparator()
        self.filemenu.addAction(self.exit_action)

        self.tool_menu = self.menubar.addMenu('&Tools')
        self.tool_menu.addAction(self.open_compare_file_action)
        self.tool_menu.addAction(self.open_compare_folder_action)
        self.tool_menu.addSeparator()
        self.tool_menu.addAction(self.reset_action)

    def get_mode(self):
        return self._mode

    def switch_to_mode(self, new_mode):
        """
        This function redresses the window to reflect the new mode

        :param new_mode:
        :return:
        """

        if new_mode == Vql.NONE:
            self.mode_label.setText('View Mode: Selection')
            self.base_repository_label.setText('No file loaded')
            self.compare_repository_label.setText('')
            self.all_chapters_treeview.setHeaderLabel('Selection Pane')
            self._mode = new_mode
            return
        else:
            if new_mode & Vql.BASE_MODEL_LOADED:
                self.mode_label.setText("View Mode: Selection")
                if new_mode & Vql.BASE_MODEL_FILE:
                    self.base_repository_label.setText('File : ' + self.base_repository_file)
                elif new_mode & Vql.BASE_MODEL_REPO:
                    self.base_repository_label.setText('Repository : ' + self.base_repository_folder)
                self.compare_repository_label.setText('')

            elif new_mode & Vql.COMP_MODEL_LOADED:
                self.mode_label.setText("View Mode: Compare")
                if new_mode & Vql.COMP_MODEL_FILE:
                    self.compare_repository_label.setText = 'File : ' + self.compare_repository_file
                elif new_mode & Vql.COMP_MODEL_REPO:
                    self.compare_repository_label.setText = 'Repository : ' + self.compare_repository_folder
            self._mode = new_mode

    # Event handlers for opening and saving models

    def on_open(self, new_mode):
        """
        Callback for the Open File menu item
        this function is the starting point for loading a model based on a .vql file
        :return: nothing
        """

        current_mode = self.get_mode()
        model_loaded = Vql.BASE_MODEL_FILE | Vql.BASE_MODEL_REPO | Vql.COMP_MODEL_FILE | Vql.COMP_MODEL_REPO
        compare_loaded = Vql.COMP_MODEL_FILE | Vql.COMP_MODEL_REPO

        if new_mode & Vql.SELECT:
            if current_mode & model_loaded:
                # some base model is open:
                if self.ask_drop_changes():
                    self.switch_to_mode(Vql.NONE)
                    self.all_chapters_treeview.tree_reset()
                    self.update_tree_widgets()
                    self.on_open(new_mode)  # recurse to the begin
            else:  # ok we can load

                if new_mode & Vql.BASE_MODEL_FILE:
                    file = self.ask_file_open()
                    if file:
                        self.switch_to_mode(Vql.SELECT | Vql.BASE_MODEL_FILE)
                        if self.load_model_from_file(file):
                            self.base_repository_file = file
                            self.switch_to_mode(Vql.SELECT | Vql.BASE_MODEL_FILE | Vql.BASE_MODEL_LOADED)

                elif new_mode & Vql.BASE_MODEL_REPO:
                    folder = self.ask_repository_open()
                    if folder:
                        self.switch_to_mode(Vql.SELECT | Vql.BASE_MODEL_REPO)
                        if self.load_model_from_repository(folder):
                            self.base_repository_folder = folder
                            self.switch_to_mode(Vql.SELECT | Vql.BASE_MODEL_REPO | Vql.BASE_MODEL_LOADED)

        elif new_mode & Vql.COMPARE:
            if current_mode & (Vql.BASE_MODEL_FILE | Vql.BASE_MODEL_REPO):  # there is a base model
                if current_mode & compare_loaded:  # there is a compare going on
                    if self.ask_drop_changes():
                        reset_mode = (current_mode ^ (current_mode & Vql.COMP_MODEL_FILE)) |\
                                     (current_mode ^ (current_mode & Vql.COMP_MODEL_REPO))
                        self.self.switch_to_mode(reset_mode)
                        self.all_chapters_treeview.tree_reset_compare()
                        self.update_tree_widgets()
                        self.on_open(new_mode)  # recurse to the begin
                else:  # ok we can load

                    if new_mode & Vql.COMP_MODEL_FILE:
                        file = self.ask_file_open()
                        if file:
                            self.switch_to_mode(Vql.COMPARE | Vql.COMP_MODEL_FILE)
                            if self.load_model_from_file(file):
                                self.compare_repository_file = file
                                self.switch_to_mode(Vql.COMPARE | Vql.COMP_MODEL_FILE | Vql.COMP_MODEL_LOADED)

                    elif new_mode & Vql.COMP_MODEL_REPO:
                        folder = self.ask_repository_open()
                        if folder:
                            self.switch_to_mode(Vql.COMPARE | Vql.COMP_MODEL_REPO)
                            if self.load_model_from_repository(folder):
                                self.compare_repository_folder = folder
                                self.switch_to_mode(Vql.COMPARE | Vql.COMP_MODEL_REPO | Vql.COMP_MODEL_LOADED)
            else:
                self.message_to_user("No repository loaded yet")

    def on_save(self, save_mode):
        """
        Callback for the Save to File menu item
        this function is the starting point for saving a model to a .vql file
        :return: nothing
        """

        if not self.get_mode() & Vql.BASE_MODEL_LOADED:
            self.message_to_user("No repository loaded yet")
            return

        if save_mode & Vql.FILE:
            file = self.ask_file_save()
            if file:
                self.save_model_to_file(file)
        elif save_mode & Vql.REPO:
            folder = self.ask_repository_save()
            if folder:
                self.save_model_to_repository(folder)

    def on_reset(self):
        """
        Event handler to reset the model
        :return: nothing
        """
        self.all_chapters_treeview.tree_reset()
        self.all_chapters_treeview.tree_reset_compare()
        self.update_tree_widgets()

    def on_selection_changed(self, item, *_):
        """
        Event handler for changes of the selection in the all_chapters_treeview (VqlModel)
        :param item: The item that changed in the all_chapters_treeview
        :type item: QTreeWidgetItem
        :param _: not used
        :return: nothing
        """
        self.all_chapters_treeview.changed = True

        # if item.childCount() > 0:
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
        self.command_txtEdit.setText("non selected")
        self.command_text_edit_label.setText("Command:")
        if isinstance(item, QTreeWidgetItem):
            if not item.data(col, Qt.UserRole) in ('root', 'chapter'):
                command = item.data(col, Qt.UserRole)
                file_name = item.data(col, Qt.EditRole)
                self.command_txtEdit.setText(command)
                self.command_text_edit_label.setText("Command: " + file_name)

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
        filename, _ = dialog.getOpenFileName(self, "Save File", path.curdir,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)",
                                             options=QFileDialog.DontResolveSymlinks)
        if not filename:
            return ''
        filename = str(filename)

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

        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setWindowTitle("Select Folder")
        dialog.setViewMode(QFileDialog.List)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        folder = dialog.getExistingDirectory(self, "Open Directory", path.curdir)

        if not folder:
            return ''

        folder = str(folder)

        if not path.isdir(folder):
            self.message_to_user("No folder found")
            return ''

        possible_folders = [name.replace(' ', '_') for name in Vql.CHAPTER_NAMES]
        matching_folders = set(possible_folders) & set(listdir(folder))

        if len(matching_folders) == 0:
            self.message_to_user("No sub folders found")
            return ''

        # part_logger = list()
        for sub_folder in matching_folders:
            part_file_to_check = path.join(folder, sub_folder, 'part') + '.log'
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
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        # dialog.setDefaultSuffix('vql')
        # dialog.setWindowTitle("Select single VQL file")
        dialog.setFileMode(QFileDialog.Directory)
        # dialog.setViewMode(QFileDialog.Detail)
        folder = dialog.getSaveFileName(self, "Save to Repository", path.curdir)

        # folder = self.ask_folder()

        if not folder:
            return ''

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

    def ask_file_save(self):
        """
        Function to ask which file to save to via a dialog
        it also checks if the file may be overwritten
        :return: Boolean if success; vql_file is set
        :rtype: bool
        """
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        dialog.setDefaultSuffix('vql')
        # dialog.setWindowTitle("Save File")
        dialog.setFileMode(QFileDialog.AnyFile)
        # dialog.setViewMode(QFileDialog.Detail)
        filename, _ = dialog.getSaveFileName(self, "Save File", path.curdir,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)")

        if not filename:  # not cancel pressed
            return ''

        filename = str(filename)

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
                    rmtree(file_path)
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
            with open(file, 'r') as f:
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
            with open(file, 'x') as f:
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
        content = ''
        for chapter_name, chapter in tree.chapters.items():
            content += chapter.header
            part_log_filepath, part_log_content = chapter.get_part_log()
            if path.isfile(part_log_filepath):
                part_logs = self.read_file(part_log_filepath).split('\n')
                for file in part_logs:
                    if path.isfile(file):
                        content += self.read_file(file)
        return content

    # Saving and loading models

    def load_model_from_file(self, file):
        """
        Function to load a single .vql file into the VqlModel instance: all_chapters_treeview
        via its parse function. This function is called after all checks have been done
        :return: nothing
        """

        if not file:
            self.message_to_user("No file found")
            return False

        self.statusBar.showMessage("Loading model")
        mode = self.get_mode()
        tree = self.all_chapters_treeview
        content = self.read_file(file)

        if content:
            tree.blockSignals(True)
            if mode & Vql.SELECT:
                tree.tree_reset()
            elif mode & Vql.COMPARE:
                tree.tree_reset_compare()

            tree.parse(content, mode)
            self.update_tree_widgets()
            tree.blockSignals(False)
        self.statusBar.showMessage("Ready")
        return True

    def load_model_from_repository(self, folder):
        """
        Function to load a repository folder structure into the VqlModel instance: all_chapters_treeview
        via the read_vql_folder function. This function is called after all checks have been done
        :return: nothing
        """

        if not folder:
            self.message_to_user("No folder found")
            return False

        mode = self.get_mode()
        tree = self.all_chapters_treeview

        self.statusBar.showMessage("Loading model")
        content = self.read_vql_folder(folder)
        if content:
            tree.blockSignals(True)
            if mode & Vql.SELECT:
                tree.tree_reset()
            elif mode & Vql.COMPARE:
                tree.tree_reset_compare()
            tree.parse(content, mode)
            self.update_tree_widgets()
            tree.blockSignals(False)
        else:
            self.statusBar.showMessage("Ready")
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
        tree.set_base_folder(folder)

        for part_log_filepath, part_log_content in tree.get_part_logs():
            sub_folder, file = path.split(part_log_filepath)
            try:
                makedirs(sub_folder)
            except OSError as e:
                self.statusBar.showMessage("Save Error")
                self.error_message_box("Error", "An error occurred during creation of the folders in : " +
                                       sub_folder, e)
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

        for file_path, content in tree.get_selected_code_files():
            if not content:
                self.statusBar.showMessage("Save Error")
                return False
            if not file_path:
                self.statusBar.showMessage("Save Error")
                return False

            if not self.write_file(file_path, content):
                self.statusBar.showMessage("Save Error")
                return False
        tree.blockSignals(False)

        self.statusBar.showMessage("Ready")
        return True

    # Update screen

    def update_tree_widgets(self):
        """
        Builds/sets new content of the selected_treeview after the selection in the all_chapters_treeview is changed
        This function copies the selected items and leaves out the chapters that are empty
        The updates are timed.
        When big changes are made (when whole chapters are unselected) the function is not redrawing the screen to often
        :return: nothing
        """
        self.update_timer.stop()
        col = 0
        tree = self.selected_treeview
        tree_all = self.all_chapters_treeview
        root = tree.invisibleRootItem()
        tree.clear()
        new_chapter = None
        expanded = [chapter_name for chapter_name, chapter in tree_all.chapters.items() if chapter.isExpanded()]
        for is_chapter, item in tree_all.selected_items(self.get_mode()):
            if is_chapter:
                new_chapter = CodeItem.make_selected_treeview_item(root, col, item.name, 'chapter', Vql.WHITE)
                if item.name in expanded:
                    new_chapter.setExpanded(True)
            else:
                _ = CodeItem.make_selected_treeview_item(new_chapter, col, item.object_name,
                                                         item.get_code(), item.get_color())

        VqlModel.update_colors(self.all_chapters_treeview)
        VqlModel.update_colors(self.selected_treeview)


