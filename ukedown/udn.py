#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals
from markdown.inlinepatterns import Pattern
from markdown import Extension
from markdown.util import etree
from markdown.blockprocessors import BlockProcessor
from markdown.preprocessors import Preprocessor
import codecs
import logging
import re

from glob import glob

# constants
# approximation of chords - covers major minor dim aug sus and 7/9/13 etc
CHORD = r'\(([A-G][adgijmnsu0-9#b+-]*)\)'
# lines that start (and optionally end) with a | character are part of boxed paragraphs
BOX = r'(^|\n)\| *([^ ][^|]*)\|?$'
# a line containing something encapsulated by [] characters
HEADER = r'^(.*)\[([^]]+)\](.*)$'

# TODO
# preprocess - replace [ ] with h2
# replace line 1 ( or the first blank line ) with h1
# presuming that it only consists of alnum¸space and hyphen (or n-dash or em-dash, bloody unicode)

class HeaderProcessor(Preprocessor):
    """ 
    assume first non-blank line is the song title (plus potentially artist)
    find and replace [] entries, replace with h2 (i.e. ##)
    """
    def __init__(self, markdown_instance=None, pattern=HEADER):
        super(HeaderProcessor, self).__init__(markdown_instance)
        self.pattern = re.compile(pattern)

    def run(self, lines):
        new_lines = []
        while True:
            # pop first line from the list
            x = lines.pop(0)

            # if it's not blank, then this is what we want
            if x.strip() != '':
                # append it flagged as h1 - remove any existing leading '#' symbols
                new_lines.append('# %s' % x.lstrip('#'))
                break
            
        # now iterate over the rest and find [ header ] sections
        for line in lines:
            # does the line match our [ ] pattern?
            m = self.pattern.match(line)
            if m:
                new_lines.append("## %s" % m.group(2).strip())
            else:
                new_lines.append(line)
        return new_lines


class ChordPattern(Pattern):
    def handleMatch(self, m):
        el = etree.Element('span')
        el.attrib['class'] =  'chord'
        el.text = m.group(2)
        return el

class BoxSectionProcessor(BlockProcessor):
    """process the ^| lines representing a box in a chord sheet"""

    def __init__(self, parser, pattern=BOX):
        super(BoxSectionProcessor, self).__init__(parser)
        self.pattern = re.compile(pattern)

    def test(self, parent, block):
        return self.pattern.search(block)

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.pattern.search(block)
        if m:
            before = block[:m.start()]  # Lines before box
            # Pass lines before blockquote in recursively for parsing forst.
            self.parser.parseBlocks(parent, [before])
            block = '\n'.join(
                [self.clean(line) for line in block[m.start():].split('\n')]
            )
        # gets the last element at this level
        sibling = self.lastChild(parent)
        if sibling is not None and sibling.tag == 'div' and sibling.get('class') == 'box':
            # Previous block was also a div
            quote = sibling
        else:
            # This is a new blockquote. Create a new parent element.
            quote = etree.SubElement(parent, 'div', {'class': 'box'})
        #    quote.set('class', 'box')
        # Recursively parse block with blockquote as parent.
        # change parser state so blockquotes embedded in lists use p tags
        self.parser.state.set('box')
        self.parser.parseChunk(quote, block)
        self.parser.state.reset()

    def clean(self, line):
        """ Remove ``|`` from beginning (and possibly end)of a line. """
        m = self.pattern.match(line)
        if line.strip() == "|" or re.match(r'^\| *\|$', line):
            return "<br />"
        elif m:
            return m.group(2)
        else:
            return line.strip()



class UkeBookExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        # add our extensions...
        # preprocessor
        md.preprocessors.add('headers', HeaderProcessor(md, HEADER), '<reference')
        md.inlinePatterns.add('chord', ChordPattern(CHORD, md), '<reference')
        md.parser.blockprocessors.add('box', BoxSectionProcessor(md.parser), '>empty')

def makeExtension(*args, **kwargs):
    return UkeBookExtension(*args, **kwargs)
