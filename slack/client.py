import json
import time
import asyncio
import uuid

import requests
import websockets
from requests import models

from static import consts
from database import log
from slack import dispatcher


class HttpException(Exception):
    """ custom exception class for failed HTTP requests """
    def __init__(self, error: str, resp: requests.models.Response =None):
        self.error = error
        if resp is not None:
            self.headers = resp.headers
        else:
            self.headers = ''

    def __str__(self):
        return self.error + str(self.headers)


def process_http_status(response):
    error_codes = {
        400: 'Bad request',
        401: 'Unauthorized',
        403: 'Forbidden',
        429: 'Too many requests',
        404: 'Page not found',
        500: 'Internal server error',
        503: 'Service unavailable'
    }
    status = response.status_code
    if status != 200:
        if status in error_codes:
            raise HttpException(error_codes[status], response)
        else:
            raise HttpException('unknown error with code: {}'.format(status))


class SlackClient(object):
    def __init__(self, token):
        self.token = token

        self.websock = None
        self.reconn_uri = ''
        self.worker_msg_queue = None

        self.last_msg_arrived = 0
        self.last_msg_sent = time.time()
        self.PENDING_MSGS = {}
        # every user in the team ('userid': 'username')
        self.USERS = {}

    @staticmethod
    def post_msg(username: str, text: str, channel: str = consts.CH_IRC_CHAT):
        requests.get("https://slack.com/api/chat.postMessage", params={'token': consts.SLACK_TOKEN,
                                                                       'channel': channel,
                                                                       'username': username,
                                                                       'text': text
                                                                       })

    def remove_from_pending_msgs(self, int_id: str):
        self.PENDING_MSGS.pop(int_id, None)

    async def append_to_pending_msgs(self, body: dict, int_id: str):
        self.PENDING_MSGS[int_id] = body
        await asyncio.sleep(5)

        popped = self.PENDING_MSGS.pop(int_id, None)
        if popped is not None:
            await self.send_msg(popped, int_id)

    async def ping(self):
        """
        send a ping message every 60 seconds
        if last message arrived more than 150 secs ago, try to reconnect
        """
        while 1:
            await asyncio.sleep(60)
            if self.websock.open:
                await self.websock.send(json.dumps({'type': 'ping', 'id': str(uuid.uuid4())}))
            else:
                log.log('{} -- {}'.format(self.websock.close_code, self.websock.close_reason), 'client.ping')
                return "WS is {}".format(self.websock.state_name)

            if (time.time() - self.last_msg_arrived) > 150:
                await self.websock.close()
                return "Last msg arrived 150+ secs ago"

    async def send_msg(self, body: dict, int_id: str='1'):
        body['id'] = int_id
        body['type'] = 'message'
        body['token'] = self.token

        reply = json.dumps(body)

        asyncio.ensure_future(self.append_to_pending_msgs(body, int_id))
        delay = self.last_msg_sent + consts.SLACK_MSG_DELAY - time.time()
        if delay > 0:
            await asyncio.sleep(delay)

        await self.websock.send(reply)
        self.last_msg_sent = time.time()

    def api_call(self, method: str, params: dict =None):
        if params is not None:
            params['token'] = self.token
        else:
            params = {'token': self.token}
        uri = 'https://slack.com/api/{}'.format(method)

        resp = requests.post(uri, data=params)
        try:
            process_http_status(resp)
            return json.loads(resp.text)
        except HttpException as e:
            log.log(str(e), 'slack.client.api_call + {}'.format(method))
            return {}

    def connect_to_rtm(self):
        args = {'simple_latest': 1, 'no_unreads': 1}
        client_info = self.api_call("rtm.start", args)

        if client_info.get('ok'):
            self.USERS = {user.get('id'): user.get('name') for user in client_info['users']}
            return client_info['url']
        else:
            log.log("Couldn't connect to Slack's RTM API, will try again in 3 secs", 'connect_to_rtm')
            time.sleep(3)
            return self.connect_to_rtm()

    async def rtm_listen(self):
        """ read websocket, toss msg in the queue, if needed """
        while 1:
            msg = await self.websock.recv()
            if msg is None:
                log.log('slack closed the connection', 'client.rtm_listen')
                return 'None received'
            self.last_msg_arrived = time.time()

            msg = json.loads(msg)

            if 'reply_to' in msg:
                if msg.get('ok'):
                    self.remove_from_pending_msgs(msg['reply_to'])
                continue

            if msg.get('user') == 'USLACKBOT' or msg.get('subtype') == 'bot_message':
                continue

            if msg.get('type') == 'message' and len(msg) == 6:
                if msg.get('subtype') == 'me_message':
                    text = '/me {}'.format(msg.get('text', ''))
                else:
                    text = msg.get('text', '')
                internal_id = str(uuid.uuid4())

                await self.worker_msg_queue.put(
                    (text,
                     msg.get('user', ''),
                     msg.get('channel', ''),
                     internal_id)
                )
            elif msg.get('type') == 'hello':
                log.log('RTM session started', '')
            elif msg.get('type') == 'reconnect_url':
                self.reconn_uri = msg.get('url')

    async def start_workers(self, uri, queue):
        self.websock = await websockets.connect(uri)
        self.worker_msg_queue = asyncio.Queue(maxsize=50)

        asyncio.ensure_future(
            dispatcher.disp_msg(self.worker_msg_queue, self, queue)
        )
        asyncio.ensure_future(
            self.rtm_listen()
        )
        return await self.ping()