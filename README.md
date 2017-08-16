# ukebook_md

 Intro
This is a python implementation of the 'ukedown' ideas put forward by @smudgefarrier as part of the 'ukebook' project hosted here on github by @birdcolour

Rather than reimplement block parsing and using regex replacements etc, I decided to write an extension 
(or in fact a series of extensions) to the standard [Markdown library](https://github.com/waylan/Python-Markdown/tree/master/markdown)
which is documented [here](https://pythonhosted.org/Markdown/extensions/api.html)

## Requirements
You'll need a python virtual environment, I've only tested with python 2.7 so far (although I'll be updating any non-py3 compatible code eventually) with at least the following installed

  * markdown (well, obviously)
  * jinja2 (for templating) - this is not used "properly" yet, I have plans for metadata and other templating tricks.

## Outstanding stuff
As in, stuff I haven't done, rather than the complimentary interpretation

  1. **Chord support** - I really like the stuff Mark already did, but I fancy having a go in python. Because.
  1. **Metadata** - tags, embedded artist and track info etc, can be used in templating, also goes into the DB Models
  1. **Web backend**. I've had a play with django for this but I think I'm going to fall back on flask.
     current thinking is to build a REST API MVC and point something javascripty and modern at it.
     I think this also plays well with the phone app side of things
  1. **frontend** of your choice. Probably all bootstrappy and stuff. Or a phone app. Or a small shell sc

Then we have all the other joys like authentication, access controls, songbook creation. All that wheel reinventing that inveterate tinkerers enjoy

## How to use it as it stands

  1. Create your virtual environment as above
  1. Activate it
  1. `./ukify.py --help` (or whatever one does on windows systems, I haven't got any :) ) 

The commandline parts to ukify don't all work yet. I have some CSS work to do, that's been a while (Eric Meyer here I come again) plus a load of other stuff.

Then if we want to be down with the cool kids (or the cool beardie hipster kids at least) we'll dockerise it all and deploy it to the cloud (man), maybe with openshift or summat.


