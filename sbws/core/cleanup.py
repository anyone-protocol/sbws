"""Util functions to cleanup disk space."""
import gzip
import logging
import os
import shutil
import stat
import time
from argparse import ArgumentDefaultsHelpFormatter
from datetime import datetime, timedelta

from sbws.globals import fail_hard
from sbws.util.filelock import DirectoryLock
from sbws.util.timestamp import unixts_to_dt_obj

log = logging.getLogger(__name__)


def gen_parser(sub):
    """
    Helper function for the broader argument parser generating code that adds
    in all the possible command line arguments for the cleanup command.

    :param argparse._SubParsersAction sub: what to add a sub-parser to
    """
    d = (
        "Compress and delete results and/or v3bw files old files."
        "Configuration options are read to determine which are old files"
    )
    p = sub.add_parser(
        "cleanup", description=d, formatter_class=ArgumentDefaultsHelpFormatter
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually compress or delete anything",
    )
    p.add_argument(
        "--no-results", action="store_true", help="Do not clean results files"
    )
    p.add_argument(
        "--no-v3bw", action="store_true", help="Do not clean v3bw files"
    )


def _get_files_mtime_older_than(dname, days_delta, extensions):
    """Return file descriptors which modification time is older than days_delta
    and which extension is one of the extensions."""
    today = datetime.utcfromtimestamp(time.time())
    oldest_day = today - timedelta(days=days_delta)
    # By default, `os.walk`` doesn't follow symlinks.
    # (https://docs.python.org/3/library/os.html#os.walk)
    for root, dirs, files in os.walk(dname):
        for f in files:
            fname = os.path.join(root, f)
            _, ext = os.path.splitext(fname)
            if ext not in extensions:
                log.debug(
                    "Ignoring %s because its extension is not in " "%s",
                    fname,
                    extensions,
                )
                continue
            # using file modification time instead of parsing the name
            # of the file.
            # `os.stat` follows sysmlinks by default
            # (https://docs.python.org/3/library/os.html#os.stat)
            filedt = unixts_to_dt_obj(
                os.stat(fname, follow_symlinks=False).st_mtime
            )
            if filedt < oldest_day:
                try:
                    fileobj = open(fname, "r")
                except FileNotFoundError:  # eg: symlink to non existing file.
                    pass
                else:
                    yield fileobj


def _delete_files(dname, file_descriptors, dry_run=True):
    """Delete the files passed as argument."""
    with DirectoryLock(dname):
        for fd in file_descriptors:
            log.info("Deleting %s", fd.name)
            # Ensure fname isn't a symlink even if `files` are obtained via
            # `os.walk`.
            if not dry_run and not stat.S_ISLNK(os.stat(fd.fileno()).st_mode):
                fd.close()
                os.remove(fd.name)


def _compress_files(dname, file_descriptors, dry_run=True):
    """Compress the files passed as argument."""
    with DirectoryLock(dname):
        for fd in file_descriptors:
            log.info("Compressing %s", fd.name)
            # Ensure fname isn't a symlink even if `files` are obtained via
            # `os.walk`.
            if dry_run or stat.S_ISLNK(os.stat(fd.fileno()).st_mode):
                continue
            out_fname = fd.name + ".gz"
            with gzip.open(out_fname, "wt") as out_fd:
                shutil.copyfileobj(fd, out_fd)
            fd.close()
            os.remove(fd.name)


def _check_validity_periods_v3bw(compress_after_days, delete_after_days):
    if 1 <= compress_after_days and compress_after_days < delete_after_days:
        return True
    fail_hard(
        "v3bw files should only be compressed after 1 day and deleted "
        "after a bigger number of days."
    )


def _clean_v3bw_files(args, conf):
    v3bw_dname = conf.getpath("paths", "v3bw_dname")
    compress_after_days = conf.getint(
        "cleanup", "v3bw_files_compress_after_days"
    )
    delete_after_days = conf.getint("cleanup", "v3bw_files_delete_after_days")
    _check_validity_periods_v3bw(compress_after_days, delete_after_days)
    # first delete so that the files to be deleted are not compressed first
    file_descriptors_to_delete = _get_files_mtime_older_than(
        v3bw_dname, delete_after_days, [".v3bw", ".gz"]
    )
    _delete_files(v3bw_dname, file_descriptors_to_delete, dry_run=args.dry_run)
    file_descriptors_to_compress = _get_files_mtime_older_than(
        v3bw_dname, compress_after_days, [".v3bw"]
    )
    # when dry_run is true, compress will also show all the files that
    # would have been deleted, since they are not really deleted
    _compress_files(
        v3bw_dname, file_descriptors_to_compress, dry_run=args.dry_run
    )


def _clean_result_files(args, conf):
    datadir = conf.getpath("paths", "datadir")
    compress_after_days = conf.getint(
        "cleanup", "data_files_compress_after_days"
    )
    delete_after_days = conf.getint("cleanup", "data_files_delete_after_days")

    # first delete so that the files to be deleted are not compressed first
    files_to_delete = _get_files_mtime_older_than(
        datadir, delete_after_days, [".txt", ".gz"]
    )
    _delete_files(datadir, files_to_delete, dry_run=args.dry_run)

    # when dry_run is true, compress will also show all the files that
    # would have been deleted, since they are not really deleted
    files_to_compress = _get_files_mtime_older_than(
        datadir, compress_after_days, [".txt"]
    )
    _compress_files(datadir, files_to_compress, dry_run=args.dry_run)


def main(args, conf):
    """
    Main entry point in to the cleanup command.

    :param argparse.Namespace args: command line arguments
    :param configparser.ConfigParser conf: parsed config files
    """
    if not args.no_results:
        _clean_result_files(args, conf)

    if not args.no_v3bw:
        _clean_v3bw_files(args, conf)
