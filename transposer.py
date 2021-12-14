#!/usr/bin/env python3
# vim: set ts=4 sts=4 sw=4 et ci nu ft=python:
import argparse
import sys
import os
from typing import List
from udn_songbook import Song

"""
A tool using the `udn_songbook` mechanisms to transpose songs by a given number of semitones
"""


def parse_cmdline(argv: List[str] = []) -> argparse.Namespace:
    """
    process commandline options and arguments
    """
    desc = """A tool using the `udn_songbook` toolset to transpose ukedown songsheets by
a given number of semitones. Can overwrite existing files if you want it to.
    """
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("filenames", nargs="+", help="filename(s) in UDN(ukedown) format to transpose")
    parser.add_argument("-t", "--semitones", type=int, help="number of semitones to shift each chord by, can be negative")
    parser.add_argument("-o", "--output", help="output filename, will dump to console if not specified. Will not work with more than one inputfile, for hopefully obvious reasons")
    parser.add_argument("-i", "--in-place", action="store_true", default=False, help="overwrite the input file with the transposed version. Use this only if you are sure you want to")


    opts = parser.parse_args()

    if opts.output and len(opts.filenames) > 1:
        raise argparse.ArgumentError("Cannot use --output with more than one input file.")

    # sanity checking to be added
    return opts

def main(opts: argparse.Namespace) -> None:
    """
    Main script entrypoint
    """

    for fname in opts.filenames:
        s = Song(fname)
        s.transpose(opts.semitones)

        if opts.in_place:
            s.save(fname)

        elif opts.output:
            s.save(opts.output)

        else:
            print(s.markup)

if __name__ == "__main__":
    opts = parse_cmdline(sys.argv[1:])
    main(opts)






