import socket
import re

from static import consts
from slack import client


class IrcBot:
    def __init__(self, serv=consts.IRC_SERVER, ch=consts.IRC_CHANNEL, name=consts.IRC_NAME, logger=None):
        self.server = serv
        self.channel = ch
        self.name = name
        self.sock = None
        self.pattern = r":(\w+).+PRIVMSG {} :(.+)".format(ch)

        self.logger = logger

    def send_msg(self, msg):
        msg = 'PRIVMSG {} :{}\r\n'.format(self.channel, msg).encode('utf-8')
        self.logger.debug('>>> OUTGOING MSG >>>: {}'.format(msg))
        self.sock.send(msg)

    def pong(self, answer):
        msg = "PONG {}\r\n".format(answer).encode('utf-8')
        self.logger.debug('>>> OUTGOING MSG >>>: {}'.format(msg))
        self.sock.send(msg)

    def read_msg_loop(self):
        while 1:
            data = self.sock.recv(2048)
            if len(data) == 0:
                self.logger.info('<<< INCOMING DATA <<<: 0 data, socket closes')
                self.sock.close()
                return
            try:
                msg = data.decode()
            except UnicodeDecodeError:
                continue
            msg = msg.strip("\r\n")
            self.logger.debug('<<< INCOMING DATA <<<: {}'.format(msg))
            match = re.match(self.pattern, msg)
            if match is not None:
                text = match.group(2)
                self.logger.debug('<<< INCOMING MSG <<<: {}'.format(msg))

                # "/me checks time" message would be displayed as "\x01ACTION: checks time\x01" in slack
                # double "_" converts to italics, text[1:8] is "ACTION "
                if text.startswith(b'\x01'.decode()) and text.endswith(b'\x01'.decode()):
                    text = '_' + text[8:-1] + '_'

                client.SlackClient.post_msg(username=match.group(1), text=text)

            elif msg.startswith("PING :"):
                self.pong(msg.split()[1])

    def login(self):
        messages = [
            "USER {} {} {} :{}\r\n".format(self.name, 'host', 'server', consts.IRC_NAME).encode('utf-8'),
            "NICK {}\r\n".format(self.name).encode('utf-8'),
            "JOIN {}\r\n".format(self.channel).encode('utf-8')
        ]
        for msg in messages:
            self.logger.debug('>>> OUTGOING MSG >>>: {}'.format(msg))
            self.sock.send(msg)

    def conn_to_sock(self, queue):
        # TODO: check if freenode supports ipv6
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server, 6667))
        # other end of the queue: slack.dispatcher (so it can forward slack -> irc messages)
        queue.put((self.sock, self.channel))


def set_logger():
    import logging
    log_level = {'debug': logging.DEBUG,
                 'info': logging.INFO,
                 'error': logging.ERROR}
    logging.basicConfig(filename=consts.LOG_FILE, level=log_level[consts.LOG_LEVEL])
    return logging.getLogger(__name__)

if __name__ == "__main__":
    pass
