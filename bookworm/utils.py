# coding: utf-8

import sys
import os
import winpaths
import glob
import clr
import wx
import hashlib
from functools import wraps, lru_cache
from subprocess import list2cmdline
from pathlib import Path
from xml.sax.saxutils import escape
from bookworm.vendor import shellapi
from bookworm import app
from bookworm.concurrency import call_threaded
from bookworm.logger import logger


log = logger.getChild(__name__)


# Sentinel
_missing = object()


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


@lru_cache(maxsize=10)
def reference_gac_assembly(glob_pattern: str):
    """
    Locate an assembly from the GAC and reference it.

    Recent versions of Pythonnet does not auto discover certain .NET framework
    assemblies, so add what we need from the global Assembly Cache (GAC).
    """
    gac_home = "Microsoft.NET\\assembly\\GAC_MSIL\\"
    assemblies = tuple(Path(winpaths.get_windows(), gac_home).rglob(glob_pattern))
    if not assemblies:
        raise OSError(f"Could not find assembily: {glob_pattern}")
    clr.AddReference(str(assemblies[0]))


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
    mat = pattern.search(text, concurrent=True)
    if not mat:
        return
    pos = mat.span()[0]
    lseg, tseg, rseg = pattern.split(text, maxsplit=1)
    snipit = "".join([lseg[-20:], tseg, rseg[:20]])
    return (pos, snipit)


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
