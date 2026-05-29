# coding: utf-8
import base64
import hashlib
import hmac
import json
from urllib.parse import urlparse
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import websocket
import _thread as thread

class Ws_Param(object):
    # WebSocket参数处理类，用于生成星火大模型API的认证URL
    def __init__(self, APPID, APIKey, APISecret, gpt_url):
        # 初始化WebSocket参数
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(gpt_url).netloc
        self.path = urlparse(gpt_url).path
        self.gpt_url = gpt_url

    def create_url(self):
        # 创建带有认证信息的WebSocket URL
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 构建签名原始字符串
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        # 使用hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        # 构建授权信息
        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        # 拼接鉴权参数，生成最终URL
        url = self.gpt_url + '?' + urlencode(v)
        return url

# 全局变量用于存储返回结果
result_content = ""

# 处理WebSocket收到的消息
def on_message(ws, message):
    global result_content
    # 解析返回的JSON数据
    data = json.loads(message)
    code = data['header']['code']
    # 检查是否有错误
    if code != 0:
        print(f'请求错误: {code}, {data}')
        ws.close()
    else:
        # 提取返回内容并累加到结果中
        choices = data["payload"]["choices"]
        status = choices["status"]
        content = choices["text"][0]["content"]
        result_content += content
        # status为2表示会话结束
        if status == 2:
            ws.close()

# 生成请求参数
def gen_params(appid, query, domain):
    # 构造发送给模型的请求数据
    data = {
        "header": {
            "app_id": appid,
            "uid": "1234",
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": 0.5,      # 控制输出随机性
                "max_tokens": 4096,      # 最大生成token数量
                "auditing": "default",   # 内容审核设置
            }
        },
        "payload": {
            "message": {
                "text": [{"role": "user", "content": query}]
            }
        }
    }
    return data

# 处理WebSocket连接建立
def on_open(ws):
    # 在新线程中发送请求数据
    thread.start_new_thread(run, (ws,))

# 发送请求数据到WebSocket服务器
def run(ws, *args):
    data = json.dumps(gen_params(appid=ws.appid, query=ws.query, domain=ws.domain))
    ws.send(data)

def call_spark_ai(query):
    """
    调用星火大模型AI函数，返回AI的回答内容

    Args:
        query (str): 要向AI询问的字符串

    Returns:
        str: AI的回答内容
    """
    global result_content
    # 清空之前的结果
    result_content = ""

    # 配置参数
    appid = "2ee660b1"
    api_secret = "N2M5ZTJiMGMwZTY3ZmQ0OGFmMDgxNDJj"
    api_key = "3dca5052038bbbb860f2de3e794eaab0"
    spark_url = "wss://spark-api.xf-yun.com/chat/max-32k"
    domain = "max-32k"

    # 创建WebSocket参数对象
    wsParam = Ws_Param(appid, api_key, api_secret, spark_url)
    # 生成认证URL
    wsUrl = wsParam.create_url()

    # 创建WebSocket应用
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_open=on_open)
    # 设置自定义属性
    ws.appid = appid
    ws.query = query
    ws.domain = domain
    # 启动WebSocket连接
    ws.run_forever()

    # 返回AI的回答内容
    return result_content

# 使用示例
# result = call_spark_ai("明天成都天气怎么样")
# print(result)
