import os
import uuid
import json
import hmac
import hashlib
import base64
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase

import http.client
import urllib.parse
import time
import uuid
from urllib import parse
class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
    
    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
    
    @staticmethod
    def create_token(access_key_id, access_key_secret):
        parameters = {'AccessKeyId': access_key_id,
                      'Action': 'CreateToken',
                      'Format': 'JSON',
                      'RegionId': 'cn-shanghai',
                      'SignatureMethod': 'HMAC-SHA1',
                      'SignatureNonce': str(uuid.uuid1()),
                      'SignatureVersion': '1.0',
                      'Timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      'Version': '2019-02-28'}
        # 构造规范化的请求字符串
        query_string = AccessToken._encode_dict(parameters)
        print('规范化的请求字符串: %s' % query_string)
        # 构造待签名字符串
        string_to_sign = 'GET' + '&' + AccessToken._encode_text('/') + '&' + AccessToken._encode_text(query_string)
        print('待签名的字符串: %s' % string_to_sign)
        # 计算签名
        secreted_string = hmac.new(bytes(access_key_secret + '&', encoding='utf-8'),
                                   bytes(string_to_sign, encoding='utf-8'),
                                   hashlib.sha1).digest()
        signature = base64.b64encode(secreted_string)
        print('签名: %s' % signature)
        # 进行URL编码
        signature = AccessToken._encode_text(signature)
        print('URL编码后的签名: %s' % signature)
        # 调用服务
        full_url = 'http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s' % (signature, query_string)
        print('url: %s' % full_url)
        # 提交HTTP GET请求
        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            key = 'Token'
            if key in root_obj:
                token = root_obj[key]['Id']
                expire_time = root_obj[key]['ExpireTime']
                return token, expire_time
        print(response.text)
        return None, None


class TTSProvider(TTSProviderBase):


    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        # 新增空值判断逻辑
        access_key_id = config.get("access_key_id")
        access_key_secret = config.get("access_key_secret")
        if access_key_id and access_key_secret:
            # 使用密钥对生成临时token
            token, expire_time = AccessToken.create_token(access_key_id, access_key_secret)
        else:
            # 直接使用预生成的长期token
            token = config.get("token")
            expire_time = None
        
        print('token: %s, expire time(s): %s' % (token, expire_time))

        self.appkey = config.get("appkey")
        self.token = token
        self.format = config.get("format", "wav")
        self.sample_rate = config.get("sample_rate", 16000)
        self.voice = config.get("voice", "xiaoyun")
        self.volume = config.get("volume", 50)
        self.speech_rate = config.get("speech_rate", 0)
        self.pitch_rate = config.get("pitch_rate", 0)

        self.host = config.get("host", "nls-gateway-cn-shanghai.aliyuncs.com")
        self.api_url = f"https://{self.host}/stream/v1/tts"
        self.header = {
            "Content-Type": "application/json"
        }

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "appkey": self.appkey,
            "token": self.token,
            "text": text,
            "format": self.format,
            "sample_rate": self.sample_rate,
            "voice": self.voice,
            "volume": self.volume,
            "speech_rate": self.speech_rate,
            "pitch_rate": self.pitch_rate
        }

        print(self.api_url, json.dumps(request_json, ensure_ascii=False))
        try:
            resp = requests.post(self.api_url, json.dumps(request_json), headers=self.header)
            # 检查返回请求数据的mime类型是否是audio/***，是则保存到指定路径下；返回的是binary格式的
            if resp.headers['Content-Type'].startswith('audio/'):
                with open(output_file, 'wb') as f:
                    f.write(resp.content)
                return output_file
            else:
                raise Exception(f"{__name__} status_code: {resp.status_code} response: {resp.content}")
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
