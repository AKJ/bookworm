# coding: utf-8

import os
import wx
from bookworm import app
from bookworm import config
from bookworm import speech
from bookworm.paths import app_path
from bookworm.reader import EBookReader
from bookworm.signals import reader_page_changed
from bookworm.utils import gui_thread_safe
from bookworm.logger import logger
from .decorators import only_when_reader_ready
from .menubar import MenubarProvider
from .toolbar import ToolbarProvider
from .state import StateProvider
from .navigation import NavigationProvider
from .annotation_dialogs import play_sound_if_note, highlight_bookmarked_positions


log = logger.getChild(__name__)


class BookViewerWindow(wx.Frame, MenubarProvider, ToolbarProvider, StateProvider):
    """The book viewer window."""

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title, name="main_window")
        self.setFrameIcon()

        self.reader = EBookReader(self)
        MenubarProvider.__init__(self)
        ToolbarProvider.__init__(self)
        self.CreateStatusBar()

        # Now create the Panel to put the other controls on.
        rect = wx.GetClientDisplayRect()
        panel = wx.Panel(self, size=(rect.width * 0.8, rect.height * 0.75))

        # Create the book reader controls
        # Translators: the label of the table-of-contents tree
        tocTreeLabel = wx.StaticText(panel, -1, _("Table of Contents"))
        self.tocTreeCtrl = wx.TreeCtrl(
            panel,
            size=(280, 160),
            style=wx.TR_TWIST_BUTTONS
            | wx.TR_NO_LINES
            | wx.TR_FULL_ROW_HIGHLIGHT
            | wx.TR_ROW_LINES,
            name="toc_tree",
        )
        # Translators: the label of the text area which shows the
        # content of the current page
        self.contentTextCtrlLabel = wx.StaticText(panel, -1, _("Content"))
        self.contentTextCtrl = wx.TextCtrl(
            panel,
            size=(200, 160),
            style=wx.TE_READONLY
            | wx.TE_MULTILINE
            | wx.TE_RICH2
            | wx.TE_AUTO_URL
            | wx.TE_PROCESS_ENTER
            | wx.TE_NOHIDESEL,
            name="content_view",
        )
        self.contentTextCtrl.Bind(
            wx.EVT_CONTEXT_MENU, lambda e: e.Skip(False), self.contentTextCtrl
        )
        self.contentTextCtrl.Bind(
            wx.EVT_RIGHT_UP, self.onContentTextCtrlContextMenu, self.contentTextCtrl
        )
        self.contentTextCtrl.SetMargins(self._get_text_view_margins())

        # Use a sizer to layout the controls, stacked horizontally and with
        # a 10 pixel border around each
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        lftSizer = wx.BoxSizer(wx.VERTICAL)
        rgtSizer = wx.BoxSizer(wx.VERTICAL)
        lftSizer.Add(tocTreeLabel, 0, wx.ALL, 5)
        lftSizer.Add(self.tocTreeCtrl, 1, wx.ALL, 5)
        rgtSizer.Add(self.contentTextCtrlLabel, 0, wx.EXPAND | wx.ALL, 5)
        rgtSizer.Add(self.contentTextCtrl, 1, wx.EXPAND | wx.ALL, 5)
        mainSizer.Add(lftSizer, 0, wx.ALL | wx.EXPAND, 10)
        mainSizer.Add(rgtSizer, 1, wx.ALL | wx.EXPAND, 10)
        panel.SetSizer(mainSizer)
        panel.Layout()

        # And also use a sizer to manage the size of the panel such
        # that it fills the frame
        sizer = wx.BoxSizer()
        sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Fit()
        self.SetMinSize(self.GetSize())
        self.CenterOnScreen(wx.BOTH)

        # Bind Events
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.onTOCItemClick, self.tocTreeCtrl)

        # Set statusbar text
        # Translators: the text of the status bar when no book is currently open.
        # It is being used also as a label for the page content text area when no book is opened.
        self._no_open_book_status = _("Press (Ctrl + O) to open an ebook")
        self._has_text_zoom = False
        self.SetStatusText(self._no_open_book_status)
        StateProvider.__init__(self)
        self._nav_provider = NavigationProvider(
            ctrl=self.contentTextCtrl,
            reader=self.reader,
            zoom_callback=self.onTextCtrlZoom,
        )
        if config.conf["general"]["play_page_note_sound"]:
            reader_page_changed.connect(play_sound_if_note, sender=self.reader)
        if config.conf["general"]["highlight_bookmarked_positions"]:
            reader_page_changed.connect(
                highlight_bookmarked_positions, sender=self.reader
            )

    def set_content(self, content):
        self.contentTextCtrl.Clear()
        self.contentTextCtrl.WriteText(content)
        self.contentTextCtrl.SetInsertionPoint(0)
        if self._has_text_zoom:
            self.contentTextCtrl.SetFont(self.contentTextCtrl.Font.MakeSmaller())
            self.contentTextCtrl.SetFont(self.contentTextCtrl.Font.MakeLarger())

    def SetStatusText(self, text, statusbar_only=False, *args, **kwargs):
        super().SetStatusText(text, *args, **kwargs)
        if not statusbar_only:
            self.contentTextCtrlLabel.SetLabel(text)

    @only_when_reader_ready
    def unloadCurrentEbook(self):
        self._page_turn_timer.Stop()
        self.reader.unload()
        self.set_content("")
        self.SetStatusText(self._no_open_book_status)
        self.tocTreeCtrl.DeleteAllItems()
        self.Title = app.display_name
        self._reset_search_history()
        self.populate_recent_file_list()

    @only_when_reader_ready
    def onTOCItemClick(self, event):
        selectedItem = event.GetItem()
        self.reader.active_section = self.tocTreeCtrl.GetItemData(selectedItem)

    def add_toc_tree(self, tree):
        self.tocTreeCtrl.DeleteAllItems()
        root = self.tocTreeCtrl.AddRoot(tree.title, data=tree)
        self._populate_tree(tree.children, root=root)
        tree.data["tree_id"] = root

    def tocTreeSetSelection(self, item):
        tree_id = item.data["tree_id"]
        self.tocTreeCtrl.EnsureVisible(tree_id)
        self.tocTreeCtrl.ScrollTo(tree_id)
        self.tocTreeCtrl.SelectItem(tree_id)
        self.tocTreeCtrl.SetFocusedItem(tree_id)

    def onTextCtrlZoom(self, direction):
        self._has_text_zoom = True
        font = self.contentTextCtrl.GetFont()
        size = font.GetPointSize()
        if direction == 1:
            if size >= 64:
                return wx.Bell()
            self.contentTextCtrl.SetFont(font.MakeLarger())
            # Translators: a message telling the user that the font size has been increased
            msg = _("The font size has been Increased")
        elif direction == -1:
            if size <= 6:
                return wx.Bell()
            self.contentTextCtrl.SetFont(font.MakeSmaller())
            # Translators: a message telling the user that the font size has been decreased
            msg = _("The font size has been decreased")
        else:
            self.contentTextCtrl.SetFont(wx.NullFont)
            # Translators: a message telling the user that the font size has been reset
            msg = _("The font size has been reset")
            self._has_text_zoom = False
        speech.announce(msg)

    def _populate_tree(self, toc, root):
        for item in toc:
            entry = self.tocTreeCtrl.AppendItem(root, item.title, data=item)
            item.data["tree_id"] = entry
            if item.children:
                self._populate_tree(item.children, entry)

    def setFrameIcon(self):
        icon_file = app_path(f"{app.name}.ico")
        if icon_file.exists():
            self.SetIcon(wx.Icon(str(icon_file)))

    def _get_text_view_margins(self):
        # XXX need to do some work here to obtain appropriate margins
        return wx.Point(100, 100)

    @gui_thread_safe
    def highlight_text(self, start, end):
        self.contentTextCtrl.SetStyle(start, end, wx.TextAttr(wx.BLACK, wx.LIGHT_GREY))

    @gui_thread_safe
    def clear_highlight(self, start=0, end=-1):
        textCtrl = self.contentTextCtrl
        end = textCtrl.LastPosition if end < 0 else end
        textCtrl.SetStyle(
            start,
            end,
            wx.TextAttr(textCtrl.ForegroundColour, textCtrl.BackgroundColour),
        )

    def get_containing_line(self, pos):
        """Returns the left and right boundaries
        for the line containing the given position.
        """
        _, col, lino = self.contentTextCtrl.PositionToXY(pos)
        left = pos - col
        return (left, left + self.contentTextCtrl.GetLineLength(lino))

    def set_text_direction(self, rtl=False):
        style = self.contentTextCtrl.GetDefaultStyle()
        style.SetAlignment(wx.TEXT_ALIGNMENT_RIGHT if rtl else wx.TEXT_ALIGNMENT_LEFT)
        self.contentTextCtrl.SetDefaultStyle(style)

    def notify_user(self, title, message, icon=wx.ICON_INFORMATION):
        wx.MessageBox(message, title, style=icon)
