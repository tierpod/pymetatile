#!/usr/bin/python

from collections import namedtuple
import sqlite3

from pyosm.point import Bound, Bounds

Metadata = namedtuple("Metadata", "center, format, bounds, minzoom, maxzoom")


class MBTileFile(object):
    """
    zoom_level = z
    tile_column = x
    tile_row = y
    """

    def __init__(self, filename, mode="rb"):
        if mode not in ("rb"):
            raise IOError("mode not supported:", mode)

        self.filename = filename
        self._conn = sqlite3.connect(filename)
        self._conn.row_factory = sqlite3.Row

        if mode == "rb":
            self.metadata = self._get_metadata()
            self.bounds = self._get_bounds()

    def _get_metadata(self):
        cur = self._conn.cursor()
        cur.execute("SELECT name, value FROM metadata")
        res = cur.fetchall()
        for row in res:
            if "center" in row:
                center = row["value"]
            if "format" in row:
                format_ = row["value"]
            if "bounds" in row:
                bounds = row["value"]
            if "minzoom" in row:
                minzoom = row["value"]
            if "maxzoom" in row:
                maxzoom = row["value"]

        return Metadata(center, format_, bounds, int(minzoom), int(maxzoom))

    def _get_bounds(self):
        result = []
        cur = self._conn.cursor()
        for z in range(self.metadata.minzoom, self.metadata.maxzoom + 1):
            cur.execute("SELECT min(tile_column) as min_x, max(tile_column) as max_x, "
                        "min(tile_row) as min_y, max(tile_row) as max_y "
                        "FROM tiles WHERE zoom_level=?", (z,))
            res = cur.fetchone()
            result.append(Bound(z, int(res["min_x"]), int(res["max_x"]),
                                int(res["min_y"]), int(res["max_y"]), flip_y=True))

        return Bounds(result)

    def __str__(self):
        return str(self.metadata)

    # with statement
    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def __contains__(self, item):
        return item in self.bounds

    def close(self):
        self._conn.close()

    def readtile(self, z, x, y):
        """Read tile data for z, x, y (int) coordinates from mbtiles file. Return bytes (str).

        >>> mb = open("tests/data/0.mbtiles")
        >>> data = mb.readtile(1, 1, 1)
        >>> print(len(data))
        26298
        >>> data = mb.readtile(999, 999, 999)
        Traceback (most recent call last):
            ...
        ValueError: data not found for given (z, x, y)
        """

        cur = self._conn.cursor()
        cur.execute("SELECT tile_data FROM tiles "
                    "WHERE zoom_level=? AND tile_row=? AND tile_column=?;", (z, x, y))
        res = cur.fetchone()
        if not res:
            raise ValueError("data not found for given (z, x, y)")

        return res["tile_data"]


def open(file, mode="rb"):
    """Wrapper around sqlite3.connect() functions. Returns MBTile file-like object.

    Available modes:
    - "rb": open for reading (default)

    Args:
        file (str): path to the file
        mode (str): mode in which the file is opened

    >>> from pyosm.point import ZXY
    >>> with open("tests/data/0.mbtiles") as mb:
    ...     print(mb)
    ...     print(mb.bounds.for_zoom(12))
    ...     print(ZXY(z=12, x=3281, y=1352) in mb)
    Metadata(center=u'108.4003,52.03223,9', format=u'png', \
bounds=u'108.3703,52.01723,108.4303,52.04723', minzoom=0, maxzoom=17)
    Bound(z:12 x:3281-3281 y:1352-1352)
    True
    """

    return MBTileFile(file, mode)