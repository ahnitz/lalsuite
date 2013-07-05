#!/usr/bin/env python
#
# Copyright (C) 2012  Leo Singer <leo.singer@ligo.org>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
Prepare a summary or digest of a gravitational wave candidate in GraCEDb,
and provide functions to write it in different formats, including FITS HEALPix
image, VOEvent, JSON, and a 'mad libs' format suitable for the body of a
GCN circular.
"""
__author__ = "Leo Singer <leo.singer@ligo.org>"


# Configure logging.
import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("digest")


def get_digest(graceid):
    """Look up an event in GraCEDb by its event id and return a digest as dictionary."""
    from ligo.gracedb.rest import GraceDb
    from cStringIO import StringIO
    import glue.ligolw.utils as ligolw_utils
    import glue.ligolw.table as ligolw_table
    import glue.ligolw.lsctables as ligolw_lsctables
    from lalinference.bayestar import fits
    import tempfile
    import shutil

    client = GraceDb()
    log.info("started GraCEDb client")

    # Read the coinc.xml file.
    filename = "coinc.xml"
    try:
        infile = client.files(graceid, filename)
    except:
        log.exception("%s:could not retrieve %s", graceid, filename)
        raise
    log.info("%s:retrieved %s", graceid, filename)

    # Parse the file as LIGO-LW XML.
    xmldoc, digest = ligolw_utils.load_fileobj(infile)

    # Retrieve the tables that we need.
    process_table = ligolw_table.get_table(xmldoc, ligolw_lsctables.ProcessTable.tableName)
    coinc_inspiral_table = ligolw_table.get_table(xmldoc, ligolw_lsctables.CoincInspiralTable.tableName)
    sngl_inspiral_table = ligolw_table.get_table(xmldoc, ligolw_lsctables.SnglInspiralTable.tableName)

    # Retrieve values from the table that we need.
    snr = coinc_inspiral_table[0].snr
    false_alarm_rate = coinc_inspiral_table[0].false_alarm_rate
    geocent_end_time = coinc_inspiral_table[0].end_time + 1e-9 * coinc_inspiral_table[0].end_time_ns
    mchirp = coinc_inspiral_table[0].mchirp
    mtotal = coinc_inspiral_table[0].mass

    # Construct digest.
    digest = {
        "graceid": graceid,
        "detectors": [],
        "snr": snr,
        "false_alarm_rate": false_alarm_rate,
        "geocent_end_time": geocent_end_time,
        "mchirp": mchirp,
        "mtotal": mtotal
    }

    # Now try to retrieve skymap.
    filename = "skymap.fits.gz"
    try:
        infile = client.files(graceid, filename)
    except:
        log.exception("%s:could not retrieve %s", graceid, filename)
        raise

    log.info("%s:retrieved %s", graceid, filename)
    # FIXME: We have to save the retrieved file contents to a temporary
    # file on disk because PyFITS does not support gzip decompression from
    # file-like objects. The astropy.io.fits module does not have this
    # limitation; when Astropy becomes a little bit more mature, we could
    # get rid of this temporary file and just read the HEALPix map directly
    # from the HTTP response object.
    with tempfile.NamedTemporaryFile(suffix=".fits.gz", prefix="skymap") as tempfile:
        shutil.copyfileobj(infile, tempfile)
        tempfile.flush()
        tempfile.seek(0)
        skymap, metadata = fits.read_sky_map(tempfile.name)
    # Convert sky map from a Numpy array to a Python list, because
    # lists are JSON-serializable but Numpy arrays are not.
    digest["skymap"] = skymap.tolist()
    log.info("extracted HEALPix map")

    return digest


def put_digest_voevent(fileobj, digest):
    """Format the digest as a VOEvent and write to fileobj."""
    log.info("writing voevent")
    raise NotImplementedError


def put_digest_madlibs(fileobj, digest):
    """Format the digest in a human-readable form with commentary, suitable for
    the content of a GCN circular, and write to fileobj."""
    log.info("writing madlib")
    raise NotImplementedError


def put_digest_json(fileobj, digest):
    """Format the digest as JSON and write to fileobj."""
    import json
    log.info("writing json")
    json.dump(dict(digest), fileobj)


if __name__ == "__main__":
    import optparse
    import sys

    # Dictionary that maps command line arguments -> functions.
    putters = {
        "voevent": put_digest_voevent,
        "madlibs": put_digest_madlibs,
        "json": put_digest_json
    }

    default_putter = "json"

    # Command line interface.
    import optparse
    parser = optparse.OptionParser(description=__doc__,
        usage="%prog [options] [-o OUTPUT] GRACEID")
    parser.add_option("-o", "--output", metavar="FILE", help="Output file (default=stdout)")
    parser.add_option("-f", "--format", metavar="|".join(putters.keys()),
        choices=putters.keys(), default=default_putter,
        help="Digest format (default=%s)" % default_putter)

    opts, args = parser.parse_args()

    if len(args) > 1:
        parser.error("too many command line arguments")
    elif len(args) == 0:
        parser.error("not enough command line arguments")
    else:
        graceid = args[0]

    digest = get_digest(graceid)
    putter = putters[opts.format]

    if opts.output is None:
        fileobj = sys.stdout
    else:
        fileobj = open(opts.output, "w")

    putter(fileobj, digest)