# https://work.weixin.qq.com/api/doc/90000/90136/91770

import httpx
import base64
import hashlib
import pathlib

def connect(webhook_url):
    return WechatWorkWebhook(webhook_url)

class WechatWorkWebhook:
    headers = {"Content-Type": "text/plain"}
    
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        
    def text(self, text, mentioned_list=[], mentioned_mobile_list=[]):
        data = {
              "msgtype": "text",
              "text": {
                  "content": text,
                  "mentioned_list": mentioned_list,
                  "mentioned_mobile_list": mentioned_mobile_list
              }
           }
        return httpx.post(self.webhook_url, headers=self.headers, json=data).json()
    
    def markdown(self, markdown):
        data = {
              "msgtype": "markdown",
              "markdown": {
                  "content": markdown
              }
           }
        return httpx.post(self.webhook_url, headers=self.headers, json=data).json()

    
    def image(self, image_path):
        with open(image_path, "rb") as image_file:
            image_base64 = str(base64.b64encode(image_file.read()), encoding='utf-8') 
        image_md5 = hashlib.md5(pathlib.Path(image_path).read_bytes()).hexdigest()

        data = {
              "msgtype": "image",
              "image": {
                 "base64": image_base64,
                 "md5": image_md5
              }
           }
        return httpx.post(self.webhook_url, headers=self.headers, json=data).json()
    
    def news(self, articles):
        data = {
              "msgtype": "news",
              "news": {
                  "articles": articles
              }
           }
        return httpx.post(self.webhook_url, headers=self.headers, json=data).json()

    def media(self, media_id):
        data = {
              "msgtype": "file",
              "file": {
                  "media_id": media_id
              }
           }
        return httpx.post(self.webhook_url, headers=self.headers, json=data).json()
    
    def upload_media(self, file_path):
        upload_url = self.webhook_url.replace('send', 'upload_media') + '&type=file'
        return httpx.post(upload_url, files=[('media', open(file_path, 'rb'))]).json()  

    def file(self, file_path):
        media_id = self.upload_media(file_path)['media_id']
        return self.media(media_id) 