"""Utils file system functions"""

import logging
import os
import shutil

log = logging.getLogger(__name__)

DISK_SPACE_TEXT = """
Disk space requirements
-----------------------
v3bw files: the maximum space required is ~{mb_bw} MB, after {d_bw} days.
result files: the maximum space required is ~{mb_results} MB, after {d_r} days.
tor directory: the space required is ~{mb_tor} MB.
code and dependencies: the space required is ~{mb_code} MB
Total disk space required is: ~{mb_total} MB
"""


def check_create_file(path: str, v3bw: bool = False) -> (None, str):
    if not os.path.exists(path):
        return path
    if os.path.islink(path):
        log.critical("Path %s is a symlink.", path)
        return None
    if not os.stat(path).st_uid == os.getuid():
        try:
            os.chown(path, os.getuid(), os.getgid())
        except PermissionError as e:
            log.critical("Can not change owner of %s: %s", path, e)
            return None
    if v3bw:
        if not oct(os.stat(path).st_mode)[-3:] == "644":
            try:
                os.chmod(path, 0o644)
                log.critical("4")
            except PermissionError as e:
                log.critical("Can not change permissions of %s: %s", path, e)
                return None
    elif not oct(os.stat(path).st_mode)[-3:] == "600":
        try:
            os.chmod(path, 0o600)
            log.critical("3")
        except PermissionError as e:
            log.critical("Can not change permissions of %s: %s", path, e)
            return None
    return path


def check_create_dir(path: str, v3bw: bool = False) -> (None, str):
    process_uid = os.getuid()
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
    except PermissionError as e:
        log.critical("Can not create %s: %s", path, e)
        return None
    if not os.stat(path).st_uid == process_uid:
        try:
            os.chown(path, process_uid, os.getgid())
        except PermissionError as e:
            log.critical("Can not change owner of %s: %s", path, e)
            return None
    # `/var/lib/sbws` (not `.sbws`), is created by the system so do not change
    # permissions
    if path == "/var/lib/sbws":
        st = os.stat(path)
        if not (oct(st.st_mode)[-1] == "5" or oct(st.st_mode)[-1] == "7"):
            log.critical("Parent dir is not readable or executable")
            return None
    elif v3bw:
        if not oct(os.stat(path).st_mode)[-3:] == "755":
            try:
                # bandit report Severity: Medium, CWE: CWE-732 on this line,
                # but other users other than the one running this must be able
                # to read the files to publish them.
                os.chmod(path, 0o755)  # nosec
                log.error("2")
            except PermissionError as e:
                log.critical("Can not change permissions of %s: %s", path, e)
                return None
    elif not oct(os.stat(path).st_mode)[-3:] == "700":
        try:
            os.chmod(path, 0o700)
            log.error("1")
        except PermissionError as e:
            log.critical("Can not change permissions of %s: %s", path, e)
            return None
    return path


def sbws_required_disk_space(conf):
    """Disk space required by sbws files.
    Rough calculations.

    :param ConfigParser conf: sbws configuration
    :returns: int, size in MB
    """
    text_dict = {}
    # Number of relays per line average size in Bytes
    size_v3bw_file = 7500 * 220
    # default crontab configuration will run genenerate every hour
    num_v3bw_files_day = 24
    # ~1000 is the length of a line when the result is successful
    # ~4550 is the number of lines of the biggest result file
    size_result_file = 4550 * 1000
    num_result_files_day = 1
    space_v3bw_files_day = size_v3bw_file * num_v3bw_files_day
    space_result_files_day = size_result_file * num_result_files_day
    size_compressed_files = 600 * 1024
    # default crontab configuration will run cleanup once a day
    # default cleanup configuration will compress v3bw files after 1 day
    # and delete them after 7 days
    v3bw_compress_after_days = conf.getint(
        "cleanup", "v3bw_files_compress_after_days"
    )
    v3bw_delete_after_days = conf.getint(
        "cleanup", "v3bw_files_delete_after_days"
    )
    v3bw_max_space_after_delete = (
        space_v3bw_files_day * v3bw_compress_after_days
    ) + (size_compressed_files * num_v3bw_files_day * v3bw_delete_after_days)
    text_dict["mb_bw"] = round(v3bw_max_space_after_delete / 1000**2)
    text_dict["d_bw"] = v3bw_delete_after_days
    # default crontab configuration will run cleanup once a day
    # default cleanup configuration will compress v3bw files after 1 day
    # and delete them after 7 days
    results_compress_after_days = conf.getint(
        "cleanup", "data_files_compress_after_days"
    )
    results_delete_after_days = conf.getint(
        "cleanup", "data_files_delete_after_days"
    )
    results_max_space_after_delete = (
        space_result_files_day * results_compress_after_days
    ) + (
        size_compressed_files * num_v3bw_files_day * results_delete_after_days
    )
    text_dict["mb_results"] = round(results_max_space_after_delete / 1000**2)
    text_dict["d_r"] = results_delete_after_days
    # not counted rotated files and assuming that when it is not rotated the
    # size will be approximately 10MiB
    space_log_files = 0
    if conf.getboolean("logging", "to_file"):
        size_log_file = conf.getint("logging", "to_file_max_bytes")
        num_log_files = conf.getint("logging", "to_file_num_backups")
        space_log_files = size_log_file * num_log_files
    text_dict["mb_log"] = space_log_files
    # roughly, size of a current tor dir
    size_tor_dir = 19828000
    text_dict["mb_tor"] = round(size_tor_dir / 1000**2)
    # roughly, the size of this code and dependencies
    size_code_deps = 2097152
    text_dict["mb_code"] = round(size_code_deps / 1000**2)
    # Multiply per 2, just in case
    size_total = (
        results_max_space_after_delete
        + v3bw_max_space_after_delete
        + space_log_files
        + size_tor_dir
        + size_code_deps
    ) * 2
    text_dict["mb_total"] = round(size_total / 1000**2)
    space_text = DISK_SPACE_TEXT.format(**text_dict)
    return space_text


def df(path):
    # Not being used, since it makes a disk space system call and some
    # systems might not allow it
    """Return space left on device where path is in MiB."""
    return round(shutil.disk_usage(path).free / (1024**2))


def is_low_space(conf):
    # Not being used, since it makes a disk space system call and some
    # systems might not allow it
    """Warn and return True when the space left on the device is less than
    what is needed for sbws and False otherwise needs.
    """
    disk_required_mb = sbws_required_disk_space(conf)
    disk_avail_mb = df(conf.getpath("paths", "sbws_home"))
    if disk_avail_mb < disk_required_mb:
        log.warning(
            "The space left on the device (%s MiB) is less than "
            "the minimum recommended to run sbws (%s MiB)."
            "Run sbws cleanup to delete old sbws generated files.",
            disk_avail_mb,
            disk_required_mb,
        )
        return True
    return False
