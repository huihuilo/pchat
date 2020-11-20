"""
Time    : 2020/11/10 22:20
Author  : rhys
WeChat   : hhl871546539
"""

from concurrent.futures import ThreadPoolExecutor
import os


recv_size = 102400  # 读取信息大小
message_decollator = "卐hhl871546539卐"  # 分隔符

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'chats.db')  # 存储临时数据地址
db_connect_pool = ThreadPoolExecutor(10)  # sqlite连接池

# 创建数据表SQL语句
create_sql_personal = """
                CREATE TABLE "personal" (
                "id"  INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                "wx_id"  TEXT NOT NULL,
                "wx_nickname"  TEXT,
                "profile"  TEXT NOT NULL,
                "login"  INTEGER NOT NULL DEFAULT 1
                );"""

create_sql_address_book = """CREATE TABLE "address_book" (
                "id"  INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                "wx_id"  TEXT NOT NULL,
                "wx_nickname"  TEXT,
                "contacts"  TEXT NOT NULL
                );"""

create_sql_to_be_send = """CREATE TABLE "to_be_send" (
                "id"  INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                "wx_id"  TEXT,
                "wx_nickname"  TEXT,
                "message"  TEXT NOT NULL
                );
                """