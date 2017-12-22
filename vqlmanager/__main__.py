#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Denodo VQL Manager
This program shows GUI to split, select, combine and compare Denodo .vql files
Dependencies: python3.6 PyQt5, qdarkstyle, sqlparse, diff_match_patch

Installation
    Install python3.6 or later from https://www.python.org/
    Make sure its in your path.

    To test it run in console or command: python -V  or python3 -V or python3.6 -V
    Use the python command reporting version 3.6
    in this example i assume it is python3

    on linux
    sudo python3.6 -m pip install wheel setuptools PyQt5 qdarkstyle sqlparse

    on windows: open cmd in admin mode
    python3.6 -m pip install wheel setuptools PyQt5 qdarkstyle sqlparse

    anaconda: open jupyter add the said libs
    Note: diff_match_patch may be called diff_match_patch_python



Author: Andre Treebus
Email: andretreebus@hotmail.com
Last edited: November 2017

classes diff_match_patch and patch_object
are written by fraser@google.com (Neil Fraser)

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


# noinspection PyPep8Naming,PyShadowingNames
class diff_match_patch:
    """Class containing the diff, match and patch methods.

    Also contains the behaviour settings.
    """

    def __init__(self):
        """Inits a diff_match_patch object with default settings.
        Redefine these in your program to override the defaults.
        """

        # Number of seconds to map a diff before giving up (0 for infinity).
        self.Diff_Timeout = 1.0
        # Cost of an empty edit operation in terms of edit characters.
        self.Diff_EditCost = 4
        # At what point is no match declared (0.0 = perfection, 1.0 = very loose).
        self.Match_Threshold = 0.5
        # How far to search for a match (0 = exact location, 1000+ = broad match).
        # A match this many characters away from the expected location will add
        # 1.0 to the score (0.0 is a perfect match).
        self.Match_Distance = 1000
        # When deleting a large block of text (over ~64 characters), how close do
        # the contents have to be to match the expected contents. (0.0 = perfection,
        # 1.0 = very loose).  Note that Match_Threshold controls how closely the
        # end points of a delete need to match.
        self.Patch_DeleteThreshold = 0.5
        # Chunk size for context length.
        self.Patch_Margin = 4

        # The number of bits in an int.
        # Python has no maximum, thus to disable patch splitting set to 0.
        # However to avoid long patches in certain pathological cases, use 32.
        # Multiple short patches (using native ints) are much faster than long ones.
        self.Match_MaxBits = 32

    #  DIFF FUNCTIONS

    # The data structure representing a diff is an array of tuples:
    # [(DIFF_DELETE, "Hello"), (DIFF_INSERT, "Goodbye"), (DIFF_EQUAL, " world.")]
    # which means: delete "Hello", add "Goodbye" and keep " world."
    DIFF_DELETE = -1
    DIFF_INSERT = 1
    DIFF_EQUAL = 0

    def diff_main(self, text1, text2, checklines=True, deadline=None):
        """Find the differences between two texts.  Simplifies the problem by
          stripping any common prefix or suffix off the texts before diffing.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          checklines: Optional speedup flag.  If present and false, then don't run
            a line-level diff first to identify the changed areas.
            Defaults to true, which does a faster, slightly less optimal diff.
          deadline: Optional time when the diff should be complete by.  Used
            internally for recursive calls.  Users should set DiffTimeout instead.

        Returns:
          Array of changes.
        """
        # Set a deadline by which time the diff must be complete.
        if deadline is None:
            # Unlike in most languages, Python counts time in seconds.
            if self.Diff_Timeout <= 0:
                deadline = maxsize
            else:
                deadline = time() + self.Diff_Timeout

        # Check for null inputs.
        if text1 is None or text2 is None:
            raise ValueError("Null inputs. (diff_main)")

        # Check for equality (speedup).
        if text1 == text2:
            if text1:
                return [(self.DIFF_EQUAL, text1)]
            return []

        # Trim off common prefix (speedup).
        commonlength = self.diff_commonPrefix(text1, text2)
        commonprefix = text1[:commonlength]
        text1 = text1[commonlength:]
        text2 = text2[commonlength:]

        # Trim off common suffix (speedup).
        commonlength = self.diff_commonSuffix(text1, text2)
        if commonlength == 0:
            commonsuffix = ''
        else:
            commonsuffix = text1[-commonlength:]
            text1 = text1[:-commonlength]
            text2 = text2[:-commonlength]

        # Compute the diff on the middle block.
        diffs = self.diff_compute(text1, text2, checklines, deadline)

        # Restore the prefix and suffix.
        if commonprefix:
            diffs[:0] = [(self.DIFF_EQUAL, commonprefix)]
        if commonsuffix:
            diffs.append((self.DIFF_EQUAL, commonsuffix))
        self.diff_cleanupMerge(diffs)
        return diffs

    def diff_compute(self, text1, text2, checklines, deadline):
        """Find the differences between two texts.  Assumes that the texts do not
          have any common prefix or suffix.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          checklines: Speedup flag.  If false, then don't run a line-level diff
            first to identify the changed areas.
            If true, then run a faster, slightly less optimal diff.
          deadline: Time when the diff should be complete by.

        Returns:
          Array of changes.
        """
        if not text1:
            # Just add some text (speedup).
            return [(self.DIFF_INSERT, text2)]

        if not text2:
            # Just delete some text (speedup).
            return [(self.DIFF_DELETE, text1)]

        if len(text1) > len(text2):
            (longtext, shorttext) = (text1, text2)
        else:
            (shorttext, longtext) = (text1, text2)
        i = longtext.find(shorttext)
        if i != -1:
            # Shorter text is inside the longer text (speedup).
            diffs = [(self.DIFF_INSERT, longtext[:i]), (self.DIFF_EQUAL, shorttext),
                     (self.DIFF_INSERT, longtext[i + len(shorttext):])]
            # Swap insertions for deletions if diff is reversed.
            if len(text1) > len(text2):
                diffs[0] = (self.DIFF_DELETE, diffs[0][1])
                diffs[2] = (self.DIFF_DELETE, diffs[2][1])
            return diffs

        if len(shorttext) == 1:
            # Single character string.
            # After the previous speedup, the character can't be an equality.
            return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

        # Check to see if the problem can be split in two.
        hm = self.diff_halfMatch(text1, text2)
        if hm:
            # A half-match was found, sort out the return data.
            (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
            # Send both pairs off for separate processing.
            diffs_a = self.diff_main(text1_a, text2_a, checklines, deadline)
            diffs_b = self.diff_main(text1_b, text2_b, checklines, deadline)
            # Merge the results.
            return diffs_a + [(self.DIFF_EQUAL, mid_common)] + diffs_b

        if checklines and len(text1) > 100 and len(text2) > 100:
            return self.diff_lineMode(text1, text2, deadline)

        return self.diff_bisect(text1, text2, deadline)

    def diff_lineMode(self, text1, text2, deadline):
        """Do a quick line-level diff on both strings, then rediff the parts for
          greater accuracy.
          This speedup can produce non-minimal diffs.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          deadline: Time when the diff should be complete by.

        Returns:
          Array of changes.
        """

        # Scan the text on a line-by-line basis first.
        (text1, text2, linearray) = self.diff_linesToChars(text1, text2)

        diffs = self.diff_main(text1, text2, False, deadline)

        # Convert the diff back to original text.
        self.diff_charsToLines(diffs, linearray)
        # Eliminate freak matches (e.g. blank lines)
        self.diff_cleanupSemantic(diffs)

        # Rediff any replacement blocks, this time character-by-character.
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

    def diff_bisect(self, text1, text2, deadline):
        """Find the 'middle snake' of a diff, split the problem in two
          and return the recursively constructed diff.
          See Myers 1986 paper: An O(ND) Difference Algorithm and Its Variations.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          deadline: Time at which to bail if not yet complete.

        Returns:
          Array of diff tuples.
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
                            return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

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
                            return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

        # Diff took too long and hit the deadline or
        # number of diffs equals number of characters, no commonality at all.
        return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

    def diff_bisectSplit(self, text1, text2, x, y, deadline):
        """Given the location of the 'middle snake', split the diff in two parts
        and recurse.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          x: Index of split point in text1.
          y: Index of split point in text2.
          deadline: Time at which to bail if not yet complete.

        Returns:
          Array of diff tuples.
        """
        text1a = text1[:x]
        text2a = text2[:y]
        text1b = text1[x:]
        text2b = text2[y:]

        # Compute both diffs serially.
        diffs = self.diff_main(text1a, text2a, False, deadline)
        diffsb = self.diff_main(text1b, text2b, False, deadline)

        return diffs + diffsb

    @staticmethod
    def diff_linesToChars(text1, text2):
        """Split two texts into an array of strings.  Reduce the texts to a string
        of hashes where each Unicode character represents one line.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          Three element tuple, containing the encoded text1, the encoded text2 and
          the array of unique strings.  The zeroth element of the array of unique
          strings is intentionally blank.
        """
        lineArray = []  # e.g. lineArray[4] == "Hello\n"
        lineHash = {}  # e.g. lineHash["Hello\n"] == 4

        # "\x00" is a valid character, but various debuggers don't like it.
        # So we'll insert a junk entry to avoid generating a null character.
        lineArray.append('')

        def diff_linesToCharsMunge(text):
            """Split a text into an array of strings.  Reduce the texts to a string
            of hashes where each Unicode character represents one line.
            Modifies linearray and linehash through being a closure.

            Args:
              text: String to encode.

            Returns:
              Encoded string.
            """
            chars = []
            # Walk the text, pulling out a substring for each line.
            # text.split('\n') would would temporarily double our memory footprint.
            # Modifying text would create many large strings to garbage collect.
            lineStart = 0
            lineEnd = -1
            while lineEnd < len(text) - 1:
                lineEnd = text.find('\n', lineStart)
                if lineEnd == -1:
                    lineEnd = len(text) - 1
                line = text[lineStart:lineEnd + 1]
                lineStart = lineEnd + 1

                if line in lineHash:
                    chars.append(chr(lineHash[line]))
                else:
                    lineArray.append(line)
                    lineHash[line] = len(lineArray) - 1
                    chars.append(chr(len(lineArray) - 1))
            return "".join(chars)

        chars1 = diff_linesToCharsMunge(text1)
        chars2 = diff_linesToCharsMunge(text2)
        return chars1, chars2, lineArray

    @staticmethod
    def diff_charsToLines(diffs, lineArray):
        """Rehydrate the text in a diff from a string of line hashes to real lines
        of text.

        Args:
          diffs: Array of diff tuples.
          lineArray: Array of unique strings.
        """
        for x in range(len(diffs)):
            text = []
            for char in diffs[x][1]:
                text.append(lineArray[ord(char)])
            diffs[x] = (diffs[x][0], "".join(text))

    @staticmethod
    def diff_commonPrefix(text1, text2):
        """Determine the common prefix of two strings.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          The number of characters common to the start of each string.
        """
        # Quick check for common null cases.
        if not text1 or not text2 or text1[0] != text2[0]:
            return 0
        # Binary search.
        # Performance analysis: http://neil.fraser.name/news/2007/10/09/
        pointermin = 0
        pointermax = min(len(text1), len(text2))
        pointermid = pointermax
        pointerstart = 0
        while pointermin < pointermid:
            if text1[pointerstart:pointermid] == text2[pointerstart:pointermid]:
                pointermin = pointermid
                pointerstart = pointermin
            else:
                pointermax = pointermid
            pointermid = (pointermax - pointermin) // 2 + pointermin
        return pointermid

    @staticmethod
    def diff_commonSuffix(text1, text2):
        """Determine the common suffix of two strings.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          The number of characters common to the end of each string.
        """
        # Quick check for common null cases.
        if not text1 or not text2 or text1[-1] != text2[-1]:
            return 0
        # Binary search.
        # Performance analysis: http://neil.fraser.name/news/2007/10/09/
        pointermin = 0
        pointermax = min(len(text1), len(text2))
        pointermid = pointermax
        pointerend = 0
        while pointermin < pointermid:
            if (text1[-pointermid:len(text1) - pointerend] ==
                    text2[-pointermid:len(text2) - pointerend]):
                pointermin = pointermid
                pointerend = pointermin
            else:
                pointermax = pointermid
            pointermid = (pointermax - pointermin) // 2 + pointermin
        return pointermid

    @staticmethod
    def diff_commonOverlap(text1, text2):
        """Determine if the suffix of one string is the prefix of another.

        Args:
          text1 First string.
          text2 Second string.

        Returns:
          The number of characters common to the end of the first
          string and the start of the second string.
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

    def diff_halfMatch(self, text1, text2):
        """Do the two texts share a substring which is at least half the length of
        the longer text?
        This speedup can produce non-minimal diffs.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          Five element Array, containing the prefix of text1, the suffix of text1,
          the prefix of text2, the suffix of text2 and the common middle.  Or None
          if there was no match.
        """
        if self.Diff_Timeout <= 0:
            # Don't risk returning a non-optimal diff if we have unlimited time.
            return None
        if len(text1) > len(text2):
            (longtext, shorttext) = (text1, text2)
        else:
            (shorttext, longtext) = (text1, text2)
        if len(longtext) < 4 or len(shorttext) * 2 < len(longtext):
            return None  # Pointless.

        def diff_halfMatchI(longtext, shorttext, i):
            """Does a substring of shorttext exist within longtext such that the
            substring is at least half the length of longtext?
            Closure, but does not reference any external variables.

            Args:
              longtext: Longer string.
              shorttext: Shorter string.
              i: Start index of quarter length substring within longtext.

            Returns:
              Five element Array, containing the prefix of longtext, the suffix of
              longtext, the prefix of shorttext, the suffix of shorttext and the
              common middle.  Or None if there was no match.
            """
            seed = longtext[i:i + len(longtext) // 4]
            best_common = ''
            j = shorttext.find(seed)
            best_longtext_a = 0
            best_longtext_b = 0
            best_shorttext_a = 0
            best_shorttext_b = 0
            while j != -1:
                prefixLength = self.diff_commonPrefix(longtext[i:], shorttext[j:])
                suffixLength = self.diff_commonSuffix(longtext[:i], shorttext[:j])
                if len(best_common) < suffixLength + prefixLength:
                    best_common = shorttext[j - suffixLength:j] + shorttext[j:j + prefixLength]
                    best_longtext_a = longtext[:i - suffixLength]
                    best_longtext_b = longtext[i + prefixLength:]
                    best_shorttext_a = shorttext[:j - suffixLength]
                    best_shorttext_b = shorttext[j + prefixLength:]
                j = shorttext.find(seed, j + 1)

            if len(best_common) * 2 >= len(longtext):
                return best_longtext_a, best_longtext_b, best_shorttext_a, best_shorttext_b, best_common
            else:
                return None

        # First check if the second quarter is the seed for a half-match.
        hm1 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 3) // 4)
        # Check again based on the third quarter.
        hm2 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 1) // 2)
        if not hm1 and not hm2:
            return None
        elif not hm2:
            hm = hm1
        elif not hm1:
            hm = hm2
        else:
            # Both matched.  Select the longest.
            if len(hm1[4]) > len(hm2[4]):
                hm = hm1
            else:
                hm = hm2

        # A half-match was found, sort out the return data.
        if len(text1) > len(text2):
            (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
        else:
            (text2_a, text2_b, text1_a, text1_b, mid_common) = hm
        return text1_a, text1_b, text2_a, text2_b, mid_common

    def diff_cleanupSemantic(self, diffs):
        """Reduce the number of edits by eliminating semantically trivial
        equalities.

        Args:
          diffs: Array of diff tuples.
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        lastequality = None  # Always equal to diffs[equalities[-1]][1]
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
                lastequality = diffs[pointer][1]
            else:  # An insertion or deletion.
                if diffs[pointer][0] == self.DIFF_INSERT:
                    length_insertions2 += len(diffs[pointer][1])
                else:
                    length_deletions2 += len(diffs[pointer][1])
                # Eliminate an equality that is smaller or equal to the edits on both
                # sides of it.
                if (lastequality and (len(lastequality) <=
                                      max(length_insertions1, length_deletions1)) and
                        (len(lastequality) <= max(length_insertions2, length_deletions2))):
                    # Duplicate record.
                    diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
                    # Change second copy to insert.
                    diffs[equalities[-1] + 1] = (self.DIFF_INSERT,
                                                 diffs[equalities[-1] + 1][1])
                    # Throw away the equality we just deleted.
                    equalities.pop()
                    # Throw away the previous equality (it needs to be reevaluated).
                    if len(equalities):
                        equalities.pop()
                    if len(equalities):
                        pointer = equalities[-1]
                    else:
                        pointer = -1
                    # Reset the counters.
                    length_insertions1, length_deletions1 = 0, 0
                    length_insertions2, length_deletions2 = 0, 0
                    lastequality = None
                    changes = True
            pointer += 1

        # Normalize the diff.
        if changes:
            self.diff_cleanupMerge(diffs)
        self.diff_cleanupSemanticLossless(diffs)

        # Find any overlaps between deletions and insertions.
        # e.g: <del>abcxxx</del><ins>xxxdef</ins>
        #   -> <del>abc</del>xxx<ins>def</ins>
        # e.g: <del>xxxabc</del><ins>defxxx</ins>
        #   -> <ins>def</ins>xxx<del>abc</del>
        # Only extract an overlap if it is as big as the edit ahead or behind it.
        pointer = 1
        while pointer < len(diffs):
            if diffs[pointer - 1][0] == self.DIFF_DELETE and diffs[pointer][0] == self.DIFF_INSERT:
                deletion = diffs[pointer - 1][1]
                insertion = diffs[pointer][1]
                overlap_length1 = self.diff_commonOverlap(deletion, insertion)
                overlap_length2 = self.diff_commonOverlap(insertion, deletion)
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

    def diff_cleanupSemanticLossless(self, diffs):
        """Look for single edits surrounded on both sides by equalities
        which can be shifted sideways to align the edit to a word boundary.
        e.g: The c<ins>at c</ins>ame. -> The <ins>cat </ins>came.

        Args:
          diffs: Array of diff tuples.
        """

        def diff_cleanupSemanticScore(one, two):
            """Given two strings, compute a score representing whether the
            internal boundary falls on logical boundaries.
            Scores range from 6 (best) to 0 (worst).
            Closure, but does not reference any external variables.

            Args:
              one: First string.
              two: Second string.

            Returns:
              The score.
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
            nonAlphaNumeric1 = not char1.isalnum()
            nonAlphaNumeric2 = not char2.isalnum()
            whitespace1 = nonAlphaNumeric1 and char1.isspace()
            whitespace2 = nonAlphaNumeric2 and char2.isspace()
            lineBreak1 = whitespace1 and (char1 == "\r" or char1 == "\n")
            lineBreak2 = whitespace2 and (char2 == "\r" or char2 == "\n")
            blankLine1 = lineBreak1 and self.BLANKLINEEND.search(one)
            blankLine2 = lineBreak2 and self.BLANKLINESTART.match(two)

            if blankLine1 or blankLine2:
                # Five points for blank lines.
                return 5
            elif lineBreak1 or lineBreak2:
                # Four points for line breaks.
                return 4
            elif nonAlphaNumeric1 and not whitespace1 and whitespace2:
                # Three points for end of sentences.
                return 3
            elif whitespace1 or whitespace2:
                # Two points for whitespace.
                return 2
            elif nonAlphaNumeric1 or nonAlphaNumeric2:
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
                commonOffset = self.diff_commonSuffix(equality1, edit)
                if commonOffset:
                    commonString = edit[-commonOffset:]
                    equality1 = equality1[:-commonOffset]
                    edit = commonString + edit[:-commonOffset]
                    equality2 = commonString + equality2

                # Second, step character by character right, looking for the best fit.
                bestEquality1 = equality1
                bestEdit = edit
                bestEquality2 = equality2
                bestScore = (diff_cleanupSemanticScore(equality1, edit) + diff_cleanupSemanticScore(edit, equality2))
                while edit and equality2 and edit[0] == equality2[0]:
                    equality1 += edit[0]
                    edit = edit[1:] + equality2[0]
                    equality2 = equality2[1:]
                    score = (diff_cleanupSemanticScore(equality1, edit) + diff_cleanupSemanticScore(edit, equality2))
                    # The >= encourages trailing rather than leading whitespace on edits.
                    if score >= bestScore:
                        bestScore = score
                        bestEquality1 = equality1
                        bestEdit = edit
                        bestEquality2 = equality2

                if diffs[pointer - 1][1] != bestEquality1:
                    # We have an improvement, save it back to the diff.
                    if bestEquality1:
                        diffs[pointer - 1] = (diffs[pointer - 1][0], bestEquality1)
                    else:
                        del diffs[pointer - 1]
                        pointer -= 1
                    diffs[pointer] = (diffs[pointer][0], bestEdit)
                    if bestEquality2:
                        diffs[pointer + 1] = (diffs[pointer + 1][0], bestEquality2)
                    else:
                        del diffs[pointer + 1]
                        pointer -= 1
            pointer += 1

    # Define some regex patterns for matching boundaries.
    BLANKLINEEND = compile(r"\n\r?\n$")
    BLANKLINESTART = compile(r"^\r?\n\r?\n")

    def diff_cleanupEfficiency(self, diffs):
        """Reduce the number of edits by eliminating operationally trivial
        equalities.

        Args:
          diffs: Array of diff tuples.
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        lastequality = None  # Always equal to diffs[equalities[-1]][1]
        pointer = 0  # Index of current position.
        pre_ins = False  # Is there an insertion operation before the last equality.
        pre_del = False  # Is there a deletion operation before the last equality.
        post_ins = False  # Is there an insertion operation after the last equality.
        post_del = False  # Is there a deletion operation after the last equality.
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
                if (len(diffs[pointer][1]) < self.Diff_EditCost and
                        (post_ins or post_del)):
                    # Candidate found.
                    equalities.append(pointer)
                    pre_ins = post_ins
                    pre_del = post_del
                    lastequality = diffs[pointer][1]
                else:
                    # Not a candidate, and can never become one.
                    equalities = []
                    lastequality = None

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

                if lastequality and ((pre_ins and pre_del and post_ins and post_del) or
                                     ((len(lastequality) < self.Diff_EditCost / 2) and
                                      (pre_ins + pre_del + post_ins + post_del) == 3)):
                    # Duplicate record.
                    diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
                    # Change second copy to insert.
                    diffs[equalities[-1] + 1] = (self.DIFF_INSERT,
                                                 diffs[equalities[-1] + 1][1])
                    equalities.pop()  # Throw away the equality we just deleted.
                    lastequality = None
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
            self.diff_cleanupMerge(diffs)

    def diff_cleanupMerge(self, diffs):
        """Reorder and merge like edit sections.  Merge equalities.
        Any edit section can move as long as it doesn't cross an equality.

        Args:
          diffs: Array of diff tuples.
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
                        # Factor out any common prefixies.
                        commonlength = self.diff_commonPrefix(text_insert, text_delete)
                        if commonlength != 0:
                            x = pointer - count_delete - count_insert - 1
                            if x >= 0 and diffs[x][0] == self.DIFF_EQUAL:
                                diffs[x] = (diffs[x][0], diffs[x][1] + text_insert[:commonlength])
                            else:
                                diffs.insert(0, (self.DIFF_EQUAL, text_insert[:commonlength]))
                                pointer += 1
                            text_insert = text_insert[commonlength:]
                            text_delete = text_delete[commonlength:]
                        # Factor out any common suffixies.
                        commonlength = self.diff_commonSuffix(text_insert, text_delete)
                        if commonlength != 0:
                            diffs[pointer] = (diffs[pointer][0], text_insert[-commonlength:] + diffs[pointer][1])
                            text_insert = text_insert[:-commonlength]
                            text_delete = text_delete[:-commonlength]
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
            self.diff_cleanupMerge(diffs)

    def diff_xIndex(self, diffs, loc):
        """loc is a location in text1, compute and return the equivalent location
        in text2.  e.g. "The cat" vs "The big cat", 1->1, 5->8

        Args:
          diffs: Array of diff tuples.
          loc: Location within text1.

        Returns:
          Location within text2.
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

    def diff_prettyHtml(self, diffs):
        """Convert a diff array into a pretty HTML report.

        Args:
          diffs: Array of diff tuples.

        Returns:
          HTML representation.
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

    def diff_text1(self, diffs):
        """Compute and return the source text (all equalities and deletions).

        Args:
          diffs: Array of diff tuples.

        Returns:
          Source text.
        """
        text = []
        for (op, data) in diffs:
            if op != self.DIFF_INSERT:
                text.append(data)
        return "".join(text)

    def diff_text2(self, diffs):
        """Compute and return the destination text (all equalities and insertions).

        Args:
          diffs: Array of diff tuples.

        Returns:
          Destination text.
        """
        text = []
        for (op, data) in diffs:
            if op != self.DIFF_DELETE:
                text.append(data)
        return "".join(text)

    def diff_levenshtein(self, diffs):
        """Compute the Levenshtein distance; the number of inserted, deleted or
        substituted characters.

        Args:
          diffs: Array of diff tuples.

        Returns:
          Number of changes.
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

    def diff_toDelta(self, diffs):
        """Crush the diff into an encoded string which describes the operations
        required to transform text1 into text2.
        E.g. =3\t-2\t+ing  -> Keep 3 chars, delete 2 chars, insert 'ing'.
        Operations are tab-separated.  Inserted text is escaped using %xx notation.

        Args:
          diffs: Array of diff tuples.

        Returns:
          Delta text.
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

    def diff_fromDelta(self, text1, delta):
        """Given the original text1, and an encoded string which describes the
        operations required to transform text1 into text2, compute the full diff.

        Args:
          text1: Source string for the diff.
          delta: Delta text.

        Returns:
          Array of diff tuples.

        Raises:
          ValueError: If invalid input.
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
                raise ValueError("Invalid diff operation in diff_fromDelta: " +
                                 token[0])
        if pointer != len(text1):
            raise ValueError(
                "Delta length (%d) does not equal source text length (%d)." %
                (pointer, len(text1)))
        return diffs

    #  MATCH FUNCTIONS

    def match_main(self, text, pattern, loc):
        """Locate the best instance of 'pattern' in 'text' near 'loc'.

        Args:
          text: The text to search.
          pattern: The pattern to search for.
          loc: The location to search around.

        Returns:
          Best match index or -1.
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
            match = self.match_bitap(text, pattern, loc)
            return match

    def match_bitap(self, text, pattern, loc):
        """Locate the best instance of 'pattern' in 'text' near 'loc' using the
        Bitap algorithm.

        Args:
          text: The text to search.
          pattern: The pattern to search for.
          loc: The location to search around.

        Returns:
          Best match index or -1.
        """
        # Python doesn't have a maxint limit, so ignore this check.
        # if self.Match_MaxBits != 0 and len(pattern) > self.Match_MaxBits:
        #  raise ValueError("Pattern too long for this application.")

        # Initialise the alphabet.
        s = self.match_alphabet(pattern)

        def match_bitapScore(e, x):
            """Compute and return the score for a match with e errors and x location.
            Accesses loc and pattern through being a closure.

            Args:
              e: Number of errors in match.
              x: Location of match.

            Returns:
              Overall score for match (0.0 = good, 1.0 = bad).
            """
            accuracy = float(e) / len(pattern)
            proximity = abs(loc - x)
            if not self.Match_Distance:
                # Dodge divide by zero error.
                return proximity and 1.0 or accuracy
            return accuracy + (proximity / float(self.Match_Distance))

        # Highest score beyond which we give up.
        score_threshold = self.Match_Threshold
        # Is there a nearby exact match? (speedup)
        best_loc = text.find(pattern, loc)
        if best_loc != -1:
            score_threshold = min(match_bitapScore(0, best_loc), score_threshold)
            # What about in the other direction? (speedup)
            best_loc = text.rfind(pattern, loc + len(pattern))
            if best_loc != -1:
                score_threshold = min(match_bitapScore(0, best_loc), score_threshold)

        # Initialise the bit arrays.
        matchmask = 1 << (len(pattern) - 1)
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
                if match_bitapScore(d, loc + bin_mid) <= score_threshold:
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
                    charMatch = 0
                else:
                    charMatch = s.get(text[j - 1], 0)
                if d == 0:  # First pass: exact match.
                    rd[j] = ((rd[j + 1] << 1) | 1) & charMatch
                else:  # Subsequent passes: fuzzy match.
                    tmp = (((rd[j + 1] << 1) | 1) & charMatch)
                    rd[j] = tmp | (((last_rd[j + 1] | last_rd[j]) << 1) | 1) | last_rd[j + 1]
                if rd[j] & matchmask:
                    score = match_bitapScore(d, j - 1)
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
            if match_bitapScore(d + 1, loc) > score_threshold:
                break
            last_rd = rd
        return best_loc

    @staticmethod
    def match_alphabet(pattern):
        """Initialise the alphabet for the Bitap algorithm.

        Args:
          pattern: The text to encode.

        Returns:
          Hash of character locations.
        """
        s = {}
        for char in pattern:
            s[char] = 0
        for i in range(len(pattern)):
            s[pattern[i]] |= 1 << (len(pattern) - i - 1)
        return s

    #  PATCH FUNCTIONS

    def patch_addContext(self, patch, text):
        """Increase the context until it is unique,
        but don't let the pattern expand beyond Match_MaxBits.

        Args:
          patch: The patch to grow.
          text: Source text.
        """
        if len(text) == 0:
            return
        pattern = text[patch.start2: patch.start2 + patch.length1]
        padding = 0

        # Look for the first and last matches of pattern in text.  If two different
        # matches are found, increase the pattern length.
        tmp = self.Match_MaxBits - self.Patch_Margin - self.Patch_Margin
        while text.find(pattern) != text.rfind(pattern) and (self.Match_MaxBits == 0 or len(pattern) < tmp):
            padding += self.Patch_Margin
            pattern = text[max(0, patch.start2 - padding):patch.start2 + patch.length1 + padding]
        # Add one chunk for good luck.
        padding += self.Patch_Margin

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

    def patch_make(self, a, b=None, c=None):
        """Compute a list of patches to turn text1 into text2.
        Use diffs if provided, otherwise compute it ourselves.
        There are four ways to call this function, depending on what data is
        available to the caller:
        Method 1:
        a = text1, b = text2
        Method 2:
        a = diffs
        Method 3 (optimal):
        a = text1, b = diffs
        Method 4 (deprecated, use method 3):
        a = text1, b = text2, c = diffs

        Args:
          a: text1 (methods 1,3,4) or Array of diff tuples for text1 to
              text2 (method 2).
          b: text2 (methods 1,4) or Array of diff tuples for text1 to
              text2 (method 3) or undefined (method 2).
          c: Array of diff tuples for text1 to text2 (method 4) or
              undefined (methods 1,2,3).

        Returns:
          Array of Patch objects.
        """

        if isinstance(a, str) and isinstance(b, str) and c is None:
            # Method 1: text1, text2
            # Compute diffs from text1 and text2.
            text1 = a
            diffs = self.diff_main(text1, b, True)
            if len(diffs) > 2:
                self.diff_cleanupSemantic(diffs)
                self.diff_cleanupEfficiency(diffs)
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
        patch = patch_obj()
        char_count1 = 0  # Number of characters into the text1 string.
        char_count2 = 0  # Number of characters into the text2 string.
        prepatch_text = text1  # Recreate the patches to determine context info.
        postpatch_text = text1
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
                postpatch_text = (postpatch_text[:char_count2] + diff_text + postpatch_text[char_count2:])
            elif diff_type == self.DIFF_DELETE:
                # Deletion.
                patch.length1 += len(diff_text)
                patch.diffs.append(diffs[x])
                postpatch_text = (postpatch_text[:char_count2] + postpatch_text[char_count2 + len(diff_text):])
            elif (diff_type == self.DIFF_EQUAL and len(diff_text) <= 2 * self.Patch_Margin and len(patch.diffs) != 0
                  and len(diffs) != x + 1):
                # Small equality inside a patch.
                patch.diffs.append(diffs[x])
                patch.length1 += len(diff_text)
                patch.length2 += len(diff_text)

            if diff_type == self.DIFF_EQUAL and len(diff_text) >= 2 * self.Patch_Margin:
                # Time for a new patch.
                if len(patch.diffs) != 0:
                    self.patch_addContext(patch, prepatch_text)
                    patches.append(patch)
                    patch = patch_obj()
                    # Unlike Unidiff, our patch lists have a rolling context.
                    # http://code.google.com/p/google-diff-match-patch/wiki/Unidiff
                    # Update prepatch text & pos to reflect the application of the
                    # just completed patch.
                    prepatch_text = postpatch_text
                    char_count1 = char_count2

            # Update the current character count.
            if diff_type != self.DIFF_INSERT:
                char_count1 += len(diff_text)
            if diff_type != self.DIFF_DELETE:
                char_count2 += len(diff_text)

        # Pick up the leftover patch if not empty.
        if len(patch.diffs) != 0:
            self.patch_addContext(patch, prepatch_text)
            patches.append(patch)
        return patches

    @staticmethod
    def patch_deepCopy(patches):
        """Given an array of patches, return another array that is identical.

        Args:
          patches: Array of Patch objects.

        Returns:
          Array of Patch objects.
        """
        patchesCopy = []
        for patch in patches:
            patchCopy = patch_obj()
            # No need to deep copy the tuples since they are immutable.
            patchCopy.diffs = patch.diffs[:]
            patchCopy.start1 = patch.start1
            patchCopy.start2 = patch.start2
            patchCopy.length1 = patch.length1
            patchCopy.length2 = patch.length2
            patchesCopy.append(patchCopy)
        return patchesCopy

    def patch_apply(self, patches, text):
        """Merge a set of patches onto the text.  Return a patched text, as well
        as a list of true/false values indicating which patches were applied.

        Args:
          patches: Array of Patch objects.
          text: Old text.

        Returns:
          Two element Array, containing the new text and an array of boolean values.
        """
        if not patches:
            return text, []

        # Deep copy the patches so that no changes are made to originals.
        patches = self.patch_deepCopy(patches)

        nullPadding = self.patch_addPadding(patches)
        text = nullPadding + text + nullPadding
        self.patch_splitMax(patches)

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
            if len(text1) > self.Match_MaxBits:
                # patch_splitMax will only provide an oversized pattern in the case of
                # a monster delete.
                start_loc = self.match_main(text, text1[:self.Match_MaxBits], expected_loc)
                if start_loc != -1:
                    end_loc = self.match_main(text, text1[-self.Match_MaxBits:], expected_loc
                                              + len(text1) - self.Match_MaxBits)
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
                    text2 = text[start_loc: end_loc + self.Match_MaxBits]
                if text1 == text2:
                    # Perfect match, just shove the replacement text in.
                    text = (text[:start_loc] + self.diff_text2(patch.diffs) + text[start_loc + len(text1):])
                else:
                    # Imperfect match.
                    # Run a diff to get a framework of equivalent indices.
                    diffs = self.diff_main(text1, text2, False)
                    if len(text1) > self.Match_MaxBits \
                            and self.diff_levenshtein(diffs) / float(len(text1)) > self.Patch_DeleteThreshold:
                        # The end points match, but the content is unacceptably bad.
                        results[-1] = False
                    else:
                        self.diff_cleanupSemanticLossless(diffs)
                        index1 = 0
                        for (op, data) in patch.diffs:
                            if op != self.DIFF_EQUAL:
                                index2 = self.diff_xIndex(diffs, index1)
                            if op == self.DIFF_INSERT:  # Insertion
                                text = text[:start_loc + index2] + data + text[start_loc + index2:]
                            elif op == self.DIFF_DELETE:  # Deletion
                                text = text[:start_loc + index2] + \
                                       text[start_loc + self.diff_xIndex(diffs, index1 + len(data)):]
                            if op != self.DIFF_DELETE:
                                index1 += len(data)
        # Strip the padding off.
        text = text[len(nullPadding):-len(nullPadding)]
        return text, results

    def patch_addPadding(self, patches):
        """Add some padding on text start and end so that edges can match
        something.  Intended to be called only from within patch_apply.

        Args:
          patches: Array of Patch objects.

        Returns:
          The padding string added to each side.
        """
        paddingLength = self.Patch_Margin
        nullPadding = ""
        for x in range(1, paddingLength + 1):
            nullPadding += chr(x)

        # Bump all the patches forward.
        for patch in patches:
            patch.start1 += paddingLength
            patch.start2 += paddingLength

        # Add some padding on start of first diff.
        patch = patches[0]
        diffs = patch.diffs
        if not diffs or diffs[0][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.insert(0, (self.DIFF_EQUAL, nullPadding))
            patch.start1 -= paddingLength  # Should be 0.
            patch.start2 -= paddingLength  # Should be 0.
            patch.length1 += paddingLength
            patch.length2 += paddingLength
        elif paddingLength > len(diffs[0][1]):
            # Grow first equality.
            extraLength = paddingLength - len(diffs[0][1])
            newText = nullPadding[len(diffs[0][1]):] + diffs[0][1]
            diffs[0] = (diffs[0][0], newText)
            patch.start1 -= extraLength
            patch.start2 -= extraLength
            patch.length1 += extraLength
            patch.length2 += extraLength

        # Add some padding on end of last diff.
        patch = patches[-1]
        diffs = patch.diffs
        if not diffs or diffs[-1][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.append((self.DIFF_EQUAL, nullPadding))
            patch.length1 += paddingLength
            patch.length2 += paddingLength
        elif paddingLength > len(diffs[-1][1]):
            # Grow last equality.
            extraLength = paddingLength - len(diffs[-1][1])
            newText = diffs[-1][1] + nullPadding[:extraLength]
            diffs[-1] = (diffs[-1][0], newText)
            patch.length1 += extraLength
            patch.length2 += extraLength

        return nullPadding

    def patch_splitMax(self, patches):
        """Look through the patches and break up any which are longer than the
        maximum limit of the match algorithm.
        Intended to be called only from within patch_apply.

        Args:
          patches: Array of Patch objects.
        """
        patch_size = self.Match_MaxBits
        if patch_size == 0:
            # Python has the option of not splitting strings due to its ability
            # to handle integers of arbitrary precision.
            return
        for x in range(len(patches)):
            if patches[x].length1 <= patch_size:
                continue
            bigpatch = patches[x]
            # Remove the big old patch.
            del patches[x]
            x -= 1
            start1 = bigpatch.start1
            start2 = bigpatch.start2
            precontext = ''
            while len(bigpatch.diffs) != 0:
                # Create one of several smaller patches.
                patch = patch_obj()
                empty = True
                patch.start1 = start1 - len(precontext)
                patch.start2 = start2 - len(precontext)
                if precontext:
                    patch.length1 = patch.length2 = len(precontext)
                    patch.diffs.append((self.DIFF_EQUAL, precontext))

                while len(bigpatch.diffs) != 0 and patch.length1 < patch_size - self.Patch_Margin:
                    (diff_type, diff_text) = bigpatch.diffs[0]
                    if diff_type == self.DIFF_INSERT:
                        # Insertions are harmless.
                        patch.length2 += len(diff_text)
                        start2 += len(diff_text)
                        patch.diffs.append(bigpatch.diffs.pop(0))
                        empty = False
                    elif (diff_type == self.DIFF_DELETE and len(patch.diffs) == 1
                          and patch.diffs[0][0] == self.DIFF_EQUAL and len(diff_text) > 2 * patch_size):

                        # This is a large deletion.  Let it pass in one chunk.
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        empty = False
                        patch.diffs.append((diff_type, diff_text))
                        del bigpatch.diffs[0]
                    else:
                        # Deletion or equality.  Only take as much as we can stomach.
                        diff_text = diff_text[:patch_size - patch.length1 - self.Patch_Margin]
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        if diff_type == self.DIFF_EQUAL:
                            patch.length2 += len(diff_text)
                            start2 += len(diff_text)
                        else:
                            empty = False

                        patch.diffs.append((diff_type, diff_text))
                        if diff_text == bigpatch.diffs[0][1]:
                            del bigpatch.diffs[0]
                        else:
                            bigpatch.diffs[0] = (bigpatch.diffs[0][0], bigpatch.diffs[0][1][len(diff_text):])

                # Compute the head context for the next patch.
                precontext = self.diff_text2(patch.diffs)
                precontext = precontext[-self.Patch_Margin:]
                # Append the end context for this patch.
                postcontext = self.diff_text1(bigpatch.diffs)[:self.Patch_Margin]
                if postcontext:
                    patch.length1 += len(postcontext)
                    patch.length2 += len(postcontext)
                    if len(patch.diffs) != 0 and patch.diffs[-1][0] == self.DIFF_EQUAL:
                        patch.diffs[-1] = (self.DIFF_EQUAL, patch.diffs[-1][1] + postcontext)
                    else:
                        patch.diffs.append((self.DIFF_EQUAL, postcontext))

                if not empty:
                    x += 1
                    patches.insert(x, patch)

    @staticmethod
    def patch_toText(patches):
        """Take a list of patches and return a textual representation.

        Args:
          patches: Array of Patch objects.

        Returns:
          Text representation of patches.
        """
        text = []
        for patch in patches:
            text.append(str(patch))
        return "".join(text)

    def patch_fromText(self, textline):
        """Parse a textual representation of patches and return a list of patch
        objects.

        Args:
          textline: Text representation of patches.

        Returns:
          Array of Patch objects.

        Raises:
          ValueError: If invalid input.
        """
        patches = []
        if not textline:
            return patches
        text = textline.split('\n')
        while len(text) != 0:
            m = match("^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@$", text[0])
            if not m:
                raise ValueError("Invalid patch string: " + text[0])
            patch = patch_obj()
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


# noinspection PyPep8Naming,PyShadowingNames
class patch_obj:
    """Class representing one patch operation.
    """

    def __init__(self):
        """Initializes with an empty list of diffs.
        """
        self.diffs = []
        self.start1 = None
        self.start2 = None
        self.length1 = 0
        self.length2 = 0

    def __str__(self):
        """Emmulate GNU diff's format.
        Header: @@ -382,8 +481,9 @@
        Indicies are printed as 1-based, not 0-based.

        Returns:
          The GNU diff string.
        """
        if self.length1 == 0:
            coords1 = str(self.start1) + ",0"
        elif self.length1 == 1:
            coords1 = str(self.start1 + 1)
        else:
            coords1 = str(self.start1 + 1) + "," + str(self.length1)
        if self.length2 == 0:
            coords2 = str(self.start2) + ",0"
        elif self.length2 == 1:
            coords2 = str(self.start2 + 1)
        else:
            coords2 = str(self.start2 + 1) + "," + str(self.length2)
        text = ["@@ -", coords1, " +", coords2, " @@\n"]

        # Escape the body of the patch with %xx notation.
        for (op, data) in self.diffs:
            if op == diff_match_patch.DIFF_INSERT:
                text.append("+")
            elif op == diff_match_patch.DIFF_DELETE:
                text.append("-")
            elif op == diff_match_patch.DIFF_EQUAL:
                text.append(" ")
            # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
            data = data.encode("utf-8")
            text.append(quote(data, "!~*'();/?:@&=+$,# ") + "\n")

        return "".join(text)


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


logging.basicConfig(filename=log_filename, level=LOGGING_LEVEL, format=LOGGING_FORMAT, filemode="w")


class LogWrapper(QObject, logging.Logger):
    """Wrapper class for logging.logger"""

    custom_signal = pyqtSignal(str)

    def __init__(self, name):
        super(LogWrapper, self).__init__(name=name)

    def error(self, msg, *args, **kwargs):
        """

        :param msg:
        :param args:
        :param kwargs:
        :return:
        """

        self.custom_signal.emit('ERROR: ' + msg)
        super(LogWrapper, self).error(msg)

    def info(self, msg, *args, **kwargs):
        """

        :param msg:
        :param args:
        :param kwargs:
        :return:
        """
        self.custom_signal.emit('INFO: ' + msg)
        super(LogWrapper, self).info(msg)

    def debug(self, msg, *args, **kwargs):
        """

        :param msg:
        :param args:
        :param kwargs:
        :return:
        """

        self.custom_signal.emit('DEBUG: ' + msg)
        super(LogWrapper, self).debug(msg)

    def critical(self, msg, *args, **kwargs):
        """

        :param msg:
        :param args:
        :param kwargs:
        :return:
        """

        self.custom_signal.emit('FATAL: ' + msg)
        super(LogWrapper, self).critical(msg)

    def warning(self, msg, *args, **kwargs):
        """

        :param msg:
        :param args:
        :param kwargs:
        :return:
        """

        self.custom_signal.emit('WARNING: ' + msg)
        super(LogWrapper, self).critical(msg)


def message_to_user(message: str, parent=None):
    """

    :param message:
    :param parent:
    :return:
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
    """
    Global constants for the gui modes
    """
    GUI_NONE = 1 << 1                  # initial or reset mode
    GUI_SELECT = 1 << 2           # gui set to selection mode
    GUI_COMPARE = 1 << 3          # gui set to compare, with a base model and a compare model


class ModelState(QObject):
    """
    Global constants for the gui modes
    """
    BASE_FILE = 1 << 4        # indicate that the base model is a single file
    BASE_REPO = 1 << 5        # indicate that the base model is a repository (folder structure)
    COMP_FILE = 1 << 6        # indicate that the base model is a single file
    COMP_REPO = 1 << 7        # indicate that the base model is a repository (folder structure)
    BASE_LOADED = 1 << 8      # indicate that the base model is loaded
    COMP_LOADED = 1 << 9      # indicate that the compare model is loaded
    BASE_UNLOAD = 1 << 10     # indicate that the base model must unload
    COMP_UNLOAD = 1 << 11     # indicate that the compare model is unload


class SourceType(QObject):
    """
    Global constants for the gui modes
    """
    FILE = ModelState.BASE_FILE | ModelState.COMP_FILE
    REPO = ModelState.BASE_REPO | ModelState.COMP_REPO


class ViewType(QObject):
    """
    Global constants for the gui modes
    """
    SCRIPT_VIEW = 1 << 12
    DENODO_VIEW = 1 << 13
    DEPEND_VIEW = 1 << 14


class CodeView(QObject):
    """
    Global constants for the gui modes
    """
    ORIGINAL_CODE = 1 << 15
    COMPARE_CODE = 1 << 16
    DIFF_CODE = 1 << 17


class Pane(QObject):
    """
    Global constants for the pane modes
    """
    LEFT = 1 << 18
    RIGHT = 1 << 19


class ItemProperties(QObject):
    """
    Role identifiers
    """
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
    """
    Debug function
    :param role:
    :return:
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

    :param item_color:
    :return:
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
    :type mode: int
    :return: a human readable string with flags
    :rtype: str
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

    :return: the list as Iterator
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
    """
    Returns a html page
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

diff_engine = diff_match_patch()
diff_engine.Diff_Timeout = 2
diff_engine.Match_Threshold = 0.0
diff_engine.Patch_DeleteThreshold = 0.0
diff_engine.Match_MaxBits = 0


def load_model_from_file(file: Path, new_mode: int, root_item, bar: QStatusBar, icons: dict, logger):
    """Loads a single .vql file into the VqlModel instance.

    :param file: path of the file to bew loaded in
    :type file: Path
    :param new_mode: either BASE_FILE or COMP_FILE
    :type new_mode: int
    :param root_item: RootItem
    :param bar:
    :param icons:
    :param logger:
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
    :param bar:
    :param icons:
    :param logger:
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

    :param file:
    :param logger:
    :return:
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
        super(TransOpenBase, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent):
        """
        Selector for the events
        :param event:
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
        """

        :param event:
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
        super(TransResetBase, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent):
        """
        Selector for the events
        :param event:
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
        """

        :param event:
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
        super(TransOpenCompare, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent):
        """
        Selector for the events
        :param event:
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
        """

        :param event:
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
        super(TransRemoveCompare, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent):
        """
        Selector for the events
        :param event:
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
        """

        :param event:
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
        super(TransResetAll, self).__init__(signal, source_state)
        self.app = _app
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent):
        """
        Selector for the events
        :param event:
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
        """

        :param event:
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
    """
    Base class for items in tree_model used in tree_views
    """
    BRANCH = 1
    LEAF = 2

    def __init__(self, class_type, parent=None, index: int=None):
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

    def changed(self):
        """

        :return:
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
        """

        :param parent:
        :return:
        """
        assert isinstance(parent, (TreeItem, type(None)))
        self.parent_item = parent
        if parent:
            self.parent_item.child_items.append(self)

    def take_children(self)->list:
        """

        :return:
        """
        temp = self.child_items
        self.child_items = list()
        return temp

    def add_children(self, new_children: list):
        """

        :param new_children:
        :return:
        """
        for child in new_children:
            assert isinstance(child, TreeItem)
            child.set_parent(self)
            self.child_items.append(child)

    def get_role_data(self, role, column: int):
        """

        :param role:
        :param column:
        :return:
        """
        if role in [DISPLAY, EDIT]:
            if column == 0:
                return self.name
            else:
                return self.column_data[column]
        elif role == COLOR:
            return QBrush(QColor(self.color))
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
            return self.tooltip
        elif role == ICON:
            return self.icon
        else:
            return NOTHING

    def set_role_data(self, role, column, value):
        """

        :param role:
        :param column:
        :param value:
        :return:
        """
        if role in [DISPLAY, EDIT]:
            if column == 0:
                self.column_data[column] = value
                self.name = value
        elif role == COLOR:
            self.color = str(value.color)
        elif role == CHECK:
            self.set_selected(False if value == UNCHECKED else True)
        elif role == TIP:
            self.tooltip = value
        else:
            return False
        return True

    def ancestors(self, tree_item):
        """

        :return:
        """
        if isinstance(tree_item, TreeItem) and not isinstance(tree_item, RootItem):
            parent_item = tree_item.parent_item
            yield parent_item
            yield from self.ancestors(parent_item)

    def descendants(self, tree_item):
        """

        :param tree_item:
        :return:
        """
        if isinstance(tree_item, TreeItem):
            for child in tree_item.child_items:
                yield child
                yield from self.descendants(child)

    def set_selected(self, select: bool):
        """

        :param select:
        :return:
        """
        self.selected = select
        self.tristate = False
        # if selected was chosen (True or False ) switch all children also
        for child in self.descendants(self):
            child.selected = select

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
        """
        reset item
        :return:
        """
        self.child_items = list()
        self.selected = True
        self.tristate = False

    def has_children(self):
        """

        :return:
        """
        return True if len(self.child_items) else False

    def child(self, row: int):
        """

        :param row:
        :return:
        """
        return self.child_items[row]

    def child_count(self)->int:
        """
        returns the count
        :return:
        """
        return len(self.child_items)

    def child_number(self)->int:
        """
        Returns the number this child has under the parent

        :return:
        """
        if self.parent_item and self.parent_item.has_children():
            return self.parent_item.child_items.index(self)
        else:
            return 0

    @staticmethod
    def get_child_index_by_name(child_items, name: str):
        """

        :param child_items:
        :param name:
        :return:
        """
        for i, child in enumerate(child_items):
            if child.name == name:
                return i
        return -1

    def column_count(self)->int:
        """

        :return:
        """
        if self.column_data:
            return len(self.column_data)
        else:
            return 0

    def set_column_data(self, column: int, value)->bool:
        """

        :param column:
        :param value:
        :return:
        """
        if 0 <= column < len(self.column_data):
            self.column_data[column] = value
            return True
        return False

    def insert_children(self, position: int, items: list)->bool:
        """

        :param position:
        :param items:
        :return:
        """
        if 0 <= position < len(self.child_items):
            for i, item in enumerate(items):
                self.child_items.insert(position + i, item)
            return True
        return False

    def insert_columns(self, position: int, columns: list)->bool:
        """

        :param position:
        :param columns:
        :return:
        """
        success = [False]
        if 0 <= position < len(self.column_data):
            success = [self.set_column_data(position + i, column) for i, column in enumerate(columns)]
            success.extend([child.insert_columns(position, columns) for child in self.child_items])
        if all(success):
            return True
        else:
            return False

    def remove_child(self, child):
        """

        :param child:
        :return:
        """
        self.child_items.remove(child)

    def remove_children(self, position: int, count: int)->bool:
        """

        :param position:
        :param count:
        :return:
        """
        if 0 <= position + count < len(self.child_items):
            for row in range(count):
                self.child_items.pop(position)
            return True
        return False

    def remove_columns(self, position: int, columns: int)->bool:
        """

        :param position:
        :param columns:
        :return:
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
        """
        rolls up the tree from the leaves
        :return:
        """
        if self.child_items:
            for item in self.child_items:
                item.clear()
        else:
            if self.parent_item:
                if self in self.parent_item.child_items:
                    self.parent_item.child_items.remove(self)


class ItemData:
    """
    Code item mode dependent data
    """

    def __init__(self, root_item):
        """
        Dict constructor with list of keys for indexing
        """

        self.denodo_path = Path()
        self.depend_path = Path()
        self.code = ''
        self.dependencies = list()
        self.dependees = list()
        self.dependee_parent = None
        self.dependees_tree = root_item


class CodeItem(TreeItem):
    """CodeItem class represents a .vql file with a single Denodo object.

    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget.
    Basically a bag for pieces of Denodo code.
    """
    headers = []

    def __init__(self, parent: TreeItem, name: str, index: int=None):
        """

        :param parent:
        :param name:
        :param index:
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
        self.base_data = ItemData(self)
        self.compare_data = ItemData(self)

    def object_type(self):
        """

        :return:
        """
        object_type = self.chapter.name[:-1] if self.chapter.name != 'DATABASE' else 'DATABASE'
        return object_type.capitalize()

    def get_child_index_by_name(self, name: str):
        """

        :param name:
        :return:
        """
        return super().get_child_index_by_name(self.child_items, self.name)

    def clear(self):
        """

        :return:
        """
        self.base_data = None
        self.compare_data = None
        self.column_data = None
        super().clear()

    def get_context_data(self, gui: int):
        """

        :param gui:
        :return:
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

        The main intel of this function is supplied by the global instance of the diff_match_patch.py engine
        maintained on Google. Here the engine is used on the two code pieces and a patch is calculated
        the patch is again inserted in the prettyHtml function of the engine and modded a bit
        The colors are similar to the usage in this tool
        to get new code (compare_code) from old code (code), remove red, add green

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
                diff_html = format_code(diff_engine.diff_prettyHtml(diff_patch))
                diff_html = diff_html.replace(diff_ins_indicator, new_diff_ins_indicator)
                diff_html = diff_html.replace(diff_del_indicator, new_diff_del_indicator)
            else:
                diff_html = format_code2(set_red(code))
        else:
            if compare_code:
                diff_html = format_code2(set_green(compare_code))

        return diff_html

    def get_file_path(self, folder: Path)->Path:
        """Get the file path for this code item.

        This function changes and slash, forward and backward into an underscore
        Warning: this can potentially be dangerous if two uniquely named objects
         turn out to have the same name after turning slashes to underscores.

        :param folder: the folder in which code item resides
        :type folder: Path
        :return: Path
        """

        file_name = folder / (self.name.replace('/', '_').replace('\\', '_') + '.vql')
        return file_name

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
        :type chapter_name: str
        :param code: the code to create the object
        :type code: str
        :return: The denodo path
        :rtype: Union[Path, None]
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
        The function constructs a unique object name in its code
        Each chapter has its own way of extracting the object name

        Warning: With newer versions of Denodo it should be checked if the structure they use is the same

        :param chapter_name: string with the name of the chapter it belongs to
        :type chapter_name: str
        :param code: string with code relating to one object in Denodo
        :type code: str
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
    It inherits from QTreeWidgetItem, so it can display in a QTreeWidget.
    """

    def __init__(self, name: str, parent: TreeItem=None):
        """Initializer of the class objects

        :param parent: reference to the parent or owner, this should be a VqlModel class (QTreeWidget)
        :type parent: Union[VqlModel, None, QTreeWidgetItem, Chapter]
        :param name: string name of the chapter
        :type name: str
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
        """

        :param name:
        :return:
        """
        return super().get_child_index_by_name(self.child_items, name)

    def clear(self):
        """

        :return:
        """
        self.code_items = None
        self.column_data = None
        super().clear()

    @staticmethod
    def make_header(chapter_name: str)->str:
        """Constructs a string that can be used to identify chapters in a Denodo exported database file.

        :param chapter_name: string with Chapter name
        :type chapter_name: str
        :return: The chapter Header
        :rtype: str
        """
        chapter_header = '# #######################################\n# ' \
                         + chapter_name + '\n# #######################################\n'
        return chapter_header

    def set_gui(self, gui: int):
        """Sets the Gui type (GUI_SELECT GUI_COMPARE) on the chapter and its children.

        :param gui: the new GUI type
        :type gui: int
        :return:None
        :rtype: None
        """
        self.gui = gui
        for code_item in self.code_items:
            code_item.set_gui(gui)

    def set_color_based_on_children(self):
        """

        :return:
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
        """Returns the combined Denodo code for a whole chapter.

        This function adds a chapter header, and only selected code items
        :param mode: either GUI_SELECT or GUI_COMPARE ; what code to return
        :type mode: int
        :param selected_only: Indicator is True if only selected items are requested
        :type selected_only: bool
        :return: string with code content
        :rtype: str
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
        """Returns data to write the part.log files.

        Returning two values: the file path for the part.log file and its content as a string.
        The content is a list of file paths pointing to the code items in this chapter.
        The part.log files are used in a repository to ensure the same order of execution.
        Only the selected code items are included.
        :param base_path: The base folder for the repo
        :type base_path:  Path
        :return: Two values, a file path and the content of the part.log file of this chapter
        :rtype: tuple Path, str
        """
        folder = base_path / self.name
        part_log_filepath = folder / LOG_FILE_NAME
        part_log = [str(code_item.get_file_path(folder)) for code_item in self.code_items if code_item.selected]
        part_log_content = '\n'.join(part_log)
        return part_log_filepath, part_log_content

    @staticmethod
    def get_chapter_by_name(chapters: Iterable, chapter_name: str):
        """Function that returns a chapter from the 'chapters' list by its name.

        :param chapters:
        :param chapter_name:
        :return:
        """
        chapter = None
        for chapter in chapters:
            if chapter.name == chapter_name:
                break
        return chapter


class DenodoFolder(TreeItem):
    """
    Class representing a denodo folder
    """

    def __init__(self, parent: TreeItem, name: str):

        super(DenodoFolder, self).__init__(DenodoFolder, parent=parent)

        self.class_type = DenodoFolder
        self.name = name
        self.column_data = [self.name]
        self.tooltip = self.name
        self.sub_folders = self.child_items
        self.gui = GUI_SELECT

    def clear(self):
        """

        :return:
        """
        self.sub_folders = None
        self.column_data = None
        super().clear()


class RootItem(TreeItem):
    """Class representing a root of a tree"""

    def __init__(self, header: str):
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
        """

        :param name:
        :return:
        """
        return super().get_child_index_by_name(self.child_items, self.name)

    def clear(self):
        """

        :return:
        """
        self.chapters = None
        self.column_data = None
        super().clear()

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
        Store the children of the root item of the tree widget
        and replace them with the stored ones.
        :return: None
        :rtype: None
        """
        self.storage_list, self.child_items = self.child_items, self.storage_list

    def add_chapters(self, chapter_names: List[str]):
        """Method that adds a chapter to the chapter list for every name given.

        :param chapter_names: list of chapter_names of type string
        :type chapter_names: list
        :return: None
        :rtype: None
        """
        for chapter_name in chapter_names:
            Chapter(chapter_name, self)

    def get_code_items(self, chapter: Chapter=None):
        """

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
        """

        :return:
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
        """

        :param file_content:
        :param mode:
        :param bar:
        :param icons:
        :param logger:
        :return:
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
        """Method with nifty code to extract en fill direct dependencies.

        Per code object upon other objects based on their vql code.
        :param gui: mode flag selector indicating what code is done
        :type gui: int
        :param bar:
        :return: None
        :rtype: None
        """
        # place holder in search strings that is unlikely in the code
        place_holder = '%&*&__&*&%'

        # helper function
        def unique_list(_list: list):
            """Function that turns a list into a list with unique items.

            Keeping the sort order.

            :param _list: the list to make unique
            :type _list: list
            :return: the list made unique
            :rtype: list
            """
            new_list = list()
            for _item in _list:
                if _item not in new_list:
                    new_list.append(_item)
            return new_list

        # helper function
        def find_dependencies(_code_objects: list, _underlying_code_objects: list, _search_template: str):
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
        def code_items_lower(_chapter: Chapter):
            """
            Returns a list of code items with their code and object names in lower case of a particular chapter
            :param _chapter: the chapter name
            :type _chapter: Chapter
            :return: the requested list of tuples
            :rtype: list(tuple(CodeItem, str, str))
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

        for i in range(15):
            parentheses = '(' * i
            searches.append(('VIEWS', 'BASE VIEWS', f"from {parentheses}{place_holder}"))
            searches.append(('VIEWS', 'BASE VIEWS', f"join {parentheses}{place_holder}"))
        searches.append(('VIEWS', 'BASE VIEWS', f"set implementation {place_holder}"))
        searches.append(('VIEWS', 'BASE VIEWS', f"datamovementplan = {place_holder}"))

        # searches.append(('VIEWS', 'VIEWS', f"from {place_holder}"))
        for i in range(15):
            parentheses = '(' * i
            searches.append(('VIEWS', 'VIEWS', f"from {parentheses}{place_holder}"))
            searches.append(('VIEWS', 'VIEWS', f"join {parentheses}{place_holder}"))
        searches.append(('VIEWS', 'VIEWS', f"set implementation {place_holder}"))
        searches.append(('VIEWS', 'VIEWS', f"datamovementplan = {place_holder}"))

        searches.append(('ASSOCIATIONS', 'VIEWS', f" {place_holder} "))

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

        Using chapter items as folders and adds code_items as children.
        This structure is stored in the storage list
        and shown when the view is switched.
        :param gui: flag to indicate compare or normal select operations
        :type gui: int
        :return: Success or not
        :rtype: bool
        """
        folders = dict()

        def child_exists(item_name: str, parent: TreeItem) -> Union[TreeItem, None]:
            """
            Checks if a folder was already created
            :param parent: The parent chapter
            :param item_name:
            :return: True is yes
            """
            if not parent:
                return None

            for _child in parent.child_items:
                if _child.name.lower() == item_name.lower():
                    return _child
            return None

        def get_folders():
            """
            Returns a dictionary with all denodo folder paths as key and a list of code_items in this path as value
            :return:
            """

            for chapter in self.chapters:
                for _code_item in chapter.code_items:
                    if chapter.name != 'FOLDERS':
                        _data = _code_item.get_context_data(gui)
                        denodo_path = _data.denodo_path
                        if gui & GUI_COMPARE and not denodo_path:  # account for lost items
                            denodo_path = _code_item.data.denodo_path
                        if denodo_path not in folders.keys():
                            folders[denodo_path] = list()
                            folders[denodo_path].append(_code_item)
                        else:
                            folders[denodo_path].append(_code_item)

        # noinspection PyBroadException
        # try:
        root = TreeItem(DenodoFolder)
        folder_item = None
        get_folders()
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
        # except Exception:
        #     return False
        return True

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
        result = (chapter.get_part_log(folder) for chapter in self.chapters if chapter.selected)
        return result

    def get_code_as_file(self, mode: int, selected: bool)->str:
        """Function that puts the code content in a single .vql file of all checked/selected items.
        :param mode: GUI indicator saving either compare code or base code GUI_SELECT or GUI_COMPARE
        :type mode: int
        :param selected: Only selected items or not
        :type selected: bool
        :return: string of code content
        :rtype: str
        """

        code = [chapter.get_code_as_file(mode, selected) for chapter in self.chapters]
        return PROP_QUOTE + '\n'.join(code)

    def get_selected_code_files(self, mode: int, folder: Path)->List[Tuple[Path, str]]:
        """Function for looping over all selected code items in the model.

        This function is used to write the repository
        :param mode: the mode to select which code; either GUI_SELECT or GUI_COMPARE
        :type mode: int
        :param folder: the proposed folder for storage
        :type folder: Path
        :return: an iterator with two unpacked values: filepath and code content
        :rtype: list(tuple(Path, str))
        """
        item_path_code = list()
        for chapter in self.chapters:
            items = [code_item for code_item in chapter.code_items if code_item.selected]
            chapter_folder = folder / chapter.name
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
        """
        Wrapper Class representing a dependee code item
        """
        # noinspection PyMissingConstructor
        def __init__(self, parent: Union[TreeItem, None], code_item: CodeItem, gui):
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
            """

            :return:
            """
            self.dependee_code_items = None
            self.column_data = None
            super().clear()


class DependencyModel(QAbstractItemModel):
    """
    Filter proxy model for treeview3
    """
    def __init__(self, parent: QTreeView, header: str):
        """

        :param parent:
        """
        super(DependencyModel, self).__init__(parent)
        self.base_header = header
        self.header = header
        self.root_item = None
        self.root_code_item = None
        self.gui = GUI_SELECT

    def recurse_dependees(self, recurse: int, parent: Dependee):
        """

        :param recurse:
        :param parent:
        :return:
        """
        recurse += 1
        if recurse == 700:
            return
        for dependee_code_item in parent.dependee_code_items:
            dependee = Dependee(parent, dependee_code_item, self.gui)
            self.recurse_dependees(recurse, dependee)

    def set_root_code_item(self, code_item):
        """

        :param code_item:
        :return:
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

    def get_root_code_item(self):
        """

        :return:
        """
        return self.root_code_item

    def headerData(self, section: int, orientation, role: int=None)-> QVariant:
        """
        Called to supply the header
        :param section:
        :param orientation:
        :param role:
        :return:
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return QVariant(self.header)
        return NOTHING

    def flags(self, index: QModelIndex):
        """

        :param index:
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
        """
        Provider function for the model and view
        :param index:
        :param role:
        :return:
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

    def index(self, row: int, column: int, parent: Union[QModelIndex, None]=None, *args, **kwargs):
        """generate an index for this item

        :param row:
        :param column:
        :param parent:
        :return:
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

    def parent(self, index: Union[QModelIndex, None]=None):
        """find the parent index"""
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
        """how many items?"""
        if not self.root_item:
            return 0
        if not parent.isValid():
            return self.root_item.child_count()
        if parent.column() > 0:
            return 0
        parent_item = parent.internalPointer()
        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex=None, *args, **kwargs)->int:
        """how many columns does this node have?"""
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
        """

        :param index:
        :return:
        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.root_item

    def hasChildren(self, parent: QModelIndex=None, *args, **kwargs):
        """
        does it?
        :param parent:
        :param args:
        :param kwargs:
        :return:
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
    """
    Filter proxy for treeview1
    """
    def __init__(self, parent: QTreeView, header: str):
        """

        :param parent:
        """
        super(ColorProxyModel, self).__init__(parent)
        # self.setFilterRole(COLOR)
        self.setDynamicSortFilter(False)
        self.header = header
        self.color_filter = None
        self.type_filter = None

    def set_color_filter(self, color: str, type_filter):
        """

        :param color:
        :param type_filter:
        :return:
        """

        if color != self.color_filter:
            self.beginResetModel()
            self.type_filter = type_filter
            self.color_filter = color
            self.endResetModel()

    def headerData(self, section: int, orientation, role: int=None)-> QVariant:
        """
        Called to supply the header
        :param section:
        :param orientation:
        :param role:
        :return:
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return QVariant(self.header)
        return NOTHING

    def flags(self, index: QModelIndex):
        """

        :param index:
        :return:
        """
        if index.isValid():
            flags = super(ColorProxyModel, self).flags(index)
            flags |= Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable
            return flags
        else:
            return Qt.NoItemFlags

    def filterAcceptsRow(self, source_row: int, parent: QModelIndex):
        """

        :param source_row:
        :param parent:
        :return:
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

    def filterAcceptsColumn(self, source_column, parent: QModelIndex):
        """

        :param source_column:
        :param parent:
        :return:
        """
        return source_column == 0
        # return True

    def data(self, index: QModelIndex, role: int=None)->QVariant:
        """

        :param index:
        :param role:
        :return:
        """

        if index.column() == 0:
            return super(ColorProxyModel, self).data(index, role)


class SelectionProxyModel(QSortFilterProxyModel):
    """
    Filter proxy for treeview2
    """
    def __init__(self, parent: QTreeView, header: str):
        """

        :param parent:
        """
        super(SelectionProxyModel, self).__init__(parent)
        self.setFilterRole(CHECK)
        self.setDynamicSortFilter(True)
        self.header = header

    def headerData(self, section: int, orientation, role: int=None)-> QVariant:
        """
        Called to supply the header
        :param section:
        :param orientation:
        :param role:
        :return:
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return QVariant(self.header)
        return NOTHING

    def flags(self, index: QModelIndex):
        """

        :param index:
        :return:
        """
        if index.isValid():
            flags = super(SelectionProxyModel, self).flags(index)
            flags |= Qt.ItemIsEnabled | Qt.ItemIsSelectable
            flags ^= Qt.ItemIsUserCheckable
            return flags
        else:
            return Qt.NoItemFlags

    def filterAcceptsRow(self, source_row: int, parent: QModelIndex):
        """

        :param source_row:
        :param parent:
        :return:
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
        """

        :param source_column:
        :param parent:
        :return:
        """
        return source_column == 0

    def data(self, index: QModelIndex, role: int=None)->QVariant:
        """
        Provider function for the model and view
        :param index:
        :param role:
        :return:
        """
        if role == CHECK:
            return NOTHING
        else:
            if index.column() == 0:
                return super(SelectionProxyModel, self).data(index, role)


class TreeModel(QAbstractItemModel):
    """
    TreeModel implementation
    """
    selection_changed = pyqtSignal(TreeItem)

    def __init__(self, parent: QTreeView, mode: int, root_node: RootItem):
        """

        :param parent:
        :param mode:
        """
        super(TreeModel, self).__init__(parent)
        self.parent = parent
        self.mode = mode
        self.root_item = root_node
        self.color_filter = None
        self.type_filter = None

    def flags(self, index: QModelIndex)->int:
        """

        :param index:
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
        """Provider function for the model and view

        :param index:
        :param role:
        :return:
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
        """
        Called to supply the header
        :param section:
        :param orientation:
        :param role:
        :return:
        """

        if role in [DISPLAY, EDIT]:
            if orientation == Qt.Horizontal:
                if 0 <= section < len(self.root_item.column_data):
                    return QVariant(self.root_item.column_data[section])
        return NOTHING

    def hasChildren(self, parent: QModelIndex=None, *args, **kwargs):
        """
        does it?
        :param parent:
        :param args:
        :param kwargs:
        :return:
        """
        if not parent.isValid():
            return self.root_item.has_children()
        if parent.column() > 0:
            return False
        parent_item = self.item_for_index(parent)
        if parent_item:
            return parent_item.has_children()
        return False

    def index(self, row: int, column: int, parent: Union[QModelIndex, None]=None, *args, **kwargs):
        """generate an index for this item

        :param row:
        :param column:
        :param parent:
        :return:
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

    def parent(self, index: Union[QModelIndex, None]=None):
        """find the parent index"""
        if not index.isValid():
            return QModelIndex()

        item = self.item_for_index(index)
        parent_item = item.parent_item

        if parent_item is self.root_item:
            return QModelIndex()
        else:
            return self.createIndex(parent_item.child_number(), 0, parent_item)

    def columnCount(self, parent: QModelIndex=None, *args, **kwargs)->int:
        """how many columns does this node have?"""
        if not parent.isValid():
            return self.root_item.column_count()

        parent_item = parent.internalPointer()
        if parent_item.has_children():
            child = parent_item.child(0)
            return child.column_count()
        else:
            return 0

    def rowCount(self, parent: QModelIndex=None, *args, **kwargs)->int:
        """how many items?"""
        if not parent.isValid():
            return self.root_item.child_count()
        if parent.column() > 0:
            return 0
        parent_item = parent.internalPointer()
        return parent_item.child_count()

    def item_for_index(self, index: QModelIndex)->Union[TreeItem, RootItem]:
        """

        :param index:
        :return:
        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.root_item

    def last_index(self):
        """Index of the very last item in the tree.
        """
        current_index = QModelIndex()
        row_count = self.rowCount(current_index)
        while row_count > 0:
            current_index = self.index(row_count - 1, 0, current_index)
            row_count = self.row_count(current_index)
        return current_index

    def reset(self):
        """
        reset the model, roll up from the leaves and remove all reverences
        :return:
        """

        self.beginResetModel()
        self.resetInternalData()
        header = str(self.root_item.header)
        self.root_item.clear()
        self.root_item.__init__(header)
        self.endResetModel()

    def remove_compare(self):
        """
        reset the model, roll up from the leaves and remove all reverences
        :return:
        """
        self.beginResetModel()
        self.root_item.remove_compare()
        self.endResetModel()

    def change_view(self, view: int)->bool:
        """

        :param view:
        :return:
        """
        self.beginResetModel()
        success = self.root_item.change_view(view)
        self.endResetModel()
        return success


class VQLManagerWindow(QMainWindow):
    """
    Main Gui Class
    """

    mode_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        """
        Constructor of the Window Class
        :param parent: The owner/parent of the instance
        :type parent: Qt.Window
        :rtype: None
        """
        # initialize main window calling its parent
        super(VQLManagerWindow, self).__init__(parent, Qt.Window)
        self.logger = LogWrapper("vql_manager")
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
    def get_pixmap(image_path):
        """

        :param image_path:
        :return:
        """
        images = Path(QFileInfo(__file__).absolutePath()) / 'images'
        return QVariant(QPixmap(str(images / image_path)).scaled(16, 16))

    def get_mode(self)->int:
        """
        getter for mode
        :return:
        """
        return self._mode

    def set_mode(self, new_mode: int):
        """
        setter for mode
        :param new_mode:
        :return:
        """
        if not self._mode == new_mode:
            self._mode = new_mode

    def add_mode(self, mode: int):
        """
        add feature to mode
        :param mode:
        :return:
        """
        assert isinstance(mode, int)
        if not self._mode & mode:
            self._mode += mode

    def sub_mode(self, mode: int):
        """
        subtract feature from mode
        :param mode:
        :return:
        """
        if self._mode & mode:
            self._mode -= mode

    def setup_states(self):
        """

        :return:
        """
        init = self.states['init']
        base = self.states['base_loaded']
        compare = self.states['compare_loaded']
        
        init.addTransition(TransOpenBase(self, init, base, self.mode_changed))
        base.addTransition(TransResetBase(self, base, init, self.mode_changed))
        base.addTransition(TransOpenCompare(self, base, compare, self.mode_changed))
        compare.addTransition(TransRemoveCompare(self, compare,  base, self.mode_changed))
        compare.addTransition(TransResetAll(self, compare, init, self.mode_changed))

    def current_base_path_label(self):
        """

        :return:
        """
        label = ''
        if self.base_repository_file:
            label = 'File: '
        if self.base_repository_folder:
            label = 'Folder: '
        if self.base_repository_file or self.base_repository_folder:
            label += self.base_repository_file if self.base_repository_file else self.base_repository_folder
        return label

    def current_compare_path_label(self):
        """

        :return:
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
    def create_tree_view(tooltip: str='')->Union[QTreeView]:
        """Factory for instances of a QTreeWidget or VqlModel

        :param tooltip: Initial tooltip
        :type tooltip: str
        :return: the TreeWidget created
        :rtype: QTreeView
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
        """Function setup up all widgets

        :return: None
        :rtype: None
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
        """

        :param msg:
        :return:
        """
        self.log_edit.appendPlainText(msg)

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

    @staticmethod
    def get_buttons_widget(button_dict: dict)->Tuple[QWidget, QButtonGroup]:
        """Constructs a series of related radio buttons used to filter CodeItems.

        :param button_dict: A dict with names and colors
        :type button_dict: dict
        :return: A tuple of widget and the group its in
        :rtype: Tuple[QWidget, QButtonGroup]
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
        """

        :param index:
        :return:
        """
        idx = self.color_proxy_model.mapToSource(index)
        self.treeview2.expand(self.proxy_model.mapFromSource(idx))

    def on_collapse_treeview(self, index):
        """

        :param index:
        :return:
        """
        idx = self.color_proxy_model.mapToSource(index)
        self.treeview2.collapse(self.proxy_model.mapFromSource(idx))

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
            color = ''
        else:
            color = self.select_button_labels[button.text()]
        self.color_proxy_model.set_color_filter(color, CodeItem)

    def on_find_button_click(self):
        """
        Event handler of the find button
        :return:
        """
        mode = self.get_mode()
        if mode & BASE_LOADED or mode & COMP_LOADED:
            what = self.find_line_edit.text().strip()
            if what:
                model = self.tree_model
                item_indices = \
                    model.match(model.index(0, 0), DISPLAY,  QVariant(what), -1, Qt.MatchRecursive | Qt.MatchStartsWith)
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
        :rtype: None
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
        """Event handler to reset everything"""

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
        """Event handler to remove the comparison."""

        if self.states['compare_loaded'] in self.state_machine.configuration():
            self.logger.info('Removing Compare.')
            self.add_mode(COMP_UNLOAD)
            self.mode_changed.emit(self.get_mode())
        else:
            self.logger.info('No comparison found')

    def on_click_item(self, item_index: QModelIndex):
        """

        :param item_index:
        :return:
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
        """

        :return:
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
        """

        :param code_item:
        :return:
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

    def get_item_sources(self, item: CodeItem, gui: int, n_recurse: int):
        """

        :param item:
        :param gui:
        :param n_recurse:
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
    def object_type(code_item):
        """

        :param code_item:
        :return:
        """
        assert isinstance(code_item, CodeItem)
        object_type = code_item.chapter.name[:-1] if code_item.chapter.name != 'DATABASE' else 'DATABASE'
        return object_type.capitalize()

    def on_selection_changed(self, item: TreeItem):
        """
        Event handler for changes of the selection (check boxes) in the treeview1
        :param item:
        :return:
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
        :rtype: None
        """
        # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
        QMessageBox.about(self, 'About ' + self.windowTitle(), about_text)

    def on_about_qt(self):
        """Event handler for the click on the About Qt menu item in the help menu.

        It uses the boilerplate Qt about box
        :return: None
        :rtype: None
        """
        # noinspection PyCallByClass,PyTypeChecker
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

        def format_sql(_code: str)->str:
            """
            
            :param _code: 
            :return: 
            """
            chars = 4
            start = _code.find(' AS SELECT ') + chars
            end = _code.find(';', start)
            if chars <= start < end:
                clause = sqlparse.format(_code[start:end], reindent=True, indent_tabs=False, indent_width=2)
                if clause:
                    return _code[:start] + '\n' + clause + _code[end:]

            return _code

        def multi_substitution(_substitutions: list, _code: str):
            """
            Simultaneously perform all substitutions on the subject string.
            :param _substitutions:
            :param _code:
            :return:
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
        """Event handler for the click on the menu item to switch between VQL view or Denodo view.

        :return: None
        :rtype: None
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

        :return: filepath
        :rtype: Path
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
        :rtype: Path
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
        """Asks user which folder to save to via a dialog.

        If the folder exists, then asks if overwrite is allowed.

        :return: Folder to store the repository
        :rtype: Path
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
        """Asks which file to save to via a dialog.

        It also checks if the file may be overwritten

        :return: the file path of the file to be written
        :rtype: Path
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
        :type file: Path
        :param content: The content to be written as string
        :type content: str
        :return: Boolean on success
        :rtype: bool
        """

        # self.logger.debug('Saving: ' + str(file))
        try:
            with file.open(mode='w') as f:
                written = f.write(content)
                self.logger.debug(f"Saved {written} characters to {str(file)}")
                return True
        except (OSError, IOError) as error:
            msg = f"An error occurred during writing of file: {str(file)}"
            self.logger.error(msg)
            error_message_box("Error", msg, str(error), parent=self)
            return False

    def save_model_to_file(self, file: Path)->bool:
        """Saves the single .vql file.

        :param file: the file!
        :type file: Path
        :return: boolean on success
        :rtype: bool
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
        :type folder: Path
        :return: boolean on success
        :rtype bool
        """
        self.logger.debug(f"Saving model to repository in folder {folder} in mode: {show_mode(self.get_mode())}")
        self.status_bar.showMessage("Saving")
        if not folder:
            self.status_bar.showMessage("Save Error")
            return False

        self.treeview1.blockSignals(True)

        for part_log_filepath, part_log_content in self.root_item.get_part_logs(folder):

            if not part_log_content or not part_log_filepath:
                self.logger.error(f"No content while saving {part_log_filepath} ")
                self.status_bar.showMessage("Save Error")
                return False

            sub_folder = part_log_filepath.parent
            if not sub_folder.is_dir():
                try:
                    self.logger.debug("Creating Directory.")
                    sub_folder.mkdir(parents=True)
                except (OSError, IOError) as error:
                    self.status_bar.showMessage("Save Error")
                    msg = f"An error occurred during creation of the folders in {sub_folder}"
                    error_message_box("Error", msg, str(error), parent=self)
                    return False

            if not self.write_file(part_log_filepath, part_log_content):
                self.status_bar.showMessage("Save Error")
                return False

        for file_path, content in self.root_item.get_selected_code_files(self.get_mode(), folder):
            if not content or not file_path:
                self.status_bar.showMessage("Save Error")
                self.logger.debug(f"Saved not OK: {str(file_path)}")
                return False
            if not self.write_file(file_path, content):
                self.status_bar.showMessage("Save Error")
                self.logger.debug("Saved not OK")
                return False

        self.treeview1.blockSignals(False)
        self.status_bar.showMessage("Ready")
        self.logger.debug("Saved OK")
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
