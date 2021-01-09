# coding: utf-8

import sys
import os
import glob
import wx
import hashlib
from functools import wraps
from subprocess import list2cmdline
from pathlib import Path
from xml.sax.saxutils import escape
from datetime import datetime
from babel.dates import format_datetime as babel_format_datetime
from bookworm.vendor import shellapi
from bookworm import app
from bookworm.concurrency import call_threaded
from bookworm.logger import logger


log = logger.getChild(__name__)


# Sentinel
_missing = object()

# New line character
NEWLINE = "\n"


def ignore(*exceptions, retval=None):
    """Execute function ignoring any one of the given exceptions if raised."""

    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not any(isinstance(e, exc) for exc in exceptions):
                    raise
                log.exception(
                    f"Ignored exc {e} raised when executing function {func}",
                    exc_info=True,
                )
                return retval

        return wrapped

    return wrapper


def restart_application(*extra_args, debug=False, restore=True):
    args = list(extra_args) + ["--restarted"]
    reader = wx.GetApp().mainFrame.reader
    if restore and reader.ready:
        args.insert(0, f"{reader.document.filename}")
        reader.save_current_position()
    if debug and ("--debug" not in args):
        args.append("--debug")
    wx.GetApp().ExitMainLoop()
    shellapi.ShellExecute(None, None, sys.executable, list2cmdline(args), None, 1)
    sys.exit(0)


def recursively_iterdir(path):
    """Iterate over files, exclusively, in path and its sub directories."""
    for item in Path(path).iterdir():
        if item.is_dir():
            yield from recursively_iterdir(item)
        else:
            yield item


def gui_thread_safe(func):
    """Always call the function in the gui thread."""

    @wraps(func)
    def wrapper(*a, **kw):
        return wx.CallAfter(func, *a, **kw)

    return wrapper


def generate_sha1hash(content):
    hasher = hashlib.sha1()
    is_file_like = hasattr(content, "seek")
    if not is_file_like:
        file = open(content, "rb")
    else:
        content.seek(0)
        file = content
    for chunk in file:
        hasher.update(chunk)
    if not is_file_like:
        file.close()
    return hasher.hexdigest()


@call_threaded
def generate_sha1hash_async(filename):
    return generate_sha1hash(filename)


def search(pattern, text):
    """Search the given text using a compiled regular expression."""
    snip_reach = 25
    len_text = len(text)
    for mat in pattern.finditer(text, concurrent=True):
        start, end = mat.span()
        snip_start = 0 if start <= snip_reach else (start - snip_reach)
        snip_end = len_text if (end + snip_reach) >= len_text else (end + snip_reach)
        snip = text[snip_start:snip_end].split()
        if len(snip) > 3:
            snip.pop(0)
            snip.pop(-1)
        yield (start, " ".join(snip))


def format_datetime(date: datetime) -> str:
    return babel_format_datetime(date, locale=app.current_language)


class cached_property(property):

    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.

    Taken as is from werkzeug, a WSGI toolkit for python.
    :copyright: (c) 2014 by the Werkzeug Team.
    """

    # implementation detail: A subclass of python's builtin property
    # decorator, we override __get__ to check for a cached value. If one
    # choses to invoke __get__ by hand the property will still work as
    # expected because the lookup logic is replicated in __get__ for
    # manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

    def __delete__(self, obj):
        obj.__dict__.pop(self.__name__)


def escape_html(text):
    """Escape the text so as to be used
    as a part of an HTML document.

    Taken from python Wiki.
    """
    html_escape_table = {'"': "&quot;", "'": "&apos;"}
    return escape(text, html_escape_table)
