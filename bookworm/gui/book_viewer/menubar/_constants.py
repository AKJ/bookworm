# coding: utf-8

import wx
import enum


class BookRelatedMenuIds(enum.IntEnum):
    """Declares  menu ids for items which are enabled/disabled
    based on whether a book is loaded or not.
    """

    # File
    export = wx.ID_SAVEAS
    closeCurrentFile = 211
    # Tools
    goToPage = 221
    searchBook = wx.ID_FIND
    findNext = 222
    findPrev = 223
    viewRenderedAsImage = 224
    scanTextOCR = 225
    # Speech
    play = 251
    stop = 252
    pauseToggle = 253
    rewind = wx.ID_BACKWARD
    fastforward = wx.ID_FORWARD
    # Annotations
    addBookmark = 241
    addNote = 242
    viewBookmarks = 243
    viewNotes = 244
    ExportNotes = 245


class ViewerMenuIds(enum.IntEnum):
    """Declares menu ids for all other menu items."""

    # Tools menu
    preferences = wx.ID_PREFERENCES
    # Speech menu
    voiceProfiles = 257
    deactivateVoiceProfiles = wx.ID_REVERT
    # Help Menu
    documentation = 801
    website = 802
    license = 803
    contributors = 812
    check_for_updates = 810
    restart_with_debug = 804
    about = 805


KEYBOARD_SHORTCUTS = {
    wx.ID_OPEN: "Ctrl-O",
    BookRelatedMenuIds.closeCurrentFile: "Ctrl-W",
    BookRelatedMenuIds.goToPage: "Ctrl-G",
    wx.ID_FIND: "Ctrl-F",
    BookRelatedMenuIds.findNext: "F3",
    BookRelatedMenuIds.findPrev: "Shift-F3",
    BookRelatedMenuIds.viewRenderedAsImage: "Ctrl-R",
    BookRelatedMenuIds.scanTextOCR: "Ctrl-shift-R",
    wx.ID_PREFERENCES: "Ctrl-Shift-P",
    BookRelatedMenuIds.play: "F5",
    BookRelatedMenuIds.pauseToggle: "F6",
    BookRelatedMenuIds.stop: "F7",
    ViewerMenuIds.voiceProfiles: "Ctrl-Shift-V",
    BookRelatedMenuIds.addBookmark: "Ctrl-B",
    BookRelatedMenuIds.addNote: "Ctrl-N",
    BookRelatedMenuIds.viewBookmarks: "Ctrl-Shift-B",
    BookRelatedMenuIds.viewNotes: "Ctrl-Shift-N",
    ViewerMenuIds.documentation: "F1",
}
