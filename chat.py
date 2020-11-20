"""
Time    : 2020/11/9 21:31
Author  : rhys
WeChat   :hhl871546539
"""
import os
import socket
import sqlite3
import time
from concurrent.futures.thread import ThreadPoolExecutor
from config import message_decollator, db_path, create_sql_personal, create_sql_address_book, create_sql_to_be_send, \
    recv_size
from helper import logger, save_profile, get_profile, save_contacts, delete_profile, delete_contacts, send_text, \
    send_image, send_file


class Server(object):
    """接收截取消息"""
    def __init__(self, client_nums=1, error_counts=50, dump_chat=True):
        """
        开启socket服务端，与截取消息工具进行通信，可部署到服务器上
        :param client_nums: 同时连接客户端数量
        :param error_counts: 错误次数，当同种错误达到一定次数，服务关闭
        :param dump_chat: 是否保存微信个人信息和通讯录到数据库，如果不保存，重启服务会出现丢失微信登录时加载的相关信息
        """
        self.client_nums = client_nums
        self.error_counts = error_counts
        self.dump_chat = dump_chat
        self.chat_pool = {}
        self.error_container = {}
        self.client_pool = ThreadPoolExecutor(self.client_nums * 3)
        self.db_init()

    def statistic_error(self, error):
        """统计错误次数，同种达到一定错误次数就终止服务"""
        error = str(error)
        count = self.error_container.get(error, 0)
        count += 1
        if count >= self.error_counts:
            logger.warn('同种错误发生次数达到最大')
            os._exit(0)
        self.error_container[error] = count

    def db_init(self):
        """初始化数据库"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("select name from sqlite_master where type='table' order by name;")
        tables = [row[0] for row in cursor.fetchall()]
        if 'personal' not in tables:
            cursor.execute(create_sql_personal)
        if 'address_book' not in tables:
            cursor.execute(create_sql_address_book)
        if 'to_be_send' not in tables:
            cursor.execute(create_sql_to_be_send)
        conn.commit()
        cursor.close()
        conn.close()

    def close_chat(self, chat, address):
        """退出微信时清除个人信息和释放相应资源"""
        delete_profile(chat.wx_id)
        delete_contacts(chat.wx_id)

    def chat_open(self, client, address):
        """监测客户端是否打开微信"""
        while not client._closed:
            try:
                message = self.get_message(client)
                if message:
                    event_type = message['event_type']
                    if event_type == '4':  # 登录成功
                        self.save_profile_to_chat(message)
                        self.register_monitor(message, client, address)
                        break
                    elif event_type == '1':  # 启动微信
                        logger.info('启动微信客户端<%s:%s>' % address)
                    elif event_type == '2':  # 退出微信
                        logger.info('退出微信客户端<%s:%s>' % address)
                        client.close()
                        break
                    elif event_type == '0':  # server重新启动后重新加载已登录的微信
                        self.reload_chat(message)
                        self.register_monitor(message, client, address, reconnect=True)
                        break
            except Exception as e:
                logger.exception(e)
                client.close()
                self.statistic_error(e)
                break

    def save_profile_to_chat(self, message):
        """保存个人信息到chat对象"""
        chat = self.get_chat(message['wx_id'], message['wx_nickname'])
        chat.profile = message
        chat.wx_id = message['wx_id']
        if self.dump_chat:
            save_profile(message)  # 保存到数据库

    def save_contacts_to_chat(self, message, chat):
        """保存通讯录到chat对象"""
        chat.contacts.setdefault(message['contacts_type'], []).append(message)
        if self.dump_chat:
            save_contacts(chat.wx_id, chat.wx_nickname, chat.contacts)

    def reload_chat(self, message):
        """服务重连时重新加载个人信息与通讯录"""
        chat = self.get_chat(message['wx_id'], message['wx_nickname'])
        chat.wx_id = message['wx_id']
        chat.wx_nickname = message['wx_nickname']
        chat.profile = get_profile(chat.wx_id)

    def register_monitor(self, message, client, address, reconnect=False):
        """登录成功后，开始监听消息的收发"""
        wx_id = message['wx_id']
        wx_nickname = message['wx_nickname']
        if not reconnect:
            logger.info('%s 登录成功<%s:%s>' % (wx_nickname, *address))
        else:
            logger.info('%s 重新连接成功<%s:%s>' % (wx_nickname, *address))
        chat = self.get_chat(wx_id, wx_nickname)
        if chat:
            chat.wx_id = wx_id
            chat.wx_nickname = wx_nickname
            self.client_pool.submit(chat.receive_handler, client, address, chat)  # 监控接收信息
            self.client_pool.submit(self.send_handler, client, chat)  # 监控发送信息
        else:
            raise KeyError('%s找不到对应的信息接收函数<%s:%s>, 请确认信息接收函数是否注册正确' % (wx_nickname, *address))

    def send_handler(self, client, chat):
        """循环查找是否有要发送的消息"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        while not client._closed:
            try:
                time.sleep(0.2)
                cursor.execute('select id, message from to_be_send where wx_id=? or wx_nickname=?', [chat.wx_id, chat.wx_nickname])
                all_data = cursor.fetchall()
                if all_data:
                    sended_row_ids = []
                    for row in all_data:
                        rowid, message = row
                        msg_type, recv_wxid, msg = message.split(message_decollator)
                        logger.info('%s ---> %s: (%s)%s' % (chat.wx_id, recv_wxid, msg_type, msg))
                        client.send(message.encode())
                        sended_row_ids.append(rowid)
                        time.sleep(0.1)
                    # 删除已发送的信息
                    base_sql = 'delete from to_be_send where id in (%s);' % ','.join(map(lambda x: '%s', sended_row_ids))
                    cursor.execute(base_sql % tuple(sended_row_ids))
                    conn.commit()
            except Exception as e:
                logger.exception(e)
                conn.rollback()
                # 这里实现返回错误信息给发送者
        cursor.close()
        conn.close()
        client.close()

    def receive_handler(self, client, address, chat):
        """监听收到的消息"""
        while not client._closed:
            try:
                message = self.get_message(client)
                if not message:
                    logger.info('已退出微信<%s:%s>' % address)
                    client.close()
                    self.close_chat(chat, address)  # 退出微信后清除登录信息
                    break
                if message['event_type'] == '6':  # 推送消息（个人，公众号，订阅号等）
                    chat.receiver(message)
                elif message['event_type'] == '5':  # 通讯录信息
                    self.save_contacts_to_chat(message, chat)
                elif message['event_type'] == '2':  # 退出微信
                    logger.info('已退出微信<%s:%s>' % address)
                    client.close()
                    self.close_chat(chat, address)  # 退出微信后清除登录信息
                    break
            except Exception as e:
                logger.exception(e)
                self.statistic_error(e)

    def get_message(self, client):
        """读取客户端消息"""
        data = client.recv(recv_size).decode()
        if data:
            message = {}
            for item in data.split('&'):
                k, v = item.split('=', 1)
                message[k] = v.replace(message_decollator, '&')
            return message

    def get_chat(self, wx_id, wx_nickname):
        """获取微信对象"""
        chat = self.chat_pool.get(wx_id) or self.chat_pool.get(wx_nickname)
        if not chat:
            raise ValueError('此微信号(wx_id: %s, wx_nickname: %s)没有与服务端绑定' % (wx_id, wx_nickname))
        return chat

    def bind(self, chat):
        """将Chat对象与服务绑定"""
        chat.receive_handler = self.receive_handler
        if chat.wx_id:
            self.chat_pool[chat.wx_id] = chat
        if chat.wx_nickname:
            self.chat_pool[chat.wx_nickname] = chat

    def run(self, host='localhost', port=8888):
        """监听连接并开启线程与客户端通信"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(self.client_nums)  # 设置客户端连接数
        logger.info('开启服务端，监听地址：%s:%s' % (host, port))
        while True:
            client, address = self.server.accept()
            self.client_pool.submit(self.chat_open, client, address)


class BaseChat(object):
    def __init__(self, wx_id=None, wx_nickname=None):
        """
        需要接收消息的微信对象，与server绑定进行信息收发的监控
        :param wx_id: 微信id
        :param wx_nickname: 微信昵称
        """
        assert wx_id or wx_nickname, "wx_id或wx_nickname参数必须有一个"
        self.wx_id = wx_id
        self.wx_nickname = wx_nickname
        self.profile = {}
        self.contacts = {}

    def get_profile(self):
        """获取微信个人信息"""
        return self.profile

    def get_friends(self):
        """获取好友"""
        return self.contacts.get('3', [])  # 1.群 2.公众号 3.好友

    def get_publics(self):
        """获取公众号"""
        return self.contacts.get('2', [])

    def get_groups(self):
        """获取群组"""
        return self.contacts.get('1', [])

    def receiver(self, msg):
        """
        接收消息函数，继承该类的子类必须实现此方法，msg为字典对象
        msg_type: 消息类型, 1:文本 3.图片 34.语音 42.个人名片 43.视频 47.动画表情 48.位置 49.公众号推送、文件、卡卷、网页分享、微信转账 10000.微信红包 （其他待补充）
        status: 0.接收 1.手机发送
        wxid1: 发送信息的微信id
        wxid2: 发送信息的微信id, 如果是个人信息为"_", 如果是群消息为发消息的微信id，wxid1则为群消息id
        receive_time: 接收信息时间
        content: 信息内容
        from: 信息发送者昵称，如果有备注则为备注
        event_type: 事件类型
        """
        raise NotImplementedError("无接收消息函数")

    def send_text(self, recv_wxid, msg):
        """发送文本信息"""
        send_text(recv_wxid, msg, self.wx_id)

    def send_image(self, recv_wxid, path):
        """发送图片"""
        send_image(recv_wxid, path, self.wx_id)

    def send_file(self, recv_wxid, path):
        """发送文件"""
        send_file(recv_wxid, path, self.wx_id)


if __name__ == '__main__':
    pass