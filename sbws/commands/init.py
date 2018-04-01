from sbws.globals import (G_INIT_FILE_MAP, is_initted, fail_hard)
from sbws.util.config import get_user_example_config
from argparse import ArgumentDefaultsHelpFormatter
import os
import shutil


def gen_parser(sub):
    p = sub.add_parser('init', formatter_class=ArgumentDefaultsHelpFormatter)


def main(args, conf, log_):
    global log
    log = log_
    if is_initted(args.directory):
        fail_hard('Directory already seems to be initted', log=log)

    if not os.path.isdir(args.directory):
        log.info('Creating', args.directory)
        os.makedirs(args.directory, exist_ok=False)

    config_fname = os.path.join(args.directory, 'config.ini')
    c = get_user_example_config()
    c['paths']['sbws_home'] = args.directory
    log.info('Creating', config_fname)
    with open(config_fname, 'wt') as fd:
        c.write(fd)

    for src, dst, ftype in G_INIT_FILE_MAP:
        dst = os.path.join(args.directory, dst)
        if os.path.exists(dst):
            log.warn(dst, 'already exists, not overwriting')
            continue
        if ftype == 'file':
            log.info('Creating', dst, '({})'.format(ftype))
            try:
                shutil.copy(src, dst)
            except PermissionError as e:
                log.warn('Unable to create {}: {}'.format(dst, e))
        else:
            fail_hard('Cannot init ftype', ftype)