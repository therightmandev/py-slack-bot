import asyncio
import re

from static import consts
from slack import functions


def remove_smileys(msg: str) -> str:
    convert = {':smile:': ':)', ':simple_smile:': ':)', ':disappointed:': ':(', ':stuck_out_tongue:': ':P',
               ':heart:': '<3'}
    for smiley in re.compile(r':\S+:').findall(msg):
        if smiley in convert:
            msg = msg.replace(smiley, convert[smiley])
        else:
            msg = msg.replace(' {}'.format(smiley), '')
    return msg


def format_irc_msg(msg: str, userid: str, slack_client) -> str:
    if msg.startswith('&gt; '):
                msg = '> ' + msg[5:]
    msg = remove_smileys(msg)
    msg = msg.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

    if msg.startswith('$'):
        return msg
    else:
        return '<{}> {}'.format(slack_client.USERS.get(userid, ''), msg)


async def disp_msg(inc_queue: asyncio.queues.Queue, slack_client, queue):
    pattern = r'has (left|joined) the channel'
    join_pattern = r'<@(\w{9})\|(\w+)> has joined the channel'

    irc_socket, irc_channel = None, ''

    while 1:
        msg, userid, ch, int_id = await inc_queue.get()

        first_word = msg.split(' ', 1)[0]
        func = functions.FUNCTION_LIST.get(first_word)

        if func is not None:
            body = func[0](**{'ch': ch,
                              'msg': msg,
                              'sender_id': userid,
                              'slack_client': slack_client})
            if body == '':
                continue
            else:
                await slack_client.send_msg(body, int_id)

        elif ch == consts.CH_IRC_CHAT:
            if re.search(pattern, msg) is None:
                formatted_msg = format_irc_msg(msg, userid, slack_client)
                if not queue.empty():
                    for _ in range(queue.qsize()):
                        irc_socket, irc_channel = queue.get()
                irc_socket.send('PRIVMSG {} :{}\r\n'.format(irc_channel, formatted_msg).encode('utf8'))

        elif ch == consts.CH_GENERAL:
            newcommer = re.search(join_pattern, msg)

            if newcommer is not None and newcommer.group(1) not in slack_client.USERS:
                # append userlist with the new guy ('id': 'name')
                slack_client.USERS[newcommer.group(1)] = newcommer.group(2)

                body = functions.greet_new_user(newcommer.group(1), newcommer.group(2), slack_client)
                await slack_client.send_msg(body, int_id)
                body2 = functions.notify_mods(newcommer.group(2))
                await slack_client.send_msg(body2)
