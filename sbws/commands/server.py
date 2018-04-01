from ..util.simpleauth import authenticate_client
from ..util.simpleauth import is_good_serverside_password_file
from sbws.globals import (fail_hard, is_initted)
from argparse import ArgumentDefaultsHelpFormatter
from threading import Thread
import socket
import time


def gen_parser(sub):
    sub.add_parser('server', formatter_class=ArgumentDefaultsHelpFormatter)


def read_line(s):
    ''' read until b'\n' is seen on the socket <s>. Return everything up until
    the newline as a str. If nothing can be read, return None. Note how that is
    different than if a newline is the first character; in that case, an empty
    str is returned '''
    chars = None
    while True:
        try:
            c = s.recv(1)
        except (ConnectionResetError, BrokenPipeError, socket.timeout) as e:
            log.info(e)
            return None
        if not c:
            return chars
        if chars is None:
            chars = ''
        if c == b'\n':
            break
        chars += c.decode('utf-8')
    return chars


def close_socket(s):
    try:
        log.info('Closing fd', s.fileno())
        s.shutdown(socket.SHUT_RDWR)
        s.close()
    except OSError:
        pass


def get_send_amount(sock):
    line = read_line(sock)
    try:
        send_amount = int(line)
    except (TypeError, ValueError):
        return None
    return send_amount


def write_to_client(sock, conf, amount):
    ''' Returns True if successful; else False '''
    log.info('Sending client no.', sock.fileno(), amount, 'bytes')
    while amount > 0:
        amount_this_time = min(conf.getint('server', 'max_send_per_write'),
                               amount)
        amount -= amount_this_time
        try:
            sock.send(b'a' * amount_this_time)
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log.info('fd', sock.fileno(), ':', e)
            return False
    return True


def new_thread(args, conf, sock):
    pw_file = conf.get('paths', 'passwords')

    def closure():
        if not authenticate_client(sock, pw_file, log.info):
            log.info('Client did not provide valid auth')
            close_socket(sock)
            return
        log.debug('Client authed successfully')
        while True:
            send_amount = get_send_amount(sock)
            if send_amount is None:
                log.info('Couldn\'t get an amount to send to', sock.fileno())
                close_socket(sock)
                return
            write_to_client(sock, conf, send_amount)
        close_socket(sock)
    thread = Thread(target=closure)
    return thread


def main(args, conf, log_):
    global log
    log = log_
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized. Try sbws init', log=log)

    pw_file = conf.get('paths', 'passwords')
    valid, error_reason = is_good_serverside_password_file(pw_file)
    if not valid:
        fail_hard(error_reason)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    h = (conf['server']['bind_ip'], conf.getint('server', 'bind_port'))
    log.notice('binding to', h)
    while True:
        try:
            server.bind(h)
        except OSError as e:
            log.warn(e)
            time.sleep(5)
        else:
            break
    log.notice('listening on', h)
    server.listen(5)
    try:
        while True:
            sock, addr = server.accept()
            log.info('accepting connection from', addr, 'as', sock.fileno())
            t = new_thread(args, conf, sock)
            t.start()
    except KeyboardInterrupt:
        pass
    finally:
        close_socket(server)