#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from markdown.inlinepatterns import Pattern
from markdown import Extension
from markdown.util import etree
from markdown.blockprocessors import BlockProcessor
import logging
import re

# constants
CHORD = r'\(([A-G][adgijmnsu0-9#b]*)\)'

logger = logging.getLogger('ukebook')
logger.setLevel = logging.DEBUG
fh = logging.FileHandler('parser.log')
logger.addHandler(fh)


# TODO
# preprocess - replace [ ] with h2
# replace line 1 ( or the first blank line ) with h1
# presuming that it only consists of alnum¸space and hyphen (or n-dash or em-dash, bloody unicode)

class ChordPattern(Pattern):
    def handleMatch(self, m):
        el = etree.Element('span')
        el.attrib['class'] =  'chord'
        el.text = m.group(2)
        return el

class ChordExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add('chord', ChordPattern(CHORD, md), '<reference')

class BoxSectionProcessor(BlockProcessor):
    """process the ^| lines representing a box in a chord sheet"""
    RE = re.compile(r'(^|\n)\| *([^ ].*)\|?$')

    def test(self, parent, block):
        return self.RE.search(block)

    def run(self, parent, blocks):
        block = blocks.pop(0)
        logger.info("processing block %s" % block)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()]  # Lines before blockquote
            # Pass lines before blockquote in recursively for parsing forst.
            self.parser.parseBlocks(parent, [before])
            # Remove ``> `` from begining of each line.
            block = '\n'.join(
                [self.clean(line) for line in block[m.start():].split('\n')]
            )
        # gets the last element at this level
        sibling = self.lastChild(parent)
        if sibling is not None and sibling.tag == 'div':
            # Previous block was a blockquote so set that as this blocks parent
            quote = sibling
        else:
            # This is a new blockquote. Create a new parent element.
            quote = etree.SubElement(parent, 'div')
            quote.set('class', 'box')
        # Recursively parse block with blockquote as parent.
        # change parser state so blockquotes embedded in lists use p tags
        self.parser.state.set('box')
        self.parser.parseChunk(quote, block)
        self.parser.state.reset()

    def clean(self, line):
        """ Remove ``|`` from beginning of a line. """
        m = self.RE.match(line)
        if line.strip() == "|" or re.match(r'\| *\|$', line):
            return ""
        elif m:
            return m.group(2)
        else:
            return line


class BoxExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.parser.blockprocessors.add('box', BoxSectionProcessor(md.parser), '<quote')
