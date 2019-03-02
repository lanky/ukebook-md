## part of ukedown ##
# patterns for  translating all the horrible 'smart' characters that word etc like to
# put in when you just want boring hyphens or quotes or brackets (or whatever)
# basically  this is a dictionary mapping ord(UNICODE) to UNICODE_REPLACEMENT


WP_JUNK = {
        # first hyphen characters, there are a few and wordprocessors do love 'em
        '\u2010': '-', # hyphen
        '\u2011': '-', # non-breaking hyphen
        '\u2012': '-', # figure-dash
        '\u2013': '-', # en-dash
        '\u2014': '-', # em-dash
        '\u2015': '-', # horizontal bar
        # then the silly pretty quote things): let's just use the normal ascii ones
        '\u2018': "'", # left single quotation
        '\u2019': "'", # right single quotation
        '\u201c': '"', # left double quotation
        '\u201d': '"', # right double quotation
        '\u2026': '...', # ellipsis
        }

# unicode strings have their own 'translate' method so we just need a table:
UNICODE_CLEAN_TABLE = dict((ord(k), v) for k,v in list(WP_JUNK.items()))

