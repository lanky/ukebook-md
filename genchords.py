#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

from jinja2 import Environment, FileSystemLoader

# string translation table for munging filenames
trans = {
        '#': 'sharp',
        '/': 'slash',
        '+': 'add'
        }
ttable = { ord(k): v  for k, v in trans.items() }

# This defines the original diagram size
BOARD = {
        # actual chord diagram dimensions
        "svg_width": 90,
        "svg_height": 130,
        # where the fretboard starts
        "board_x": 15,
        "board_y": 30,
        # fretboard dimensions
        "board_width": 54,
        "board_height": 90,
        # how many frets
        "fretcount": 5,
        # not likely to change, but in theory, this could do guitar chords (etc)
        "stringcount": 4,
        }

SAMPLES = [
    { 'name': 'F#',
      'barres': [ (1, 1, 4) ],
      'startpos': 0,
      'frets': [ 3, 0, 2, 0 ],
      },
    { 'name': 'Em7',
      'startpos': 0,
      'frets': [ 0, 2, 0, 2 ],
      },
    { 'name': 'Bm',
      'startpos': 0,
      'frets': [ 4, 2, 2, 2 ],
      }
]


def render(template, context, template_dir="templates"):
    """
    Creates a custom jinja2 environment and generates the provided template i
    - allows for customisation of outputted HTML if wanted

    Args:
        template(str): name of template file
        context(dict): dictionary of key,value pairs to use inside template

    Kwargs:
        template_dir(str): where to look for templates,
                           default is the local 'templates' directory.

    """
    j2env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True)

    tpl = j2env.get_template(template)

    return tpl.render(context)


if __name__ == "__main__":
    for chord in SAMPLES:
        safename = chord['name'].translate(ttable)
        chord.update(BOARD)
        with open("{}.svg".format(safename), 'w') as chordout:
            chordout.write(render('drawnchord.svg.j2', chord))


