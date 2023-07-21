import re
from pathlib import Path

from bs4 import BeautifulSoup as bs


def process_links(indexhtml: str | Path) -> str:
    """
    ensures all links processed are internal. returns str
    """
    with Path(indexhtml).open() as idx:
        idxsoup = bs(idx, features="lxml")
        for a in idxsoup.findAll("a"):
            if re.match(r"title_\d{3}", a["href"]):
                continue
            else:
                linkid = a["id"].split("_")[1]
                a["href"] = "#title_{}".format(linkid)
        return str(idxsoup)

