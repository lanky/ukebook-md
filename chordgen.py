#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, absolute_import
import os
import sys
import yaml
import codecs
from jinja2 import Environment, FileSystemLoader

def symbolise(name):
    """
    replace pretend symbols with real ones (unicode ftw)
    """
    translations = {
            'b': u'♭',
            '#': u'♯'
            }
    tt = { ord(k): v for k, v in translations.items() }

    return unicode(name).translate(tt)

def merge_ctx(base, **kwargs):
    """
    create a merged context for passing into jinja template

    Args:
        base(dict): basic layout information, fretboard info, diag size etc
    Kwargs:
        name: un-translated name of chord, special symbols and all


    """
    context = {}
    # calculate context settings.
    # need to get fret and string spacing and positions.
    # There are only 3 gaps for 4 strings (etc)
    sgap = ( base['fboard']['right'] - base['fboard']['left'] ) / float( base['fboard']['strings'] - 1 )
    # there will be x+1 fret lines, though, so we need to recognise that
    fgap = ( base['fboard']['bottom'] - base['fboard']['top'] ) / float(base['fboard']['frets'])
    # we only need x positions for strings.
    strings = [ base['fboard']['left'] + (idx * sgap)
                for idx in xrange(base['fboard']['strings']) ]
    # frets require an extra addition for the 'nut', or 'fret 0'
    frets = [ base['fboard']['top'] + ( idx * fgap )
              for idx in xrange(base['fboard']['frets']) ]
    # add the baseline
    frets.append(base['fboard']['bottom'])

    context.update(base)
    context['frets'] = frets
    context['strings'] = strings

    # radius for rounding rectangles and sizing finger positions
    # makes circles half a fret gap
    context['radius'] = fgap / 4
    # centre for positioning halfway between frets
    context['centre'] = fgap / 2

    # caculate mid-fret positions to simplify marker stuff
    bpos = kwargs.get('barre', 0)
    if bpos != 0:
        # barre is provided as a fret number
        # we need to calculate offsets
        # barres are wider than the board by radius * 2
        # and offset from position by radius in both x and y axes
        context['barre'] = {
                'position': kwargs['barre'],
                'left': base['fboard']['left'] - context['radius'],
                'top': (frets[bpos] - context['centre']) - context['radius'],
                'width':  base['fboard']['right'] - base['fboard']['left'] +
                          (context['radius'] * 2),
                'height': context['radius'] * 2,
                }

    context['fingers'] = []
    for fpos in kwargs.get('fingers', []):
        if fpos == 0:
            context['fingers'].append(fpos)
        else:
            # we have to be relative to the barre if there is one
            context['fingers'].append(frets[fpos + bpos] - (fgap / 2))

    context['name'] = kwargs.get('name')
    return context


if __name__ == "__main__":
    # we need to load a config for our chord diagram
    cfg = {}
    try:
        with codecs.open('chord_diag.yml', mode="r", encoding="utf-8") as cfile:
            cfg.update(yaml.safe_load(cfile))
    except:
        raise

    env = Environment(loader=FileSystemLoader('templates'))
    tpl = env.get_template('fretboard.svg.j2')

    try:
        chords = yaml.load(codecs.open('chords.yml', mode="r", encoding="utf-8"))
        for label, ch in chords.items():
            print("rendering {}".format(label))
            if 'name' not in ch:
                ch['name'] = symbolise(label)
            with codecs.open("{}.svg".format(label), mode='w', encoding="utf-8") as output:
                output.write(tpl.render(merge_ctx(cfg, **ch)))
    except:
        raise

