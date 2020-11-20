# pchat
微信pc端python代码操控(欢迎提出问题，作者尽最大努力改进)  
先点个star吧
## 背景
1. 很多系统有监控群聊消息的需求
2. 大部分微信都登录不了网页版，python操纵微信的第三方库已无法使用，如itchat
3. 实时同步微信公众号文章，目前实现无非以下几种：
* 爬取搜狗搜索接口，但会被限制请求次数，不能实时同步，并且拿到的文章信息也不全
* 登录微信订阅号，爬取搜索文章接口，不能实时获取，有被封号封IP的风险
* 获取pc微信窗口点击公众号文章，再通过mitmproxy拦截请求，这种方法也实现不了实时获取，而且微信对阅读文章数有限制
* 通过登录网页版实时获取，大部分微信无法登录网页版，行不通

## 项目原理
接收消息： pc微信接收到消息 ---> 拦截工具拦截消息 ---> 发送到服务端  
发送消息： 服务端发送消息 ---> 拦截工具接收消息转发 ---> 发送到pc微信

## 项目介绍
1. 可以发送文字，图片，文件，实时获取消息(包括公众号推文)
2. 服务端可部署到外网服务器上
3. 服务端如果部署到其他机器上，发送文件，图片时，确保传入的路径在微信客户端存在，或者先把文件传到微信客户端机器上，再将路径发送过去
4. 服务端重启不会丢失已登录微信的个人消息，客户端重新连接即可
5. 可以接入多个微信客户端
6. 拦截工具按每个微信号一元一天收取费用
7. 添加微信付费后，作者会返回使用有效期，有效期内可以正常使用拦截功能
6. 具体消息类型的处理自行研究开发，如有需求可联系作者微信

## 环境配置：
客户端需要用window系统，服务端不受限制，Python3.2+, 服务端可以使用进程管理工具部署，如：supervisor

## 使用示例
1. 安装2.6.8.51版本微信（必须安装此版本）

2. 编写服务端代码
```python
from chat import Server, BaseChat


class MyChat(BaseChat):
    def receiver(self, msg):
        print("收到来自 %s 的消息：%s" % (msg['from'], msg['content']))


server = Server()
chat = MyChat(wx_nickname='Python开发')
server.bind(chat)  # 绑定登录的微信
server.run()
```

3. 打开拦截工具wechathelper.exe，输入服务端绑定的地址和端口

4. 点击启动按钮后，微信客户端会自动打开，登录与服务端绑定的微信号

5. 拦截工具为付费功能，一块钱一天，添加微信付费后即可使用
![](tools/使用教程.gif)
6. 具体业务需求可以看源码进行相应的开发，如：实现获取公众号消息，自动回复功能，聊天机器人等

## 其他语言开发
此项目为python语言开发，也可以用其他语言进行开发，
只需实现一个socket服务端即可接受到微信客户端的消息，根据消息格式进行相关逻辑的编写。  

如果服务端自己开发需要注意以下几点：
1. socket读取消息粘包和漏包的问题
2. 服务端崩溃时，重启后如果想保持正常使用，最好将微信个人信息，通讯录，这些登录时才能获取到的信息保存下来

## 声明
请勿使用该工具扰乱他人，或者违反法律，如被封号概不负责(请尽量使用小号)，使用此工具造成的法律纠纷，本人概不负责。  