import logging
import platform
import sys

from requests.__version__ import __version__ as requests_version
from stem import __version__ as stem_version

import sbws.core.cleanup
import sbws.core.flowctrl2
import sbws.core.generate
import sbws.core.scanner
import sbws.core.stats
from sbws import __version__ as version
from sbws.util.config import configure_logging, get_config, validate_config
from sbws.util.fs import check_create_dir, sbws_required_disk_space
from sbws.util.parser import create_parser

log = logging.getLogger(__name__)


def _ensure_dirs(conf):
    log.debug("Ensuring all dirs exists.")
    # It is needed to check sbws_home dir too to ensure that it has read
    # permission for other users, so that the bandwidth files can be read by
    # these other users.
    # Create all files and directories with permissions only for the current
    # user.
    if (
        not check_create_dir(conf.getpath("paths", "sbws_home"), v3bw=True)
        or not check_create_dir(conf.getpath("paths", "datadir"))
        or not check_create_dir(conf.getpath("paths", "v3bw_dname"), v3bw=True)
        or not check_create_dir(conf.getpath("paths", "log_dname"))
    ):
        sys.exit(1)


def _adjust_log_level(args, conf):
    if not args.log_level:
        return
    conf["logger_sbws"]["level"] = args.log_level


def _get_startup_line():
    py_ver = platform.python_version()
    py_plat = platform.platform()
    return "sbws %s with python %s on %s, stem %s, and requests %s" % (
        version,
        py_ver,
        py_plat,
        stem_version,
        requests_version,
    )


def main():
    parser = create_parser()
    args = parser.parse_args()
    conf = get_config(args)
    _adjust_log_level(args, conf)
    conf_valid, conf_errors = validate_config(conf)
    if not conf_valid:
        for e in conf_errors:
            log.critical(e)
        exit(1)
    # Create directories after the home have been obtained from the config.
    _ensure_dirs(conf)
    configure_logging(args, conf)
    parser.description = sbws_required_disk_space(conf)
    def_args = [args, conf]
    def_kwargs = {}
    known_commands = {
        "cleanup": {
            "f": sbws.core.cleanup.main,
            "a": def_args,
            "kw": def_kwargs,
        },
        "scanner": {
            "f": sbws.core.scanner.main,
            "a": def_args,
            "kw": def_kwargs,
        },
        "generate": {
            "f": sbws.core.generate.main,
            "a": def_args,
            "kw": def_kwargs,
        },
        "stats": {"f": sbws.core.stats.main, "a": def_args, "kw": def_kwargs},
        "flowctrl2": {
            "f": sbws.core.flowctrl2.main,
            "a": def_args,
            "kw": def_kwargs,
        },
    }
    try:
        if args.command not in known_commands:
            parser.print_help()
        else:
            log.info(_get_startup_line())
            comm = known_commands[args.command]
            exit(comm["f"](*comm["a"], **comm["kw"]))
    except KeyboardInterrupt:
        print("")
