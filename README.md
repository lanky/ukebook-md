# ukebook_md

## Intro
This is a toolset including a python implementation of the 'ukedown' ideas put forward by @smudgefarrier as part of the 'ukebook' project hosted here on github by @birdcolour.
It is intended to be used to manage songbooks for ukulele groups, specifically Karauke, where we have a requirement to produce both 'band' and 'singers' versions of a given song.

It is implemented as an extension (or in fact a series of extensions) to the standard [Markdown library](https://github.com/waylan/Python-Markdown/tree/master/markdown) which is documented [here](https://pythonhosted.org/Markdown/extensions/api.html)

THis repo contains the core `ukedown` extensions, plus a toolset to convert directories full of 'ukedown' formatted files to HTML, with index pages and (fairly) responsive CSS.
The end goal will be to build responsive HTML (Supporting rotate and resize) and PDF documents in both landscape and portrait modes, in a variety of styles, but initially

  1. karauke band format (inline chords, but no diagrams)
  2. karauke singers' format (no inline chords or diagrams - lyrics only)
  3. Ukulele Wednesdays format (both inline chords and diagrams)

## What's here?
The core elements are the 'ukedown' markdown extensions, used to identify chords and other elements and generate HTML from them.

### configuration files
  `chords.yml` - defines fingering, neck position and barres for every known chord. These are used to generate SVG chord diagrams (scalable vector diagrams) which are inserted into each songsheet

  `fretboard.yml` - defines a standard ukulele fretboard (for use with an SVG template) - number of strings etc is customisable, so could also be used for other instruments (guitar etc)

### utility scripts
There are several scripts, the most important being
`genbook.py`, which generates an almost-EPUB structure (the EPUB paarts need some work) using a directory containing *ukedown* formatted songs (more details on that later) as inputs
This script calls functions from `chordgen.py` to render SVG documents for each known chord shape (definitions are in  `chords.yml`)
It generates HTML pages for each song, with inline chord diagrams and an index page with links to them.


## Requirements
You'll need a python virtual environment, preferably python 3.5+ - the toolset has only been tested with that. There is a `requirements.txt` file in the repo that can be used to generate this. Or you can just install all those packages into a system or user directory, of course.

  * markdown (well, obviously)
  * jinja2 (for templating) - this is not used "properly" yet, I have plans for metadata and other templating tricks.

## Current Functionality
  * Generation of HTML documents, with links to CSS files, all within an 'EPUB' directory structure
  * SVG chord diagrams
  * HTML docs generated from modular jinja2 templates
  * CSS grid used for a flexible layout - text degrades into multiple columns as the page gets wider.

## PDF Generation
PDF generation is handled by the [Weasyprint](https://weasyprint.org/) libraries.

A separate tool has been added to build PDFs from web content, but this will eventually be added to the main book generation tools.

PDF generation has some basic requirements:
  * weasyprint doesn't support CSS Grid (yet?), so a separate print CSS sheet has been written to handle this.
  * It cannot render internal (i.e. directly in HTML) SVG images, so generate the web content using the `--external` flag.

### An example
Generate web content using the PDF stylesheet (it still works as HTML):
```python
./genbook.py --external -o BOOK_DIRECTORY -s pdfprint INPUT_DIRECTORY
```
Then use the included `makepdf.py` script to generate your output PDF

```python
./makepdf.py BOOK_DIRECTORY -o FILENAME.pdf
```

# Ukedown formatting
I should really call this something different as it's not just for ukes. Oh well.
Songs are written in plain text format, as used in [ukulele wednesdays](http://www.ukulelewednesdays.com) songbooks,
but without unnecessary formatting.

There are many examples of these in the `inputs` directory

## supported ukedown-specific markup styles

  * the first non-blank line in a songsheet should contain TITLE - ARTIST. These are used in metadata, for index generation and rendered as `<h1>`

  * `()` identifies a chord, e.g. `(C)` or `(Dsus4)`. Avoid silliness like `(F - Single Strums)` or weird unicode chars like downarrows.
    These are rendered as  in `<span class="chord">` elements

  * currently `()` also marks backing vox, for patterns that are not chords.
    I shall probably change that to <> or similar to avoid confusion. These map to *italic* elements

  * `[]` marks section headers (chorus etc) - these map to `<span>` elements

  * `{}` mark performance notes, e.g. `{single strums}` - rendered as  **[bold]** text

  * `|` at the beginning (and optionally at the end of a line) denotes a 'boxout' - basically a paragraph with borders, not a single cell table. Used for repeated sections

## Current Limitations
  * multiple boxes must be separated by at least one blank line.
  * Chords cannot go on the same line as **[section headers]**
  * hiding chords with CSS (`display: none`) doesn't collapse whitespace, so can mess up text flow.

## Usage

  1. Ensure you have an appropriate python interpreter (python3.5+ ideally, but at least python3 since the updates). Python2 may work, but I've not tested that for ages.
  1. Create a virtualenv - I'm a huge fan of `virtualenvwrapper` for this, but maybe that's just me.
  1. `pip install --upgrade -r requirements.txt`
  1. Create/Add/Remove/Edit songsheets in `inputs` or another directory or your choice
  1. Generate a songbook using `./genbook.py` (see `genbook.py --help` for more details)


# Outstanding/TODO/etc
  * more automation
  * Better CSS
  * Actual proper controllable font scaling (probably requires javascript, which may not work properly in EPUB.)
  * refactoring to use classes, to let this fit into an MVC model in the future (This is currently underway in a feature branch)
  * integration of PDF rendering, on a per-song or per-book basis


The commandline parts to ukify don't all work yet. I have some CSS work to do, that's been a while (Eric Meyer here I come again) plus a load of other stuff.

Then if we want to be down with the cool kids (or the cool beardie hipster kids at least) we'll dockerise it all and deploy it to the cloud (man), maybe with openshift or summat.


