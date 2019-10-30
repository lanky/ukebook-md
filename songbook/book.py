#!/usr/bin/env python3
# vim: set ts=4 sts=4 sw=4 et ci nu ft=python:

import os
from glob import glob

from jinja2 import Environement, FilesystemLoader

from . import song

class SongBook(object):
    """
    wrapper around a list of songs with additional context
    provides stylesheets, template environments, indexing etc
    """

    def __init__(self, inputs=[], stylesheets=[]):
        """
        Create a songbook object from a list of inputs.
        Inputs can be directories, too.
        By default, songbook content is just a list, so can have
        repeat entries.
        """
        self._inputs = inputs
        self._stylesheets = stylesheets
        # keep track of all the chord diagrams we need for the book
        self.chords = set([])
        self.contents = []
        self.index = {}

    def populate(self):
        """
        Reads in the content of any input directories, as Song objects
        """
        for src in self.inputs:
            rp = os.path.realpath(src)
            if os.path.isfile(rp) and fnmatch.fnmatch(os.path.basename(src), '*.udn'):
                self.contents.append(song.Song(s))
            elif os.path.isdir(rp):
                for rt, dirs, files in os.walk(rp):
                    flist = fnmatch.filter([ os.path.join(rt, f) for f in files ], '*.udn')
                    self.contents.extend([song.Song(f) for f in flist])
            else:
                print("cannot load from non-file/dir {}".format(src))

        self.chords = set(s.chords for s in self.contents)

    def collate(self):
        """
        reduce contents list to unique entries, indexed on title - artist
        """
        for entry in self.contents:
            k = '{0.title}-{0.artist}'.format(entry).lower().replace(' ', '_')
            self.index[k] = entry

    def update(self, inputs):
        """
        replace entires in an existing songbook using the provided inputs
        This will regenerate the index
        """
        pass

    def refresh(self):
        """
        reload all the current inputs (that have changed)
        This is a checksumming/stat operation
        """
        # walk over current index/contents
        # check stat for last change (since songbook population)
        # compare checksum - has the content actually changed?
        # this is a PATH operation and may rebuild the songbook index
        # this permits us to change metadata (title etc) and have the book
        # reordered appropriately.
        pass




    def render(self, template):
        # renders the songook to a file or files.
        pass
