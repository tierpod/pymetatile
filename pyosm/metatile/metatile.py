#!/usr/bin/python
"""Provides metatile description based on OSM and mod_tile:
https://wiki.openstreetmap.org/wiki/Meta_tiles
https://github.com/openstreetmap/mod_tile
"""

import os.path
import re

from pyosm.point import Point
from pyosm.buffer import Buffer

# metatile size
META_SIZE = 8
# metatile extension
META_EXT = ".meta"
META_URL_RE = re.compile(r"(\w+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)\.meta")


class Metatile(object):
    """Attributes:
        z, x, y (int): zoom coordinate
        hashes (list of 5 int): metatile hashes
        style (str): style name
        ext (str): metatile extension (".meta")
    """

    def __init__(self, z, hashes, style):
        self.z = z
        self.hashes = hashes
        self.style = style
        self.ext = META_EXT
        self.x, self.y = hashes_to_xy(hashes)
        self.max_x = self.x + len(self) - 1
        self.max_y = self.y + len(self) - 1

    def __str__(self):
        return "Metatile(z:{z}, x:{x}-{max_x}, y:{y}-{max_y}, style:{style})".format(
            **self.__dict__)

    def points(self):
        """Returns list of all points inside metatile."""

        x, y = self.x, self.y
        return [Point(xx, yy) for xx in range(x, self.max_x + 1) for yy in range(y, self.max_y + 1)]

    def __iter__(self):
        return iter(self.points())

    def __next__(self):
        return self.next()

    def next(self):
        return next(self)

    def filepath(self, basedir=""):
        """Calculates metatile filepath using basedir (str).

        >>> mt = Metatile.from_url("mapname/10/0/1/2/3/4.meta")
        >>> print(mt.filepath("/cache"))
        /cache/mapname/10/0/1/2/3/4.meta
        """

        h0 = str(self.hashes[0])
        h1 = str(self.hashes[1])
        h2 = str(self.hashes[2])
        h3 = str(self.hashes[3])
        h4 = str(self.hashes[4])
        return os.path.join(basedir, self.style, str(self.z), h0, h1, h2, h3, h4 + self.ext)

    def __len__(self):
        """Calculates min size of tiles with data inside metatile.

        >>> from pyosm.tile import Tile
        >>> mt = Metatile.from_tile(Tile(z=1, x=1, y=1, style="mapname"))
        >>> print(len(mt))
        2
        """

        return min(META_SIZE, 1 << self.z)

    def __contains__(self, tile):
        """Returns True if tile (tile.Tile) inside Metatile.

        >>> from pyosm.tile import Tile
        >>> mt = Metatile.from_tile(Tile(z=10, x=696, y=320, style="", ext=".png"))
        >>> Tile(z=10, x=696, y=320, style="", ext=".png") in mt
        True
        >>> Tile(z=10, x=703, y=327, style="", ext=".png") in mt
        True
        >>> Tile(z=10, x=704, y=328, style="", ext=".png") in mt
        False
        >>> Tile(z=10, x=695, y=319, style="", ext=".png") in mt
        False
        """

        if tile.style != self.style:
            return False

        if tile.z != self.z:
            return False

        if tile.x < self.x or tile.x > self.max_x:
            return False

        if tile.y < self.y or tile.y > self.max_y:
            return False

        return True

    def __eq__(self, metatile):
        """Return True if metatile (pyosm.metatile.Metatile) equals to Metatile.

        >>> mt1 = Metatile.from_url("mapname/10/0/0/33/180/128.meta")
        >>> mt2 = Metatile.from_url("mapname/10/0/0/33/180/128.meta")
        >>> mt3 = Metatile.from_url("mapname/10/0/0/33/180/0.meta")
        >>> mt1 == mt2
        True
        >>> mt1 == mt3
        False
        """

        if self.style != metatile.style:
            return False

        if self.z != metatile.z:
            return False

        if self.x != metatile.x:
            return False

        if self.y != metatile.y:
            return False

        return True

    @classmethod
    def from_url(cls, url):
        """Creates new Metatile from metatile url (str with format style/z/h0/h1/h2/h3/h4.meta).

        >>> print(Metatile.from_url("mapname/10/0/0/33/180/128.meta"))
        Metatile(z:10, x:696-703, y:320-327, style:mapname)
        """

        match = META_URL_RE.search(url)
        if not match:
            raise ValueError("unable to covert uri to Metatile")

        style, z, h0, h1, h2, h3, h4 = match.groups()
        hashes = [int(h0), int(h1), int(h2), int(h3), int(h4)]

        return Metatile(z=int(z), hashes=hashes, style=style)

    @classmethod
    def from_tile(cls, t):
        """Create new Metatile from pyosm.point.Tile object.

        >>> from pyosm.tile import Tile
        >>> tile = Tile(z=10, x=697, y=321, style="mapname")
        >>> print(Metatile.from_tile(tile))
        Metatile(z:10, x:696-703, y:320-327, style:mapname)
        """

        hashes = xy_to_hashes(t.x, t.y)
        return Metatile(z=t.z, hashes=hashes, style=t.style)


def hashes_to_xy(hashes):
    """Calculates metatile x, y (int) coordinates from hashes (list of 5 ints). Returns Point(x, y).
    """

    x = 0
    y = 0

    for i in range(5):
        x <<= 4
        y <<= 4
        x |= (hashes[i] & 0xf0) >> 4
        y |= (hashes[i] & 0x0f)

    return Point(x, y)


def xy_to_hashes(x, y):
    """Calculates metatile hashes (list of 5 ints) from x, y (int) coordinates."""

    hashes = []
    x = x & ~(META_SIZE - 1)
    y = y & ~(META_SIZE - 1)

    for _ in range(5):
        hashes.append(((x & 0x0f) << 4) | (y & 0x0f))
        x >>= 4
        y >>= 4
    hashes.reverse()

    return hashes


def bound_to_metatiles(bound, style=""):
    """Split bound (pyosm.point.Bound) to list of pyosm.metatile.Metatile. Returns iterator.

    >>> from pyosm.point import Bound
    >>> bound = Bound(z=10, min_x=692, min_y=318, max_x=703, max_y=324)
    >>> metatiles = bound_to_metatiles(bound, style="mapname")
    >>> for mt in metatiles:
    ...     print(mt)
    Metatile(z:10, x:688-695, y:312-319, style:mapname)
    Metatile(z:10, x:688-695, y:320-327, style:mapname)
    Metatile(z:10, x:696-703, y:312-319, style:mapname)
    Metatile(z:10, x:696-703, y:320-327, style:mapname)
    """

    buf = Buffer()
    for point in bound.points():
        hashes = xy_to_hashes(point.x, point.y)
        metatile = Metatile(z=bound.z, hashes=hashes, style=style)
        if metatile not in buf:
            buf.append(metatile)
            yield metatile
