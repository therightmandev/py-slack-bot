import multiprocessing
import asyncio
import time
import logging

import requests

from IRC import irc_bot
from slack import client
from static import consts


def slack(queue):
    logger = client.set_logger()
    clnt = client.SlackClient(consts.SLACK_TOKEN, logger=logger)

    read_loop = asyncio.get_event_loop()
    while 1:
        rtm_socket_url = clnt.connect_to_rtm()
        logger.info('RTM entry point: {}'.format(rtm_socket_url))
        try:
            val = read_loop.run_until_complete(
                clnt.start_workers(rtm_socket_url, queue)
            )
        except RuntimeError as e:
            logger.warning(e)
            read_loop.close()
            break


def irc(queue):
    irc_logger = irc_bot.set_logger()
    client = irc_bot.IrcBot(name="slk_fwd", logger=irc_logger)
    while 1:
        client.conn_to_sock(queue)
        client.login()
        client.read_msg_loop()
        irc_logger.info('Irc Module returned, trying to reconnect in 15 sec')

        # may have to add max try later
        time.sleep(15)
        irc_logger.info('trying to reconnect')


def is_network_down():
    url = 'http://google.com'
    resp = process_get_request(url)
    return resp == ''


def did_ip_change(last_known_ip):
    url = 'http://ipecho.net/plain'
    resp = process_get_request(url)
    if resp.startswith('Error'):
        logger.warning('Current ip unknown. HTTP response: {}'.format(resp))
        return False
    return resp != last_known_ip


def start_processes():
    queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=slack, args=(queue, ))
    p2 = multiprocessing.Process(target=irc, args=(queue, ))

    proc = (p1, p2)
    for p in proc:
        p.start()
        logger.info('Process started: {}\tPID: {}'.format(p, p.pid))

    return proc


def process_get_request(uri, timeout=6.0):
    try:
        response = requests.get(uri, timeout=timeout)
    except requests.ConnectionError as e:
        logging.error('Network problem:', e)
        return ''
    except requests.Timeout as e:
        logging.error('Request timed out:', e)
        return ''
    else:
        if response.status_code == 200:
            logging.debug('Response from {}: {}'.format(uri, response.text))
            return response.text
        else:
            logging.warning('Response error code from {}: {}'.format(uri, response.status_code))
            return 'Error:', response.status_code


def set_logger():
    import logging
    log_level = {'debug': logging.DEBUG,
                 'info': logging.INFO,
                 'error': logging.ERROR}
    logging.basicConfig(filename=consts.LOG_FILE, level=log_level[consts.LOG_LEVEL])
    return logging.getLogger(__name__)

if __name__ == '__main__':
    logger = set_logger()

    curr_ip = input('current ip: ')
    logger.info('Current IP set to: {}'.format(curr_ip))

    procs = start_processes()
    while 1:
        time.sleep(300)

        if is_network_down():
            for p in procs:
                p.terminate()
                logger.info('Terminated: {}\tPID: {}'.format(p, p.pid))
            while 1:
                time.sleep(120)
                if not is_network_down():
                    procs = start_processes()
                    curr_ip = process_get_request('http://ipecho.net/plain')
                    logger.debug('Current IP set to: {}'.format(curr_ip))
                    break

        elif did_ip_change(last_known_ip=curr_ip):
            for p in procs:
                p.terminate()
                logger.info('Terminated: {}\tPID: {}'.format(p, p.pid))
            # router reconnected, can just restart everything
            procs = start_processes()
            curr_ip = process_get_request('http://ipecho.net/plain')
            logger.debug('Current IP set to: {}'.format(curr_ip))
