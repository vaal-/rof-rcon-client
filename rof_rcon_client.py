# -*- coding: utf-8 -*-
import functools
import logging
import select
import six
import socket
import struct
import time
try:
    from urllib.parse import parse_qsl, unquote_plus
except ImportError:
    from urllib import unquote_plus
    from urlparse import parse_qsl


RESPONSE_STATUS = {
    '1': 'RCR_OK',
    '2': 'RCR_ERR_UNKNOWN',
    '3': 'RCR_ERR_UNKNOWN_COMMAND',
    '4': 'RCR_ERR_PARAM_COUNT',
    '5': 'RCR_ERR_RECVBUFFER',
    '6': 'RCR_ERR_AUTH_INCORRECT',
    '7': 'RCR_ERR_SERVER_NOT_RUNNING',
    '8': 'RCR_ERR_SERVER_USER',
    '9': 'RCR_ERR_UNKNOWN_USER',
    '10': 'RCR_ERR_PROTOCOL',
    '11': 'RCR_ERR_OUTBUFFER',
}

PLAYER_STATUS = {
    '0': 'PS_SPECTATOR',
    '1': 'PS_LOBBY_READY',
    '2': 'PS______NONE',
    '3': 'PS_DOGFIGHT_READY',
    '4': 'PS_CRAFTSITE_READY'
}


def auto_reconnect(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.auto_reconnect:
            try:
                return func(self, *args, **kwargs)
            except socket.error:
                self._reconnect()
                return func(self, *args, **kwargs)
        else:
            return func(self, *args, **kwargs)
    return wrapper


class RConClientError(Exception):
    pass


class RConClient(object):
    def __init__(self, login, password, host='localhost', port=8991,
                 auto_connect=True, auto_reconnect=True, logger=None,
                 conn_timeout=5, conn_max_attempts=10):
        self.address = (host, port)
        self.login = login
        self.password = password
        self.socket = None
        self.auto_reconnect = auto_reconnect
        # при попытке повторного подключения менее через 5 секунд
        #  - DServer не отвечает на команды RCon
        self.conn_timeout = conn_timeout
        self.conn_max_attempts = conn_max_attempts
        self._num_conn_attempts = 0
        self.logger = logger or logging.getLogger('rof_rcon_client')
        if auto_connect:
            self.connect()

    def connect(self):
        self.socket = socket.create_connection(self.address, timeout=5)
        self.logger.debug('rcon has connected to the server')
        self.auth()

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
            self.logger.debug('rcon has disconnected from the server')

    def _reconnect(self):
        self.disconnect()
        while self._num_conn_attempts <= self.conn_max_attempts:
            time.sleep(self.conn_timeout)
            self._num_conn_attempts += 1
            self.logger.warning('rcon has tried reconnected to the server, attempt {} of {}'
                                .format(self._num_conn_attempts, self.conn_max_attempts))
            try:
                self.connect()
                self._num_conn_attempts = 0
                self.logger.warning('rcon has reconnected to the server')
                break
            except socket.error:
                continue

    def _send_to_socket(self, data):
        if self.socket:
            select.select([], [self.socket], [])
            self.socket.sendall(data)
        else:
            raise socket.error('rcon socket connection broken')

    def _read_from_socket(self, length):
        select.select([self.socket], [], [])
        chunks = []
        while length > 0:
            chunk = self.socket.recv(length)
            if chunk == six.binary_type():
                raise socket.error('rcon socket connection broken')
            chunks.append(chunk)
            length -= len(chunk)
        return six.binary_type().join(chunks)

    @auto_reconnect
    def _command(self, command):
        command_utf8 = command.encode(encoding='utf8')
        data_length = len(command_utf8) + 1
        self._send_to_socket(struct.pack('h{}s'.format(data_length), data_length, command_utf8))
        self.logger.debug('rcon sent command [{}] to the server'.format(command))
        response_length = self._read_from_socket(2)
        # if response_length:
        data_length = struct.unpack('h', response_length)[0]
        response_data = self._read_from_socket(data_length)
        # if response_data:
        params = dict(parse_qsl(response_data[:-1].decode(encoding='utf8')))
        params['STATUS'] = RESPONSE_STATUS[params['STATUS']]
        if params['STATUS'] == 'RCR_OK':
            self.logger.debug('rcon received an response from the server\n{}'.format(params))
        else:
            self.logger.error('rcon received an error from the server\n{} => {}'.format(command, params['STATUS']))
            raise RConClientError(params['STATUS'])
        return params

    def auth(self):
        return self._command('auth {self.login} {self.password}'.format(**locals()))

    def get_my_status(self):
        return self._command('mystatus')

    def get_console_log(self):
        return self._command('getconsole')['console']

    def get_player_list(self):
        r = self._command('getplayerlist')
        players = []
        if 'playerList' in r:
            r = r['playerList'].split('|')
            headers = r[0].split(',')
            for line in r[1:]:
                player_dict = dict(zip(headers, line.split(',')))
                players.append({
                    'id': int(player_dict['cId']),
                    'status': PLAYER_STATUS[player_dict['ingameStatus']],
                    'ping': int(player_dict['nServerPing']),
                    'name': unquote_plus(player_dict['name']),
                    'account_id': unquote_plus(player_dict['playerId']),
                    'profile_id': unquote_plus(player_dict['profileId']),
                })
        return players

    def get_server_status(self):
        return self._command('serverstatus')

    def get_sps(self):
        return self._command('spsget')

    def reset_sps(self):
        return self._command('spsreset')

    def shutdown(self):
        return self._command('shutdown')

    def open_sds(self, path):
        return self._command('opensds {path}'.format(**locals()))

    def close_sds(self):
        return self._command('closesds')

    def kick_by_name(self, name):
        return self._command('kick name {name}'.format(**locals()))

    def kick_by_cid(self, client_id):
        return self._command('kick cid {client_id}'.format(**locals()))

    def kick_by_login(self, login):
        return self._command('kick playerid {login}'.format(**locals()))

    def kick_by_ids(self, ids):
        return self._command('kick profileid {ids}'.format(**locals()))

    def ban_by_name(self, name, ban_account=False):
        if ban_account:
            return self._command('banuser name {name}'.format(**locals()))
        else:
            return self._command('ban name {name}'.format(**locals()))

    def ban_by_cid(self, client_id, ban_account=False):
        if ban_account:
            return self._command('banuser cid {client_id}'.format(**locals()))
        else:
            return self._command('ban cid {client_id}'.format(**locals()))

    def ban_by_login(self, login, ban_account=False):
        if ban_account:
            return self._command('banuser playerid {login}'.format(**locals()))
        else:
            return self._command('ban playerid {login}'.format(**locals()))

    def ban_by_ids(self, ids, ban_account=False):
        if ban_account:
            return self._command('banuser profileid {ids}'.format(**locals()))
        else:
            return self._command('ban profileid {ids}'.format(**locals()))

    def unban_all(self):
        return self._command('unbanall')

    def server_input(self, trigger):
        return self._command('serverinput {trigger}'.format(**locals()))

    def send_stat_now(self):
        return self._command('sendstatnow')

    def cut_chat_log(self):
        return self._command('cutchatlog')

    def send_chat_msg_to_all(self, msg):
        return self._command('chatmsg 0 -1 {msg}'.format(**locals()))

    def send_chat_msg_to_coal(self, msg, coalition):
        return self._command('chatmsg 1 {coalition} {msg}'.format(**locals()))

    def send_chat_msg_to_country(self, msg, country):
        return self._command('chatmsg 2 {country} {msg}'.format(**locals()))

    def send_chat_msg_to_client(self, msg, client):
        return self._command('chatmsg 3 {client} {msg}'.format(**locals()))
