import multiprocessing
import asyncio
import time

import requests

from IRC.irc_bot import IrcBot
from slack.client import SlackClient
from static import consts
from website import site
from database import log


def slack(queue):
    client = SlackClient(consts.SLACK_TOKEN)

    read_loop = asyncio.get_event_loop()
    while 1:
        rtm_socket_url = client.connect_to_rtm()

        try:
            val = read_loop.run_until_complete(
                client.start_workers(rtm_socket_url, queue)
            )
            log.log(val, 'main.slack')
        except RuntimeError as e:
            log.log(str(e), 'client.start_workers')
            read_loop.close()
            break


def irc(queue):
    client = IrcBot(name="slk_fwd")
    while 1:
        client.conn_to_sock(queue)
        client.login()
        client.read_msg_loop()
        # wait before reconnecting
        # may have to add max try later
        time.sleep(15)


def site_():
    site.main()


def is_network_down():
    try:
        # google's server ip (to avoid dns lookup)
        # will raise timeout exception if my internet sucks
        requests.get('http://173.194.113.103:80', timeout=5.0)
        return False
    except Exception as e:
        log.log(str(e), 'main.have_network_issues')
        return True


def did_ip_change(last_known_ip):
    try:
        resp = requests.get('http://ipecho.net/plain', timeout=5.0)
        if resp.status_code == 200:
            if last_known_ip != resp.text:
                log.log(
                    'IP changed ({} -> {})'.format(last_known_ip, resp.text),
                    'main.is_ip_unchanged'
                )
                return True
            else:
                return False
        else:
            return False
    except Exception:
        return False


def start_processes():
    queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=slack, args=(queue, ))
    p2 = multiprocessing.Process(target=irc, args=(queue, ))
    p3 = multiprocessing.Process(target=site_, args=())

    p1.start()
    p2.start()
    p3.start()

    return p1, p2, p3

if __name__ == '__main__':
    curr_ip = input('current ip: ')

    procs = start_processes()
    while 1:
        time.sleep(300)

        if is_network_down():
            for p in procs:
                p.terminate()
            while 1:
                time.sleep(60)
                if not is_network_down():
                    procs = start_processes()
                    # TODO: error handling
                    curr_ip = requests.get('http://ipecho.net/plain').text
                    break

        elif did_ip_change(last_known_ip=curr_ip):
            for p in procs:
                p.terminate()
            # router reconnected, can just restart everything
            procs = start_processes()
            # TODO: error handling
            curr_ip = requests.get('http://ipecho.net/plain').text
