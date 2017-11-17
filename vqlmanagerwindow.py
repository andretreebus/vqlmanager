#!/usr/bin/python3
# -*- coding: utf-8 -*-

from os import path, remove, makedirs, listdir, unlink
from shutil import rmtree

from PyQt5.QtCore import Qt, QSize, QRect, QFileInfo, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QGridLayout, QSizePolicy
from PyQt5.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PyQt5.QtWidgets import QTextEdit, QStatusBar, QAction, QMenuBar, QFileDialog, QMessageBox
from vql_model import VqlModel
from code_item import CodeItem
from vql_manager_core import VQL_Constants as VQL


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

        # root is the folder from which this file runs
        self._root = QFileInfo(__file__).absolutePath()

        # initialize main window calling its parent
        super(VQLManagerWindow, self).__init__(parent, Qt.Window)

        self.resize(1200, 800)
        self.setMinimumSize(QSize(860, 440))
        self.setMaximumSize(QSize(1920, 1080))
        self.setIconSize(QSize(32, 32))
        self.setWindowIcon(QIcon(self._root + '/images/splitter.png'))
        self.setWindowTitle("VQL Manager")

        # initialize mainwidget and layout
        self.mainwidget = QWidget(self, flags=Qt.Widget)
        self.layout = QGridLayout(self.mainwidget)
        self.layout.setContentsMargins(23, 23, 23, 23)
        self.layout.setSpacing(8)

        # Add Widgets ####################################################################################
        self.all_chapters_treeview = VqlModel(self.mainwidget)
        self.all_chapters_treeview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.all_chapters_treeview.setSelectionMode(QAbstractItemView.NoSelection)
        self.all_chapters_treeview.setIconSize(QSize(16, 16))
        self.all_chapters_treeview.setUniformRowHeights(True)
        self.all_chapters_treeview.setHeaderLabel('No file selected')
        # self.all_chapters_treeview.setToolTip("Select code parts: Right mouse click")
        # self.all_chapters_treeview.setToolTipDuration(2000)
        self.all_chapters_treeview.setIconSize(QSize(16, 16))
        self.all_chapters_treeview.setColumnCount(1)
        self.all_chapters_treeview.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.all_chapters_treeview.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.selected_treeview = QTreeWidget(self.mainwidget)
        self.selected_treeview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.selected_treeview.setSelectionMode(QAbstractItemView.NoSelection)
        self.selected_treeview.setUniformRowHeights(True)
        self.selected_treeview.setHeaderLabel('Selection Pane')
        self.selected_treeview.setToolTip("Selected parts: Click to view source code")
        self.selected_treeview.setToolTipDuration(2000)
        self.selected_treeview.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.selected_treeview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.selected_treeview.setIconSize(QSize(16, 16))
        self.selected_treeview.setColumnCount(1)

        self.command_text_edit_label = QLabel(self.mainwidget)
        self.command_text_edit_label.setText("Command:")
        self.command_text_edit_label.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.command_text_edit_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.mode_label = QLabel(self.mainwidget)
        self.mode_label.setText("View Mode: Selection")
        self.mode_label.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.mode_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.base_model_path_label = QLabel(self.mainwidget)
        self.base_model_path_label.setText("File: base model")
        self.base_model_path_label.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.base_model_path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.compare_model_path_label = QLabel(self.mainwidget)
        self.compare_model_path_label.setText("File: compare model")
        self.compare_model_path_label.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.compare_model_path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.selection_viewer_label = QLabel(self.mainwidget)
        self.selection_viewer_label.setText("selview")
        self.selection_viewer_label.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.selection_viewer_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.command_txtEdit = QTextEdit(self.mainwidget)
        self.command_txtEdit.setAcceptRichText(False)
        self.command_txtEdit.setLineWrapMode(0)
        self.command_txtEdit.setReadOnly(True)
        self.command_txtEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.command_txtEdit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.command_txtEdit.setText("non selected")
        self.command_txtEdit.setMinimumSize(QSize(VQLManagerWindow.PANE_WIDTH, 0))
        self.command_txtEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        #  Layout ################################################################################
        # left pane
        self.layout.addWidget(self.mode_label,                0, 0, 1, 1)
        self.layout.addWidget(self.base_model_path_label,     1, 0, 1, 1)
        self.layout.addWidget(self.compare_model_path_label, 2, 0, 1, 1)
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

        self.statusBar = QStatusBar(self)
        self.statusBar.setMinimumSize(QSize(0, 20))
        self.statusBar.showMessage("Ready")
        self.setStatusBar(self.statusBar)

        # Parent mainWidget to the QMainWindow
        self.setCentralWidget(self.mainwidget)

        #  Actions and Menubar ###############################################################################
        # Open File
        self.open_file_action = QAction(QIcon(self._root + '/images/open_file.png'), '&Open File', self)
        self.open_file_action.setShortcut('Ctrl+O')
        self.open_file_action.setStatusTip('Open Single VQL File')
        self.open_file_action.triggered.connect(self.on_file_open)

        # Open Repository
        self.open_folder_action = QAction(QIcon(self._root + '/images/open_repo.png'), 'Open &Repository', self)
        self.open_folder_action.setShortcut('Ctrl+R')
        self.open_folder_action.setStatusTip('Open a repository containing folders with separate vql scripts')
        self.open_folder_action.triggered.connect(self.on_repository_open)

        # Save As File
        self.export_file_action = QAction(QIcon(self._root + '/images/save_file.png'), 'Save As File', self)
        self.export_file_action.setStatusTip('Save selection to a repository folder')
        self.export_file_action.triggered.connect(self.on_save_to_file)

        # Save As Repository
        self.export_folder_action = QAction(QIcon(self._root + '/images/save_repo.png'), '&Save As Repository', self)
        self.export_folder_action.setShortcut('Ctrl+S')
        self.export_folder_action.setStatusTip('Save selection to a repository folder')
        self.export_folder_action.triggered.connect(self.on_save_to_repository)

        # Exit App
        self.exit_action = QAction(QIcon(self._root + '/images/exit.png'), '&Exit', self)
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.setStatusTip('Exit application')
        self.exit_action.triggered.connect(QApplication.quit)

        # Compare with File
        self.open_file2_action = QAction(QIcon(self._root + '/images/open_file.png'), '&Open File to Compare', self)
        self.open_file2_action.setShortcut('Ctrl+O')
        self.open_file2_action.setStatusTip('Open Single VQL File')
        self.open_file2_action.triggered.connect(self.on_file2_open)

        # Compare with Folder
        self.open_folder2_action = QAction(QIcon(self._root + '/images/open_repo.png'),
                                           'Open &Repository to Compare', self)
        self.open_folder2_action.setShortcut('Ctrl+R')
        self.open_folder2_action.setStatusTip('Open a repository containing folders with separate vql scripts')
        self.open_folder2_action.triggered.connect(self.on_repository2_open)

        # Reset everything
        self.reset_action = QAction(QIcon(self._root + '/images/reset.png'), 'Reset &Everything', self)
        # self.reset_action.setShortcut('Ctrl+E')
        self.reset_action.setStatusTip('Reset the application to a clean state')
        self.reset_action.triggered.connect(self.on_reset)

        #  Menu
        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QRect(0, 0, 1200, 23))

        self.filemenu = self.menubar.addMenu('&File')
        self.filemenu.addAction(self.open_file_action)
        self.filemenu.addAction(self.open_folder_action)
        self.filemenu.addAction(self.export_file_action)
        self.filemenu.addAction(self.export_folder_action)
        self.filemenu.addSeparator()
        self.filemenu.addAction(self.exit_action)

        self.tool_menu = self.menubar.addMenu('&Tools')
        self.tool_menu.addAction(self.open_file2_action)
        self.tool_menu.addAction(self.open_folder2_action)
        self.tool_menu.addSeparator()
        self.tool_menu.addAction(self.reset_action)

        # CallbacksL Slots and Signals ###########################################################################
        self.all_chapters_treeview.itemChanged.connect(self.on_selection_changed)
        self.selected_treeview.itemClicked.connect(self.on_click_item_selected)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_selected_treeview)

        # Initialize class properties ###########################################################################

        self.mode = VQLManagerWindow.SELECT
        self._vql_file = ''
        self.compare_file = ''
        self._repository = ''
        self.compare_repository = ''
        self.model_loaded = False
        self.model2_loaded = False


    @property
    def repository_base_folder(self):
        """
        This method runs whenever you try to get chapter_folder
        chapter_folder is the base folder of a code repository (collection of files in folders)
        :return: _chapter_folder instance property
        :rtype: str
        """
        return self._repository

    @repository_base_folder.setter
    def repository_base_folder(self, folder_name):
        """
        This method runs whenever you try to set chapter_folder
        chapter_folder is the base folder of a code repository (collection of files in folders)
        :return: nothing
        """
        self._repository = folder_name
        if self.mode == VqlModel.SELECT:
            self.all_chapters_treeview.setHeaderLabel('Repository: ' + folder_name)
        else:
            self.all_chapters_treeview.setHeaderLabel('Diff: ' + folder_name)

    @property
    def vql_file(self):
        """
        This method runs whenever you try to get vql_file (getter)
        :return: __vql_file instance property
        :rtype: str
        """
        return self._vql_file

    @vql_file.setter
    def vql_file(self, file_name):
        """
        This method runs whenever you try to set vql_file
        :return: nothing
        """
        self._vql_file = file_name
        self.all_chapters_treeview.setHeaderLabel('File: ' + file_name)

    def window_switch_to_mode(self):
        if self.mode & VQL.SELECT:
            self.mode_label.setText("View Mode: Selection")
            self.compare_model_path_label.setText = ''
            self.base_model_path_label.setText = 'File : ' + self.base_model_path
        elif self.mode & VQL.COMPARE:
            self.mode_label.setText("View Mode: Selection")
            self.compare_model_path_label.setText = 'Compared with: ' + self.compare_model_path


    # Event handlers for opening and saving models
    def on_file_open(self):
        """
        Callback for the Open File menu item
        this function is the starting point for loading a model based on a .vql file
        :return: nothing
        """
        if self.model_loaded:
            if self.ask_drop_changes():
                self.model_loaded = False
                self.on_file_open()
        else:
            if self.ask_file_open():
                self.load_model_from_file()
                self.model_loaded = True

    def on_file2_open(self):
        """
        Callback for the Open File menu item
        this function is the starting point for loading a model based on a .vql file
        :return: nothing
        """

        if self.model_loaded:
            if self.model2_loaded:
                if self.ask_drop_changes():
                    self.model2_loaded = False
                    self.on_file2_open()
            else:
                self.mode = VQLManagerWindow.COMPARE
                if self.ask_file_open():
                    self.load_model_from_file()
                    self.model2_loaded = True
                else:
                    self.mode = VQLManagerWindow.SELECT
        else:
            self.message_to_user("No repository loaded yet")

    def on_repository_open(self):
        """
        Callback for the Open Folder menu item
        this function is the starting point for loading a model based on a .vql file
        :return: nothing
        """

        if not self.model_loaded:
            if self.ask_repository_open():
                self.load_model_from_repository()
                self.model_loaded = True
        else:
            if self.ask_drop_changes():
                self.all_chapters_treeview.tree_reset()
                self.model_loaded = False
                self.on_repository_open()

    def on_repository2_open(self):
        """
        Callback for the Open Folder menu item
        this function is the starting point for loading a model based on a .vql file
        :return: nothing
        """
        if self.model_loaded:
            if self.model2_loaded:
                if self.ask_drop_changes():
                    self.all_chapters_treeview.tree2_reset()
                    self.model2_loaded = False
                    self.on_repository2_open()
            else:
                self.mode = VQLManagerWindow.COMPARE
                if self.ask_repository_open():
                    self.load_model_from_repository()
                    self.model2_loaded = True
                else:
                    self.mode = VQLManagerWindow.SELECT
        else:
            self.message_to_user("No repository loaded yet")

    def on_save_to_file(self):
        """
        Callback for the Save to File menu item
        this function is the starting point for saving a model to a .vql file
        :return: nothing
        """
        if self.model_loaded:
            if self.ask_file_save():
                self.save_model_to_file()
        else:
            self.message_to_user("No repository loaded yet")

    def on_save_to_repository(self):
        """
        Callback for the Save to Folder (Repository) File menu
        this function is the starting point for saving a model to a repository folder structure
        :return: nothing
        """
        if self.model_loaded:
            if self.ask_repository_save():
                self.save_model_to_repository()
        else:
            self.message_to_user("No repository loaded yet")

    def on_reset(self):
        """
        Event handler to reset the model
        :return: nothing
        """
        self.all_chapters_treeview.tree_reset()
        self.update_selected_treeview()
        self.model_loaded = False
        if self.model2_loaded:
            self.all_chapters_treeview.tree2_reset()

    def on_selection_changed(self, item, *_):
        """
        Event handler for changes of the selection in the all_chapters_treeview (VqlModel)
        :param item: The item that changed in the all_chapters_treeview
        :type item: QTreeWidgetItem
        :param _: not used
        :return: nothing
        """
        self.all_chapters_treeview.changed = True

        if item.childCount() > 0:
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

    def ask_repository_open(self):
        """
        Function to ask which folder to open via a dialog
        it also checks if all files mentioned in the part.log files exist
        :return: Boolean if success; chapter_folder is set
        :rtype: bool
        """

        folder = self.ask_folder()
        possible_folders = [name.replace(' ', '_') for name in self.all_chapters_treeview.CHAPTER_NAMES]
        if not folder:
            return False

        if not path.isdir(folder):
            return False

        matching_folders = set(possible_folders) & set(listdir(folder))

        if len(matching_folders) == 0:
            return False

        part_logger = ''
        for sub_folder in matching_folders:
            file_to_check = path.join(folder, sub_folder, 'part') + '.log'
            if path.isfile(file_to_check):
                file = self.read_file(file_to_check)
                part_logger += file.strip() + '\n'
            else:
                self.message_to_user("File: " + file_to_check +
                                     " not found. Make sure your repository is not corrupt")
                return False

        for file_to_check in part_logger[:-1].split('\n'):
            if not path.isfile(file_to_check):
                self.message_to_user("File: " + file_to_check +
                                     " not found. Make sure your repository is not corrupt")
                return False

        if self.mode == VqlModel.SELECT:
            self.repository_base_folder = folder
        else:
            self.compare_repository = folder
        return True

    def ask_folder(self):
        """
        General function to ask a folder to open via a dialog
        :return: the requested folder path
        :rtype: str
        """
        result = None
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setWindowTitle("Select Folder")
        dialog.setViewMode(QFileDialog.List)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        folder = dialog.getExistingDirectory(self, "Open Directory", path.curdir)
        folder = str(folder)
        if len(folder) > 0:
            result = str(folder)
        return result

    def ask_repository_save(self):
        """
        Function to ask which folder to save to via a dialog
        it also checks if the folder is empty and may be overwritten
        :return: Boolean if success: chapter_folder is set
        :rtype: bool
        """
        ok = False
        folder = self.ask_folder()
        if folder:
            if path.isdir(folder):
                if listdir(folder):
                    if self.ask_overwrite():
                        self.clear_export_folder(folder)
                        ok = True
                else:
                    ok = True
            else:
                try:
                    makedirs(folder)
                    ok = True
                except OSError as e:
                    self.error_message_box('Error', 'Error creating folder', e)
                    ok = False
            if ok:
                self.repository_base_folder = folder
        else:
            ok = False
        return ok

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
        dialog.setWindowTitle("Select single VQL file")
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        filename, _ = dialog.getSaveFileName(self, "Save File", path.curdir,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)")

        if len(filename) > 0:  # not cancel pressed
            filename = str(filename)

            if not ('.' in filename):
                filename = filename + '.vql'

            if path.isfile(filename):
                if self.ask_overwrite():
                    self.vql_file = filename
                    return True
                else:
                    return False
            else:
                self.vql_file = filename
                return True
        else:
            return False

    def ask_file_open(self):
        """
        Function to ask which file to open to via a dialog
        it also checks if the file exists and has a .vql extension
        :return: Boolean if success; vql_file is set
        :rtype: bool
        """
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setDefaultSuffix('vql')
        dialog.setWindowTitle("Select single VQL file")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
        filename, _ = dialog.getOpenFileName(self,  "Save File", path.curdir,
                                             "Denodo Scripts (*.vql);;Text files (*.txt);;All files (*)",
                                             options=QFileDialog.DontResolveSymlinks)
        if not len(filename) == 0:
            filename = str(filename)

            if path.isfile(filename) and filename[-4:] == '.vql':
                if self.mode == VQLManagerWindow.SELECT:
                    self.vql_file = filename
                elif self.mode == VQLManagerWindow.COMPARE:
                    self.compare_file = filename
                return True
            else:
                return False
        else:
            return False

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
        if self.all_chapters_treeview.changed:
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
        else:
            return True

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
                                       + self.repository_base_folder, e)

    def save_model_to_file(self):
        """
        Function to save the single .vql file
        :return: Boolean on success
        :rtype: bool
        """
        ok = False
        self.statusBar.showMessage("Saving")
        tree = self.all_chapters_treeview
        tree.blockSignals(True)
        if path.isfile(self.vql_file):
            try:
                remove(self.vql_file)
            except OSError as e:
                self.error_message_box("Error", "An error occurred during removal of file : " + self.vql_file, e)

        if self.write_file(self.vql_file, tree.get_code_as_file(selected=True)):
            ok = True

        tree.blockSignals(False)
        if ok:
            self.statusBar.showMessage("Ready")
        else:
            self.statusBar.showMessage("Save error")
        return ok

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

    def save_model_to_repository(self):
        """
        Function to save the model selection to a repository
        The files are written to chapter_folder
        :return: Boolean on success
        :rtype: bool
        """
        ok = True
        if self.repository_base_folder:
            self.statusBar.showMessage("Saving")
            tree = self.all_chapters_treeview
            tree.blockSignals(True)
            tree.set_base_folder(self.repository_base_folder)

            for part_log_filepath, part_log_content in tree.get_part_logs():
                folder, file = path.split(part_log_filepath)

                try:
                    makedirs(folder)
                except OSError as e:
                    ok = False
                    self.error_message_box("Error", "An error occurred during creation of the folders in : " +
                                           folder, e)

                if not self.write_file(part_log_filepath, part_log_content):
                    ok = False

            for file_path, content in tree.get_selected_code_files():
                if not self.write_file(file_path, content):
                    ok = False
            tree.blockSignals(False)
        else:
            ok = False

        if ok:
            self.statusBar.showMessage("Ready")
        else:
            self.statusBar.showMessage("Save Error")

    def load_model_from_file(self):
        """
        Function to load a single .vql file into the VqlModel instance: all_chapters_treeview
        via its parse function. This function is called after all checks have been done
        :return: nothing
        """
        if self.vql_file:
            content = ''
            self.statusBar.showMessage("Loading model")
            if self.mode == VQLManagerWindow.SELECT:
                content = self.read_file(self.vql_file)
            elif self.mode == VQLManagerWindow.COMPARE:
                content = self.read_file(self.compare_file)

            if content:
                tree = self.all_chapters_treeview
                tree.blockSignals(True)
                if self.mode == VQLManagerWindow.SELECT:
                    tree.tree_reset()
                tree.parse(content, self.mode)
                self.update_selected_treeview()
                tree.blockSignals(False)
                self.statusBar.showMessage("Ready")
            else:
                self.statusBar.showMessage("No model found")

    def load_model_from_repository(self):
        """
        Function to load a repository folder structure into the VqlModel instance: all_chapters_treeview
        via the read_vql_folder function. This function is called after all checks have been done
        :return: nothing
        """

        if self.repository_base_folder:
            tree = self.all_chapters_treeview
            tree.blockSignals(True)
            self.statusBar.showMessage("Loading model")
            content = ''
            if self.mode == VQLManagerWindow.SELECT:
                tree.tree_reset()
                content = self.read_vql_folder(self.repository_base_folder)
            elif self.mode == VQLManagerWindow.COMPARE:
                content = self.read_vql_folder(self.compare_repository)
            tree.parse(content, self.mode)
            self.update_selected_treeview()
            tree.blockSignals(False)
            self.statusBar.showMessage("Ready")
        else:
            self.statusBar.showMessage("No model found")

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

    def update_selected_treeview(self):
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
        for is_chapter, item in tree_all.selected_items(self.mode):
            if is_chapter:
                new_chapter = CodeItem.make_selected_treeview_item(root, col, item.name, 'chapter', CodeItem.WHITE)
            else:
                _ = CodeItem.make_selected_treeview_item(new_chapter, col, item.object_name,
                                                         item.get_code(), item.get_color())
        VqlModel.update_colors(self.all_chapters_treeview)
        VqlModel.update_colors(self.selected_treeview)


