"""
Time    : 2020/11/10 22:19
Author  : rhys
WeChat   : hhl871546539
"""
import json
import sqlite3
import datetime
from config import message_decollator, db_path, db_connect_pool
import traceback


class Logger(object):
    def __init__(self):
        self.now = datetime.datetime.now
        self.fmt = "%Y-%m-%d %H:%M:%S"

    def info(self, msg):
        print('\033[0;30m[%s INFO] %s\033[0m' % (self.now().strftime(self.fmt), msg))

    def debug(self, msg):
        print('\033[0;37m[%s DEBUG] %s\033[0m' % (self.now().strftime(self.fmt), msg))

    def warn(self, msg):
        print('\033[0;33m[%s WARNING] %s\033[0m' % (self.now().strftime(self.fmt), msg))

    def error(self, msg):
        print('\033[0;31m[%s ERROR] %s\033[0m' % (self.now().strftime(self.fmt), msg))

    def exception(self, e):
        error_stack = traceback.format_exc()
        print('\033[0;31m[%s EXCEPTION] %s\033[0m' % (self.now().strftime(self.fmt), error_stack))


logger = Logger()



def save_profile(message):
    """保存微信个人信息"""
    def execute(message):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            'insert into personal(wx_id, wx_nickname, profile) values (?, ?, ?)',
            [message['wx_id'], message['wx_nickname'], json.dumps(message)]
        )
        conn.commit()
        cursor.close()
        conn.close()
    db_connect_pool.submit(execute, message)


def get_profile(wx_id):
    """获取微信个人信息"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('select profile from personal where wx_id="%s" and login=1' % wx_id)
    profile = json.loads(cursor.fetchone()[0])
    cursor.close()
    conn.close()
    return profile


def delete_profile(wx_id):
    """删除微信个人信息"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('delete from personal where wx_id="%s"' % wx_id)
    conn.commit()
    cursor.close()
    conn.close()


def save_contacts(wx_id, wx_nickname, contacts):
    """保存微信通讯录，异步保存，避免粘包"""
    def execute(wx_id, wx_nickname, contacts):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('select id from address_book where wx_id="%s"' % wx_id)
        row = cursor.fetchone()
        if row:
            cursor.execute(
                'update address_book set wx_nickname=?, contacts=? where id=?',
                [wx_nickname, json.dumps(contacts), row[0]]
            )
        else:
            cursor.execute(
                'insert into address_book(wx_id, wx_nickname, contacts) values (?, ?, ?)',
                [wx_id, wx_nickname, json.dumps(contacts)]
            )
        conn.commit()
        cursor.close()
        conn.close()
    db_connect_pool.submit(execute, wx_id, wx_nickname, contacts)


def delete_contacts(wx_id):
    """删除通讯录"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('delete from address_book where wx_id="%s"' % wx_id)
    conn.commit()
    cursor.close()
    conn.close()


def chat_send(message, wx_id=None, wx_nickname=None):
    """发送微信消息"""
    assert wx_id or wx_nickname, 'wx_id 和 wx_nickname必须指明一个'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('insert into to_be_send(wx_id, wx_nickname, message) values(?, ?, ?)', [wx_id, wx_nickname, message])
    conn.commit()
    cursor.close()
    conn.close()


def send_text(recv_wxid, text, wx_id=None, wx_nickname=None):
    """发送文字信息"""
    chat_send(message_decollator.join(('SendText', recv_wxid, text)), wx_id, wx_nickname)


def send_image(recv_wxid, path, wx_id=None, wx_nickname=None):
    """发送图片"""
    chat_send(message_decollator.join(('SendImag', recv_wxid, path)), wx_id, wx_nickname)


def send_file(recv_wxid, path, wx_id=None, wx_nickname=None):
    """发送文件"""
    chat_send(message_decollator.join(('SendFile', recv_wxid, path)), wx_id, wx_nickname)


if __name__ == '__main__':
    logger.info('info: 这是有颜色的文字')
    logger.debug('debug: 这是有颜色的文字')
    logger.warn('warn: 这是有颜色的文字')
    logger.error('error: 这是有颜色的文字')