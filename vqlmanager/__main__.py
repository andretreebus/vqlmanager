#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Denodo VQL Manager
This program shows GUI to split, select, combine and compare Denodo .vql files
Dependencies: python3.6 PyQt5, qdarkstyle, sqlparse

Installation:
    Install python3.6 or later from https://www.python.org/
    Make sure its in your path.

    To test it run in console or command: python -V  or python3 -V or python3.6 -V
    Use the python command reporting version 3.6
    In this example i assume it is python3

    On linux
    sudo python3.6 -m pip install wheel setuptools PyQt5 qdarkstyle sqlparse

    on windows: open cmd
    python3.6 -m pip install wheel setuptools PyQt5 qdarkstyle sqlparse

    anaconda: open jupyter add the said libs

    Put this file in a folder to your own preference, for example: C:\vqlmanager
    Make a launcher or shortcut that states: python3 C:\vqlmanager\__main__.py
    Make sure the launcher or shortcut starts in this folder

    Open the launcher to start the program


Usage:



Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017

The classes DiffMatchPatch and PatchObject are written by Neil Fraser (fraser@google.com)
These classes are modified for readability and python3 use only

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

__author__ = 'andretreebus@hotmail.com (Andre Treebus)'

# standard library
from sys import exit, argv, version_info, maxsize
from pathlib import Path
from typing import Iterator, List, Union, Sized, Tuple, Iterable
from functools import partial
from re import escape, match, compile, sub
from time import time
from urllib.parse import quote, unquote
import logging

# other libs
from PyQt5.QtCore import Qt, QObject, QSize, QRect, QFileInfo, QVariant, QSettings
from PyQt5.QtCore import QModelIndex, QSortFilterProxyModel, QAbstractItemModel
from PyQt5.QtCore import QStateMachine, QSignalTransition, QState, pyqtSignal
from PyQt5.QtGui import QIcon, QBrush, QColor, QFont, QPixmap, QTextOption
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QTreeView, QPushButton, QLineEdit
from PyQt5.QtWidgets import QMenu, QLabel, QAbstractItemView, QSplitter, QVBoxLayout, QHeaderView
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QRadioButton, QButtonGroup
from PyQt5.QtWidgets import QTextEdit, QStatusBar, QAction, QFileDialog, QMessageBox, QPlainTextEdit
import qdarkstyle
import sqlparse


app = None

# registry data
COMPANY = "www.erasmusmc.nl"
APPLICATION_NAME = "VQL Manager"


class PatchObject:
    """Class representing one patch operation."""
    # The data structure representing a diff is an array of tuples:
    # [(DIFF_DELETE, "Hello"), (DIFF_INSERT, "Goodbye"), (DIFF_EQUAL, " world.")]
    # which means: delete "Hello", add "Goodbye" and keep " world."
    DIFF_DELETE = -1
    DIFF_INSERT = 1
    DIFF_EQUAL = 0

    def __init__(self):
        """Initializes with an empty list of diffs."""
        self.diffs = []
        self.start1 = None
        self.start2 = None
        self.length1 = 0
        self.length2 = 0

    def __str__(self) -> str:
        """Emulate GNU diff's format.
        Header: @@ -382,8 +481,9 @@
        Indices are printed as 1-based, not 0-based.

        :return: The GNU diff string.
        """
        if self.length1 == 0:
            coordinates1 = str(self.start1) + ",0"
        elif self.length1 == 1:
            coordinates1 = str(self.start1 + 1)
        else:
            coordinates1 = str(self.start1 + 1) + "," + str(self.length1)
        if self.length2 == 0:
            coordinates2 = str(self.start2) + ",0"
        elif self.length2 == 1:
            coordinates2 = str(self.start2 + 1)
        else:
            coordinates2 = str(self.start2 + 1) + "," + str(self.length2)
        text = ["@@ -", coordinates1, " +", coordinates2, " @@\n"]

        # Escape the body of the patch with %xx notation.
        for op, data in self.diffs:
            if op == self.DIFF_INSERT:
                text.append("+")
            elif op == self.DIFF_DELETE:
                text.append("-")
            elif op == self.DIFF_EQUAL:
                text.append(" ")
            # High ascii will raise UnicodeDecodeError. Use Unicode instead.
            data = data.encode("utf-8")
            text.append(quote(data, "!~*'();/?:@&=+$,# ") + "\n")
        return "".join(text)


class DiffMatchPatch:
    """Class containing the diff, match and patch methods and behaviour settings."""

    DIFF_DELETE = PatchObject.DIFF_DELETE
    DIFF_INSERT = PatchObject.DIFF_INSERT
    DIFF_EQUAL = PatchObject.DIFF_EQUAL

    # Define some regex patterns for matching boundaries.
    BLANK_LINE_END = compile(r"\n\r?\n$")
    BLANK_LINE_START = compile(r"^\r?\n\r?\n")

    def __init__(self):
        """Initializes a diff_match_patch object with default settings.
        Redefine these in your program to override the defaults.
        """

        # Number of seconds to map a diff before giving up (0 for infinity).
        self.diff_timeout = 1.0
        # Cost of an empty edit operation in terms of edit characters.
        self.diff_edit_cost = 4
        # At what point is no match declared (0.0 = perfection, 1.0 = very loose).
        self.match_threshold = 0.5
        # How far to search for a match (0 = exact location, 1000+ = broad match).
        # A match this many characters away from the expected location will add
        # 1.0 to the score (0.0 is a perfect match).
        self.match_distance = 1000
        # When deleting a large block of text (over ~64 characters), how close do
        # the contents have to be to match the expected contents. (0.0 = perfection,
        # 1.0 = very loose).  Note that Match_Threshold controls how closely the
        # end points of a delete need to match.
        self.patch_delete_threshold = 0.5
        # Chunk size for context length.
        self.patch_margin = 4

        # The number of bits in an int.
        # Python has no maximum, thus to disable patch splitting set to 0.
        # However to avoid long patches in certain pathological cases, use 32.
        # Multiple short patches (using native ints) are much faster than long ones.
        self.match_max_bits = 32

    def diff_main(self, text1: str, text2: str, check_lines: bool=True, deadline: int=None)->list:
        """Find the differences between two texts.  Simplifies the problem by
          stripping any common prefix or suffix off the texts before diffing.

        :param text1: Old string to be diffed.
        :param text2: New string to be diffed.
        :param check_lines: Optional speedup flag.  If present and false, then don't run
            a line-level diff first to identify the changed areas.
            Defaults to true, which does a faster, slightly less optimal diff.
        :param deadline: Optional time when the diff should be complete by.
            Used internally for recursive calls.  Users should set DiffTimeout instead.
        :return: Array of changes
        """

        # Set a deadline by which time the diff must be complete.
        if deadline is None:
            # Unlike in most languages, Python counts time in seconds.
            if self.diff_timeout <= 0:
                deadline = maxsize
            else:
                deadline = time() + self.diff_timeout

        # Check for null inputs.
        if text1 is None or text2 is None:
            raise ValueError("Null inputs. (diff_main)")

        # Check for equality (speedup).
        if text1 == text2:
            if text1:
                return [(self.DIFF_EQUAL, text1)]
            return []

        # Trim off common prefix (speedup).
        common_length = self.diff_common_prefix(text1, text2)
        common_prefix = text1[:common_length]
        text1 = text1[common_length:]
        text2 = text2[common_length:]

        # Trim off common suffix (speedup).
        common_length = self.diff_common_suffix(text1, text2)
        if common_length == 0:
            common_suffix = ''
        else:
            common_suffix = text1[-common_length:]
            text1 = text1[:-common_length]
            text2 = text2[:-common_length]

        # Compute the diff on the middle block.
        diffs = self.diff_compute(text1, text2, check_lines, deadline)

        # Restore the prefix and suffix.
        if common_prefix:
            diffs[:0] = [(self.DIFF_EQUAL, common_prefix)]
        if common_suffix:
            diffs.append((self.DIFF_EQUAL, common_suffix))
        self.diff_cleanup_merge(diffs)
        return diffs

    def diff_compute(self, text1: str, text2: str, check_lines: bool, deadline: int)->list:
        """Find the differences between two texts.  Assumes that the texts do not
          have any common prefix or suffix.

        :param text1: Old string to be diffed.
        :param text2: New string to be diffed.
        :param check_lines: Speedup flag.  If false, then don't run a line-level diff
            first to identify the changed areas.
            If true, then run a faster, slightly less optimal diff.
        :param deadline: Time when the diff should be complete by.
        :return: Array of changes.
        """

        if not text1:
            # Just add some text (speedup).
            return [(self.DIFF_INSERT, text2)]

        if not text2:
            # Just delete some text (speedup).
            return [(self.DIFF_DELETE, text1)]

        if len(text1) > len(text2):
            long_text, short_text = text1, text2
        else:
            short_text, long_text = text1, text2
        i = long_text.find(short_text)
        if i != -1:
            # Shorter text is inside the longer text (speedup).
            diffs = [(self.DIFF_INSERT, long_text[:i]), (self.DIFF_EQUAL, short_text),
                     (self.DIFF_INSERT, long_text[i + len(short_text):])]
            # Swap insertions for deletions if diff is reversed.
            if len(text1) > len(text2):
                diffs[0] = (self.DIFF_DELETE, diffs[0][1])
                diffs[2] = (self.DIFF_DELETE, diffs[2][1])
            return diffs

        if len(short_text) == 1:
            # Single character string.
            # After the previous speedup, the character can't be an equality.
            return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

        # Check to see if the problem can be split in two.
        half_match = self.diff_half_match(text1, text2)
        if half_match:
            # A half-match was found, sort out the return data.
            text1_prefix, text1_postfix, text2_prefix, text2_postfix, mid_common = half_match
            # Send both pairs off for separate processing.
            diffs_pre = self.diff_main(text1_prefix, text2_prefix, check_lines, deadline)
            diffs_post = self.diff_main(text1_postfix, text2_postfix, check_lines, deadline)
            # Merge the results.
            return diffs_pre + [(self.DIFF_EQUAL, mid_common)] + diffs_post

        if check_lines and len(text1) > 100 and len(text2) > 100:
            return self.diff_line_mode(text1, text2, deadline)

        return self.diff_bisect(text1, text2, deadline)

    def diff_line_mode(self, text1: str, text2: str, deadline: int)->list:
        """Do a quick line-level diff on both strings, then re-diff the parts for greater accuracy.
          This speedup can produce non-minimal diffs.

        :param text1: Old string to be diffed.
        :param text2: New string to be diffed.
        :param deadline: Time when the diff should be complete by.
        :return: Array of changes.
        """
        # Scan the text on a line-by-line basis first.
        text1, text2, line_array = self.diff_lines_to_chars(text1, text2)

        diffs = self.diff_main(text1, text2, False, deadline)

        # Convert the diff back to original text.
        self.diff_chars_to_lines(diffs, line_array)
        # Eliminate freak matches (e.g. blank lines)
        self.diff_cleanup_semantic(diffs)

        # Re-diff any replacement blocks, this time character-by-character.
        # Add a dummy entry at the end.
        diffs.append((self.DIFF_EQUAL, ''))
        pointer = 0
        count_delete = 0
        count_insert = 0
        text_delete = ''
        text_insert = ''
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_INSERT:
                count_insert += 1
                text_insert += diffs[pointer][1]
            elif diffs[pointer][0] == self.DIFF_DELETE:
                count_delete += 1
                text_delete += diffs[pointer][1]
            elif diffs[pointer][0] == self.DIFF_EQUAL:
                # Upon reaching an equality, check for prior redundancies.
                if count_delete >= 1 and count_insert >= 1:
                    # Delete the offending records and add the merged ones.
                    a = self.diff_main(text_delete, text_insert, False, deadline)
                    diffs[pointer - count_delete - count_insert: pointer] = a
                    pointer = pointer - count_delete - count_insert + len(a)
                count_insert = 0
                count_delete = 0
                text_delete = ''
                text_insert = ''

            pointer += 1

        diffs.pop()  # Remove the dummy entry at the end.

        return diffs

    def diff_bisect(self, text1: str, text2: str, deadline: int)->list:
        """Find the 'middle snake' of a diff, split the problem in two
          and return the recursively constructed diff.
          See Myers 1986 paper: An O(ND) Difference Algorithm and Its Variations.

        :param text1: Old string to be diffed.
        :param text2: New string to be diffed.
        :param deadline: Time at which to bail if not yet complete.
        :return: Array of diff tuples.
        """
        # Cache the text lengths to prevent multiple calls.
        text1_length = len(text1)
        text2_length = len(text2)
        max_d = (text1_length + text2_length + 1) // 2
        v_offset = max_d
        v_length = 2 * max_d
        v1 = [-1] * v_length
        v1[v_offset + 1] = 0
        v2 = v1[:]
        delta = text1_length - text2_length
        # If the total number of characters is odd, then the front path will
        # collide with the reverse path.
        front = (delta % 2 != 0)
        # Offsets for start and end of k loop.
        # Prevents mapping of space beyond the grid.
        k1start = 0
        k1end = 0
        k2start = 0
        k2end = 0
        for d in range(max_d):
            # Bail out if deadline is reached.
            if time() > deadline:
                break

            # Walk the front path one step.
            for k1 in range(-d + k1start, d + 1 - k1end, 2):
                k1_offset = v_offset + k1
                if k1 == -d or (k1 != d and v1[k1_offset - 1] < v1[k1_offset + 1]):
                    x1 = v1[k1_offset + 1]
                else:
                    x1 = v1[k1_offset - 1] + 1
                y1 = x1 - k1
                while x1 < text1_length and y1 < text2_length and text1[x1] == text2[y1]:
                    x1 += 1
                    y1 += 1
                v1[k1_offset] = x1
                if x1 > text1_length:
                    # Ran off the right of the graph.
                    k1end += 2
                elif y1 > text2_length:
                    # Ran off the bottom of the graph.
                    k1start += 2
                elif front:
                    k2_offset = v_offset + delta - k1
                    if 0 <= k2_offset < v_length and v2[k2_offset] != -1:
                        # Mirror x2 onto top-left coordinate system.
                        x2 = text1_length - v2[k2_offset]
                        if x1 >= x2:
                            # Overlap detected.
                            return self.diff_bisect_split(text1, text2, x1, y1, deadline)

            # Walk the reverse path one step.
            for k2 in range(-d + k2start, d + 1 - k2end, 2):
                k2_offset = v_offset + k2
                if k2 == -d or (k2 != d and v2[k2_offset - 1] < v2[k2_offset + 1]):
                    x2 = v2[k2_offset + 1]
                else:
                    x2 = v2[k2_offset - 1] + 1
                y2 = x2 - k2
                while x2 < text1_length and y2 < text2_length and text1[-x2 - 1] == text2[-y2 - 1]:
                    x2 += 1
                    y2 += 1
                v2[k2_offset] = x2
                if x2 > text1_length:
                    # Ran off the left of the graph.
                    k2end += 2
                elif y2 > text2_length:
                    # Ran off the top of the graph.
                    k2start += 2
                elif not front:
                    k1_offset = v_offset + delta - k2
                    if 0 <= k1_offset < v_length and v1[k1_offset] != -1:
                        x1 = v1[k1_offset]
                        y1 = v_offset + x1 - k1_offset
                        # Mirror x2 onto top-left coordinate system.
                        x2 = text1_length - x2
                        if x1 >= x2:
                            # Overlap detected.
                            return self.diff_bisect_split(text1, text2, x1, y1, deadline)

        # Diff took too long and hit the deadline or
        # number of diffs equals number of characters, no commonality at all.
        return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

    def diff_bisect_split(self, text1: str, text2: str, x: int, y: int, deadline: int)->list:
        """Given the location of the 'middle snake', split the diff in two parts and recurse.

        :param text1: Old string to be diffed.
        :param text2: New string to be diffed.
        :param x: Index of split point in text1.
        :param y: Index of split point in text2.
        :param deadline: Time at which to bail if not yet complete.
        :return:  Array of diff tuples.
        """

        text1a = text1[:x]
        text2a = text2[:y]
        text1b = text1[x:]
        text2b = text2[y:]

        # Compute both diffs serially.
        diffs_prefix = self.diff_main(text1a, text2a, False, deadline)
        diffs_postfix = self.diff_main(text1b, text2b, False, deadline)

        return diffs_prefix + diffs_postfix

    @staticmethod
    def diff_lines_to_chars(text1: str, text2: str)->Tuple[str, str, list]:
        """Split two texts into an array of strings.  Reduce the texts to a string
        of hashes where each Unicode character represents one line.

        :param text1: First string.
        :param text2: Second string.
        :return: Three element tuple, containing the encoded text1, the encoded text2 and
          the array of unique strings.  The zeroth element of the array of unique
          strings is intentionally blank.
        """

        line_array = []  # e.g. lineArray[4] == "Hello\n"
        line_hash = {}  # e.g. lineHash["Hello\n"] == 4

        # "\x00" is a valid character, but various debuggers don't like it.
        # So we'll insert a junk entry to avoid generating a null character.
        line_array.append('')

        def diff_lines_to_chars_munge(text: str)->str:
            """Split a text into an array of strings.  Reduce the texts to a string
            of hashes where each Unicode character represents one line.
            Modifies line-array and line-hash through being a closure.

            :param text: String to encode.
            :return: Encoded string.
            """

            chars = []
            # Walk the text, pulling out a substring for each line.
            # text.split('\n') would would temporarily double our memory footprint.
            # Modifying text would create many large strings to garbage collect.
            line_start = 0
            line_end = -1
            while line_end < len(text) - 1:
                line_end = text.find('\n', line_start)
                if line_end == -1:
                    line_end = len(text) - 1
                line = text[line_start:line_end + 1]
                line_start = line_end + 1

                if line in line_hash:
                    chars.append(chr(line_hash[line]))
                else:
                    line_array.append(line)
                    line_hash[line] = len(line_array) - 1
                    chars.append(chr(len(line_array) - 1))
            return "".join(chars)

        chars1 = diff_lines_to_chars_munge(text1)
        chars2 = diff_lines_to_chars_munge(text2)
        return chars1, chars2, line_array

    @staticmethod
    def diff_chars_to_lines(diffs: list, line_array: list):
        """Rehydrate the text in a diff from a string of line hashes to real lines of text.

        :param diffs:  Array of diff tuples.
        :param line_array: Array of unique strings.
        :return: None
        """
        for x in range(len(diffs)):
            text = []
            for char in diffs[x][1]:
                text.append(line_array[ord(char)])
            diffs[x] = (diffs[x][0], "".join(text))

    @staticmethod
    def diff_common_prefix(text1: str, text2: str)->int:
        """Determine the common prefix of two strings.

        :param text1: First string.
        :param text2: Second string.
        :return:  The number of characters common to the start of each string.
        """

        # Quick check for common null cases.
        if not text1 or not text2 or text1[0] != text2[0]:
            return 0

        # Binary search.
        # Performance analysis: http://neil.fraser.name/news/2007/10/09/
        pointer_min = 0
        pointer_max = min(len(text1), len(text2))
        pointer_mid = pointer_max
        pointer_start = 0
        while pointer_min < pointer_mid:
            if text1[pointer_start:pointer_mid] == text2[pointer_start:pointer_mid]:
                pointer_min = pointer_mid
                pointer_start = pointer_min
            else:
                pointer_max = pointer_mid
            pointer_mid = (pointer_max - pointer_min) // 2 + pointer_min
        return pointer_mid

    @staticmethod
    def diff_common_suffix(text1: str, text2: str)->int:
        """Determine the common suffix of two strings.

        :param text1: First string.
        :param text2: Second string.
        :return: The number of characters common to the end of each string.
        """
        # Quick check for common null cases.
        if not text1 or not text2 or text1[-1] != text2[-1]:
            return 0
        # Binary search.
        # Performance analysis: http://neil.fraser.name/news/2007/10/09/
        length_text1 = len(text1)
        length_text2 = len(text2)
        pointer_min = 0
        pointer_max = min(length_text1, length_text2)
        pointer_mid = pointer_max
        pointer_end = 0
        while pointer_min < pointer_mid:
            if text1[-pointer_mid:length_text1 - pointer_end] == text2[-pointer_mid:length_text2 - pointer_end]:
                pointer_min = pointer_mid
                pointer_end = pointer_min
            else:
                pointer_max = pointer_mid
            pointer_mid = (pointer_max - pointer_min) // 2 + pointer_min
        return pointer_mid

    @staticmethod
    def diff_common_overlap(text1: str, text2: str)->int:
        """Determine if the suffix of one string is the prefix of another.

        :param text1: First string.
        :param text2: Second string.
        :return: The number of characters common to the end of the first string and the start of the second string.
        """
        # Cache the text lengths to prevent multiple calls.
        text1_length = len(text1)
        text2_length = len(text2)
        # Eliminate the null case.
        if text1_length == 0 or text2_length == 0:
            return 0
        # Truncate the longer string.
        if text1_length > text2_length:
            text1 = text1[-text2_length:]
        elif text1_length < text2_length:
            text2 = text2[:text1_length]
        text_length = min(text1_length, text2_length)
        # Quick check for the worst case.
        if text1 == text2:
            return text_length

        # Start by looking for a single character match
        # and increase length until no match is found.
        # Performance analysis: http://neil.fraser.name/news/2010/11/04/
        best = 0
        length = 1
        while True:
            pattern = text1[-length:]
            found = text2.find(pattern)
            if found == -1:
                return best
            length += found
            if found == 0 or text1[-length:] == text2[:length]:
                best = length
                length += 1

    def diff_half_match(self, text1: str, text2: str)->Union[None, Tuple[str, str, str, str, str]]:
        """Do the two texts share a substring which is at least half the length of
        the longer text? This speedup can produce non-minimal diffs.

        :param text1: First string.
        :param text2: Second string.
        :return: Five element Array, containing the prefix of text1, the suffix of text1,
          the prefix of text2, the suffix of text2 and the common middle.  Or None
          if there was no match.
        """
        if self.diff_timeout <= 0:
            # Don't risk returning a non-optimal diff if we have unlimited time.
            return None
        if len(text1) > len(text2):
            long_text, short_text = text1, text2
        else:
            short_text, long_text = text1, text2
        if len(long_text) < 4 or len(short_text) * 2 < len(long_text):
            return None  # Pointless.

        def diff_half_match_inner(_long_text: str, _short_text: str, i: int)\
                ->Union[None, Tuple[str, str, str, str, str]]:
            """Does a substring of shorttext exist within longtext such that the
            substring is at least half the length of longtext?
            Closure, but does not reference any external variables.

            :param _long_text: Longer string.
            :param _short_text: Shorter string.
            :param i: Start index of quarter length substring within longtext.
            :return: Five element Array, containing the prefix of longtext, the suffix of
                longtext, the prefix of short_text, the suffix of short_text and the
                common middle.  Or None if there was no match.
            """

            seed = _long_text[i:i + len(_long_text) // 4]
            best_common = ''
            j = _short_text.find(seed)
            long_text_prefix = 0
            long_text_suffix = 0
            short_text_prefix = 0
            short_text_suffix = 0
            while j != -1:
                prefix_length = self.diff_common_prefix(_long_text[i:], _short_text[j:])
                suffix_length = self.diff_common_suffix(_long_text[:i], _short_text[:j])
                if len(best_common) < suffix_length + prefix_length:
                    best_common = _short_text[j - suffix_length:j] + _short_text[j:j + prefix_length]
                    long_text_prefix = _long_text[:i - suffix_length]
                    long_text_suffix = _long_text[i + prefix_length:]
                    short_text_prefix = _short_text[:j - suffix_length]
                    short_text_suffix = _short_text[j + prefix_length:]
                j = _short_text.find(seed, j + 1)

            if len(best_common) * 2 >= len(_long_text):
                return long_text_prefix, long_text_suffix, short_text_prefix, short_text_suffix, best_common
            else:
                return None

        # First check if the second quarter is the seed for a half-match.
        half_match_1 = diff_half_match_inner(long_text, short_text, (len(long_text) + 3) // 4)
        # Check again based on the third quarter.
        half_match_2 = diff_half_match_inner(long_text, short_text, (len(long_text) + 1) // 2)

        if not half_match_1 and not half_match_2:
            return None
        elif not half_match_2:
            half_match = half_match_1
        elif not half_match_1:
            half_match = half_match_2
        else:
            # Both matched.  Select the longest.
            if len(half_match_1[4]) > len(half_match_2[4]):
                half_match = half_match_1
            else:
                half_match = half_match_2

        # A half-match was found, sort out the return data.
        if len(text1) > len(text2):
            text1_prefix, text1_suffix, text2_prefix, text2_suffix, mid_common = half_match
        else:
            text2_prefix, text2_suffix, text1_prefix, text1_suffix, mid_common = half_match
        return text1_prefix, text1_suffix, text2_prefix, text2_suffix, mid_common

    def diff_cleanup_semantic(self, diffs: list):
        """Reduce the number of edits by eliminating semantically trivial equalities.

        :param diffs: Array of diff tuples.
        :return:
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        last_equality = None  # Always equal to diffs[equalities[-1]][1]
        pointer = 0  # Index of current position.
        # Number of chars that changed prior to the equality.
        length_insertions1, length_deletions1 = 0, 0
        # Number of chars that changed after the equality.
        length_insertions2, length_deletions2 = 0, 0
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
                equalities.append(pointer)
                length_insertions1, length_insertions2 = length_insertions2, 0
                length_deletions1, length_deletions2 = length_deletions2, 0
                last_equality = diffs[pointer][1]
            else:  # An insertion or deletion.
                if diffs[pointer][0] == self.DIFF_INSERT:
                    length_insertions2 += len(diffs[pointer][1])
                else:
                    length_deletions2 += len(diffs[pointer][1])
                # Eliminate an equality that is smaller or equal to the edits on both
                # sides of it.
                if last_equality:
                    if len(last_equality) <= max(length_insertions1, length_deletions1):
                        if len(last_equality) <= max(length_insertions2, length_deletions2):
                            # Duplicate record.
                            diffs.insert(equalities[-1], (self.DIFF_DELETE, last_equality))
                            # Change second copy to insert.
                            diffs[equalities[-1] + 1] = (self.DIFF_INSERT, diffs[equalities[-1] + 1][1])
                            # Throw away the equality we just deleted.
                            equalities.pop()
                            # Throw away the previous equality (it needs to be reevaluated).
                            if equalities:
                                equalities.pop()
                            if equalities:
                                pointer = equalities[-1]
                            else:
                                pointer = -1
                            # Reset the counters.
                            length_insertions1, length_deletions1 = 0, 0
                            length_insertions2, length_deletions2 = 0, 0
                            last_equality = None
                            changes = True
            pointer += 1

        # Normalize the diff.
        if changes:
            self.diff_cleanup_merge(diffs)
        self.diff_cleanup_semantic_loss_less(diffs)

        # Find any overlaps between deletions and insertions.
        # Only extract an overlap if it is as big as the edit ahead or behind it.
        pointer = 1
        while pointer < len(diffs):
            if diffs[pointer - 1][0] == self.DIFF_DELETE and diffs[pointer][0] == self.DIFF_INSERT:
                deletion = diffs[pointer - 1][1]
                insertion = diffs[pointer][1]
                overlap_length1 = self.diff_common_overlap(deletion, insertion)
                overlap_length2 = self.diff_common_overlap(insertion, deletion)
                if overlap_length1 >= overlap_length2:
                    if overlap_length1 >= len(deletion) / 2.0 or overlap_length1 >= len(insertion) / 2.0:
                        # Overlap found.  Insert an equality and trim the surrounding edits.
                        diffs.insert(pointer, (self.DIFF_EQUAL, insertion[:overlap_length1]))
                        diffs[pointer - 1] = (self.DIFF_DELETE, deletion[:len(deletion) - overlap_length1])
                        diffs[pointer + 1] = (self.DIFF_INSERT, insertion[overlap_length1:])
                        pointer += 1
                else:
                    if overlap_length2 >= len(deletion) / 2.0 or overlap_length2 >= len(insertion) / 2.0:
                        # Reverse overlap found.
                        # Insert an equality and swap and trim the surrounding edits.
                        diffs.insert(pointer, (self.DIFF_EQUAL, deletion[:overlap_length2]))
                        diffs[pointer - 1] = (self.DIFF_INSERT, insertion[:len(insertion) - overlap_length2])
                        diffs[pointer + 1] = (self.DIFF_DELETE, deletion[overlap_length2:])
                        pointer += 1
                pointer += 1
            pointer += 1

    def diff_cleanup_semantic_loss_less(self, diffs: list):
        """Look for single edits surrounded on both sides by equalities
        which can be shifted sideways to align the edit to a word boundary.
        e.g: The c<ins>at c</ins>ame. -> The <ins>cat </ins>came.

        :param diffs: Array of diff tuples.
        :return: None
        """
        def diff_cleanup_semantic_score(one: str, two: str)->int:
            """Given two strings, compute a score representing whether the
            internal boundary falls on logical boundaries.
            Scores range from 6 (best) to 0 (worst).
            Closure, but does not reference any external variables.

            :param one: First string.
            :param two: Second string.
            :return: The score
            """
            if not one or not two:
                # Edges are the best.
                return 6

            # Each port of this function behaves slightly differently due to
            # subtle differences in each language's definition of things like
            # 'whitespace'.  Since this function's purpose is largely cosmetic,
            # the choice has been made to use each language's native features
            # rather than force total conformity.
            char1 = one[-1]
            char2 = two[0]
            non_alpha_numeric1 = not char1.isalnum()
            non_alpha_numeric2 = not char2.isalnum()
            whitespace1 = non_alpha_numeric1 and char1.isspace()
            whitespace2 = non_alpha_numeric2 and char2.isspace()
            line_break1 = whitespace1 and (char1 == "\r" or char1 == "\n")
            line_break2 = whitespace2 and (char2 == "\r" or char2 == "\n")
            blank_line1 = line_break1 and self.BLANK_LINE_END.search(one)
            blank_line2 = line_break2 and self.BLANK_LINE_START.match(two)
            if blank_line1 or blank_line2:
                # Five points for blank lines.
                return 5
            elif line_break1 or line_break2:
                # Four points for line breaks.
                return 4
            elif non_alpha_numeric1 and not whitespace1 and whitespace2:
                # Three points for end of sentences.
                return 3
            elif whitespace1 or whitespace2:
                # Two points for whitespace.
                return 2
            elif non_alpha_numeric1 or non_alpha_numeric2:
                # One point for non-alphanumeric.
                return 1
            return 0

        pointer = 1
        # Intentionally ignore the first and last element (don't need checking).
        while pointer < len(diffs) - 1:
            if diffs[pointer - 1][0] == self.DIFF_EQUAL and diffs[pointer + 1][0] == self.DIFF_EQUAL:
                # This is a single edit surrounded by equalities.
                equality1 = diffs[pointer - 1][1]
                edit = diffs[pointer][1]
                equality2 = diffs[pointer + 1][1]

                # First, shift the edit as far left as possible.
                common_offset = self.diff_common_suffix(equality1, edit)
                if common_offset:
                    common_string = edit[-common_offset:]
                    equality1 = equality1[:-common_offset]
                    edit = common_string + edit[:-common_offset]
                    equality2 = common_string + equality2

                # Second, step character by character right, looking for the best fit.
                best_equality1 = equality1
                best_edit = edit
                best_equality2 = equality2
                best_score = diff_cleanup_semantic_score(equality1, edit) + diff_cleanup_semantic_score(edit, equality2)
                while edit and equality2 and edit[0] == equality2[0]:
                    equality1 += edit[0]
                    edit = edit[1:] + equality2[0]
                    equality2 = equality2[1:]
                    score = diff_cleanup_semantic_score(equality1, edit) + diff_cleanup_semantic_score(edit, equality2)
                    # The >= encourages trailing rather than leading whitespace on edits.
                    if score >= best_score:
                        best_score = score
                        best_equality1 = equality1
                        best_edit = edit
                        best_equality2 = equality2

                if diffs[pointer - 1][1] != best_equality1:
                    # We have an improvement, save it back to the diff.
                    if best_equality1:
                        diffs[pointer - 1] = (diffs[pointer - 1][0], best_equality1)
                    else:
                        del diffs[pointer - 1]
                        pointer -= 1
                    diffs[pointer] = (diffs[pointer][0], best_edit)
                    if best_equality2:
                        diffs[pointer + 1] = (diffs[pointer + 1][0], best_equality2)
                    else:
                        del diffs[pointer + 1]
                        pointer -= 1
            pointer += 1

    def diff_cleanup_efficiency(self, diffs: list):
        """Reduce the number of edits by eliminating operationally trivial equalities.

        :param diffs:  Array of diff tuples.
        :return: None
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        last_equality = None  # Always equal to diffs[equalities[-1]][1]
        pointer = 0  # Index of current position.
        pre_ins = False  # Is there an insertion operation before the last equality.
        pre_del = False  # Is there a deletion operation before the last equality.
        post_ins = False  # Is there an insertion operation after the last equality.
        post_del = False  # Is there a deletion operation after the last equality.
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
                if len(diffs[pointer][1]) < self.diff_edit_cost and (post_ins or post_del):
                    # Candidate found.
                    equalities.append(pointer)
                    pre_ins = post_ins
                    pre_del = post_del
                    last_equality = diffs[pointer][1]
                else:
                    # Not a candidate, and can never become one.
                    equalities = []
                    last_equality = None

                post_ins = post_del = False
            else:  # An insertion or deletion.
                if diffs[pointer][0] == self.DIFF_DELETE:
                    post_del = True
                else:
                    post_ins = True

                # Five types to be split:
                # <ins>A</ins><del>B</del>XY<ins>C</ins><del>D</del>
                # <ins>A</ins>X<ins>C</ins><del>D</del>
                # <ins>A</ins><del>B</del>X<ins>C</ins>
                # <ins>A</del>X<ins>C</ins><del>D</del>
                # <ins>A</ins><del>B</del>X<del>C</del>

                if last_equality:
                    condition1 = pre_ins and pre_del and post_ins and post_del
                    ins_del_sum = int(pre_ins) + int(pre_del) + int(post_ins) + int(post_del)
                    condition2 = (len(last_equality) < (self.diff_edit_cost / 2)) and ins_del_sum == 3
                    if condition1 or condition2:
                        # Duplicate record.
                        diffs.insert(equalities[-1], (self.DIFF_DELETE, last_equality))
                        # Change second copy to insert.
                        diffs[equalities[-1] + 1] = (self.DIFF_INSERT, diffs[equalities[-1] + 1][1])
                        equalities.pop()  # Throw away the equality we just deleted.
                        last_equality = None
                        if pre_ins and pre_del:
                            # No changes made which could affect previous entry, keep going.
                            post_ins = post_del = True
                            equalities = []
                        else:
                            if len(equalities):
                                equalities.pop()  # Throw away the previous equality.
                            if len(equalities):
                                pointer = equalities[-1]
                            else:
                                pointer = -1
                            post_ins = post_del = False
                        changes = True

            pointer += 1

        if changes:
            self.diff_cleanup_merge(diffs)

    def diff_cleanup_merge(self, diffs: list):
        """Reorder and merge like edit sections.  Merge equalities.
        Any edit section can move as long as it doesn't cross an equality.

        :param diffs: The diffs to be cleaned up, this diffs list is edited here as if passed by ref
        :return: None
        """
        diffs.append((self.DIFF_EQUAL, ''))  # Add a dummy entry at the end.
        pointer = 0
        count_delete = 0
        count_insert = 0
        text_delete = ''
        text_insert = ''
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_INSERT:
                count_insert += 1
                text_insert += diffs[pointer][1]
                pointer += 1
            elif diffs[pointer][0] == self.DIFF_DELETE:
                count_delete += 1
                text_delete += diffs[pointer][1]
                pointer += 1
            elif diffs[pointer][0] == self.DIFF_EQUAL:
                # Upon reaching an equality, check for prior redundancies.
                if count_delete + count_insert > 1:
                    if count_delete != 0 and count_insert != 0:
                        # Factor out any common prefixes.
                        common_length = self.diff_common_prefix(text_insert, text_delete)
                        if common_length != 0:
                            x = pointer - count_delete - count_insert - 1
                            if x >= 0 and diffs[x][0] == self.DIFF_EQUAL:
                                diffs[x] = (diffs[x][0], diffs[x][1] + text_insert[:common_length])
                            else:
                                diffs.insert(0, (self.DIFF_EQUAL, text_insert[:common_length]))
                                pointer += 1
                            text_insert = text_insert[common_length:]
                            text_delete = text_delete[common_length:]
                        # Factor out any common suffixes.
                        common_length = self.diff_common_suffix(text_insert, text_delete)
                        if common_length != 0:
                            diffs[pointer] = (diffs[pointer][0], text_insert[-common_length:] + diffs[pointer][1])
                            text_insert = text_insert[:-common_length]
                            text_delete = text_delete[:-common_length]
                    # Delete the offending records and add the merged ones.
                    if count_delete == 0:
                        diffs[pointer - count_insert: pointer] = [(self.DIFF_INSERT, text_insert)]
                    elif count_insert == 0:
                        diffs[pointer - count_delete: pointer] = [(self.DIFF_DELETE, text_delete)]
                    else:
                        diffs[pointer - count_delete - count_insert: pointer] = \
                            [(self.DIFF_DELETE, text_delete), (self.DIFF_INSERT, text_insert)]
                    pointer = pointer - count_delete - count_insert + 1
                    if count_delete != 0:
                        pointer += 1
                    if count_insert != 0:
                        pointer += 1
                elif pointer != 0 and diffs[pointer - 1][0] == self.DIFF_EQUAL:
                    # Merge this equality with the previous one.
                    diffs[pointer - 1] = (diffs[pointer - 1][0], diffs[pointer - 1][1] + diffs[pointer][1])
                    del diffs[pointer]
                else:
                    pointer += 1

                count_insert = 0
                count_delete = 0
                text_delete = ''
                text_insert = ''

        if diffs[-1][1] == '':
            diffs.pop()  # Remove the dummy entry at the end.

        # Second pass: look for single edits surrounded on both sides by equalities
        # which can be shifted sideways to eliminate an equality.
        # e.g: A<ins>BA</ins>C -> <ins>AB</ins>AC
        changes = False
        pointer = 1
        # Intentionally ignore the first and last element (don't need checking).
        while pointer < len(diffs) - 1:
            if diffs[pointer - 1][0] == self.DIFF_EQUAL and diffs[pointer + 1][0] == self.DIFF_EQUAL:
                # This is a single edit surrounded by equalities.
                if diffs[pointer][1].endswith(diffs[pointer - 1][1]):
                    # Shift the edit over the previous equality.
                    tmp = diffs[pointer][1][:-len(diffs[pointer - 1][1])]
                    diffs[pointer] = (diffs[pointer][0], diffs[pointer - 1][1] + tmp)
                    diffs[pointer + 1] = (diffs[pointer + 1][0], diffs[pointer - 1][1] + diffs[pointer + 1][1])
                    del diffs[pointer - 1]
                    changes = True
                elif diffs[pointer][1].startswith(diffs[pointer + 1][1]):
                    # Shift the edit over the next equality.
                    diffs[pointer - 1] = (diffs[pointer - 1][0], diffs[pointer - 1][1] + diffs[pointer + 1][1])
                    tmp = diffs[pointer][1][len(diffs[pointer + 1][1]):]
                    diffs[pointer] = (diffs[pointer][0], tmp + diffs[pointer + 1][1])
                    del diffs[pointer + 1]
                    changes = True
            pointer += 1

        # If shifts were made, the diff needs reordering and another shift sweep.
        if changes:
            self.diff_cleanup_merge(diffs)

    def diff_x_index(self, diffs: list, loc: int)->int:
        """loc is a location in text1, compute and return the equivalent location in text2.
        e.g. "The cat" vs "The big cat", 1->1, 5->8

        :param diffs: Array of diff tuples.
        :param loc: Location within text1.
        :return:  Location within text2.
        """
        chars1 = 0
        chars2 = 0
        last_chars1 = 0
        last_chars2 = 0
        x = 0
        for x in range(len(diffs)):
            (op, text) = diffs[x]
            if op != self.DIFF_INSERT:  # Equality or deletion.
                chars1 += len(text)
            if op != self.DIFF_DELETE:  # Equality or insertion.
                chars2 += len(text)
            if chars1 > loc:  # Overshot the location.
                break
            last_chars1 = chars1
            last_chars2 = chars2

        if len(diffs) != x and diffs[x][0] == self.DIFF_DELETE:
            # The location was deleted.
            return last_chars2
        # Add the remaining len(character).
        return last_chars2 + (loc - last_chars1)

    def diff_pretty_html(self, diffs: list)->str:
        """Convert a diff array into a pretty HTML report.

        :param diffs: Array of diff tuples.
        :return: HTML representation.
        """
        html = []
        for (op, data) in diffs:
            text = (data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "&para;<br>"))
            if op == self.DIFF_INSERT:
                html.append("<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
            elif op == self.DIFF_DELETE:
                html.append("<del style=\"background:#ffe6e6;\">%s</del>" % text)
            elif op == self.DIFF_EQUAL:
                html.append("<span>%s</span>" % text)
        return "".join(html)

    def diff_text1(self, diffs: list)->str:
        """Compute and return the source text (all equalities and deletions).

        :param diffs: Array of diff tuples.
        :return: Source text.
        """
        text = []
        for (op, data) in diffs:
            if op != self.DIFF_INSERT:
                text.append(data)
        return "".join(text)

    def diff_text2(self, diffs)->str:
        """"Compute and return the destination text (all equalities and insertions).

        :param diffs: Array of diff tuples.
        :return: Destination text.
        """
        text = []
        for (op, data) in diffs:
            if op != self.DIFF_DELETE:
                text.append(data)
        return "".join(text)

    def diff_levenshtein(self, diffs: list)->int:
        """Compute the Levenshtein distance; the number of inserted, deleted or substituted characters.

        :param diffs: Array of diff tuples.
        :return: Number of changes.
        """
        levenshtein = 0
        insertions = 0
        deletions = 0
        for (op, data) in diffs:
            if op == self.DIFF_INSERT:
                insertions += len(data)
            elif op == self.DIFF_DELETE:
                deletions += len(data)
            elif op == self.DIFF_EQUAL:
                # A deletion and an insertion is one substitution.
                levenshtein += max(insertions, deletions)
                insertions = 0
                deletions = 0
        levenshtein += max(insertions, deletions)
        return levenshtein

    def diff_to_delta(self, diffs: list)->str:
        """Crush the diff into an encoded string which describes the operations
        required to transform text1 into text2.
        E.g. =3\t-2\t+ing  -> Keep 3 chars, delete 2 chars, insert 'ing'.
        Operations are tab-separated.  Inserted text is escaped using %xx notation.

        :param diffs:  Array of diff tuples.
        :return:  Delta text.
        """
        text = []
        for (op, data) in diffs:
            if op == self.DIFF_INSERT:
                # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
                data = data.encode("utf-8")
                text.append("+" + quote(data, "!~*'();/?:@&=+$,# "))
            elif op == self.DIFF_DELETE:
                text.append("-%d" % len(data))
            elif op == self.DIFF_EQUAL:
                text.append("=%d" % len(data))
        return "\t".join(text)

    def diff_from_delta(self, text1: str, delta: str)->list:
        """Given the original text1, and an encoded string which describes the
        operations required to transform text1 into text2, compute the full diff.

        :param text1: Source string for the diff.
        :param delta: Delta text.
        :return: Array of diff tuples.
        """
        diffs = []
        pointer = 0  # Cursor in text1
        tokens = delta.split("\t")
        for token in tokens:
            if token == "":
                # Blank tokens are ok (from a trailing \t).
                continue
            # Each token begins with a one character parameter which specifies the
            # operation of this token (delete, insert, equality).
            param = token[1:]
            if token[0] == "+":
                param = unquote(param)
                diffs.append((self.DIFF_INSERT, param))
            elif token[0] == "-" or token[0] == "=":
                try:
                    n = int(param)
                except ValueError:
                    raise ValueError("Invalid number in diff_fromDelta: " + param)
                if n < 0:
                    raise ValueError("Negative number in diff_fromDelta: " + param)
                text = text1[pointer: pointer + n]
                pointer += n
                if token[0] == "=":
                    diffs.append((self.DIFF_EQUAL, text))
                else:
                    diffs.append((self.DIFF_DELETE, text))
            else:
                # Anything else is an error.
                raise ValueError("Invalid diff operation in diff_fromDelta: " + token[0])
        if pointer != len(text1):
            raise ValueError("Delta length (%d) does not equal source text length (%d)." % (pointer, len(text1)))
        return diffs

    #  MATCH FUNCTIONS

    def match_main(self, text: str, pattern, loc: int)->int:
        """Locate the best instance of 'pattern' in 'text' near 'loc'.

        :param text: The text to search.
        :param pattern: The pattern to search for.
        :param loc: The location to search around.
        :return: Best match index or -1.
        """
        # Check for null inputs.
        if text is None or pattern is None:
            raise ValueError("Null inputs. (match_main)")

        loc = max(0, min(loc, len(text)))
        if text == pattern:
            # Shortcut (potentially not guaranteed by the algorithm)
            return 0
        elif not text:
            # Nothing to match.
            return -1
        elif text[loc:loc + len(pattern)] == pattern:
            # Perfect match at the perfect spot!  (Includes case of null pattern)
            return loc
        else:
            # Do a fuzzy compare.
            return self.match_bitap(text, pattern, loc)

    def match_bitap(self, text, pattern, loc):
        """Locate the best instance of 'pattern' in 'text' near 'loc' using the Bitap algorithm.

        :param text: The text to search.
        :param pattern: The pattern to search for.
        :param loc: The location to search around.
        :return: Best match index or -1.
        """
        # Python doesn't have a maxint limit, so ignore this check.
        # if self.Match_MaxBits != 0 and len(pattern) > self.Match_MaxBits:
        #  raise ValueError("Pattern too long for this application.")

        # Initialise the alphabet.
        s = self.match_alphabet(pattern)

        def match_bitap_score(n_errors, _loc)->float:
            """Compute and return the score for a match with e errors and x location.
            Accesses loc and pattern through being a closure.

            :param n_errors: Number of errors in match.
            :param _loc:  Location of match
            :return: Overall score for match (0.0 = good, 1.0 = bad).
            """
            accuracy = float(n_errors) / len(pattern)
            proximity = abs(loc - _loc)
            if not self.match_distance:
                # Dodge divide by zero error.
                return proximity and 1.0 or accuracy
            return accuracy + (proximity / float(self.match_distance))

        # Highest score beyond which we give up.
        score_threshold = self.match_threshold
        # Is there a nearby exact match? (speedup)
        best_loc = text.find(pattern, loc)
        if best_loc != -1:
            score_threshold = min(match_bitap_score(0, best_loc), score_threshold)
            # What about in the other direction? (speedup)
            best_loc = text.rfind(pattern, loc + len(pattern))
            if best_loc != -1:
                score_threshold = min(match_bitap_score(0, best_loc), score_threshold)

        # Initialise the bit arrays.
        match_mask = 1 << (len(pattern) - 1)
        best_loc = -1

        bin_max = len(pattern) + len(text)
        # Empty initialization added to appease pychecker.
        last_rd = None
        for d in range(len(pattern)):
            # Scan for the best match each iteration allows for one more error.
            # Run a binary search to determine how far from 'loc' we can stray at
            # this error level.
            bin_min = 0
            bin_mid = bin_max
            while bin_min < bin_mid:
                if match_bitap_score(d, loc + bin_mid) <= score_threshold:
                    bin_min = bin_mid
                else:
                    bin_max = bin_mid
                bin_mid = (bin_max - bin_min) // 2 + bin_min

            # Use the result from this iteration as the maximum for the next.
            bin_max = bin_mid
            start = max(1, loc - bin_mid + 1)
            finish = min(loc + bin_mid, len(text)) + len(pattern)

            rd = [0] * (finish + 2)
            rd[finish + 1] = (1 << d) - 1
            for j in range(finish, start - 1, -1):
                if len(text) <= j - 1:
                    # Out of range.
                    char_match = 0
                else:
                    char_match = s.get(text[j - 1], 0)
                if d == 0:  # First pass: exact match.
                    rd[j] = ((rd[j + 1] << 1) | 1) & char_match
                else:  # Subsequent passes: fuzzy match.
                    tmp = (((rd[j + 1] << 1) | 1) & char_match)
                    rd[j] = tmp | (((last_rd[j + 1] | last_rd[j]) << 1) | 1) | last_rd[j + 1]
                if rd[j] & match_mask:
                    score = match_bitap_score(d, j - 1)
                    # This match will almost certainly be better than any existing match.
                    # But check anyway.
                    if score <= score_threshold:
                        # Told you so.
                        score_threshold = score
                        best_loc = j - 1
                        if best_loc > loc:
                            pass
                            # When passing loc, don't exceed our current distance from loc.
                            # start = max(1, 2 * loc - best_loc)
                        else:
                            # Already passed loc, downhill from here on in.
                            break
            # No hope for a (better) match at greater error levels.
            if match_bitap_score(d + 1, loc) > score_threshold:
                break
            last_rd = rd
        return best_loc

    @staticmethod
    def match_alphabet(pattern: str)->dict:
        """Initialise the alphabet for the Bitap algorithm.

        :param pattern: The text to encode.
        :return: Hash of character locations.
        """
        s = {}
        for char in pattern:
            s[char] = 0
        for i in range(len(pattern)):
            s[pattern[i]] |= 1 << (len(pattern) - i - 1)
        return s

    #  PATCH FUNCTIONS

    def patch_add_context(self, patch: PatchObject, text: str):
        """Increase the context until it is unique, but don't let the pattern expand beyond Match_MaxBits.

        :param patch:  The patch to grow.
        :param text: Source text.
        :return:
        """
        if len(text) == 0:
            return
        pattern = text[patch.start2: patch.start2 + patch.length1]
        padding = 0

        # Look for the first and last matches of pattern in text.  If two different
        # matches are found, increase the pattern length.
        tmp = self.match_max_bits - self.patch_margin - self.patch_margin
        while text.find(pattern) != text.rfind(pattern) and (self.match_max_bits == 0 or len(pattern) < tmp):
            padding += self.patch_margin
            pattern = text[max(0, patch.start2 - padding):patch.start2 + patch.length1 + padding]
        # Add one chunk for good luck.
        padding += self.patch_margin

        # Add the prefix.
        prefix = text[max(0, patch.start2 - padding): patch.start2]
        if prefix:
            patch.diffs[:0] = [(self.DIFF_EQUAL, prefix)]
        # Add the suffix.
        suffix = text[patch.start2 + patch.length1:patch.start2 + patch.length1 + padding]
        if suffix:
            patch.diffs.append((self.DIFF_EQUAL, suffix))

        # Roll back the start points.
        patch.start1 -= len(prefix)
        patch.start2 -= len(prefix)
        # Extend lengths.
        patch.length1 += len(prefix) + len(suffix)
        patch.length2 += len(prefix) + len(suffix)

    def patch_make(self, a: str, b: Union[str, list, None]=None, c: Union[str, list, None]=None)->List[PatchObject]:
        """Compute a list of patches to turn text1 into text2.
        Use diffs if provided, otherwise compute it ourselves.
        There are four ways to call this function, depending on what data is
        available to the caller:
            Method 1: a = text1, b = text2
            Method 2: a = diffs
            Method 3 (optimal): a = text1, b = diffs
            Method 4 (deprecated, use method 3): a = text1, b = text2, c = diffs

        :param a: text1 (methods 1,3,4) or Array of diff tuples for text1 to text2 (method 2).
        :param b: text2 (methods 1,4) or Array of diff tuples for text1 to text2 (method 3) or undefined (method 2).
        :param c: Array of diff tuples for text1 to text2 (method 4) or undefined (methods 1,2,3).
        :return: Array of Patch objects.
        """
        if isinstance(a, str) and isinstance(b, str) and c is None:
            # Method 1: text1, text2
            # Compute diffs from text1 and text2.
            text1 = a
            diffs = self.diff_main(text1, b, True)
            if len(diffs) > 2:
                self.diff_cleanup_semantic(diffs)
                self.diff_cleanup_efficiency(diffs)
        elif isinstance(a, list) and b is None and c is None:
            # Method 2: diffs
            # Compute text1 from diffs.
            diffs = a
            text1 = self.diff_text1(diffs)
        elif isinstance(a, str) and isinstance(b, list) and c is None:
            # Method 3: text1, diffs
            text1 = a
            diffs = b
        elif (isinstance(a, str) and isinstance(b, str) and
              isinstance(c, list)):
            # Method 4: text1, text2, diffs
            # text2 is not used.
            text1 = a
            diffs = c
        else:
            raise ValueError("Unknown call format to patch_make.")

        if not diffs:
            return []  # Get rid of the None case.
        patches = []
        patch = PatchObject()
        char_count1 = 0  # Number of characters into the text1 string.
        char_count2 = 0  # Number of characters into the text2 string.
        pre_patch_text = text1  # Recreate the patches to determine context info.
        post_patch_text = text1
        for x in range(len(diffs)):
            (diff_type, diff_text) = diffs[x]
            if len(patch.diffs) == 0 and diff_type != self.DIFF_EQUAL:
                # A new patch starts here.
                patch.start1 = char_count1
                patch.start2 = char_count2
            if diff_type == self.DIFF_INSERT:
                # Insertion
                patch.diffs.append(diffs[x])
                patch.length2 += len(diff_text)
                post_patch_text = (post_patch_text[:char_count2] + diff_text + post_patch_text[char_count2:])
            elif diff_type == self.DIFF_DELETE:
                # Deletion.
                patch.length1 += len(diff_text)
                patch.diffs.append(diffs[x])
                post_patch_text = (post_patch_text[:char_count2] + post_patch_text[char_count2 + len(diff_text):])
            elif (diff_type == self.DIFF_EQUAL and len(diff_text) <= 2 * self.patch_margin and len(patch.diffs) != 0
                  and len(diffs) != x + 1):
                # Small equality inside a patch.
                patch.diffs.append(diffs[x])
                patch.length1 += len(diff_text)
                patch.length2 += len(diff_text)

            if diff_type == self.DIFF_EQUAL and len(diff_text) >= 2 * self.patch_margin:
                # Time for a new patch.
                if len(patch.diffs) != 0:
                    self.patch_add_context(patch, pre_patch_text)
                    patches.append(patch)
                    patch = PatchObject()
                    # Unlike Unidiff, our patch lists have a rolling context.
                    # http://code.google.com/p/google-diff-match-patch/wiki/Unidiff
                    # Update prepatch text & pos to reflect the application of the
                    # just completed patch.
                    pre_patch_text = post_patch_text
                    char_count1 = char_count2

            # Update the current character count.
            if diff_type != self.DIFF_INSERT:
                char_count1 += len(diff_text)
            if diff_type != self.DIFF_DELETE:
                char_count2 += len(diff_text)

        # Pick up the leftover patch if not empty.
        if len(patch.diffs) != 0:
            self.patch_add_context(patch, pre_patch_text)
            patches.append(patch)
        return patches

    @staticmethod
    def patch_deep_copy(patches: List[PatchObject])->List[PatchObject]:
        """Given an array of patches, return another array that is identical.

        :param patches: Array of Patch objects.
        :return: Array of Patch objects.
        """
        patches_copy = []
        for patch in patches:
            patch_copy = PatchObject()
            # No need to deep copy the tuples since they are immutable.
            patch_copy.diffs = patch.diffs[:]
            patch_copy.start1 = patch.start1
            patch_copy.start2 = patch.start2
            patch_copy.length1 = patch.length1
            patch_copy.length2 = patch.length2
            patches_copy.append(patch_copy)
        return patches_copy

    def patch_apply(self, patches: List[PatchObject], text: str)->Tuple[str, List[bool]]:
        """Merge a set of patches onto the text.  Return a patched text, as well
        as a list of true/false values indicating which patches were applied.

        :param patches: Array of Patch objects.
        :param text: Old text.
        :return: Two element Array, containing the new text and an array of boolean values.
        """
        if not patches:
            return text, []

        # Deep copy the patches so that no changes are made to originals.
        patches = self.patch_deep_copy(patches)

        null_padding = self.patch_add_padding(patches)
        text = null_padding + text + null_padding
        self.patch_split_max(patches)

        # delta keeps track of the offset between the expected and actual location
        # of the previous patch.  If there are patches expected at positions 10 and
        # 20, but the first patch was found at 12, delta is 2 and the second patch
        # has an effective expected position of 22.
        delta = 0
        results = []
        for patch in patches:
            expected_loc = patch.start2 + delta
            text1 = self.diff_text1(patch.diffs)
            end_loc = -1
            if len(text1) > self.match_max_bits:
                # patch_splitMax will only provide an oversized pattern in the case of
                # a monster delete.
                start_loc = self.match_main(text, text1[:self.match_max_bits], expected_loc)
                if start_loc != -1:
                    tmp = expected_loc + len(text1) - self.match_max_bits
                    end_loc = self.match_main(text, text1[-self.match_max_bits:], tmp)
                    if end_loc == -1 or start_loc >= end_loc:
                        # Can't find valid trailing context.  Drop this patch.
                        start_loc = -1
            else:
                start_loc = self.match_main(text, text1, expected_loc)
            if start_loc == -1:
                # No match found.  :(
                results.append(False)
                # Subtract the delta for this failed patch from subsequent patches.
                delta -= patch.length2 - patch.length1
            else:
                # Found a match.  :)
                results.append(True)
                delta = start_loc - expected_loc
                if end_loc == -1:
                    text2 = text[start_loc: start_loc + len(text1)]
                else:
                    text2 = text[start_loc: end_loc + self.match_max_bits]
                if text1 == text2:
                    # Perfect match, just shove the replacement text in.
                    text = (text[:start_loc] + self.diff_text2(patch.diffs) + text[start_loc + len(text1):])
                else:
                    # Imperfect match.
                    # Run a diff to get a framework of equivalent indices.
                    diffs = self.diff_main(text1, text2, False)
                    tmp = self.diff_levenshtein(diffs) / float(len(text1))
                    if len(text1) > self.match_max_bits and tmp > self.patch_delete_threshold:
                        # The end points match, but the content is unacceptably bad.
                        results[-1] = False
                    else:
                        self.diff_cleanup_semantic_loss_less(diffs)
                        index1 = 0
                        for (op, data) in patch.diffs:
                            if op != self.DIFF_EQUAL:
                                index2 = self.diff_x_index(diffs, index1)
                            if op == self.DIFF_INSERT:  # Insertion
                                text = text[:start_loc + index2] + data + text[start_loc + index2:]
                            elif op == self.DIFF_DELETE:  # Deletion
                                tmp = text[start_loc + self.diff_x_index(diffs, index1 + len(data)):]
                                text = text[:start_loc + index2] + tmp
                            if op != self.DIFF_DELETE:
                                index1 += len(data)
        # Strip the padding off.
        text = text[len(null_padding):-len(null_padding)]
        return text, results

    def patch_add_padding(self, patches: List[PatchObject])->str:
        """Add some padding on text start and end so that edges can match something.
        Intended to be called only from within patch_apply.

        :param patches: Array of Patch objects.
        :return: The padding string added to each side.
        """
        padding_length = self.patch_margin
        null_padding = ""
        for x in range(1, padding_length + 1):
            null_padding += chr(x)

        # Bump all the patches forward.
        for patch in patches:
            patch.start1 += padding_length
            patch.start2 += padding_length

        # Add some padding on start of first diff.
        patch = patches[0]
        diffs = patch.diffs
        if not diffs or diffs[0][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.insert(0, (self.DIFF_EQUAL, null_padding))
            patch.start1 -= padding_length  # Should be 0.
            patch.start2 -= padding_length  # Should be 0.
            patch.length1 += padding_length
            patch.length2 += padding_length
        elif padding_length > len(diffs[0][1]):
            # Grow first equality.
            extra_length = padding_length - len(diffs[0][1])
            new_text = null_padding[len(diffs[0][1]):] + diffs[0][1]
            diffs[0] = (diffs[0][0], new_text)
            patch.start1 -= extra_length
            patch.start2 -= extra_length
            patch.length1 += extra_length
            patch.length2 += extra_length

        # Add some padding on end of last diff.
        patch = patches[-1]
        diffs = patch.diffs
        if not diffs or diffs[-1][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.append((self.DIFF_EQUAL, null_padding))
            patch.length1 += padding_length
            patch.length2 += padding_length
        elif padding_length > len(diffs[-1][1]):
            # Grow last equality.
            extra_length = padding_length - len(diffs[-1][1])
            new_text = diffs[-1][1] + null_padding[:extra_length]
            diffs[-1] = (diffs[-1][0], new_text)
            patch.length1 += extra_length
            patch.length2 += extra_length

        return null_padding

    def patch_split_max(self, patches: List[PatchObject]):
        """Look through the patches and break up any which are longer than the maximum limit of the match algorithm.
        Intended to be called only from within patch_apply.

        :param patches: Array of Patch objects.
        :return:
        """
        patch_size = self.match_max_bits
        if patch_size == 0:
            # Python has the option of not splitting strings due to its ability
            # to handle integers of arbitrary precision.
            return
        for x in range(len(patches)):
            if patches[x].length1 <= patch_size:
                continue
            big_patch = patches[x]
            # Remove the big old patch.
            del patches[x]
            x -= 1
            start1 = big_patch.start1
            start2 = big_patch.start2
            pre_context = ''
            while len(big_patch.diffs) != 0:
                # Create one of several smaller patches.
                patch = PatchObject()
                empty = True
                patch.start1 = start1 - len(pre_context)
                patch.start2 = start2 - len(pre_context)
                if pre_context:
                    patch.length1 = patch.length2 = len(pre_context)
                    patch.diffs.append((self.DIFF_EQUAL, pre_context))

                while len(big_patch.diffs) != 0 and patch.length1 < patch_size - self.patch_margin:
                    (diff_type, diff_text) = big_patch.diffs[0]
                    if diff_type == self.DIFF_INSERT:
                        # Insertions are harmless.
                        patch.length2 += len(diff_text)
                        start2 += len(diff_text)
                        patch.diffs.append(big_patch.diffs.pop(0))
                        empty = False
                    elif (diff_type == self.DIFF_DELETE and len(patch.diffs) == 1
                          and patch.diffs[0][0] == self.DIFF_EQUAL and len(diff_text) > 2 * patch_size):

                        # This is a large deletion.  Let it pass in one chunk.
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        empty = False
                        patch.diffs.append((diff_type, diff_text))
                        del big_patch.diffs[0]
                    else:
                        # Deletion or equality.  Only take as much as we can stomach.
                        diff_text = diff_text[:patch_size - patch.length1 - self.patch_margin]
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        if diff_type == self.DIFF_EQUAL:
                            patch.length2 += len(diff_text)
                            start2 += len(diff_text)
                        else:
                            empty = False

                        patch.diffs.append((diff_type, diff_text))
                        if diff_text == big_patch.diffs[0][1]:
                            del big_patch.diffs[0]
                        else:
                            big_patch.diffs[0] = (big_patch.diffs[0][0], big_patch.diffs[0][1][len(diff_text):])

                # Compute the head context for the next patch.
                pre_context = self.diff_text2(patch.diffs)
                pre_context = pre_context[-self.patch_margin:]
                # Append the end context for this patch.
                post_context = self.diff_text1(big_patch.diffs)[:self.patch_margin]
                if post_context:
                    patch.length1 += len(post_context)
                    patch.length2 += len(post_context)
                    if len(patch.diffs) != 0 and patch.diffs[-1][0] == self.DIFF_EQUAL:
                        patch.diffs[-1] = (self.DIFF_EQUAL, patch.diffs[-1][1] + post_context)
                    else:
                        patch.diffs.append((self.DIFF_EQUAL, post_context))

                if not empty:
                    x += 1
                    patches.insert(x, patch)

    @staticmethod
    def patch_to_text(patches: List[PatchObject])->str:
        """Take a list of patches and return a textual representation.

        :param patches: Array of Patch objects.
        :return: Text representation of patches.
        """
        text = []
        for patch in patches:
            text.append(str(patch))
        return "".join(text)

    def patch_from_text(self, text_line: str)->List[PatchObject]:
        """Parse a textual representation of patches and return a list of patch objects.

        :param text_line: Text representation of patches.
        :return: Array of Patch objects.
        """
        patches = []
        if not text_line:
            return patches
        text = text_line.split('\n')
        while len(text) != 0:
            m = match("^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@$", text[0])
            if not m:
                raise ValueError("Invalid patch string: " + text[0])
            patch = PatchObject()
            patches.append(patch)
            patch.start1 = int(m.group(1))
            if m.group(2) == '':
                patch.start1 -= 1
                patch.length1 = 1
            elif m.group(2) == '0':
                patch.length1 = 0
            else:
                patch.start1 -= 1
                patch.length1 = int(m.group(2))

            patch.start2 = int(m.group(3))
            if m.group(4) == '':
                patch.start2 -= 1
                patch.length2 = 1
            elif m.group(4) == '0':
                patch.length2 = 0
            else:
                patch.start2 -= 1
                patch.length2 = int(m.group(4))

            del text[0]

            while len(text) != 0:
                if text[0]:
                    sign = text[0][0]
                else:
                    sign = ''
                line = unquote(text[0][1:])
                if sign == '+':
                    # Insertion.
                    patch.diffs.append((self.DIFF_INSERT, line))
                elif sign == '-':
                    # Deletion.
                    patch.diffs.append((self.DIFF_DELETE, line))
                elif sign == ' ':
                    # Minor equality.
                    patch.diffs.append((self.DIFF_EQUAL, line))
                elif sign == '@':
                    # Start of next patch.
                    break
                elif sign == '':
                    # Blank line?  Whatever.
                    pass
                else:
                    # WTF?
                    raise ValueError("Invalid patch mode: '%s'\n%s" % (sign, line))
                del text[0]
        return patches


diff_engine = DiffMatchPatch()
diff_engine.diff_timeout = 2
diff_engine.match_threshold = 0.0
diff_engine.patch_delete_threshold = 0.0
diff_engine.match_max_bits = 0


def error_message_box(title: str, text: str, error: str, parent=None):
    """General messagebox if an error happened.

    :param title: Title of dialog window
    :type title: str
    :param text: Main text of dialog window
    :type text: str
    :param error: the error text generated by python
    :type error: str
    :param parent: The parent widget owning this messagebox
    :type parent: QWidget
    :return: None
    :rtype: None
    """

    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Critical)
    msg.setText("<strong>An error has occurred!<strong>")
    msg.setInformativeText(text)
    msg.setDetailedText(error)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.setDefaultButton(QMessageBox.Ok)
    msg.exec()


# setup logger
LOGGING_LEVEL = logging.DEBUG
LOGGING_FORMAT = "%(levelname)s %(asctime)s - %(message)s "
script_path = Path(__file__).parent.resolve()
log_filename = script_path / "log" / "vql_manager.log"
log_dir = log_filename.parent

if not log_dir.is_dir():
    try:
        log_dir.mkdir()
    except (OSError, IOError) as e:
        _msg = f"Could not create log directory: {str(log_filename.parent)}"
        error_message_box("Log file error", _msg, str(e))

if not log_filename.is_file():
    try:
        log_filename.touch()
    except (OSError, IOError) as e:
        _msg = f"Could not create logfile: {str(log_filename)}"
        error_message_box("Log file error", _msg, str(e))


class LogWrapper(QObject):
    """Wrapper class for logging.logger"""

    custom_signal = pyqtSignal(str)
    loggers = set()

    def __init__(self, name, _format='', level=logging.INFO, filename='vql_manager.log', filemode='w'):
        """Class initializer

        :param name: name of the app
        :param _format: format of the log
        :param level: level of the log
        :param filename: filename
        :param filemode: filemode of teh log: either 'a' or 'w'
        """

        super(LogWrapper, self).__init__()
        self.format = _format
        self.level = level
        self.name = name
        self.filename = filename
        self.filemode = filemode

        # logging.basicConfig(filename=self.filename, level=self.level, format=self.format, filemode=self.filemode)

        self.log_formatter = logging.Formatter(self.format)
        self.file_logger = logging.FileHandler(self.filename, mode=self.filemode)
        self.file_logger.setFormatter(self.log_formatter)

        self.logger = logging.getLogger(self.name)
        if name not in self.loggers:
            self.loggers.add(name)
            self.logger.setLevel(self.level)
            self.logger.addHandler(self.file_logger)

    # noinspection PyUnusedLocal
    def error(self, msg, *args, **kwargs):
        """Wraps logger function and sends a signal

        :param msg: the message to log
        :param args: not used
        :param kwargs: not used
        :return: None
        """
        self.custom_signal.emit('ERROR: ' + msg)
        self.logger.error(msg)

    # noinspection PyUnusedLocal
    def info(self, msg, *args, **kwargs):
        """Wraps logger function and sends a signal

        :param msg: the message to log
        :param args: not used
        :param kwargs: not used
        :return: None
        """
        self.custom_signal.emit('INFO: ' + msg)
        self.logger.info(msg)

    # noinspection PyUnusedLocal
    def debug(self, msg, *args, **kwargs):
        """Wraps logger function and sends a signal

        :param msg: the message to log
        :param args: not used
        :param kwargs: not used
        :return: None
        """
        self.custom_signal.emit('DEBUG: ' + msg)
        self.logger.debug(msg)

    # noinspection PyUnusedLocal
    def critical(self, msg, *args, **kwargs):
        """Wraps logger function and sends a signal

        :param msg: the message to log
        :param args: not used
        :param kwargs: not used
        :return: None
        """
        self.custom_signal.emit('FATAL: ' + msg)
        self.logger.critical(msg)

    # noinspection PyUnusedLocal
    def warning(self, msg, *args, **kwargs):
        """Wraps logger function and sends a signal

        :param msg: the message to log
        :param args: not used
        :param kwargs: not used
        :return: None
        """
        self.custom_signal.emit('WARNING: ' + msg)
        self.logger.warning(msg)


def message_to_user(message: str, parent=None):
    """General messagebox to inform the user

    :param message: the message of the messagebox
    :param parent: the parent widget
    :return: None
    """

    msg = QMessageBox(parent)
    msg.setWindowTitle("You got a message!")
    msg.setIcon(QMessageBox.Question)
    msg.setText("<strong>" + message + "<strong>")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.setDefaultButton(QMessageBox.Ok)
    msg.exec()


# convenience names for class constants
PART_STATE = Qt.PartiallyChecked
CHECKED = Qt.Checked
UNCHECKED = Qt.Unchecked

# Hint for the width of the tree widgets
PANE_WIDTH = 300

# # application modes en flags

# colors used
red = "#ff4444"
green = "#44ff44"
yellow = "#ffff44"
white = "#cccccc"

LOG_FILE_NAME = "part.log"

# main chapter names as used in Denodo code
CHAPTER_NAMES = ["I18N MAPS", "DATABASE", "FOLDERS", "LISTENERS JMS", "DATASOURCES", "WRAPPERS",
                 "STORED PROCEDURES", "TYPES", "MAPS", "BASE VIEWS", "VIEWS", "ASSOCIATIONS",
                 "WEBSERVICES", "WIDGETS", "WEBCONTAINER WEB SERVICE DEPLOYMENTS",
                 "WEBCONTAINER WIDGET DEPLOYMENTS"]

# the delimiter use to separate chapters into CodeItems
DELIMITER = "CREATE OR REPLACE"

# Start quote of the Denodo script
PROP_QUOTE = "# REQUIRES-PROPERTIES-FILE - # Do not remove this comment!\n#\n"


# app_state flags
class GuiType(QObject):
    """Global constants for the gui modes"""
    GUI_NONE = 1 << 1                  # initial or reset mode
    GUI_SELECT = 1 << 2           # gui set to selection mode
    GUI_COMPARE = 1 << 3          # gui set to compare, with a base model and a compare model


class ModelState(QObject):
    """Global constants for the gui modes"""
    BASE_FILE = 1 << 4        # indicate that the base model is a single file
    BASE_REPO = 1 << 5        # indicate that the base model is a repository (folder structure)
    COMP_FILE = 1 << 6        # indicate that the base model is a single file
    COMP_REPO = 1 << 7        # indicate that the base model is a repository (folder structure)
    BASE_LOADED = 1 << 8      # indicate that the base model is loaded
    COMP_LOADED = 1 << 9      # indicate that the compare model is loaded
    BASE_UNLOAD = 1 << 10     # indicate that the base model must unload
    COMP_UNLOAD = 1 << 11     # indicate that the compare model is unload


class SourceType(QObject):
    """Global constants for the gui modes"""
    FILE = ModelState.BASE_FILE | ModelState.COMP_FILE
    REPO = ModelState.BASE_REPO | ModelState.COMP_REPO


class ViewType(QObject):
    """Global constants for the gui modes"""
    SCRIPT_VIEW = 1 << 12
    DENODO_VIEW = 1 << 13
    DEPEND_VIEW = 1 << 14


class CodeView(QObject):
    """Global constants for the gui modes"""
    ORIGINAL_CODE = 1 << 15
    COMPARE_CODE = 1 << 16
    DIFF_CODE = 1 << 17


class Pane(QObject):
    """Global constants for the pane modes"""
    LEFT = 1 << 18
    RIGHT = 1 << 19


class ItemProperties(QObject):
    """Role identifiers"""
    DISPLAY = Qt.DisplayRole
    EDIT = Qt.EditRole
    COLOR = Qt.ForegroundRole
    DATA = Qt.UserRole + 1
    TYPE = Qt.UserRole + 2
    CHECK = Qt.CheckStateRole
    TIP = Qt.ToolTipRole
    ICON = Qt.DecorationRole


GUI_NONE = GuiType.GUI_NONE
GUI_SELECT = GuiType.GUI_SELECT
GUI_COMPARE = GuiType.GUI_COMPARE

BASE_FILE = ModelState.BASE_FILE
BASE_REPO = ModelState.BASE_REPO
COMP_FILE = ModelState.COMP_FILE
COMP_REPO = ModelState.COMP_REPO
BASE_LOADED = ModelState.BASE_LOADED
COMP_LOADED = ModelState.COMP_LOADED
BASE_UNLOAD = ModelState.BASE_UNLOAD
COMP_UNLOAD = ModelState.COMP_UNLOAD


FILE = SourceType.FILE
REPO = SourceType.REPO

SCRIPT_VIEW = ViewType.SCRIPT_VIEW
DENODO_VIEW = ViewType.DENODO_VIEW
DEPEND_VIEW = ViewType.DEPEND_VIEW

ORIGINAL_CODE = CodeView.ORIGINAL_CODE
COMPARE_CODE = CodeView.COMPARE_CODE
DIFF_CODE = CodeView.DIFF_CODE

LEFT = Pane.LEFT
RIGHT = Pane.RIGHT

DISPLAY = ItemProperties.DISPLAY
EDIT = ItemProperties.EDIT
COLOR = ItemProperties.COLOR
DATA = ItemProperties.DATA
TYPE = ItemProperties.TYPE
CHECK = ItemProperties.CHECK
TIP = ItemProperties.TIP
ICON = ItemProperties.ICON

ROLES = [DISPLAY, EDIT, COLOR, DATA, TYPE, CHECK, TIP, ICON]

FONT = QFont()
FONT.setPointSize(8)

NOTHING = QVariant()

RECENT_FILES = "recent_file_list"
RECENT_REPOSITORIES = "recent_repositories_list"
MAX_RECENT_FILES = 8


def show_role(role: int)->str:
    """Debug function printing the role info

    :param role: the role
    :return: human readable string
    """
    result = 'NOTHING'
    if role == DISPLAY:
        result = 'DISPLAY'
    elif role == EDIT:
        result = 'EDIT'
    elif role == COLOR:
        result = 'COLOR'
    elif role == DATA:
        result = 'DATA'
    elif role == TYPE:
        result = 'TYPE'
    elif role == CHECK:
        result = 'CHECK'
    elif role == TIP:
        result = 'TIP'
    return result


def show_color(item_color: QBrush)->str:
    """Debug function to get the color in human readable form

    :param item_color: The color as a QBrush
    :return: human readable string
    """
    color = 'None'
    if item_color:
        if item_color == red:
            color = 'red'
        elif item_color == green:
            color = 'green'
        elif item_color == yellow:
            color = 'yellow'
        elif item_color == white:
            color = 'white'
    return color


def show_mode(mode: int)->str:
    """Returns debug info string to logger.

    :param mode: the mode to show
    :return: a human readable string with flags
    """
    gui_types = {GUI_NONE: "GUI_NONE", GUI_SELECT: "GUI_SELECT", GUI_COMPARE: "GUI_COMPARE"}

    model_states = {BASE_FILE: "BASE_FILE", BASE_REPO: "BASE_REPO", COMP_FILE: "COMP_FILE", COMP_REPO: "COMP_REPO",
                    BASE_LOADED: "BASE_LOADED", COMP_LOADED: "COMP_LOADED",
                    BASE_UNLOAD: "BASE_UNLOAD", COMP_UNLOAD: "COMP_UNLOAD"}

    source_types = {FILE: "FILE", REPO: "REPO"}

    mode_txt = list()
    for num, name in gui_types.items():
        if mode & num:
            mode_txt.append(name)
    for num, name in model_states.items():
        if mode & num:
            mode_txt.append(name)
    for num, name in source_types.items():
        if mode & num:
            mode_txt.append(name)
    return " : ".join(mode_txt)


def get_reserved_words()->Iterator[Sized]:
    """Returns a list (Iterator) over the Denodo reserved words.

    :return: the list with reserved words
    """
    words = '''ADD,AS,ANY,OPT,OR,CREATE,VIEW,NULL,ALTER,NOT,FROM,AND,SELECT,WHEN,JOIN,IS,ON,LEFT,CASE,TABLE,
    WHERE,DEFAULT,OFF,JDBC,INNER,OF,ZERO,NOS,UNION,DF,DISTINCT,ASC,FULL,FALSE,DESC,BASE,DATABASE,TRUE,ALL,
    CONTEXT,CONNECT,LDAP,WITH,SWAP,ARN,BOTH,CALL,CROSS,CURRENT_DATE,CURRENT_TIMESTAMP,CUSTOM,DROP,EXISTS,
    FETCH,FLATTEN,GRANT,GROUP BY,GS,HASH,HAVING,HTML,IF,INTERSECT,INTO,LEADING,LIMIT,MERGE,MINUS,MY,NATURAL,
    NESTED,OBL,ODBC,OFFSET,ONE,ORDER BY,ORDERED,PRIVILEGES,READ,REVERSEORDER,REVOKE,RIGHT,
    ROW,TO,TRACE,TRAILING,USER,USING,WRITE,WS'''
    words = words.replace('\n', '')
    words = words.split(',')
    words.append(DELIMITER)
    words.extend([name[:-1] for name in CHAPTER_NAMES if not name == 'DATABASE'])
    words.append('DATABASE')
    # noinspection PyTypeChecker
    reserved_words = list(reversed(sorted(words, key=len)))
    return reserved_words


HIGHLIGHTED_WORDS = get_reserved_words()
SUBSTITUTIONS = list([(word, '<span><rword style="color:#b220e8;">' + str(word) + '</rword></span>')
                      for word in HIGHLIGHTED_WORDS])


def doc_template(object_name: str, body: str)->str:
    """Returns an html page

    :param object_name: name of the object
    :param body: body of the page
    :return: the page
    """
    doc = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>""" + object_name + """</title>
    <meta name="description" content="Denodo code part">
  </head>
  <body>""" + body + """</body>
</html>
"""
    return doc


about_text = """
VQL Manager was created by Erasmus MC Rotterdam The Netherlands 2017.
This application is open source software.
Questions and remarks should be sent to: andretreebus@hotmail.com
"""


def load_model_from_file(file: Path, new_mode: int, root_item, bar: QStatusBar, icons: dict, logger):
    """Loads a single .vql file into the VqlModel instance.

    :param file: path of the file to bew loaded in
    :type file: Path
    :param new_mode: either BASE_FILE or COMP_FILE
    :type new_mode: int
    :param root_item: RootItem
    :param bar: statusbar
    :param icons: icons
    :param logger: logger
    :return: None
    :rtype: None
    """
    content = read_file(file, logger)
    if content:
        root_item.parse(content, new_mode, bar, icons, logger)


def load_model_from_repository(folder: Path, new_mode: int, root_item, bar: QStatusBar, icons: dict, logger):
    """Loads a repository folder structure into the VqlModel instance.

    :param folder: the folder containing the repository
    :type folder: Path
    :param new_mode: flag indication BASE_REPO or COMP_REPO
    :param root_item: the root
    :param bar: statusbar
    :param icons: icons
    :param logger: logger
    :return: None
    :rtype: None
    """

    existing_folders = {sub_folder for sub_folder in folder.iterdir()}
    possible_folders = {folder / sub_folder for sub_folder in CHAPTER_NAMES}
    matching_folders = existing_folders & possible_folders
    if not matching_folders:
        # noinspection PyArgumentList
        QApplication.setOverrideCursor(Qt.WaitCursor)
        message = "No repository found. Did not find any matching sub folders."
        message_to_user(message)
        return

    msg = 'Make sure your repository is not corrupt.'
    part_files = [folder / sub_folder / LOG_FILE_NAME
                  for sub_folder in CHAPTER_NAMES if folder / sub_folder in matching_folders]
    non_existing_part_files = [str(part_file) for part_file in part_files if not part_file.is_file()]
    existing_part_files = [part_file for part_file in part_files if part_file.is_file()]
    if non_existing_part_files:
        missing = ', '.join(non_existing_part_files)
        message_to_user(f"{LOG_FILE_NAME} file(s): {missing} not found. {msg}")

    all_code_files = list()

    for part_file in existing_part_files:
        file_content = read_file(part_file, logger)
        code_files = [Path(code_file) for code_file in file_content.split('\n')]
        non_existing_code_files = [str(code_file) for code_file in code_files if not code_file.is_file()]
        if non_existing_code_files:
            missing = ', '.join(non_existing_code_files)
            message_to_user(f"Code file(s): {missing} not found. {msg}")
        existing_code_files = [(str(code_file.parent.name), code_file)
                               for code_file in code_files if code_file.is_file()]
        all_code_files.extend(existing_code_files)

    content = PROP_QUOTE
    for chapter in root_item.chapters:
        content += chapter.header
        files = [file for chapter_name, file in all_code_files if chapter_name == chapter.name]
        for file in files:
            content += read_file(file, logger)

    if content:
        if content:
            root_item.parse(content, new_mode, bar, icons, logger)
    else:
        error_message_box('Load Failed', 'No content found', '')
        return


def read_file(file: Path, logger) -> str:
    """General function to read in a file

    :param file: the file to be read
    :param logger: the logger in the app
    :return: None
    """

    logger.debug('Reading: ' + str(file))
    content = None
    try:
        with file.open() as f:
            content = f.read()
    except (OSError, IOError) as error:
        msg = "An error occurred during reading of file: "
        error_message_box("Error", msg + str(file), str(error))
    if content:
        logger.debug(f"{str(file)} with {len(content)} characters read.")
    return content


class TransOpenBase(QSignalTransition):
    """Transition class from init to base_loaded"""
    
    def __init__(self, _app: QMainWindow, source_state: QState, target_state: QState, signal):
        """Initializer of the class. this is a class responsible for the transition between states

        :param _app: the QmainWindow app
        :param source_state: starting state in the statemachine
        :param target_state: target state in the statemachine
        :param signal: the signal that triggers transition, this is the mode_change.emit
            eventTest is called after this signal is emitted. When the test returns True
            the onTransition is called by the state_machine
        """
        super(TransOpenBase, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent)->bool:
        """Selector for the transition. this function listens to the signals and tests them.
        If the test succeeds the transition is called.

        :param event: the signal or other event
        :return:
        """
        if type(event) != QStateMachine.SignalEvent:
            return False
        mode = event.arguments()[0]

        if not mode & BASE_LOADED:
            if mode & (BASE_FILE | BASE_REPO):
                if self.app.base_repository_file or self.app.base_repository_folder:
                    return True
            return False
        else:
            return False

    def onTransition(self, event: QStateMachine.SignalEvent):
        """This method is called to actually make the transition to another state of the app

        :param event: not used here
        :return:
        """
        mode = event.arguments()[0]
        s = self.app
        s.setWindowTitle(APPLICATION_NAME + ' Base Mode')
        s.diff_buttons.setHidden(True)
        s.select_buttons.setHidden(True)
        s.code_show_selector = ORIGINAL_CODE
        s.compare_repository_label.setText('')
        # noinspection PyArgumentList
        QApplication.setOverrideCursor(Qt.WaitCursor)
        s.treeview1.blockSignals(True)
        s.tree_model.beginResetModel()
        if mode & BASE_FILE:
            s.logger.debug(f"Loading model from file in {show_mode(mode)} mode")
            # noinspection PyUnresolvedReferences
            s.status_bar.showMessage("Loading model from file.")
            file = s.base_repository_file
            s.base_repository_label.setText('File : ' + str(file))
            load_model_from_file(file, BASE_FILE | GUI_SELECT, s.root_item, s.status_bar, s.icons, s.logger)
            s.working_folder = file.resolve().parent
            s.add_to_recent_files(file, FILE)

        elif mode & BASE_REPO:
            s.logger.debug(f"Loading model from repository in {show_mode(mode)} mode")
            # noinspection PyUnresolvedReferences
            s.status_bar.showMessage("Loading model from repository")
            repo = s.base_repository_folder
            s.base_repository_label.setText('Repository : ' + str(repo))
            load_model_from_repository(repo, BASE_REPO | GUI_SELECT, s.root_item, s.status_bar, s.icons, s.logger)
            s.working_folder = repo
            s.add_to_recent_files(repo, REPO)

        if mode & SCRIPT_VIEW:
            s.denodo_folder_structure_action.setChecked(False)
            s.on_switch_view()

        s.tree_model.endResetModel()
        s.treeview1.blockSignals(False)
        s.dependency_model.gui = GUI_SELECT
        s.logger.debug(f"Loading model from file finished.")

        # noinspection PyArgumentList
        QApplication.restoreOverrideCursor()

        s.export_file_action.setEnabled(True)
        s.export_folder_action.setEnabled(True)
        s.open_compare_file_action.setEnabled(True)
        s.open_compare_folder_action.setEnabled(True)
        s.denodo_folder_structure_action.setEnabled(True)
        s.compare_recent_repository_menu.setEnabled(True)
        s.compare_recent_file_menu.setEnabled(True)
        s.add_mode(BASE_LOADED)
        # noinspection PyUnresolvedReferences
        s.status_bar.showMessage("Ready")
        s.logger.debug("Finished setting mode: " + show_mode(s.get_mode()))


class TransResetBase(QSignalTransition):
    """Transition class from base_loaded to init"""

    def __init__(self, _app: QMainWindow, source_state: QState, target_state: QState, signal):
        """Initializer of the class. this is a class responsible for the transition between states

        :param _app: the QmainWindow app
        :param source_state: starting state in the statemachine
        :param target_state: target state in the statemachine
        :param signal: the signal that triggers transition, this is the mode_change.emit
            eventTest is called after this signal is emitted. When the test returns True
            the onTransition is called by the state_machine
        """
        super(TransResetBase, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent)->bool:
        """Selector for the transition. this function listens to the signals and tests them.
        If the test succeeds the transition is called.

        :param event: the signal or other event
        :return:
        """
        if type(event) != QStateMachine.SignalEvent:
            return False
        mode = event.arguments()[0]
        if mode & BASE_UNLOAD:
            if mode & BASE_LOADED:
                if mode & (BASE_FILE | BASE_REPO):
                    if self.app.base_repository_file or self.app.base_repository_folder:
                        return True
            return False
        else:
            return False

    def onTransition(self, event):
        """This method is called to actually make the transition to another state of the app

        :param event: not used here
        :return:
        """
        mode = event.arguments()[0]
        old_mode = int(mode)
        s = self.app
        s.setWindowTitle(APPLICATION_NAME)
        # noinspection PyArgumentList
        QApplication.setOverrideCursor(Qt.WaitCursor)
        s.treeview1.blockSignals(True)

        s.tree_model.reset()

        s.base_repository_file = ''
        s.base_repository_folder = ''
        s.compare_repository_file = ''
        s.compare_repository_folder = ''

        s.base_repository_label.setText('No File opened')

        s.export_file_action.setEnabled(False)
        s.export_folder_action.setEnabled(False)
        s.open_compare_file_action.setEnabled(False)
        s.open_compare_folder_action.setEnabled(False)
        s.denodo_folder_structure_action.setEnabled(False)
        s.compare_recent_repository_menu.setEnabled(False)
        s.compare_recent_file_menu.setEnabled(False)
        # noinspection PyUnresolvedReferences
        s.status_bar.showMessage("All Reset")

        removals = (BASE_UNLOAD, BASE_LOADED, BASE_REPO, BASE_FILE)

        for removal in removals:
            if old_mode & removal:
                old_mode -= removal
        s.set_mode(old_mode)

        # noinspection PyArgumentList
        QApplication.restoreOverrideCursor()
        s.logger.debug("Finished removing base, mode : " + show_mode(s.get_mode()))


class TransOpenCompare(QSignalTransition):
    """Transition class from base_loaded to compare_loaded"""
    
    def __init__(self, _app: QMainWindow, source_state: QState, target_state: QState, signal):
        """Initializer of the class. this is a class responsible for the transition between states

        :param _app: the QmainWindow app
        :param source_state: starting state in the statemachine
        :param target_state: target state in the statemachine
        :param signal: the signal that triggers transition, this is the mode_change.emit
            eventTest is called after this signal is emitted. When the test returns True
            the onTransition is called by the state_machine
        """
        super(TransOpenCompare, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent)->bool:
        """Selector for the transition. this function listens to the signals and tests them.
        If the test succeeds the transition is called.

        :param event: the signal or other event
        :return:
        """
        if type(event) != QStateMachine.SignalEvent:
            return False
        mode = event.arguments()[0]

        if mode & BASE_LOADED:
            if self.app.compare_repository_file or self.app.compare_repository_folder:
                return True
            return False
        else:
            return False

    def onTransition(self, event: QStateMachine.SignalEvent):
        """This method is called to actually make the transition to another state of the app

        :param event: not used here
        :return:
        """
        mode = event.arguments()[0]
        s = self.app
        s.setWindowTitle(APPLICATION_NAME + ' Compare Mode')
        s.diff_buttons.setHidden(False)
        s.select_buttons.setHidden(False)
        # noinspection PyArgumentList
        QApplication.setOverrideCursor(Qt.WaitCursor)
        s.treeview1.blockSignals(True)
        s.tree_model.beginResetModel()
        s.code_show_selector = DIFF_CODE
        s.on_click_item(None)

        if mode & COMP_FILE:
            s.logger.debug(f"Loading model from file in {show_mode(mode)} mode")
            # noinspection PyUnresolvedReferences
            s.status_bar.showMessage("Loading model from file.")
            file = s.compare_repository_file
            s.compare_repository_label.setText('File : ' + str(file))
            load_model_from_file(file, COMP_FILE | GUI_SELECT, s.root_item, s.status_bar, s.icons, s.logger)
            s.working_folder = file.resolve().parent
            s.add_to_recent_files(file, FILE)
        elif mode & COMP_REPO:
            s.logger.debug(f"Loading model from repository in {show_mode(mode)} mode")
            # noinspection PyUnresolvedReferences
            s.status_bar.showMessage("Loading model from repository")
            repo = s.compare_repository_folder
            s.compare_repository_label.setText('Repository : ' + str(repo))
            load_model_from_repository(repo, COMP_REPO | GUI_SELECT, s.root_item, s.status_bar, s.icons, s.logger)
            s.working_folder = repo
            s.add_to_recent_files(repo, REPO)

        if mode & SCRIPT_VIEW:
            s.denodo_folder_structure_action.setChecked(False)
            s.on_switch_view()

        s.tree_model.endResetModel()
        s.dependency_model.gui = GUI_COMPARE
        s.treeview1.blockSignals(False)
        s.reset_compare_action.setEnabled(True)
        s.logger.debug(f"Loading model from file finished.")
        # noinspection PyUnresolvedReferences
        s.status_bar.showMessage("Ready")
        # noinspection PyArgumentList
        QApplication.restoreOverrideCursor()

        s.add_mode(COMP_LOADED)
        s.sub_mode(GUI_SELECT)
        s.add_mode(GUI_COMPARE)
        s.logger.debug("Finished setting mode: " + show_mode(s.get_mode()))


class TransRemoveCompare(QSignalTransition):
    """Transition class from compare_loaded to base_loaded"""
    def __init__(self, _app: QMainWindow, source_state: QState, target_state: QState, signal):
        """Initializer of the class. this is a class responsible for the transition between states

        :param _app: the QmainWindow app
        :param source_state: starting state in the statemachine
        :param target_state: target state in the statemachine
        :param signal: the signal that triggers transition, this is the mode_change.emit
            eventTest is called after this signal is emitted. When the test returns True
            the onTransition is called by the state_machine
        """
        super(TransRemoveCompare, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent)->bool:
        """Selector for the transition. this function listens to the signals and tests them.
        If the test succeeds the transition is called.

        :param event: the signal or other event
        :return:
        """
        if type(event) != QStateMachine.SignalEvent:
            return False
        mode = event.arguments()[0]

        if mode & COMP_UNLOAD:
            if mode & COMP_LOADED:
                if mode & BASE_LOADED:
                    if mode & (COMP_FILE | COMP_REPO):
                        if self.app.compare_repository_file or self.app.compare_repository_folder:
                            return True
            return False
        else:
            return False

    def onTransition(self, event):
        """This method is called to actually make the transition to another state of the app

        :param event: not used here
        :return:
        """
        mode = event.arguments()[0]
        old_mode = int(mode)
        s = self.app
        # noinspection PyArgumentList
        QApplication.setOverrideCursor(Qt.WaitCursor)
        s.setWindowTitle(APPLICATION_NAME + ' Base Mode')
        s.diff_buttons.setHidden(True)
        s.select_buttons.setHidden(True)
        s.reset_compare_action.setEnabled(False)
        s.code_show_selector = ORIGINAL_CODE
        s.on_click_item(None)

        s.treeview1.blockSignals(True)
        s.tree_model.remove_compare()
        s.dependency_model.gui = GUI_SELECT
        s.compare_repository_file = ''
        s.compare_repository_folder = ''
        s.compare_repository_label.setText('')
        removals = (COMP_UNLOAD, COMP_LOADED, COMP_FILE, COMP_REPO, GUI_COMPARE)

        for removal in removals:
            if old_mode & removal:
                old_mode -= removal
        s.set_mode(old_mode)
        s.add_mode(GUI_SELECT)

        s.treeview1.blockSignals(False)
        # noinspection PyArgumentList
        QApplication.restoreOverrideCursor()
        s.logger.debug("Finished removal of compare, mode: " + show_mode(s.get_mode()))


class TransResetAll(QSignalTransition):
    """Transition class from compare_loaded to init"""
    def __init__(self, _app: QMainWindow, source_state: QState, target_state: QState, signal):
        """Initializer of the class. this is a class responsible for the transition between states

        :param _app: the QmainWindow app
        :param source_state: starting state in the statemachine
        :param target_state: target state in the statemachine
        :param signal: the signal that triggers transition, this is the mode_change.emit
            eventTest is called after this signal is emitted. When the test returns True
            the onTransition is called by the state_machine
        """
        super(TransResetAll, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent)->bool:
        """Selector for the transition. this function listens to the signals and tests them.
        If the test succeeds the transition is called.

        :param event: the signal or other event
        :return:
        """
        if type(event) != QStateMachine.SignalEvent:
            return False
        mode = event.arguments()[0]

        if mode & BASE_LOADED:
            if mode & COMP_LOADED:
                if mode & COMP_UNLOAD:
                    if mode & BASE_UNLOAD:
                        if mode & (COMP_FILE | COMP_REPO):
                            if mode & (BASE_REPO | BASE_FILE):
                                if self.app.base_repository_file or self.app.base_repository_folder:
                                    if self.app.compare_repository_file or self.app.compare_repository_folder:
                                        return True
            return False
        else:
            return False

    def onTransition(self, event):
        """This method is called to actually make the transition to another state of the app

        :param event: not used here
        :return:
        """
        mode = event.arguments()[0]
        old_mode = int(mode)
        s = self.app
        s.setWindowTitle(APPLICATION_NAME)
        s.diff_buttons.setHidden(True)
        s.select_buttons.setHidden(True)
        s.code_show_selector = ORIGINAL_CODE
        # noinspection PyArgumentList
        QApplication.setOverrideCursor(Qt.WaitCursor)
        s.treeview1.blockSignals(True)

        s.treemodel.reset()

        s.base_repository_file = ''
        s.base_repository_folder = ''
        s.compare_repository_file = ''
        s.compare_repository_folder = ''

        s.base_repository_label.setText('No File opened ')
        s.compare_repository_label.setText('')
        # noinspection PyUnresolvedReferences
        s.status_bar.showMessage("All Reset")

        removals = (COMP_UNLOAD, BASE_UNLOAD, COMP_LOADED, BASE_LOADED, COMP_FILE, COMP_REPO, BASE_REPO, BASE_FILE)

        for removal in removals:
            if old_mode & removal:
                old_mode -= removal
        s.set_mode(old_mode)

        s.export_file_action.setEnabled(False)
        s.export_folder_action.setEnabled(False)
        s.open_compare_file_action.setEnabled(False)
        s.open_compare_folder_action.setEnabled(False)
        s.denodo_folder_structure_action.setEnabled(False)
        s.compare_recent_repository_menu.setEnabled(False)
        s.compare_recent_file_menu.setEnabled(False)

        s.treeview1.blockSignals(False)
        s.dependency_model.gui = GUI_SELECT
        # noinspection PyArgumentList
        QApplication.restoreOverrideCursor()
        s.logger.debug("Finished resetting to init, mode: " + show_mode(s.get_mode()))


class TreeItem(object):
    """Base class for items in tree_model used in tree_views. Will be sub-classed for all treelike items."""
    BRANCH = 1
    LEAF = 2

    def __init__(self, class_type, parent=None, index: int=None):
        """Class initializer

        :param class_type: the type of the subclass
        :param parent: the parent, the higher node in the tree
        :param index: the child index this node has in the parent object
        """
        self.parent_item = parent
        self.class_type = class_type
        if parent:
            if index is None:
                self.parent_item.child_items.append(self)
            else:
                self.parent_item.child_items.insert(index, self)

        self.child_items = list()
        self.column_data = list()
        self.name = ''
        self.color = white
        self.selected = True
        self.tristate = False
        self.tooltip = ''
        self.node_type = TreeItem.BRANCH
        self.icon = QVariant()

    def changed(self)->bool:
        """Returns True if the item has changed. This means is not selected of has children that are not selected

        :return: Returns True if the item has changed.
        """

        if self.node_type == TreeItem.LEAF:
            return not self.selected
        else:
            if self.selected:
                if self.has_children():
                    if any([child.changed() for child in self.child_items]):
                        return True
                    else:
                        return False
            else:
                if self.has_children():
                    return True
                else:
                    return False

    def set_parent(self, parent):
        """Sets the parent item, adds this item to the parents children
        :param parent: the parent item
        """
        assert isinstance(parent, (TreeItem, type(None)))
        self.parent_item = parent
        if parent:
            self.parent_item.child_items.append(self)

    def take_children(self)->list:
        """Allows other objects to take ownership of the children of this tree item.
        The reference to the list of children is destroyed
        :return: A list with this items children
        """
        temp = self.child_items
        self.child_items = list()
        return temp

    def add_children(self, new_children: list):
        """Adds children to this item

        :param new_children: A list with tree items
        """
        for child in new_children:
            assert isinstance(child, TreeItem)
            child.set_parent(self)
            self.child_items.append(child)

    def get_role_data(self, role: int, column: int)->QVariant:
        """Returns the requested data for a role cast to QVariant by the QAbstractTreeModel class

        :param role: The role requested
        :param column: The column (only col 0 used here)
        :return: The data to support the model
        """
        if role in [DISPLAY, EDIT]:
            if column == 0:
                return QVariant(self.name)
            else:
                return QVariant(self.column_data[column])
        elif role == COLOR:
            return QVariant(QBrush(QColor(self.color)))
        elif role == CHECK:
            if column == 0:
                if self.tristate:
                    return PART_STATE
                else:
                    if self.selected:
                        return CHECKED
                    else:
                        return UNCHECKED
        elif role == TIP:
            return QVariant(self.tooltip)
        elif role == ICON:
            return QVariant(self.icon)
        else:
            return NOTHING

    def set_role_data(self, role: int, column: int, value: QVariant)->bool:
        """Sets the data for a role by the QAbstractTreeModel class
        if modifications are made by the user of its tree views

        :param role: The role the data has
        :param column: The column it belongs to
        :param value: the new value
        :return: True if success
        """
        if role in [DISPLAY, EDIT]:
            if column == 0:
                self.column_data[column] = str(value)
                self.name = str(value)
        elif role == COLOR:
            self.color = str(QBrush(value).color())
        elif role == CHECK:
            self.set_selected(False if value == UNCHECKED else True)
        elif role == TIP:
            self.tooltip = str(value)
        else:
            return False
        return True

    def ancestors(self, tree_item):
        """This generator yields all ancestors in the tree of the item given
        :param tree_item: the TreeItem instance whose ancestors are yielded
        :return:
        """
        if isinstance(tree_item, TreeItem) and not isinstance(tree_item, RootItem):
            parent_item = tree_item.parent_item
            yield parent_item
            yield from self.ancestors(parent_item)

    def descendants(self, tree_item):
        """This generator yields all descendants in the tree of the item given

        :param tree_item:the TreeItem instance whose descendants are yielded
        :return:
        """
        if isinstance(tree_item, TreeItem):
            for child in tree_item.child_items:
                yield child
                yield from self.descendants(child)

    def set_selected(self, select: bool):
        """Sets the item selected and takes care to select also the children and sets the tristate

        :param select: A boolean
        """
        if select == self.selected:
            return
        self.selected = select
        self.tristate = False
        # if selected was chosen (True or False ) switch all children also
        for child in self.descendants(self):
            child.selected = select

        # Solve the tristate and selection for the parents
        for parent in self.ancestors(self):
            child_select_list = list(map(lambda x: x.selected, self.descendants(parent)))
            if child_select_list:
                any_child_selected = any(child_select_list)
                all_children_selected = all(child_select_list)
                selected = True if any_child_selected else False
                parent.tristate = True if selected and not all_children_selected else False
                if not any_child_selected:
                    parent.selected = False
                    parent.tristate = False
                if all_children_selected:
                    parent.selected = True
                    parent.tristate = False
                if parent.tristate:
                    parent.selected = True

    def invalidate(self):
        """Resets the this tree item
        :return:
        """
        self.child_items = list()
        self.column_data = list()
        self.name = ''
        self.color = white
        self.selected = True
        self.tristate = False
        self.tooltip = ''
        self.node_type = TreeItem.BRANCH
        self.icon = QVariant()
        self.parent_item = None

    def has_children(self)->bool:
        """Returns True if this item has child items

        :return: Boolean if children present
        """
        return True if len(self.child_items) else False

    def child(self, row: int):
        """Returns the child tree item at index row

        :param row: the index or position of the child in the child list
        :return: a TreeItem instance
        """
        if row < self.child_count():
            return self.child_items[row]
        else:
            return None

    def child_count(self)->int:
        """Returns the child count
        :return:
        """
        return len(self.child_items)

    def child_number(self)->int:
        """Returns the number (index) this child has in its parents child list

        :return: the row or index
        """
        if self.parent_item and self.parent_item.has_children():
            return self.parent_item.child_items.index(self)
        else:
            return -1

    @staticmethod
    def get_child_index_by_name(child_items: list, name: str)->int:
        """Returns the child with given name in the list child items

        :param child_items: the list with items
        :param name: the name sought
        :return: the index of the child
        """
        for i, child in enumerate(child_items):
            if child.name == name:
                return i
        return -1

    def column_count(self)->int:
        """Returns the column count of this item

        :return: the count
        """
        if self.column_data:
            return len(self.column_data)
        else:
            return 0

    def set_column_data(self, column: int, value)->bool:
        """Sets data in the given column

        :param column: the number of the column
        :param value: the new value
        :return:
        """
        if 0 <= column < len(self.column_data):
            self.column_data[column] = value
            return True
        return False

    def insert_children(self, position: int, items: list)->bool:
        """Inserts a list with children (TreeItem instances)
        at index position in the child item list of this tree item

        :param position: the index the children are inserted
        :param items: list with TreeItems
        :return: True if success
        """
        if 0 <= position < len(self.child_items):
            for i, item in enumerate(items):
                self.child_items.insert(position + i, item)
            return True
        return False

    def insert_columns(self, position: int, columns: list)->bool:
        """Inserts/overwrites a list with columns at index position in the columns list of this tree item

        :param position: the index in columns
        :param columns: the new columns
        :return:True if success
        """
        success = [False]
        if 0 <= position < len(self.column_data):
            success = [self.set_column_data(position + i, column) for i, column in enumerate(columns)]
            # success.extend([child.insert_columns(position, columns) for child in self.child_items])
        if all(success):
            return True
        else:
            return False

    def remove_child(self, child)->bool:
        """Removes child from child items

        :param child: the child to be removed
        :return: True if successfully removed
        """
        if child in self.child_items:
            self.child_items.remove(child)
            return True
        return False

    def remove_children(self, position: int, count: int)->bool:
        """Removes count children from index position and onwards

        :param position: the index to start removals
        :param count: the number of removals
        :return: True if successfully removed
        """
        if 0 <= position + count < len(self.child_items):
            for row in range(count):
                self.child_items.pop(position)
            return True
        return False

    def remove_columns(self, position: int, columns: int)->bool:
        """Removes count columns from index position and onwards on this item and all its children

        :param position: the index to start removals
        :param columns:  the number of removals
        :return: True if successfully removed
        """
        success = [False]
        if 0 <= position + columns < self.column_count():
            success = [True]
            for column in range(columns):
                self.column_data.pop(position)
                success.extend([child.remove_columns(position, columns) for child in self.child_items])
        if all(success):
            return True
        else:
            return False

    def clear(self):
        """Removes this item and all its descendants, rolling up the tree from the leaves
        :return: None
        """
        if self.child_items:
            for item in self.child_items:
                item.clear()
        else:
            if self.parent_item:
                if self in self.parent_item.child_items:
                    self.parent_item.child_items.remove(self)


class ItemData:
    """Code item state dependent data. A code item can have 2 Item data objects,
    one used as base_data and one used as compare_data """

    def __init__(self, root_item):
        """Initializer of the class
        :param root_item: the root for the dependees, this is also the CodeItem instance that owns this ItemData
            representing the code item the ItemData belongs to
        :type root_item: CodeItem
        """
        self.denodo_path = Path()
        self.depend_path = Path()
        self.code = ''
        self.dependencies = list()
        self.dependees = list()
        self.dependee_parent = None
        self.dependees_tree = root_item


class CodeItem(TreeItem):
    """CodeItem class represents the code for a single Denodo object,
    e.g. a wrapper or a view or a base view"""
    headers = []

    def __init__(self, parent: TreeItem, name: str, index: int=None):
        """Initializer of the class sets up its data

        :param parent: The parent of this CodeItem, either a chapter or denodo folder depending on the view
        :param name: name of the code item
        :param index: if given, this will make this CodeItem the child with index index in the parents child list
        """
        super(CodeItem, self).__init__(CodeItem, parent=parent, index=index)
        self.class_type = CodeItem
        if isinstance(parent, Chapter):
            self.chapter = self.parent_item
        self.node_type = TreeItem.LEAF
        self.name = name
        self.column_data = [self.name]
        self.tooltip = self.object_type() + ': ' + self.name if self.chapter else 'Code Item' + ': ' + self.name
        self.script_path = '/' + self.chapter.name + '/' + self.name

        # main code data and other state dependent data are stored in these two variables
        self.base_data = ItemData(self)
        self.compare_data = ItemData(self)

    def object_type(self)->str:
        """Returns a presentable string with the category (chapter) of this code item

        :return: string
        """
        object_type = self.chapter.name[:-1] if self.chapter.name != 'DATABASE' else 'DATABASE'
        return object_type.capitalize()

    def get_child_index_by_name(self, name: str)->int:
        """Returns the index of the child with given name or -1 if not found

        :param name: the name sought
        :return: the index if found, -1 otherwise
        """
        return super().get_child_index_by_name(self.child_items, self.name)

    def clear(self):
        """Clears all data in this item, and removes it and all its descendants

        :return:
        """
        self.base_data = None
        self.compare_data = None
        self.column_data = None
        self.script_path = ''
        super().clear()

    def get_context_data(self, gui: int)->Union[ItemData, None]:
        """Returns this items ItemData object for the given app state (gui)

        :param gui: The context used, indicating the state of the app either GUI_SELECT or GUI_COMPARE
        :return: The item data or None
        """
        if gui & GUI_SELECT:
            data = self.base_data
        elif gui & GUI_COMPARE:
            data = self.compare_data
        else:
            data = None
        return data

    @staticmethod
    def get_diff(code: str, compare_code: str)->str:
        """Supplies the code edit widget with html for the comparison.

        The main intel of this function is supplied by the global DiffMatchPatch instance
        Here the engine is used on the two code pieces and a patch is calculated
        the patch is again inserted in the pretty_html function of the engine and modded a bit

        no changes: white
        modified code item: red and green text parts
        lost code (not present in compare code): red,
        newly added code: green

        :param code: the original code
        :type code: str
        :param compare_code: the new code
        :type compare_code: str
        :return: html representation of teh difference
        :rtype: str
        """
        def format_code(_code: str)->str:
            """
            Formats a code piece as html
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            _code = _code.replace('<br>', '<br />\n')
            _code = _code.replace('&para;', '')
            _code = _code.replace('    ', ' &nbsp; &nbsp; &nbsp; &nbsp; ')
            return _code

        def format_code2(_code: str)->str:
            """
            Formats a code piece as html
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            _code = _code.replace('\n', '<br />\n')
            _code = _code.replace('    ', ' &nbsp; &nbsp; &nbsp; &nbsp; ')
            return _code

        def set_green(_code: str)->str:
            """
            Formats a code piece as html to set it green
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            return '<span>' + new_diff_ins_indicator + _code + '</ins></span>'

        def set_red(_code: str)->str:
            """
            Formats a code piece as html to set it red
            :param _code: The code to be formatted
            :return: the html of the code
            :rtype: str
            """
            return '<span>' + new_diff_del_indicator + _code + '</del></span>'

        diff_ins_indicator = '<ins style="background:#e6ffe6;">'
        diff_del_indicator = '<del style="background:#ffe6e6;">'
        new_diff_ins_indicator = '<ins style="color:' + green + ';">'
        new_diff_del_indicator = '<del style="color:' + red + ';">'
        diff_html = ''
        if code:
            if compare_code:
                diff_patch = diff_engine.diff_main(code, compare_code)
                diff_html = format_code(diff_engine.diff_pretty_html(diff_patch))
                diff_html = diff_html.replace(diff_ins_indicator, new_diff_ins_indicator)
                diff_html = diff_html.replace(diff_del_indicator, new_diff_del_indicator)
            else:
                diff_html = format_code2(set_red(code))
        else:
            if compare_code:
                diff_html = format_code2(set_green(compare_code))

        return diff_html

    def get_file_path(self, folder: Path)->Path:
        """Get the file path for this code item. This function changes and slash,
        forward and backward into an underscore

        Warning: this can potentially be dangerous if two uniquely named objects
        turn out to have the same name after turning slashes to underscores.

        :param folder: the folder in which code item resides
        :return: Path of the code item
        """
        return folder / (self.name.replace('/', '_').replace('\\', '_') + '.vql')

    def remove_compare(self):
        """Function reverts the loading of compare code.

        :return: removal
        :rtype: Union[CodeItem, None]
        """
        if self.compare_data.code:
            self.compare_data = ItemData(self)
            if self.base_data.code:
                self.selected = True
                self.color = red if self.base_data.dependees else white
            else:
                if isinstance(self.parent_item, TreeItem):
                    return self
        else:
            if self.base_data.code:
                self.selected = True
                self.color = red if self.base_data.dependees else white
            else:
                if isinstance(self.parent_item, TreeItem):
                    return self
        return None

    @staticmethod
    def extract_denodo_folder_name_from_code(chapter_name: str, code: str)->Union[Path, None]:
        """Extracts the denodo folder name from code.

        :param chapter_name: Type of denodo object
        :param code: the code to create the object
        :return: The denodo path
        """
        if chapter_name == 'DATASOURCES' and code.find('DATASOURCE LDAP') > -1:
                folder_path = ''
        elif chapter_name in ['I18N MAPS', 'DATABASE', 'DATABASE CONFIGURATION', 'TYPES']:
            folder_path = ''
        elif chapter_name == 'FOLDERS':
            start = code.find('\'') + 2
            end = len(code) - 5
            folder_path = code[start:end]
        else:
            start = code.find('FOLDER = \'') + 11
            end = code.find('\'', start)
            folder_path = code[start:end]

        if folder_path:
            folder_path = Path(folder_path.lower())
        else:
            folder_path = None
        return folder_path

    @staticmethod
    def extract_object_name_from_code(chapter_name: str, code: str)->str:
        """Searches for the Denodo object name.

        Helper function for the 'parse' function
        The function constructs a unique object name from its code
        Each chapter has its own way of extracting the object name

        Warning: With newer versions of Denodo it should be checked if the structure they use is the same

        :param chapter_name: string with the name of the chapter it belongs to
        :param code: string with code relating to one object in Denodo
        :return: string with the object name
        """

        def get_last_word(line: str)->str:
            """
            Helper function for the extract_filename function
            :param line: string, one line of code (the first line)
            :return: string with the last word on the line
            """
            line_reversed = line.strip()[::-1]
            last_space = line_reversed.find(' ')
            last_word = line_reversed[0:last_space][::-1]
            return last_word.strip()

        object_name = ''

        # Object names are on the first line of the code item
        first_line = code[0:code.find("\n")]

        if chapter_name == 'I18N MAPS':
            object_name = get_last_word(first_line[0:-2])
        elif chapter_name == 'DATABASE':
            object_name = first_line.split()[4]
        elif chapter_name == 'FOLDERS':
            object_name = first_line[27:-3]
        elif chapter_name == 'LISTENERS JMS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'DATASOURCES':
            object_name = get_last_word(first_line)
        elif chapter_name == 'WRAPPERS':
            object_name = get_last_word(first_line)
        elif chapter_name == 'STORED PROCEDURES':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'TYPES':
            object_name = first_line.split()[4]
        elif chapter_name == 'MAPS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'BASE VIEWS':
            object_name = first_line.split()[4]
        elif chapter_name == 'VIEWS':
            split = first_line.split(' ')
            if split[3] == 'INTERFACE':
                object_name = split[5]
            else:
                object_name = split[4]
        elif chapter_name == 'ASSOCIATIONS':
            object_name = first_line.split()[4]
        elif chapter_name == 'WEBSERVICES':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WIDGETS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WEBCONTAINER WEB SERVICE DEPLOYMENTS':
            pass  # Todo: we don't use these kind of objects in Denodo
        elif chapter_name == 'WEBCONTAINER WIDGET DEPLOYMENTS':
            pass  # Todo: we don't use these kind of objects in Denodo
        return object_name


class Chapter(TreeItem):
    """Chapter class represents a group of Denodo objects of the same kind.
    For example: a BASEVIEW or a ASSOCIATION etc.
    The Chapter class also represents a folder in the repository.
    The Chapter class is the owner/parent of the CodeItems.
    """

    def __init__(self, name: str, parent: TreeItem=None):
        """Initializer of the class objects

        :param parent: reference to the parent or owner, this should be a VqlModel class (QTreeWidget)
        :param name: string name of the chapter
        """
        super(Chapter, self).__init__(Chapter, parent=parent)
        self.class_type = Chapter
        self.name = name
        self.column_data = [self.name]
        self.tooltip = self.name
        self.header = self.make_header(name)
        self.code_items = self.child_items
        self.gui = GUI_SELECT

    def get_child_index_by_name(self, name: str):
        """Returns the index of the child with given name or -1 if not found

        :param name: the name sought
        :return: the index if found, -1 otherwise
        """
        return super().get_child_index_by_name(self.child_items, name)

    def clear(self):
        """Removes this chapter and all its children

        :return: None
        """
        self.code_items = None
        self.column_data = None
        super().clear()

    @staticmethod
    def make_header(chapter_name: str)->str:
        """Constructs a string that can be used to identify chapters in a Denodo exported database file.

        :param chapter_name: string with Chapter name
        :return: The chapter Header
        """
        chapter_header = '# #######################################\n# ' \
                         + chapter_name + '\n# #######################################\n'
        return chapter_header

    def set_gui(self, gui: int):
        """Sets the Gui type (GUI_SELECT GUI_COMPARE) on the chapter and its children.

        :param gui: the new GUI type
        :return:None
        """
        self.gui = gui
        for code_item in self.code_items:
            code_item.set_gui(gui)

    def set_color_based_on_children(self):
        """Calculates the color of this chapter in the tree view
        based on the color of its children in GUI_COMPARE state.

        The chapter turns red if all children are lost, green if all children are new, yellow if there is a mix
        white if all items have the same original code and compare code

        :return: None
        """
        unique_colors = list(set([code_item.color for code_item in self.code_items]))
        length = len(unique_colors)
        if length == 0:
                self.color = red
                self.set_selected(False)
        elif length == 1:
            self.color = unique_colors[0]
        else:
            self.color = yellow

    # export functions
    # to file
    def get_code_as_file(self, mode: int, selected_only: bool)->str:
        """Returns the combined Denodo code for a whole chapter given he selection for saving purposes.

        This function adds a chapter header, and only selected code items if selected_only is True
        :param mode: either GUI_SELECT or GUI_COMPARE ; what code to return
        :param selected_only: Indicator is True if only selected items are requested
        :return: string with code content
        """
        code = []
        if selected_only:
            if self.selected or any([code_item.selected for code_item in self.code_items]):
                if mode & GUI_SELECT:
                    code = [code_item.base_data.code for code_item in self.code_items if code_item.selected]
                elif mode & GUI_COMPARE:
                    code = [code_item.compare_data.code for code_item in self.code_items if code_item.selected]
        else:
            if mode & GUI_SELECT:
                code = [code_item.base_data.code for code_item in self.code_items]
            elif mode & GUI_COMPARE:
                code = [code_item.compare_data.code for code_item in self.code_items]
        return self.header + '\n'.join(code)

    # to repository
    def get_part_log(self, base_path: Path)->Tuple[Path, str]:
        """Returns data to write the part.log files. Returns a tuple with two values:
        the file path for the part.log file and its content as a string.

        The content is a list of file paths pointing to the code items in this chapter.
        The part.log files are used in a repository to ensure the same order of execution.
        Only the selected code items are included.
        :param base_path: The base folder for the repo
        :return: Tuple of two values, a file path and the content of the part.log file of this chapter
        """
        folder = base_path / self.name
        part_log_filepath = folder / LOG_FILE_NAME
        part_log = [str(code_item.get_file_path(folder)) for code_item in self.code_items if code_item.selected]
        part_log_content = '\n'.join(part_log)
        return part_log_filepath, part_log_content

    @staticmethod
    def get_chapter_by_name(chapters: Iterable, chapter_name: str):
        """Function that returns a Chapter Object from the 'chapters' list by its name.

        :param chapters: List with chapters
        :param chapter_name: the name of a chapter
        :return: The Chapter with the requested name or None if not found
        :rtype: Union[Chapter, None]
        """
        for chapter in chapters:
            if chapter.name == chapter_name:
                return chapter
        return None


class DenodoFolder(TreeItem):
    """Class representing a Denodo folder"""

    def __init__(self, parent: TreeItem, name: str):
        """
        Class Initializer
        :param parent: the parent (DenodoFolder) if this folder
        :param name: the name of this folder
        """
        super(DenodoFolder, self).__init__(DenodoFolder, parent=parent)
        self.class_type = DenodoFolder
        self.name = name
        self.column_data = [self.name]
        self.tooltip = self.name
        self.sub_folders = self.child_items
        self.gui = GUI_SELECT

    def clear(self):
        """Removes this DenodoFolder and all its descendant denodoFolder and code items

        :return: None
        """
        self.name = None
        self.sub_folders = None
        self.column_data = None
        super().clear()


class RootItem(TreeItem):
    """Class representing a root of the tree.
    This class also owns most business logic for parsing the files.
    Generally this is the class the QMainWindow and QAbstractModel class talk to.
    It holds all data and serves loading and saving.
    """

    def __init__(self, header: str):
        """
        Class Initializer
        :param header: The header of the column 0 in the treeview1
        """
        super(RootItem, self).__init__(RootItem)
        self.class_type = RootItem
        self.chapters = self.child_items
        self.storage_list = list()
        self.add_chapters(CHAPTER_NAMES)
        self.header = header
        self.column_data = [header]
        self.name = 'root'
        self.view = SCRIPT_VIEW
        self.icon = QVariant()

    def get_child_index_by_name(self, name: str):
        """Returns the index of the child with given name or -1 if not found

        :param name: the name sought
        :return: the index if found, -1 otherwise
        """
        return super().get_child_index_by_name(self.child_items, self.name)

    def clear(self):
        """Removes this RootItem and all its descendants

        :return: None
        """
        self.chapters = None
        self.column_data = None
        super().clear()

    def change_view(self, mode: int)->bool:
        """Method that swaps the tree items from VQL View to Denodo file structure view and back.
        The actual switch is done in switch_view function.
        This function handles the surrounding aspects.
        :param mode: the mode flag with bits for the new view either VQL_VIEW or DENODO_VIEW
        :return: Success or not
        """
        gui = mode & (GUI_NONE | GUI_SELECT | GUI_COMPARE)
        if self.view & mode:
            return True

        if mode & SCRIPT_VIEW:
            if self.storage_list:
                self.switch_view()
                self.view = SCRIPT_VIEW
                return True
            else:
                pass
        elif mode & DENODO_VIEW:
            if self.storage_list:
                self.switch_view()
                self.view = DENODO_VIEW
                return True
            else:
                # build denodo view
                if self.build_denodo_view(gui):
                    if self.storage_list:
                        self.switch_view()
                        self.view = DENODO_VIEW
                        return True
        return False

    def switch_view(self):
        """Method to switch view between VQL or Denodo file structure.
        Store the children of the root item in the storage_list and replace them with the stored ones.

        :return: None
        """
        self.storage_list, self.child_items = self.child_items, self.storage_list

    def add_chapters(self, chapter_names: List[str]):
        """Method that adds a chapter to the chapter list for every name given.

        :param chapter_names: list of chapter_names of type string
        :return: None
        """
        for chapter_name in chapter_names:
            Chapter(chapter_name, self)

    def get_code_items(self, chapter: Chapter=None):
        """Generator that yields all code_items in all chapters, or only from the given chapter

        :return:
        """
        if chapter:
            for code_item in chapter.code_items:
                yield code_item
        else:
            for chapter_item in self.chapters:
                for code_item in chapter_item.code_items:
                    yield code_item

    def remove_compare(self):
        """Reverts the GUI_COMPARE state to the GUI_SELECT state

        :return: None
        """
        for chapter in self.chapters:
            chapter.color = white
            chapter.selected = True
            chapter.tristate = False
        to_be_removed = list()
        for code_item in self.get_code_items():
            to_be_removed.append(code_item.remove_compare())
        for code_item in to_be_removed:
            if code_item:
                code_item.parent_item.remove_child(code_item)

    def parse(self, file_content: str, mode: int, bar: QStatusBar, icons: dict, logger: LogWrapper):
        """Parses the file content to build up a tree structure with chapters and code items
        in both GUI_SELECT and GUI_COMPARE states.

        :param file_content: the file contents as a string, if a repository is opened,
            the code is bundled in this file content as well before it is send here
        :param mode: mode flag carrying info about the current gui, type of file etc
        :param bar: the status bar of QMainWindow
        :param icons: the dict with icons for code items and chapters
        :param logger: the logger
        :return: None
        """
        logger.info('Start parsing data.')
        gui = GUI_NONE

        if mode & (BASE_FILE | BASE_REPO):
            gui = GUI_SELECT
        elif mode & (COMP_FILE | COMP_REPO):
            gui = GUI_COMPARE
            # set all items to red, indicating they are lost.. this will later change if not
            # self.remove_compare()

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
                code = code
                object_name = CodeItem.extract_object_name_from_code(chapter.name, code)  # extract object name
                bar.showMessage(f"Loading: {object_name}")
                logger.info(f"Loading: {object_name}")
                if not object_name:
                    continue
                if gui == GUI_SELECT:
                    # add the code item to the chapter
                    code_item = CodeItem(chapter, object_name)
                    data = code_item.base_data
                    data.code = code
                    data.denodo_path = CodeItem.extract_denodo_folder_name_from_code(chapter.name, code)
                    code_item.icon = icons[chapter.name]

                elif mode & (COMP_FILE | COMP_REPO):   # COMPARE case
                    # Check if item exists, and where
                    i = chapter.get_child_index_by_name(object_name)
                    if i > -1:
                        # an existing code item
                        code_item = chapter.code_items[i]
                        data = code_item.compare_data
                        data.code = code
                        data.denodo_path = CodeItem.extract_denodo_folder_name_from_code(chapter.name, code)
                        base_code = code_item.base_data.code
                        if code.strip() == base_code.strip():
                            code_item.color = white
                        else:
                            code_item.color = yellow
                        index = i
                    else:  # code object does not yet exist
                        code_item = CodeItem(chapter, object_name, index=index + 1)
                        data = code_item.compare_data
                        data.code = code
                        data.denodo_path = CodeItem.extract_denodo_folder_name_from_code(chapter.name, code)
                        code_item.color = green
                        code_item.icon = icons[chapter.name]
                        index += 1

        if mode & (COMP_FILE | COMP_REPO):
            for code_item in self.get_code_items():
                if code_item.base_data.code and not code_item.compare_data.code:
                    code_item.color = red
                    code_item.set_selected(False)
            for chapter in self.chapters:
                chapter.set_color_based_on_children()
        logger.info(f"Analyzing objects ...")

        self.get_dependencies(gui, bar)

        # formatting the tree items
        if gui & GUI_SELECT:
            for code_item in self.get_code_items():
                data = code_item.get_context_data(gui)
                if data.dependees:
                    code_item.color = red

        logger.info('Finished parsing data.')
        return True

    def get_dependencies(self, gui: int, bar: QStatusBar):
        """Method with nifty code to extract and fill direct dependencies of code items based on their code.

        :param gui: mode flag selector indicating what code is used
        :param bar: the status bar of QMainWindow
        :return: None
        """
        # place holder in search strings that is unlikely in the code
        place_holder = '%&*&__&*&%'

        # helper function
        def unique_list(_list: list)->list:
            """Function that turns a list into a list with unique items while keeping the sort order.

            :param _list: the list to make unique
            :return: the list made unique
            """
            new_list = list()
            for _item in _list:
                if _item not in new_list:
                    new_list.append(_item)
            return new_list

        # helper function
        def find_dependencies(_code_objects: List[Tuple[CodeItem, str, str]],
                              _underlying_code_objects: List[Tuple[CodeItem, str, str]], _search_template: str):
            """Function finds and adds the direct dependencies of code objects
            in the lower-cased code of underlying objects.
            Basically it looks for the code_item's object name in the code of the underlying objects
            via a particular search string per chapter type.
            :param _code_objects: a list of tuples (code object, object name, code)
            :param _underlying_code_objects: a list of tuples (code object, object name, code) of underlying objects
            :param _search_template: a template for the search string in which the object names can be put
            :return: None
            """
            for _code_item, _, code in _code_objects:
                bar.showMessage(f"Analyzing: {_code_item.name}")
                for other_code_item, other_name, other_code in _underlying_code_objects:
                    search_string = _search_template.replace(place_holder, other_name)
                    if not code.find(search_string) == -1:
                        _data = _code_item.get_context_data(gui)
                        _data.dependencies.append(other_code_item)
                        _data = other_code_item.get_context_data(gui)
                        _data.dependees.append(_code_item)

        # helper function
        def code_items_lower(_chapter: Chapter)->List[Tuple[CodeItem, str, str]]:
            """
            Returns a list of code items with their code and object names in lower case of a particular chapter
            :param _chapter: the chapter name
            :return: the requested list of tuples
            """
            items = None
            if gui & GUI_SELECT:
                items = [(_code_item, _code_item.name.lower(), _code_item.base_data.code.lower())
                         for _code_item in self.get_code_items(chapter=_chapter)]
            elif gui & GUI_COMPARE:
                items = [(_code_item, _code_item.name.lower(), _code_item.compare_data.code.lower())
                         for _code_item in self.get_code_items(chapter=_chapter)]
            return items

        # construct the searches in a list of tuples:
        # 1 the items analysed
        # 2 the underlying items
        # 3 the search string template

        searches = list()
        searches.append(('WRAPPERS', 'DATASOURCES', f"datasourcename={place_holder}"))
        searches.append(('BASE VIEWS', 'WRAPPERS', f"wrapper (jdbc {place_holder})"))
        searches.append(('BASE VIEWS', 'WRAPPERS', f"wrapper (df {place_holder})"))
        searches.append(('BASE VIEWS', 'WRAPPERS', f"wrapper (ldap {place_holder})"))

        for i in range(15):  # up to 15 possible parentheses are sought
            parentheses = '(' * i
            searches.append(('VIEWS', 'BASE VIEWS', f"from {parentheses}{place_holder}"))
            searches.append(('VIEWS', 'BASE VIEWS', f"join {parentheses}{place_holder}"))
        searches.append(('VIEWS', 'BASE VIEWS', f"set implementation {place_holder}"))
        searches.append(('VIEWS', 'BASE VIEWS', f"datamovementplan = {place_holder}"))

        for i in range(15):   # up to 15 possible parentheses are sought
            parentheses = '(' * i
            searches.append(('VIEWS', 'VIEWS', f"from {parentheses}{place_holder}"))
            searches.append(('VIEWS', 'VIEWS', f"join {parentheses}{place_holder}"))
        searches.append(('VIEWS', 'VIEWS', f"set implementation {place_holder}"))
        searches.append(('VIEWS', 'VIEWS', f"datamovementplan = {place_holder}"))

        # to count associations are dependees too switch the following line on
        # searches.append(('ASSOCIATIONS', 'VIEWS', f" {place_holder} "))

        # perform the searches and store dependencies
        for chapter_name, underlying_chapter_name, search_template in searches:
            chapter = Chapter.get_chapter_by_name(self.chapters, chapter_name)
            underlying_chapter = Chapter.get_chapter_by_name(self.chapters, underlying_chapter_name)
            code_objects = code_items_lower(chapter)
            underlying_code_objects = code_items_lower(underlying_chapter)
            find_dependencies(code_objects, underlying_code_objects, search_template)

        # clean up the lists
        for code_item in self.get_code_items():
            data = code_item.get_context_data(gui)
            # remove self references and double items in the dependencies and dependees lists
            if code_item in data.dependencies:
                data.dependencies.remove(code_item)
            data.dependencies = unique_list(data.dependencies)
            if code_item in data.dependees:
                data.dependees.remove(code_item)
            data.dependees = unique_list(data.dependees)

            # remove circular references
            to_be_removed = list()
            for dependee in data.dependees:
                if dependee in data.dependencies:
                    to_be_removed.append(dependee)
            for item in to_be_removed:
                data.dependees.remove(item)

    def build_denodo_view(self, gui: int)->bool:
        """Method that builds up the Denodo folder structure.

        This structure is stored in the storage list
        and shown when the view is switched.
        :param gui: flag to indicate compare or normal select operations
        :return: Success or not
        """

        def child_exists(item_name: str, parent: TreeItem) -> Union[TreeItem, None]:
            """Checks if a child already exists and if so, returns that child, None otherwise

            :param item_name: name of the child
            :param parent: The parent denodo folder
            :return: the child if found, None otherwise
            """
            if not parent:
                return None

            for _child in parent.child_items:
                if _child.name.lower() == item_name.lower():
                    return _child
            return None

        def get_folders()->dict:
            """Returns a dictionary with all denodo folder paths as key and a list of code_items in this path as value
            :return: the folders
            """
            _folders = dict()
            for chapter in self.chapters:
                for _code_item in chapter.code_items:
                    if chapter.name != 'FOLDERS':
                        _data = _code_item.get_context_data(gui)
                        denodo_path = _data.denodo_path
                        if gui & GUI_COMPARE and not denodo_path:  # account for lost items
                            denodo_path = _code_item.data.denodo_path
                        if denodo_path not in _folders.keys():
                            _folders[denodo_path] = list()
                            _folders[denodo_path].append(_code_item)
                        else:
                            _folders[denodo_path].append(_code_item)
            return _folders

        root = TreeItem(DenodoFolder)
        folder_item = None
        folders = get_folders()
        folder_parts = ((folder.parts, code_items) for folder, code_items in folders.items() if folder)

        for parts, code_items in folder_parts:
            old_parent = root
            for part in parts:
                if part != '/':
                    folder_item = child_exists(part, old_parent)
                    if not folder_item:
                        folder_item = DenodoFolder(old_parent, part)
                    old_parent = folder_item
            if folder_item:
                for code_item in code_items:
                    code_item.set_parent(folder_item)

        for child in root.child_items:
            child.parent_item = self

        self.storage_list = root.take_children()
        return True

    def get_part_logs(self, base_repository_folder: Path)->List[Tuple[Path, str]]:
        """Returns all part.log data for saving a repository given a base repository folder.
        Only selected chapters and code items are included.

        :param base_repository_folder: The folder to save the repo to
        :return: List with tuples of filepaths and part.log content
        """
        result = list([chapter.get_part_log(base_repository_folder) for chapter in self.chapters if chapter.selected])
        return result

    def get_code_as_file(self, mode: int, selected: bool)->str:
        """Function that puts the code content in a single .vql file of all items.
        If selected is True, only selected items are included.
        :param mode: GUI indicator saving either compare code or base code GUI_SELECT or GUI_COMPARE
        :param selected: Only selected items or not
        :return: string of code content
        """
        code = [chapter.get_code_as_file(mode, selected) for chapter in self.chapters]
        return PROP_QUOTE + '\n'.join(code)

    def get_selected_code_files(self, mode: int, base_repository_folder: Path)->List[Tuple[Path, str]]:
        """Function for looping over all selected code items in the model.
        This function is used to write the repository.
        
        :param mode: the mode to select which code; either GUI_SELECT or GUI_COMPARE
        :param base_repository_folder: the proposed folder for storage
        :return: a list with tuples: filepath and code content
        """
        item_path_code = list()
        for chapter in self.chapters:
            items = [code_item for code_item in chapter.code_items if code_item.selected]
            chapter_folder = base_repository_folder / chapter.name
            for code_item in items:
                item_path = code_item.get_file_path(chapter_folder)
                if mode & COMP_LOADED:
                    item_code = code_item.compare_data.code
                elif mode & BASE_LOADED:
                    item_code = code_item.base_data.code
                else:
                    item_code = ''
                item_path_code.append((item_path, item_code))
        return item_path_code


class Dependee(TreeItem):
        """Wrapper Class representing a dependee code item"""

        # noinspection PyMissingConstructor
        def __init__(self, parent: Union[TreeItem, None], code_item: CodeItem, gui):
            """
            Class Initializer
            :param parent: the parent dependee, this code object is dependent on
            :param code_item: the code item this dependee represents
            :param gui: the gui state, either GUI_SELECT or GUI_COMPARE
            """
            self.parent_item = parent
            self.class_type = Dependee
            self.name = code_item.name
            self.code_item = code_item
            self.column_data = [self.name]
            self.tooltip = code_item.tooltip
            self.child_items = list()
            self.gui = gui
            self.color = white
            self.dependee_code_items = code_item.get_context_data(gui).dependees
            for dependee in self.dependee_code_items:
                child = Dependee(self, dependee, self.gui)
                self.child_items.append(child)
            self.node_type = TreeItem.BRANCH
            self.selected = True
            self.tristate = False
            self.icon = code_item.icon

        def clear(self):
            """Removes this item and all its descendants

            :return: None
            """
            self.dependee_code_items = None
            self.column_data = None
            super().clear()


class DependencyModel(QAbstractItemModel):
    """Model for treeview3 to show dependees of a selected code item. This class implements QAbstractItemModel"""

    def __init__(self, parent: QTreeView, header: str):
        """Class initializer

        :param parent: the treeview this model serves
        """
        super(DependencyModel, self).__init__(parent)
        self.base_header = header
        self.header = header
        self.gui = GUI_SELECT

        # Dependee root object releated to the root_code_item
        self.root_item = None

        # CodeItem object that is wrapped
        self.root_code_item = None

    def recurse_dependees(self, recurse: int, parent: Dependee):
        """Recurrent function that builds up the dependee tree for a given parent item

        :param recurse: integer used internally to restrict stack overflow on recursion limit
        :param parent: the parent item
        :return: None
        """
        recurse += 1
        if recurse == 700:
            return
        for dependee_code_item in parent.dependee_code_items:
            dependee = Dependee(parent, dependee_code_item, self.gui)
            self.recurse_dependees(recurse, dependee)

    def set_root_code_item(self, code_item: Union[CodeItem, None]):
        """Sets the root item and build the related tree of dependees and resets the model

        :param code_item: the base code item
        :return: None
        """
        self.root_code_item = code_item
        self.beginResetModel()
        if code_item:
            self.header = self.base_header + ": " + code_item.name
            self.root_item = Dependee(None, code_item, self.gui)
            self.recurse_dependees(0, self.root_item)
        else:
            self.header = self.base_header
            self.root_item = None
        self.endResetModel()

    def get_root_code_item(self)->CodeItem:
        """Getter for the CodeItem this dependee represents

        :return: the root code item
        """
        return self.root_code_item

    def headerData(self, section: int, orientation: int, role: int=None)-> QVariant:
        """Called by QTreeView to supply the header data

        :param section: the index or column if orientation is Qt.Horizontal
        :param orientation: orientation of the header
        :param role: the type of data requested
        :return: the header data for this role or Nothing (QVariant())
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return QVariant(self.header)
        return NOTHING

    def flags(self, index: QModelIndex)->int:
        """Returns behavioral flags to the Qtreeview for a given QModelIndex

        :param index: the index whose flags are requested
        :return:
        """
        if index.isValid():
            flags = super(DependencyModel, self).flags(index)
            flags |= Qt.ItemIsEnabled | Qt.ItemIsSelectable
            flags ^= Qt.ItemIsUserCheckable
            return flags
        else:
            return Qt.NoItemFlags

    def data(self, index: QModelIndex, role: int=None)->QVariant:
        """Returns data for a specific role to the QTreeview

        :param index: the index whose flags are requested
        :param role: the type of data requested
        :return: the data as a QVariant
        """
        if role == CHECK:
            return NOTHING

        if self.root_item:
            if index.column() == 0:
                if role in ROLES:
                    item = self.item_for_index(index)
                    data = item.get_role_data(role, index.column())
                    return QVariant(data)
                elif role == Qt.FontRole:
                    return QVariant(FONT)
        return NOTHING

    def index(self, row: int, column: int, parent: Union[QModelIndex, None]=None, *args, **kwargs)->QModelIndex:
        """Returns a QModelIndex for an requested item in the QTreeview or its proxy model
        based on its parent QModelIndex, its child_number(indicated by row) and column

        :param row: the index of the child in the parents child list
        :param column: the column the index is generated for
        :param parent: the QmodelIndex representing the parent of the requested index
        :return: a QModelIndex pointing to the right TreeItem
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not self.root_item:
            return QModelIndex()

        parent_item = self.item_for_index(parent)
        if parent_item.has_children() and 0 <= row < parent_item.child_count():
            child = parent_item.child(row)
            if 0 <= column < child.column_count():
                index = self.createIndex(row, column, child)
                return index

        # print(f"call def index:    row: {row},  col:{column};  parent ...")
        return QModelIndex()

    def parent(self, index: Union[QModelIndex, None]=None)->QModelIndex:
        """Returns a QModelIndex of the parent of given index

        :param index: a QmodelIndex representing a child
        :return: the QModelIndex of its parent
        """
        if not self.root_item:
            return QModelIndex()

        if not index.isValid():
            return QModelIndex()

        item = self.item_for_index(index)
        parent_item = item.parent_item

        if parent_item is self.root_item:
            return QModelIndex()
        else:
            return self.createIndex(parent_item.child_number(), 0, parent_item)

    def rowCount(self, parent: QModelIndex=None, *args, **kwargs)->int:
        """Returns the number of children of a parent represented by its QModelIndex

        :param parent: the QmodelIndex representing the parent
        :param args: not used
        :param kwargs: not used
        :return: number of children (rows)
        """

        if not self.root_item:
            return 0
        if not parent.isValid():
            return self.root_item.child_count()
        if parent.column() > 0:
            return 0
        parent_item = parent.internalPointer()
        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex=None, *args, **kwargs)->int:
        """Returns the number of columns of a parent represented by its QModelIndex

        :param parent: the QModelIndex representing the parent
        :param args: not used
        :param kwargs: not used
        :return: number of columns
        """
        if not self.root_item:
            return 1
        if not parent.isValid():
            return self.root_item.column_count()

        parent_item = parent.internalPointer()
        if parent_item.has_children():
            child = parent_item.child(0)
            return child.column_count()
        else:
            return 0

    def item_for_index(self, index: QModelIndex)->Union[TreeItem, RootItem]:
        """Returns the TreeItem represented by index using its internalPointer() function

        :param index: the QModelIndex pointing to the item
        :return: the item itself
        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.root_item

    def hasChildren(self, parent: QModelIndex=None, *args, **kwargs)->bool:
        """Returns a boolean indicating whether the TreeItem represented by the given QModelIndex of the parent
        has children.

        :param parent: the QModelIndex representing the parent
        :param args: not used
        :param kwargs: not used
        :return: True if parent item has children
        """
        if not self.root_item:
            return False
        if not parent.isValid():
            return self.root_item.has_children()
        if parent.column() > 0:
            return False
        parent_item = self.item_for_index(parent)
        if parent_item:
            return parent_item.has_children()
        return False


class ColorProxyModel(QSortFilterProxyModel):
    """Filter proxy model for treeview1 to allow color based filtering.
    this class overrides/implements several functions of QSortFilterProxyModel
    Basically it is a data provider for the QTreeview sourced by the TreeModel Class
    """

    def __init__(self, parent: QTreeView, header: str):
        """Class Initializer

        :param parent: the treeview this model serves
        """
        super(ColorProxyModel, self).__init__(parent)
        # self.setFilterRole(COLOR)
        self.setDynamicSortFilter(False)
        self.header = header
        self.color_filter = None
        self.type_filter = None

    def set_color_filter(self, color: str, type_filter):
        """Setter for the color and class types to be filtered.
        This function also resets the model so active filtering is initiated.

        :param color: string with color data e.g. '#ffffff'
        :param type_filter: a type e.g. Chapter or CodeItem
        :return: None
        """

        if color != self.color_filter:
            self.beginResetModel()
            self.type_filter = type_filter
            self.color_filter = color
            self.endResetModel()

    def headerData(self, section: int, orientation, role: int=None)-> QVariant:
        """Called by QTreeView to supply the header data

        :param section: the index or column if orientation is Qt.Horizontal
        :param orientation: orientation of the header
        :param role: the type of data requested
        :return: the header data for this role or Nothing (QVariant())
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return QVariant(self.header)
        return NOTHING

    def flags(self, index: QModelIndex):
        """Returns behavioral flags to the QTreeview for a given QModelIndex

        :param index: the index whose flags are requested
        :return:
        """
        if index.isValid():
            flags = super(ColorProxyModel, self).flags(index)
            flags |= Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable
            return flags
        else:
            return Qt.NoItemFlags

    def filterAcceptsRow(self, source_row: int, parent: QModelIndex)->bool:
        """Returns a boolean indicating the requested row is included or not.
        Thus making a filter between the TreeModel and treeview1
        This filters uses the color of items as criterion

        :param source_row: the row (child_number) in the TreeModel
        :param parent: the QModelIndex of the parent
        :return: boolean, True if this child is included
        """
        source_col = 0
        source_item = self.sourceModel().index(source_row, source_col, parent).internalPointer()

        if source_item:
            if self.color_filter and self.type_filter:
                if source_item.class_type == self.type_filter:
                    if source_item.color == self.color_filter:
                        return True
                    else:
                        return False
                if source_item.has_children():
                    return True
                else:
                    return False
        return True

    def filterAcceptsColumn(self, source_column, parent: QModelIndex)->bool:
        """Returns a boolean indicating the requested column is included or not.
        Thus making a filter between the TreeModel and treeview1.
        Only column 0 is used.

        :param source_column: the column in the column_data of the parent
        :param parent: the QModelIndex of the parent
        :return: boolean, True if this column is included
        """
        return source_column == 0

    def data(self, index: QModelIndex, role: int=None)->QVariant:
        """Returns data for a specific role to the QTreeview

        :param index: the index whose flags are requested
        :param role: the type of data requested
        :return: the data as a QVariant
        """
        if index.column() == 0:
            return super(ColorProxyModel, self).data(index, role)


class SelectionProxyModel(QSortFilterProxyModel):
    """Filter proxy model for treeview2 to allow selection based filtering.
    this class overrides/implements several functions of QSortFilterProxyModel
    Basically it is a data provider for the QTreeview sourced by the TreeModel Class
    """

    def __init__(self, parent: QTreeView, header: str):
        """Class Initializer

        :param parent: the treeview this model serves
        """
        super(SelectionProxyModel, self).__init__(parent)
        self.setFilterRole(CHECK)
        self.setDynamicSortFilter(True)
        self.header = header

    def headerData(self, section: int, orientation, role: int=None)-> QVariant:
        """Called by QTreeView to supply the header data

        :param section: the index or column if orientation is Qt.Horizontal
        :param orientation: orientation of the header
        :param role: the type of data requested
        :return: the header data for this role or Nothing (QVariant())
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return QVariant(self.header)
        return NOTHING

    def flags(self, index: QModelIndex):
        """Returns behavioral flags to the Qtreeview for a given QModelIndex

        :param index: the index whose flags are requested
        :return:
        """
        if index.isValid():
            flags = super(SelectionProxyModel, self).flags(index)
            flags |= Qt.ItemIsEnabled | Qt.ItemIsSelectable
            flags ^= Qt.ItemIsUserCheckable
            return flags
        else:
            return Qt.NoItemFlags

    def filterAcceptsRow(self, source_row: int, parent: QModelIndex)->bool:
        """Returns a boolean indicating the requested row is included or not.
        Thus making a filter between the TreeModel and treeview2
        This filters uses the selected state of items as criterion

        :param source_row: the row (child_number) in the TreeModel
        :param parent: the QModelIndex of the parent
        :return: boolean, True if this child is included
        """
        source_col = 0
        source_item = self.sourceModel().index(source_row, source_col, parent).internalPointer()
        if source_item:
            if isinstance(source_item, (Chapter, DenodoFolder)):
                if not source_item.selected:
                    selected = False
                elif source_item.has_children():
                    selected = True
                else:
                    selected = False
            elif isinstance(source_item, CodeItem):
                selected = source_item.selected
            else:
                return False
            return selected
        return False

    def filterAcceptsColumn(self, source_column, parent: QModelIndex):
        """Returns a boolean indicating the requested column is included or not.
        Thus making a filter between the TreeModel and treeview2.
        Only column 0 is used.

        :param source_column: the column in the column_data of the parent
        :param parent: the QModelIndex of the parent
        :return: boolean, True if this column is included
        """
        return source_column == 0

    def data(self, index: QModelIndex, role: int=None)->QVariant:
        """Returns data for a specific role to the QTreeview

        :param index: the index whose flags are requested
        :param role: the type of data requested
        :return: the data as a QVariant
        """
        if role == CHECK:
            return NOTHING
        else:
            if index.column() == 0:
                return super(SelectionProxyModel, self).data(index, role)


class TreeModel(QAbstractItemModel):
    """Base model for all treeviews. Implements QAbstractItemModel."""

    selection_changed = pyqtSignal(TreeItem)  # signal for the VQLManagerWindow

    def __init__(self, parent: QTreeView, mode: int, root_node: RootItem):
        """Class Initializer

        :param parent: the treeview this model serves
        :param mode: the mode of operandi
        :param root_node: the RootItem that contains all item data
        """

        super(TreeModel, self).__init__(parent)
        self.parent = parent
        self.mode = mode
        self.root_item = root_node
        self.color_filter = None
        self.type_filter = None

    def flags(self, index: QModelIndex)->int:
        """Returns behavioral flags to the Qtreeview for a given QModelIndex

        :param index: the index whose flags are requested
        :return:
        """
        if index.isValid():
            flags = super(TreeModel, self).flags(index)
            flags |= Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable
            return flags
        else:
            return Qt.NoItemFlags

    # noinspection PyUnresolvedReferences
    def setData(self, index: QModelIndex, new_data: Union[QVariant], role=None)->bool:
        """
        Puts changed data back into the base data
        :param index:
        :param new_data:
        :param role:
        :return:
        """
        if role == CHECK and index.column() == 0 and index.isValid():
            item = self.item_for_index(index)
            if item:
                self.layoutAboutToBeChanged.emit()
                if item.set_role_data(role, index.column(), new_data):
                    self.selection_changed.emit(item)
                    self.layoutChanged.emit()
                    return True
        self.layoutChanged.emit()
        return False

    def data(self, index: QModelIndex, role: int=None)->QVariant:
        """Returns data for a specific role to the QTreeview or proxy

        :param index: the index whose flags are requested
        :param role: the type of data requested
        :return: the data as a QVariant
        """
        if role in ROLES:
            item = self.item_for_index(index)
            data = item.get_role_data(role, index.column())
        elif role == Qt.FontRole:
            return QVariant(FONT)
        else:
            return NOTHING
        return QVariant(data)

    def headerData(self, section: int, orientation, role: int=None)->QVariant:
        """Called by QTreeView or proxy models to supply the header data

        :param section: the index or column if orientation is Qt.Horizontal
        :param orientation: orientation of the header
        :param role: the type of data requested
        :return: the header data for this role or Nothing (QVariant())
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if 0 <= section < len(self.root_item.column_data):
                    return QVariant(self.root_item.column_data[section])
        return NOTHING

    def hasChildren(self, parent: QModelIndex=None, *args, **kwargs)->bool:
        """Returns a boolean indicating whether the TreeItem represented by the given QModelIndex of the parent
        has children.

        :param parent: the QModelIndex representing the parent
        :param args: not used
        :param kwargs: not used
        :return: True if parent item has children
        """
        if not parent.isValid():
            return self.root_item.has_children()
        if parent.column() > 0:
            return False
        parent_item = self.item_for_index(parent)
        if parent_item:
            return parent_item.has_children()
        return False

    def index(self, row: int, column: int, parent: Union[QModelIndex, None]=None, *args, **kwargs)->QModelIndex:
        """Returns a QModelIndex for an requested item in the QTreeview or its proxy model
        based on its parent QModelIndex, its child_number(indicated by row) and column

        :param row: the index of the child in the parents child list
        :param column: the column the index is generated for
        :param parent: the QmodelIndex representing the parent of the requested index
        :return: a QModelIndex pointing to the right TreeItem
        """
        if not parent:
            parent = QModelIndex()

        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = self.item_for_index(parent)
        if parent_item.has_children() and 0 <= row < parent_item.child_count():
            child = parent_item.child(row)
            if 0 <= column < child.column_count():
                index = self.createIndex(row, column, child)
                return index
        return QModelIndex()

    def parent(self, index: Union[QModelIndex, None]=None)->QModelIndex:
        """Returns a QModelIndex of the parent of given index

        :param index: a QmodelIndex representing a child
        :return: the QModelIndex of its parent
        """
        if not index.isValid():
            return QModelIndex()

        item = self.item_for_index(index)
        parent_item = item.parent_item

        if parent_item is self.root_item:
            return QModelIndex()
        else:
            return self.createIndex(parent_item.child_number(), 0, parent_item)

    def columnCount(self, parent: QModelIndex=None, *args, **kwargs)->int:
        """Returns the number of columns of a parent represented by its QModelIndex

        :param parent: the QmodelIndex representing the parent
        :param args: not used
        :param kwargs: not used
        :return: number of columns
        """
        if not parent.isValid():
            return self.root_item.column_count()

        parent_item = parent.internalPointer()
        if parent_item.has_children():
            child = parent_item.child(0)
            return child.column_count()
        else:
            return 0

    def rowCount(self, parent: QModelIndex=None, *args, **kwargs)->int:
        """Returns the number of children of a parent represented by its QModelIndex

        :param parent: the QmodelIndex representing the parent
        :param args: not used
        :param kwargs: not used
        :return: number of children (rows)
        """
        if not parent.isValid():
            return self.root_item.child_count()
        if parent.column() > 0:
            return 0
        parent_item = parent.internalPointer()
        return parent_item.child_count()

    def item_for_index(self, index: QModelIndex)->Union[TreeItem, RootItem]:
        """Returns the TreeItem represented by index using its internalPointer() function

        :param index: the QModelIndex pointing to the item
        :return: the item itself
        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.root_item

    def reset(self):
        """Resets the model, roll up from the leaves and remove all reverences

        :return: None
        """
        self.beginResetModel()
        self.resetInternalData()
        header = str(self.root_item.header)
        self.root_item.clear()
        self.root_item.__init__(header)
        self.endResetModel()

    def remove_compare(self):
        """Reverts the model to a state before the GUI_COMPARE state
        :return: None
        """
        self.beginResetModel()
        self.root_item.remove_compare()
        self.endResetModel()
        if self.mode & GUI_COMPARE:
            self.mode -= GUI_COMPARE
        self.mode |= GUI_SELECT

    def change_view(self, view: int)->bool:
        """Changes the view to the new view.
        possible views are: DENODO_VIEW or SCRIPT_VIEW

        :param view: integer with the requested view
        :return: True if success
        """

        self.beginResetModel()
        success = self.root_item.change_view(view)
        self.endResetModel()
        return success


class VQLManagerWindow(QMainWindow):
    """Main Gui Class"""

    mode_changed = pyqtSignal(int)   # signal for the state_machine to handle transitions

    def __init__(self, parent=None):
        """
        Constructor of the Window Class
        :param parent: The owner/parent of the instance
        """
        # initialize main window calling its parent
        super(VQLManagerWindow, self).__init__(parent, Qt.Window)
        self.logger = LogWrapper('vqlmanager', _format=LOGGING_FORMAT, level=LOGGING_LEVEL, filename=log_filename)
        self.logger.debug("Start Window creation")
        self.setAttribute(Qt.WA_DeleteOnClose)  # close children on exit

        # _root is the folder from which this file runs
        self._root = Path(QFileInfo(__file__).absolutePath())
        images = Path(QFileInfo(__file__).absolutePath()) / 'images'

        self.icons = {
            'I18N MAPS': self.get_pixmap('lang_map.png'),
            'DATABASE': self.get_pixmap('database.png'),
            'FOLDERS': self.get_pixmap('folder.png'),
            'LISTENERS JMS': self.get_pixmap('listener.png'),
            'DATASOURCES': self.get_pixmap('data_source.png'),
            'WRAPPERS': self.get_pixmap('wrapper.png'),
            'STORED PROCEDURES': self.get_pixmap('stored_procedure.png'),
            'TYPES': self.get_pixmap('type_def.png'),
            'MAPS': self.get_pixmap('key_value_map.png'),
            'BASE VIEWS': self.get_pixmap('base_view.png'),
            'VIEWS': self.get_pixmap('view.png'),
            'ASSOCIATIONS': self.get_pixmap('association.png'),
            'WEBSERVICES': self.get_pixmap('web_service.png'),
            'WIDGETS': self.get_pixmap('web_container.png'),
            'WEBCONTAINER WEB SERVICE DEPLOYMENTS': self.get_pixmap('web_container.png'),
            'WEBCONTAINER WIDGET DEPLOYMENTS': self.get_pixmap('web_container.png')
        }

        self.resize(1200, 800)
        self.setMinimumSize(QSize(860, 440))
        self.setIconSize(QSize(32, 32))
        self.setWindowIcon(QIcon(str(images / 'splitter.png')))
        self.setWindowTitle(APPLICATION_NAME)

        self.select_button_labels = {'All': white, 'Lost': red, 'New': green, 'Same': white, 'Changed': yellow}
        self.diff_button_labels = {'Changes': yellow, 'Original': white, 'New': green}

        # instantiate widgets
        self.main_widget = QWidget(self, flags=Qt.Widget)
        self.main_layout = QGridLayout()

        self.main_splitter = QSplitter()
        self.header_splitter = QSplitter()
        self.content_splitter = QSplitter()
        self.right_side_splitter = QSplitter()
        self.tree_views_splitter = QSplitter()
        self.log_splitter = QSplitter()

        self.right_content_box = QVBoxLayout()
        self.left_header_box = QVBoxLayout()
        self.right_header_box = QVBoxLayout()
        self.find_header_box = QHBoxLayout()
        self.code_edit_box = QVBoxLayout()
        self.treeview2_box = QVBoxLayout()
        self.treeview3_box = QVBoxLayout()
        self.log_box = QVBoxLayout()
        self.info_box = QVBoxLayout()

        self.right_content_widget = QWidget(self, flags=Qt.Widget)
        self.left_header_widget = QWidget(self, flags=Qt.Widget)
        self.right_header_widget = QWidget(self, flags=Qt.Widget)
        self.code_edit_widget = QWidget(self, flags=Qt.Widget)
        self.find_header_widget = QWidget(self, flags=Qt.Widget)
        self.treeview2_widget = QWidget(self, flags=Qt.Widget)
        self.treeview3_widget = QWidget(self, flags=Qt.Widget)
        self.log_widget = QWidget(self, flags=Qt.Widget)
        self.info_widget = QWidget(self, flags=Qt.Widget)

        self.item_info = QPlainTextEdit()
        self.base_repository_label = QLabel()
        self.compare_repository_label = QLabel()
        self.search_label = QLabel()
        self.find_line_edit = QLineEdit()
        self.find_button = QPushButton()
        self.log_edit = QPlainTextEdit()

        self.select_buttons, self.select_buttons_group = self.get_buttons_widget(self.select_button_labels)
        self.diff_buttons, self.diff_buttons_group = self.get_buttons_widget(self.diff_button_labels)

        self.icon_size = QSize(16, 16)
        self.treeview1 = self.create_tree_view()
        self.treeview2 = self.create_tree_view()
        self.treeview3 = self.create_tree_view()

        self.root_item = RootItem('Selection Pane')
        self.tree_model = TreeModel(self.treeview1, LEFT | GUI_SELECT | SCRIPT_VIEW, self.root_item)
        self.color_proxy_model = ColorProxyModel(self.treeview1, 'Selection Pane')
        self.color_proxy_model.setSourceModel(self.tree_model)
        self.treeview1.setModel(self.color_proxy_model)

        self.proxy_model = SelectionProxyModel(self.treeview2, 'View Selection')
        self.proxy_model.setSourceModel(self.tree_model)
        self.treeview2.setModel(self.proxy_model)

        self.dependency_model = DependencyModel(self.treeview3, 'Dependencies Pane')
        self.treeview3.setModel(self.dependency_model)

        # create source code view
        self.code_text_edit = QTextEdit()

        # create statusbar
        self.status_bar = self.statusBar()

        #  Create Actions and Menubar ###############################################################################
        self.open_file_action = QAction(QIcon(str(images / 'open_file.png')), '&Open File', self)
        self.open_folder_action = QAction(QIcon(str(images / 'open_repo.png')), 'Open &Repository', self)
        self.export_file_action = QAction(QIcon(str(images / 'save_file.png')), 'Save As File', self)
        self.export_folder_action = QAction(QIcon(str(images / 'save_repo.png')), '&Save As Repository', self)
        self.exit_action = QAction(QIcon(str(images / 'exit.png')), '&Exit', self)

        self.export_file_action.setEnabled(False)
        self.export_folder_action.setEnabled(False)

        # Create recent file menu
        self.recent_file_actions = list()
        self.recent_repository_actions = list()
        self.compare_recent_file_actions = list()
        self.compare_recent_repository_actions = list()

        for i in range(MAX_RECENT_FILES):
            action = QAction(self)
            action.setVisible(False)
            # noinspection PyUnresolvedReferences
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_SELECT | BASE_FILE))
            self.recent_file_actions.append(action)
            action = QAction(self)
            action.setVisible(False)
            # noinspection PyUnresolvedReferences
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_SELECT | BASE_REPO))
            self.recent_repository_actions.append(action)
            action = QAction(self)
            action.setVisible(False)
            # noinspection PyUnresolvedReferences
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_COMPARE | COMP_FILE))
            self.compare_recent_file_actions.append(action)
            action = QAction(self)
            action.setVisible(False)
            # noinspection PyUnresolvedReferences
            action.triggered.connect(partial(self.on_open_recent_files, i, GUI_COMPARE | COMP_REPO))
            self.compare_recent_repository_actions.append(action)

        # create compare with File menu
        image = QIcon(str(images / 'open_file.png'))
        self.open_compare_file_action = QAction(image, '&Open File to Compare', self)
        image = QIcon(str(images / 'open_repo.png'))
        self.open_compare_folder_action = QAction(image, 'Open &Repository to Compare', self)
        image = QIcon(str(images / 'open_repo.png'))
        self.denodo_folder_structure_action = QAction(image, 'Denodo Folder Structure', self)

        self.open_compare_file_action.setEnabled(False)
        self.open_compare_folder_action.setEnabled(False)
        self.denodo_folder_structure_action.setEnabled(False)

        # Reset everything

        self.reset_compare_action = QAction(QIcon(str(images / 'reset.png')), 'Remove &Comparison', self)
        self.reset_action = QAction(QIcon(str(images / 'reset.png')), 'Reset &Everything', self)
        # create about actions
        self.about_action = QAction("&About", self)
        self.about_qt_action = QAction("About &Qt", self)

        # Menu
        self.menubar = self.menuBar()
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

        # Format and setup all widgets
        self.setup_ui()

        # Initialize class properties ###########################################################################
        # self.last_clicked_class_type = None
        self.working_folder = None
        self.base_repository_file = None
        self.base_repository_folder = None
        self.compare_repository_file = None
        self.compare_repository_folder = None
        self._mode = 0
        self.code_show_selector = ORIGINAL_CODE
        self.code_text_edit_cache = None

        # setup state machine
        self.state_machine = QStateMachine()
        self.states = dict(init=QState(self.state_machine),
                           base_loaded=QState(self.state_machine),
                           compare_loaded=QState(self.state_machine))
        self.setup_states()
        self.state_machine.setInitialState(self.states['init'])
        self.state_machine.start()
        self.logger.debug("Finished Window creation")

    @staticmethod
    def get_pixmap(image_path: str)-> QVariant:
        """Returns the pixmap of icons, given their path

        :param image_path: the relative path / filename to the image
        :return: a QVariant holding the pixmap
        """
        images = Path(QFileInfo(__file__).absolutePath()) / 'images'
        return QVariant(QPixmap(str(images / image_path)).scaled(16, 16))

    def get_mode(self)->int:
        """Getter for current mode. Mode encapsulates the state of the app,
        what kind of files are loaded, if theu are loaded etc.

        :return: the current mode
        """
        return self._mode

    def set_mode(self, new_mode: int):
        """Setter for the current mode
        :param new_mode: the new mode
        :return: None
        """
        if not self._mode == new_mode:
            self._mode = new_mode

    def add_mode(self, mode: int):
        """Adds a feature to the current mode
        :param mode: the feature to be added
        :return: None
        """
        assert isinstance(mode, int)
        if not self._mode & mode:
            self._mode += mode

    def sub_mode(self, mode: int):
        """Subtract a feature from the current mode
        :param mode: The feature to be subtracted
        :return: None
        """
        if self._mode & mode:
            self._mode -= mode

    def setup_states(self):
        """Sets up the states of the state machine.
        Three states are used:
            init; the initial state
            base: the state when base data is loaded, often indicated by the mode flag: GUI_SELECT
            compare:  the state when compare data is also loaded, often indicated by the mode flag: GUI_COMPARE
        The classes TransOpenBase, TransResetBase, TransOpenCompare, TransRemoveCompare and TransResetAll
        are used to manage the transition between states

        :return: None
        """
        init = self.states['init']
        base = self.states['base_loaded']
        compare = self.states['compare_loaded']
        
        init.addTransition(TransOpenBase(self, init, base, self.mode_changed))
        base.addTransition(TransResetBase(self, base, init, self.mode_changed))
        base.addTransition(TransOpenCompare(self, base, compare, self.mode_changed))
        compare.addTransition(TransRemoveCompare(self, compare,  base, self.mode_changed))
        compare.addTransition(TransResetAll(self, compare, init, self.mode_changed))

    def current_base_path_label(self)->str:
        """Returns the label text for the base data

        :return: string with base data type and location
        """
        label = ''
        if self.base_repository_file:
            label = 'File: '
        if self.base_repository_folder:
            label = 'Folder: '
        if self.base_repository_file or self.base_repository_folder:
            label += self.base_repository_file if self.base_repository_file else self.base_repository_folder
        return label

    def current_compare_path_label(self)->str:
        """Returns the label text for the compare data

        :return: string with compare data type and location
        """
        label = ''
        if self.compare_repository_file:
            label = 'File: '
        if self.compare_repository_folder:
            label = 'Folder: '

        if self.compare_repository_file or self.compare_repository_folder:
            label += self.compare_repository_file if self.compare_repository_file else self.compare_repository_folder
        return label

    @staticmethod
    def create_tree_view(tooltip: str='')->QTreeView:
        """Factory for instances of TreeView, setting common properties of them all

        :param tooltip: Initial tooltip
        :return: the TreeView created
        """
        icon_size = QSize(16, 16)
        tree_view = QTreeView()
        tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree_view.setSelectionMode(QAbstractItemView.NoSelection)
        tree_view.setSelectionBehavior(QAbstractItemView.SelectItems)
        tree_view.setEnabled(True)
        tree_view.setItemsExpandable(True)
        tree_view.setSortingEnabled(False)
        tree_view.setRootIsDecorated(True)
        tree_view.setIconSize(icon_size)
        tree_view.setUniformRowHeights(True)
        tree_view.setAnimated(True)

        # hack to make horizontal scrollbars appear when needed
        header = tree_view.header()
        header.setStretchLastSection(False)
        header.setResizeContentsPrecision(0)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        if tooltip:
            tree_view.setToolTip(tooltip)
            tree_view.setToolTipDuration(2000)
        return tree_view

    # noinspection PyUnresolvedReferences
    def setup_ui(self):
        """Method to setup up all widgets

        :return: None
        """
        self.logger.debug("Start setup window ui")

        # Configure Widgets ####################################################################################
        self.search_label.setText('Search')
        self.find_button.setText('Find')

        self.select_buttons.setHidden(True)
        self.diff_buttons.setHidden(True)

        self.code_text_edit.setLineWrapMode(0)
        self.code_text_edit.setReadOnly(True)
        self.code_text_edit.setText("")
        self.log_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.log_edit.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.log_edit.setMaximumBlockCount(1000)
        self.item_info.setPlainText("")

        self.status_bar.setMinimumSize(QSize(0, 20))
        self.status_bar.showMessage("Ready")

        #  Layout ################################################################################

        self.main_splitter.setOrientation(Qt.Vertical)
        self.header_splitter.setOrientation(Qt.Horizontal)
        self.content_splitter.setOrientation(Qt.Horizontal)
        self.right_side_splitter.setOrientation(Qt.Vertical)
        self.tree_views_splitter.setOrientation(Qt.Horizontal)
        self.log_splitter.setOrientation(Qt.Horizontal)

        self.right_content_widget.setLayout(self.right_content_box)
        self.left_header_widget.setLayout(self.left_header_box)
        self.right_header_widget.setLayout(self.right_header_box)
        self.code_edit_widget.setLayout(self.code_edit_box)
        self.find_header_widget.setLayout(self.find_header_box)
        self.treeview2_widget.setLayout(self.treeview2_box)
        self.treeview3_widget.setLayout(self.treeview3_box)
        self.log_widget.setLayout(self.log_box)
        self.info_widget.setLayout(self.info_box)

        # noinspection PyArgumentList
        self.log_box.addWidget(self.log_edit)
        # noinspection PyArgumentList
        self.info_box.addWidget(self.item_info)

        self.log_splitter.addWidget(self.log_widget)
        self.log_splitter.addWidget(self.info_widget)

        # noinspection PyArgumentList
        self.right_content_box.addWidget(self.treeview1)
        # noinspection PyArgumentList
        self.right_content_box.addWidget(self.select_buttons)

        # noinspection PyArgumentList
        self.treeview2_box.addWidget(self.treeview2)

        # noinspection PyArgumentList
        self.treeview3_box.addWidget(self.treeview3)

        # noinspection PyArgumentList
        self.find_header_box.addWidget(self.search_label)
        # noinspection PyArgumentList
        self.find_header_box.addWidget(self.find_line_edit)
        # noinspection PyArgumentList
        self.find_header_box.addWidget(self.find_button)

        # noinspection PyArgumentList
        # self.left_header_box.addWidget(self.mode_label)
        # noinspection PyArgumentList
        self.left_header_box.addWidget(self.base_repository_label)
        # noinspection PyArgumentList
        self.left_header_box.addWidget(self.compare_repository_label)

        # noinspection PyArgumentList
        self.right_header_box.addWidget(self.find_header_widget)

        # noinspection PyArgumentList
        self.code_edit_box.addWidget(self.code_text_edit)
        # noinspection PyArgumentList
        self.code_edit_box.addWidget(self.diff_buttons)

        # noinspection PyArgumentList
        self.header_splitter.addWidget(self.left_header_widget)
        # noinspection PyArgumentList
        self.header_splitter.addWidget(self.right_header_widget)

        self.tree_views_splitter.addWidget(self.treeview3_widget)
        self.tree_views_splitter.addWidget(self.treeview2_widget)
        self.right_side_splitter.addWidget(self.tree_views_splitter)
        self.right_side_splitter.addWidget(self.code_edit_widget)

        self.content_splitter.addWidget(self.right_content_widget)
        self.content_splitter.addWidget(self.right_side_splitter)

        self.main_splitter.addWidget(self.header_splitter)
        self.main_splitter.addWidget(self.content_splitter)
        self.main_splitter.addWidget(self.log_splitter)

        self.main_splitter.setStretchFactor(1, 1)
        self.log_splitter.setStretchFactor(0, 0.5)
        self.main_splitter.setSizes([50, 800, 100])
        self.log_splitter.setSizes([500, 200])
        self.header_splitter.setSizes([300, 300])

        self.header_splitter.setHandleWidth(0)
        self.main_splitter.setHandleWidth(0)
        self.content_splitter.setHandleWidth(0)
        self.tree_views_splitter.setHandleWidth(0)
        self.right_side_splitter.setHandleWidth(0)
        self.log_splitter.setHandleWidth(0)

        self.main_widget.setLayout(self.main_layout)
        self.main_layout.addWidget(self.main_splitter)

        # Parent mainWidget to the QMainWindow
        self.setCentralWidget(self.main_widget)

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
        self.reset_action.triggered.connect(self.on_reset)

        self.reset_compare_action.setStatusTip('Remove comparison')
        self.reset_compare_action.triggered.connect(self.on_remove_comparison)

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
        for action in self.recent_file_actions:
            self.recent_file_menu.addAction(action)

        self.recent_repository_separator = self.filemenu.addSeparator()
        self.recent_repository_menu = self.filemenu.addMenu('Recent Repositories')
        for action in self.recent_repository_actions:
            self.recent_repository_menu.addAction(action)

        self.filemenu.addSeparator()
        self.filemenu.addAction(self.exit_action)

        self.compare_menu = self.menubar.addMenu('&Compare')
        self.compare_menu.addAction(self.open_compare_file_action)
        self.compare_menu.addAction(self.open_compare_folder_action)

        self.compare_recent_file_separator = self.compare_menu.addSeparator()
        self.compare_recent_file_menu = self.compare_menu.addMenu('Recent Files')
        for action in self.compare_recent_file_actions:
            self.compare_recent_file_menu.addAction(action)

        self.compare_recent_repository_separator = self.compare_menu.addSeparator()
        self.compare_recent_repository_menu = self.compare_menu.addMenu('Recent Repositories')

        for action in self.compare_recent_repository_actions:
            self.compare_recent_repository_menu.addAction(action)

        self.compare_recent_repository_menu.setEnabled(False)
        self.compare_recent_file_menu.setEnabled(False)
        self.reset_compare_action.setEnabled(False)

        self.update_recent_file_actions()

        self.options_menu = self.menubar.addMenu('&Options')
        self.options_menu.addAction(self.denodo_folder_structure_action)
        self.options_menu.addSeparator()
        self.options_menu.addAction(self.reset_compare_action)
        self.options_menu.addAction(self.reset_action)

        self.help_menu = self.menubar.addMenu('&Help')
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.about_qt_action)

        # Callbacks Slots and Signals #####################################################
        self.treeview1.expanded.connect(self.on_expand_treeview)
        self.treeview1.collapsed.connect(self.on_collapse_treeview)
        self.treeview1.clicked.connect(self.on_click_item)
        self.treeview2.clicked.connect(self.on_click_item)
        self.treeview3.clicked.connect(self.on_click_item)
        self.tree_model.selection_changed.connect(self.on_selection_changed)
        self.tree_model.dataChanged.connect(self.on_selection_changed)
        self.find_button.released.connect(self.on_find_button_click)
        self.find_line_edit.returnPressed.connect(self.on_find_button_click)
        self.logger.custom_signal.connect(self.on_log_message)

        # Radio buttons
        self.select_buttons_group.buttonClicked.connect(self.on_select_buttons_clicked)
        self.diff_buttons_group.buttonClicked.connect(self.on_diff_buttons_clicked)
        self.logger.debug("Finished setup window ui")

    def on_log_message(self, msg):
        """Puts the log message onto the screen in the log_edit widget.

        :param msg: the message
        :return: None
        """
        self.log_edit.appendPlainText(msg)

    def update_recent_file_actions(self):
        """Updates the Action objects in the menu to reflect the recent file storage.

        :return: None
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

    @staticmethod
    def get_buttons_widget(button_dict: dict)->Tuple[QWidget, QButtonGroup]:
        """Constructs a series of related radio buttons used to filter CodeItems.

        :param button_dict: A dict with names and colors
        :return: A tuple of widget and the group its in
        """
        layout = QHBoxLayout()  # layout for the central widget
        # noinspection PyArgumentList
        widget = QWidget()  # central widget
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
            # noinspection PyArgumentEqualDefault
            layout.addWidget(btn, 0, Qt.AlignLeft)
        return widget, group

    # Event handlers

    def on_expand_treeview(self, index):
        """Event handler for expand events of treeview1.
        This event is copied to treeview2 so expanding treeview1 items are folowed in treeview2

        :param index: the QModelIndex of the item expanded
        :return: none
        """
        idx = self.color_proxy_model.mapToSource(index)
        self.treeview2.expand(self.proxy_model.mapFromSource(idx))

    def on_collapse_treeview(self, index):
        """Event handler for collapse events of treeview1.
        This event is copied to treeview2 so collapsing treeview1 items are followed in treeview2

        :param index: the QModelIndex of the item expanded
        :return: none
        """
        idx = self.color_proxy_model.mapToSource(index)
        self.treeview2.collapse(self.proxy_model.mapFromSource(idx))

    def on_open_recent_files(self, index: int, mode: int):
        """Event handler for the click on a recent files menu item.

        This function collects the data from the OS storage about the recent file/repo list
        and initiates a loading process.

        :param index: Index of the menu item clicked
        :param mode: mode flag of the application
        :return: None
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
        """Event handler for the radio buttons in the left pane to filter the items in treeview1 on color.
        :param button: the button clicked
        :return: None
        """
        if button.text() == 'All':
            color = ''
        else:
            color = self.select_button_labels[button.text()]
        self.color_proxy_model.set_color_filter(color, CodeItem)

    def on_find_button_click(self):
        """Event handler of the find button. Sets the focus on the first found item and logs all items found

        :return: None
        """
        mode = self.get_mode()
        if mode & BASE_LOADED or mode & COMP_LOADED:
            what = self.find_line_edit.text().strip()
            if what:
                model = self.tree_model
                match_mode = Qt.MatchRecursive | Qt.MatchStartsWith
                item_indices = model.match(model.index(0, 0), DISPLAY,  QVariant(what), -1, match_mode)
                if item_indices:
                    items = (index.internalPointer() for index in item_indices)
                    item_strings = \
                        (self.object_type(item) + ': ' + item.name for item in items if item.class_type == CodeItem)
                    for item_string in item_strings:
                        self.logger.info(f"Found: {item_string}")

                    item = item_indices[0]
                    self.treeview1.setCurrentIndex(self.color_proxy_model.mapFromSource(item))
                    self.treeview1.setFocus()
                    self.status_bar.showMessage(f"Found {str(len(item_indices))} occurrences. The first shown; see log")
                else:
                    self.treeview1.setFocus()
                    self.status_bar.showMessage(f"The term: {what} was not found.")

    def on_diff_buttons_clicked(self, button: QRadioButton):
        """Event handler for the radio buttons in the right pane to filter the view of code, during a compare.
        e.g. as original, new code, or changes

        :param button: the button clicked
        :return: None
        """
        text = button.text()
        if text == 'Original':
            self.code_show_selector = ORIGINAL_CODE
        elif text == 'New':
            self.code_show_selector = COMPARE_CODE
        elif text == 'Changes':
            self.code_show_selector = DIFF_CODE
        self.show_code_text()

    def on_open(self, new_mode: int, load_path: Path=None):
        """Event handler Open File menu items and Compare open items.
        This function is the starting point for loading a model based on a .vql file or a repository

        :param new_mode: the mode of opening
        :param load_path: optional parameter for loading from a recent file list
        :return: None
        """

        file = None
        folder = None
        if load_path:
            self.logger.info(f"Open file or repository {load_path} in mode: {show_mode(new_mode)} mode.")
            if new_mode & FILE:
                    file = Path(load_path)
            elif new_mode & REPO:
                    folder = Path(load_path)
            else:
                return

        if new_mode & GUI_SELECT:
            if self.states['base_loaded'] in self.state_machine.configuration():
                # some base model is open:
                if self.ask_drop_changes():
                    self.add_mode(BASE_UNLOAD)
                    self.mode_changed.emit(self.get_mode())
                    if load_path:
                        self.on_open(self.get_mode() | new_mode, load_path)  # recurse to the begin
                    else:
                        self.on_open(self.get_mode() | new_mode)  # recurse to the begin
                else:
                    return
            elif self.states['init'] in self.state_machine.configuration():
                if new_mode & BASE_FILE:
                    if not file:
                        file = self.ask_file_open()
                    if file:
                        self.base_repository_file = file
                        self.add_mode(BASE_FILE)
                        self.mode_changed.emit(self.get_mode())
                        self.add_mode(GUI_SELECT)
                        return
                elif new_mode & BASE_REPO:
                    if not folder:
                        folder = self.ask_repository_open()
                    if folder:
                        self.base_repository_folder = folder
                        self.add_mode(BASE_REPO)
                        self.mode_changed.emit(self.get_mode())
                        self.add_mode(GUI_SELECT)
                        return
        elif new_mode & GUI_COMPARE:
            if self.states['compare_loaded'] in self.state_machine.configuration():
                if self.ask_drop_changes():
                    self.add_mode(COMP_UNLOAD)
                    self.mode_changed.emit(self.get_mode())
                    if load_path:
                        self.on_open(self.get_mode() | new_mode, load_path)  # recurse to the begin
                    else:
                        self.on_open(self.get_mode() | new_mode)  # recurse to the begin
                else:
                    return
            elif self.states['base_loaded'] in self.state_machine.configuration():
                if new_mode & COMP_FILE:
                    if not file:
                        file = self.ask_file_open()
                    if file:
                        self.compare_repository_file = file
                        self.add_mode(COMP_FILE)
                        self.mode_changed.emit(self.get_mode())
                        self.add_mode(GUI_COMPARE)
                        return
                elif new_mode & COMP_REPO:
                    if not folder:
                        folder = self.ask_repository_open()
                    if folder:
                        self.compare_repository_folder = folder
                        self.add_mode(COMP_REPO)
                        self.mode_changed.emit(self.get_mode())
                        self.add_mode(GUI_COMPARE)
                        return
            else:
                message_to_user("No repository loaded yet", parent=self)
        self.logger.info("File or repository loaded.")

    def on_save(self, save_mode: int):
        """Event handler for the Save to File or Save to Repository menu items.
        This function is the starting point for saving a model to a .vql file or repository.
        Only selected items in the base model are saved!

        :return: None
        """
        self.logger.info(f"Saving file or repository in {show_mode(save_mode)} mode.")
        current_mode = self.get_mode()
        if not current_mode & BASE_LOADED:
            message_to_user("No repository loaded yet", parent=self)
            return

        if save_mode & FILE:
            file = self.ask_file_save()
            if file:
                self.save_model_to_file(file)
                self.logger.info(f"{file} saved.")
        elif save_mode & REPO:
            folder = self.ask_repository_save()
            if folder:
                self.save_model_to_repository(folder)
                self.logger.info(f"{folder} saved.")

    def on_reset(self):
        """Event handler to reset everything

        :return: None
        """

        if self.states['base_loaded'] in self.state_machine.configuration():
            self.logger.info('Application reset.')
            self.add_mode(BASE_UNLOAD)
            self.mode_changed.emit(self.get_mode())
        elif self.states['compare_loaded'] in self.state_machine.configuration():
            self.logger.info('Application reset.')
            self.add_mode(BASE_UNLOAD)
            self.add_mode(COMP_UNLOAD)
            self.mode_changed.emit(self.get_mode())
        else:
            self.logger.info('Application is already in initial state')

    def on_remove_comparison(self):
        """Event handler to remove the comparison.

        :return: None
        """

        if self.states['compare_loaded'] in self.state_machine.configuration():
            self.logger.info('Removing Compare.')
            self.add_mode(COMP_UNLOAD)
            self.mode_changed.emit(self.get_mode())
        else:
            self.logger.info('No comparison found')

    def on_click_item(self, item_index: QModelIndex):
        """Event handler when an item in any treeview is clicked
        A click on a CodeItem results in its code, info etc to be shown in the appropriate widgets

        :param item_index: the QModelIndex of the item
        :return: None
        """
        if not item_index:
            self.dependency_model.set_root_code_item(None)
            self.code_text_edit_cache = None
            self.item_info.setPlainText('')
            self.code_text_edit.setText('')
            return

        if not item_index.isValid():
            return

        if item_index.model() is self.dependency_model:
            item = item_index.internalPointer().code_item
        else:
            item = item_index.model().mapToSource(item_index).internalPointer()

        if item:
            self.show_item_data(item)

    def show_item_data(self, item):
        """Helper function of on_click_item to show the info about a CodeItem

        :return: None
        """
        if isinstance(item, CodeItem):
            self.logger.debug('CodeItem clicked on View Pane: ' + item.name)
            if item != self.dependency_model.get_root_code_item():
                self.dependency_model.set_root_code_item(item)
                self.treeview3.expandAll()

            cache = dict()
            cache['object_name'] = item.name
            cache['code'] = item.base_data.code
            cache['compare_code'] = item.compare_data.code
            self.code_text_edit_cache = cache
            self.show_code_text()
            self.show_info(item)
        else:
            if self.dependency_model.get_root_code_item():
                self.dependency_model.set_root_code_item(None)
            self.item_info.setPlainText('')
            self.code_text_edit_cache = None
            self.code_text_edit.setText('')

    def show_info(self, code_item):
        """Helper function of show_item_data to show the info about a CodeItem

        :param code_item: the CodeItem whose info is shown
        :return: None
        """
        if not code_item:
            self.item_info.setPlainText('')
            return
        name = code_item.name

        if self.states['base_loaded'] in self.state_machine.configuration():
            gui = GUI_SELECT
        elif self.states['compare_loaded'] in self.state_machine.configuration():
            gui = GUI_COMPARE
        else:
            self.item_info.setPlainText('')
            return
        header = self.object_type(code_item) + ': ' + name
        data = code_item.get_context_data(gui)
        denodo_path = data.denodo_path
        repository_path = str(code_item.get_file_path(Path(code_item.chapter.name)))
        sources = list([f"[{self.object_type(source)} : {source.name}]"
                        for source in self.get_item_sources(code_item, gui, 0)])
        sources = set(sources)
        source_string = '\n>> ' + '\n>> '.join(sources)
        info = header
        info += f"\nDenodo path: {denodo_path}"
        info += f"\nRepository path: {repository_path}"

        info += f"\nSources: {source_string}"
        self.item_info.setPlainText(info)

    def show_code_text(self):
        """Shows the code of the clicked CodeItem in the Code edit widget.
        This function uses the cached CodeItem

        :return: None
        """

        if self.code_text_edit_cache:
            # convenience names
            item_data = self.code_text_edit_cache
            selector = self.code_show_selector
            put_text = self.code_text_edit.setHtml
            object_name = item_data['object_name']
            html_code = ''
            if self.states['base_loaded'] in self.state_machine.configuration():
                html_code = self.format_source_code(object_name, item_data['code'], selector)
            elif self.states['compare_loaded'] in self.state_machine.configuration():
                if selector & ORIGINAL_CODE:
                    html_code = self.format_source_code(object_name, item_data['code'], selector)
                elif selector & COMPARE_CODE:
                    html_code = self.format_source_code(object_name, item_data['compare_code'], selector)
                elif selector & DIFF_CODE:
                    difference = CodeItem.get_diff(item_data['code'], item_data['compare_code'])
                    html_code = self.format_source_code(object_name, difference, selector)
            put_text(html_code)

    def get_item_sources(self, item: CodeItem, gui: int, n_recurse: int):
        """Generator for all dependencies of a CodeItem

        :param item: the CodeItem whose dependencies are yielded
        :param gui: the gui indicating compare code or base code
        :param n_recurse: internal variable to prevent stack overflows
        :return:
        """
        n_recurse = n_recurse + 1
        if n_recurse > 500:
            return
        data = item.get_context_data(gui)
        last = True if len(data.dependencies) == 1 else False
        for dependency in data.dependencies:
            if last:
                yield dependency
            yield from self.get_item_sources(dependency, gui, n_recurse)

    @staticmethod
    def object_type(code_item)->str:
        """Returns a presentable string with the category (chapter) of this code item

        :param code_item: the code item whose info is shown
        :return: the presentable string
        """
        assert isinstance(code_item, CodeItem)
        object_type = code_item.chapter.name[:-1] if code_item.chapter.name != 'DATABASE' else 'DATABASE'
        return object_type.capitalize()

    def on_selection_changed(self, item: TreeItem):
        """Event handler for changes in the selection (check boxes) in the treeview1.
        This function checks effects on other items through dependencies and dependees
        and issues warnings in the log

        :param item: The Item whose selection is changed
        :return: None
        """
        info = ''
        selected_string = 'selected' if item.selected else 'unselected'

        if isinstance(item, Chapter):
            msg = f"Chapter:{item.name} got {selected_string}."
            self.logger.info(msg)
            self.status_bar.showMessage(msg)
        elif isinstance(item, DenodoFolder):
            msg = f"Denodo folder:{item.name} got {selected_string}."
            self.logger.info(msg)
            self.status_bar.showMessage(msg)
        elif isinstance(item, CodeItem):
            mode = self.get_mode()
            item_string = f"{self.object_type(item)}:{item.name}"
            msg = f"{item_string} got {selected_string}."
            self.logger.info(msg)
            self.status_bar.showMessage(msg)
            if mode & GUI_SELECT:
                data = item.base_data
                if item.selected:
                    info = f"Please check if all dependencies of {item_string} are fulfilled.\n"
                    info += "This software does not check that."
                    self.status_bar.showMessage(info)
                else:
                    if any([dependee.selected for dependee in data.dependees]):
                        info = 'Warning: This item has other items that are dependent on it.\n'
                        info += 'These are now orphaned.\nPlease see log file for the list of affected items.'
                        dependees_orphaned = [dependee for dependee in data.dependees if dependee.selected]
                        for dependee in dependees_orphaned:
                            orphan_string = f"{self.object_type(dependee)}:{dependee.name}"
                            self.logger.warning(f"Un-selecting of {item_string} caused orphan: {orphan_string}")

            elif mode & GUI_COMPARE:
                data = item.compare_data
                if item.selected:
                    if item.color == red:  # lost item got selected
                        data.code = item.base_data.code  # fill compare code with base code, so code can be saved
                        items = {code_item.object_name for code_item in item.base_data.dependencies}
                        dependencies_not_met = [item for item in items if not data.code or not item.selected]
                        if any(dependencies_not_met):
                            info = 'Warning: This base data item depends on base data items\n'
                            info += 'that are not selected or do not exist in the compare base.\n'
                            info += 'Please see log file for the list of dependencies.'
                            for dependency_not_met in dependencies_not_met:
                                dependency_string = f"{self.object_type(dependency_not_met)}:{dependency_not_met.name}"
                                self.logger.warning(f"Selecting of {item_string} caused dependency to be "
                                                    f"broken with: {dependency_string}")
                    else:
                        info = f"Please check if all dependencies of {item_string} are fulfilled."
                        self.status_bar.showMessage(info)
                        info += "\nThis software does not check that."
                else:
                    if item.color == red:  # lost item got unselected
                        data.code = ''  # remove the code again
                    if any([dependee.selected for dependee in data.dependees]):
                        info = 'Warning: This item has other items that are dependent on it.'
                        self.status_bar.showMessage(info)
                        info += '\nThese are now orphaned.\nPlease see log file for the list of affected items.'
                        dependees_orphaned = [dependee for dependee in data.dependees if dependee.selected]
                        for dependee in dependees_orphaned:
                            orphan_string = f"{self.object_type(dependee)}:{dependee.name}"
                            self.logger.warning(f"Un-selecting of {item_string} caused orphan: {orphan_string}")
        if info:
            self.item_info.setPlainText(info)

    def on_about_vql_manager(self):
        """Event handler for the click on the About menu item in the help menu.

        :return: None
        """
        # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
        QMessageBox.about(self, 'About ' + self.windowTitle(), about_text)

    def on_about_qt(self):
        """Event handler for the click on the About Qt menu item in the help menu.
        It uses the boilerplate Qt about box

        :return: None
        """
        # noinspection PyCallByClass,PyTypeChecker
        QMessageBox.aboutQt(self, self.windowTitle())

    @staticmethod
    def format_source_code(object_name: str, raw_code: str, code_type: int)->str:
        """Creates html for the code edit widget to view the source code.

        :param object_name: Name of the CodeItem
        :param raw_code: the raw code string
        :param code_type: and indicator what code is formatted either ORIGINAL_CODE or COMPARE_CODE or DIFF_CODE
        :return: the constructed html
        """

        def format_sql(_code: str)->str:
            """Formats the sql in the code of View type CodeItems

            :param _code: the code to be formatted
            :return: the formatted code
            """
            chars = 4
            start = _code.find(' AS SELECT ') + chars
            end = _code.find(';', start)
            if chars <= start < end:
                clause = sqlparse.format(_code[start:end], reindent=True, indent_tabs=False, indent_width=2)
                if clause:
                    return _code[:start] + '\n' + clause + _code[end:]

            return _code

        def multi_substitution(_substitutions: list, _code: str)->str:
            """
            Simultaneously perform all substitutions on the subject string.
            :param _substitutions: list with substitutions
            :param _code: the code
            :return: the substituted code
            """
            re_pattern = '|'.join(f"(\\b{escape(original)}\\b)" for original, substitute in _substitutions)
            _substitutions = [substitute for original, substitute in _substitutions]
            return sub(re_pattern, lambda x: _substitutions[x.lastindex - 1], _code)

        if not raw_code:
            return ''

        html = ''
        if code_type & (ORIGINAL_CODE | COMPARE_CODE):
            code = raw_code
            code = format_sql(code)
            code = multi_substitution(SUBSTITUTIONS, code)
            code = code.replace('\n', '<br />\n')
            code = code.replace('    ', ' &nbsp; &nbsp; &nbsp; &nbsp; ')
            body = '<p style="color:' + white + '">' + code + '</p>'
            body = body.replace(object_name, '<font color="' + red + '">' + object_name + '</font>')
            html = doc_template(object_name, body)
        elif code_type & DIFF_CODE:
            html = doc_template(object_name, raw_code)
        return html

    def on_switch_view(self):
        """Event handler for the click on the menu item to switch between SCRIPT view or Denodo view.

        :return: None
        """

        if self.get_mode() & BASE_LOADED:
            if self.denodo_folder_structure_action.isChecked():
                if self.tree_model.change_view(self.get_mode() | DENODO_VIEW):
                    self.denodo_folder_structure_action.setText('Switch to VQL View')
                    self.logger.debug('Switching to Denodo View')
                else:
                    message_to_user('Denodo view not possible. Missing folders in the code.', parent=self)
                    self.denodo_folder_structure_action.setChecked(False)
                    self.logger.debug('Switch to Denodo View aborted')
            else:
                self.logger.debug('Switching to VQL View')
                self.denodo_folder_structure_action.setText('Switch to DENODO View')
                self.tree_model.change_view(self.get_mode() | SCRIPT_VIEW)

    # dialogs for opening and saving

    def ask_file_open(self)->Union[Path, None]:
        """Asks user which file to open to via a dialog.

        :return: the selected filepath
        """
        self.logger.info('Asking file to open.')
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
            message_to_user("File does not exist", parent=self)
            return None

        if not filename.suffix == '.vql':
            message_to_user("This file has the wrong extension", parent=self)
            return None

        self.logger.info('Got: ' + str(filename))
        return filename

    def ask_repository_open(self)->Union[Path, None]:
        """Asks user which repository (folder) to open via a dialog.

        :return: the folder path
        """
        self.logger.info('Asking repository to open.')
        open_path = str(self.working_folder if self.working_folder else Path.cwd())

        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptOpen)
        dialog.setWindowTitle("Select Folder")
        dialog.setViewMode(QFileDialog.List)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        # noinspection PyArgumentList,PyArgumentList
        folder = dialog.getExistingDirectory(self, "Open Directory", open_path)

        if not folder:
            return None
        folder = Path(str(folder))
        if not folder.is_dir():
            message_to_user("No folder found", parent=self)
            return None
        self.logger.info('Got:' + str(folder))
        return folder

    def ask_repository_save(self)->Union[Path, None]:
        """Asks user which folder to save to via a dialog. If the folder exists, asks if overwrite is allowed.

        :return: Folder to store the repository
        """
        self.logger.info('Asking repository to save.')
        open_path = str(self.working_folder if self.working_folder else Path.cwd())
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        dialog.setFileMode(QFileDialog.Directory)
        # noinspection PyArgumentList,PyArgumentList
        folder = dialog.getExistingDirectory(self, "Save to Repository", open_path)

        if not folder:
            return None
        folder = Path(str(folder))

        if not folder.is_dir():
            try:
                folder.mkdir(parents=True)
                return folder
            except OSError as error:
                error_message_box('Error', 'Error creating folder', str(error), parent=self)
                return None

        for file, content in self.root_item.get_selected_code_files(self.get_mode(), folder):
            print(file)

        if any([path.exists() for path, _ in self.root_item.get_selected_code_files(self.get_mode(), folder)]):
            if not self.ask_overwrite():
                return None
        self.logger.info('Got:' + str(folder))
        return folder

    def ask_file_save(self)->Union[Path, None]:
        """Asks which file to save to via a dialog. It also checks if the file may be overwritten

        :return: the file path of the file to be written
        """
        self.logger.info('Asking file to save.')
        open_path = str(self.working_folder if self.working_folder else Path.cwd())
        dialog = QFileDialog(self)
        dialog.setAcceptMode(dialog.AcceptSave)
        dialog.setDefaultSuffix('vql')
        dialog.setFileMode(QFileDialog.AnyFile)
        # noinspection PyArgumentList,PyArgumentList
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
        self.logger.info('Got:' + str(filename))
        return filename

    # General purpose dialogs
    def ask_overwrite(self)->bool:
        """General Messagebox to warn/ask for files to be overwritten.

        :return: Boolean if allowed
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
        """

        if not self.root_item.changed():
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

    def write_file(self, file: Path, content: str)->bool:
        """General function to write a file to disk

        :param file: the path where the file should be written to
        :param content: The content to be written as string
        :return: Boolean on success
        """

        # self.logger.debug('Saving: ' + str(file))
        try:
            with file.open(mode='w') as f:
                f.write(content)
                # self.logger.debug(f"Saved {written} characters to {str(file)}")
                return True
        except (OSError, IOError) as error:
            msg = f"An error occurred during writing of file: {str(file)}"
            self.logger.error(msg)
            error_message_box("Error", msg, str(error), parent=self)
            return False

    def save_model_to_file(self, file: Path)->bool:
        """Saves the single .vql file.

        :param file: the file!
        :return: boolean True on success
        """

        self.logger.debug(f"Saving model to file in {file} in mode: {show_mode(self.get_mode())}")

        self.status_bar.showMessage("Saving")
        self.treeview1.blockSignals(True)
        content = self.root_item.get_code_as_file(self.get_mode(), selected=True)
        self.treeview1.blockSignals(False)
        if content:
            if self.write_file(file, content):
                self.status_bar.showMessage("Ready")
                self.logger.debug("Saved OK")
                return True
            else:
                self.status_bar.showMessage("Save error")
                self.logger.debug("Not Saved")
                return False

    def save_model_to_repository(self, folder: Path)->bool:
        """Saves the model selection to a repository.

        The files are written to chapter_folders
        :param folder: The folder to write the repository
        :return: boolean on success
        """
        self.logger.debug(f"Saving model to repository in folder {folder} in mode: {show_mode(self.get_mode())}")
        self.status_bar.showMessage("Saving")
        if not folder:
            self.status_bar.showMessage("Save Error")
            return False

        self.treeview1.blockSignals(True)

        for part_log_filepath, part_log_content in self.root_item.get_part_logs(folder):

            if not part_log_content or not part_log_filepath:
                self.logger.debug(f"No content while saving {part_log_filepath} ")
                continue
                # self.status_bar.showMessage("Save Error")
                # return False

            sub_folder = part_log_filepath.parent
            if not sub_folder.is_dir():
                try:
                    self.logger.debug(f"Creating Directory: {sub_folder}")
                    sub_folder.mkdir(parents=True)
                except (OSError, IOError) as error:
                    self.status_bar.showMessage("Save Error")
                    msg = f"An error occurred during creation of folder: {sub_folder}"
                    error_message_box("Error", msg, str(error), parent=self)
                    self.treeview1.blockSignals(False)
                    return False

            if not self.write_file(part_log_filepath, part_log_content):
                self.status_bar.showMessage("Save Error")
                self.treeview1.blockSignals(False)
                return False

        for file_path, content in self.root_item.get_selected_code_files(self.get_mode(), folder):
            if not content or not file_path:
                self.status_bar.showMessage("Save Error")
                self.logger.warning(f"Missing content or file path: {str(file_path)}")
                continue
            if not self.write_file(file_path, content):
                self.status_bar.showMessage(f"Save Error: {file_path}")
                self.logger.warning(f"Save of {file_path} did not succeed")
                self.treeview1.blockSignals(False)
                return False

        self.treeview1.blockSignals(False)
        self.status_bar.showMessage("Ready")
        self.logger.debug("Saved OK")
        return True

    def add_to_recent_files(self, file_path: Path, mode: int):
        """Function adds a file path to the OS storage of recent files.

        :param file_path: The path to add
        :param mode: selector flag either REPO or FILE
        :return: None
        """
        self.logger.debug(f"Adding {file_path} to recent file list in {show_mode(mode)} mode")
        settings = QSettings(COMPANY, APPLICATION_NAME)

        if not settings:
            self.logger.debug("No resent file settings found.")
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
        self.logger.debug("Path added to recent files or folders.")


def main():
    """Main entry point for the application

    Boilerplate python code to start and end the application and allows it to be in a module or library
    :return:
    """

    global app

    if version_info < (3, 6):
        message_to_user('You need at least Python version 3.6 to run this application.')
        return

    app = QApplication(argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = VQLManagerWindow()
    window.show()
    exit(app.exec())


if __name__ == '__main__':
    main()
