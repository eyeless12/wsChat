#!/usr/bin/env python3
import json
from enum import Enum

import aiohttp
from aiohttp import web

MTYPE = 'mtype'
ID = 'id'
TEXT = 'text'
IDTO = 'to'


class MType(Enum):
    MSG = 0
    DM = 1
    USER_ENTER = 2
    USER_LEAVE = 3
    INIT = 4
    TEXT = 5


class WSChat:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.conns = {}

    async def main_page(self, request):
        return web.FileResponse('./index_.html')

    async def handler(self, request):
        app = request.app
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        while True:
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == "ping":
                    await ws.send_str(json.dumps("pong"))
                    continue
                msg, msg_type, to = await self.parse_message(msg.data, ws)
                if msg_type is MType.DM:
                    await self.send_to(msg, to)
                else:
                    await self.send_for_all_except(msg, ws)

            elif msg.type == aiohttp.WSMsgType.CLOSE:
                break

        user_id = self.get_user(ws)
        user_left = {'mtype': MType.USER_LEAVE.name, 'id': user_id}
        await self.send_for_all_except(json.dumps(user_left), ws)
        self.conns.pop(user_id)

        return ws

    async def parse_message(self, request, ws):
        message = json.loads(request)
        if message[MTYPE] == MType.INIT.name:
            self.conns[message[ID]] = ws
            answer = {'mtype': MType.USER_ENTER.name, 'id': message[ID]}
            return json.dumps(answer), MType.INIT, None
        if message[MTYPE] == MType.TEXT.name:
            answer = dict()
            if message[IDTO]:
                answer[MTYPE] = MType.DM.name
                answer[IDTO] = message[IDTO]
            else:
                answer[MTYPE] = MType.MSG.name
            answer[ID] = message[ID]
            answer[TEXT] = message[TEXT]
            print(json.dumps(answer))
            return json.dumps(answer), MType.DM if IDTO in answer else MType.MSG, answer[ID] if IDTO in answer else None

    async def send_for_all_except(self, message, sender):
        for user in self.conns.values():
            if user != sender:
                await user.send_str(message)

    async def send_to(self, message, to):
        await self.conns[to].send_str(message)

    def get_user(self, ws):
        for user in self.conns:
            if self.conns[user] == ws:
                return user

    def run(self):
        app = web.Application()

        app.router.add_get('/', self.main_page)
        app.router.add_get('/chat', self.handler)
        web.run_app(app, host=self.host, port=self.port)


if __name__ == '__main__':
    WSChat().run()
