import socket
import re

from static import consts
from slack import client


class IrcBot:
    def __init__(self, serv=consts.IRC_SERVER, ch=consts.IRC_CHANNEL, name=consts.IRC_NAME):
        self.server = serv
        self.channel = ch
        self.name = name
        self.sock = None
        self.pattern = r":(\w+).+PRIVMSG {} :(.+)".format(ch)

    def send_msg(self, msg):
        self.sock.send('PRIVMSG {} :{}\r\n'.format(self.channel, msg).encode('utf-8'))

    def pong(self, answer):
        self.sock.send("PONG {}\r\n".format(answer).encode('utf-8'))

    def read_msg_loop(self):
        while 1:
            data = self.sock.recv(2048)
            if len(data) == 0:
                self.sock.close()
                return
            try:
                msg = data.decode()
            except UnicodeDecodeError:
                continue
            msg = msg.strip("\r\n")
            match = re.match(self.pattern, msg)
            if match is not None:
                text = match.group(2)

                # "/me checks time" message would be displayed as "\x01ACTION: checks time\x01" in slack
                # double "_" converts to italics, text[1:8] is "ACTION "
                if text.startswith(b'\x01'.decode()) and text.endswith(b'\x01'.decode()):
                    text = '_' + text[8:-1] + '_'

                client.SlackClient.post_msg(username=match.group(1), text=text)

            elif msg.startswith("PING :") != -1:
                self.pong(msg.split()[1])

    def login(self):
        self.sock.send("USER {} {} {} :{}\r\n".format(self.name, 'host', 'server', consts.IRC_NAME).encode('utf-8'))
        self.sock.send("NICK {}\r\n".format(self.name).encode('utf-8'))
        self.sock.send("JOIN {}\r\n".format(self.channel).encode('utf-8'))

    def conn_to_sock(self, queue):
        # TODO: check if freenode supports ipv6
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server, 6667))
        # other end of the queue: slack.dispatcher (so it can forward slack -> irc messages)
        queue.put((self.sock, self.channel))

if __name__ == "__main__":
    pass
