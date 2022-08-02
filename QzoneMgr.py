import base64
import json
import logging
from select import select
import threading
import time
from datetime import datetime
import re

import requests

EMOTION_INFO_API = "https://user.qzone.qq.com/proxy/domain/r.qzone.qq.com/cgi-bin/user/qz_opcnt2?_stp={" \
                   "}&unikey=http://user.qzone.qq.com/{}/mood/{}&face=0&fupdate=1 "


def image_base64(image_path):
    pic = open(image_path, "rb")
    pic_base64 = base64.b64encode(pic.read())

    pic.close()
    return str(pic_base64)[2:-1]


def generate_gtk(skey):
    """生成gtk"""
    hash_val = 5381
    for i in range(len(skey)):
        hash_val += (hash_val << 5) + ord(skey[i])
    return str(hash_val & 2147483647)


def get_picbo_and_richval(upload_result):
    json_data = upload_result
    if json_data['ret'] != 0:
        raise Exception("上传图片失败")
    picbo_spt = json_data['data']['url'].split('&bo=')
    if len(picbo_spt) < 2:
        raise Exception("上传图片失败")
    picbo = picbo_spt[1]

    richval = ",{},{},{},{},{},{},,{},{}".format(json_data['data']['albumid'], json_data['data']['lloc'],
                                                 json_data['data']['sloc'], json_data['data']['type'],
                                                 json_data['data']['height'], json_data['data']['width'],
                                                 json_data['data']['height'], json_data['data']['width'])

    return picbo, richval


class RefreshQzoneTokenException(Exception):
    pass


class QzoneOperator:
    """Qzone内容管理类"""
    uin = 0
    cookie_dict = {}
    cookie = ""
    qzone_token = ""

    gtk = ""
    gtk2 = ""

    headers = {
        'User-Agent': 'User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/69.0.3497.100 Safari/537.36',
    }

    cookie_invalidated_callback = None

    keepalive_proxy_thread = None

    def __init__(self, uin, cookie, keepalive=True, cookie_invalidated_callback=None):
        self.cookie_invalidated_callback = cookie_invalidated_callback
        self.__reset(uin, cookie, keepalive)
        logging.info("QzoneOperator初始化完成:uin={}".format(uin))

    def __reset(self, uin, cookie, keepalive):
        global inst

        if uin is None or cookie is None:
            raise Exception('需提供uin和cookie')
        if not isinstance(uin, int):
            raise Exception('uin必须是整数')
        if ("skey" not in cookie) or ("p_skey" not in cookie):
            raise Exception("cookie必须包含skey和p_skey")
        self.uin = uin
        self.cookie = cookie
        cookies = cookie.split(';')
        for cookie in cookies:
            cookie_pair = cookie.strip().split('=')
            if len(cookie_pair) >= 2:
                self.cookie_dict[cookie_pair[0]] = cookie_pair[1]

        self.gtk = generate_gtk(self.cookie_dict['skey'])
        self.gtk2 = generate_gtk(self.cookie_dict['p_skey'])

        # if self.keepalive_proxy_thread!=None:
        #     self.keepalive_proxy_thread.terminate()

        # print(self.cookie_dict)

        inst = self

        self.refresh_qzone_token(attempt=5)

        if keepalive:
            self.keepalive_proxy_thread = threading.Thread(target=self.__keepalive, args=(), daemon=True)
            self.keepalive_proxy_thread.start()

    def __keepalive(self):
        global inst
        while True:
            if inst != self:
                return  # 如果不是当前实例，则退出
            if self.qzone_token == 'invalidated':
                return
            try:
                self.refresh_qzone_token(attempt=10)
            except RefreshQzoneTokenException:
                self.keepalive_proxy_thread = None
                return
            time.sleep(600)

    def refresh_qzone_token(self, attempt=1):
        """刷新qzone_token
        :return: 尝试次数
        :except: 刷新失败
        """
        for i in range(attempt):
            try:
                response = requests.get(
                    url="https://h5.qzone.qq.com/feeds/inpcqq",
                    params={"uin": self.uin, "qqver": 5749, "timestamp": int(datetime.now().timestamp() * 1000)},
                    headers=self.headers, cookies=self.cookie_dict)
                if response.status_code == 200:
                    tokens = re.findall(r'window.g_qzonetoken.*try{return "(.*?)";} catch\(e\)', response.text)
                    if len(tokens) > 0:
                        self.qzone_token = tokens[0]
                        return i + 1
            except Exception as e:
                continue
        self.cookie_invalidated_callback()
        self.qzone_token = 'invalidated'
        raise RefreshQzoneTokenException("刷新qzone_token失败")

    def upload_image_file(self, file_path):
        b64 = image_base64(file_path)
        return self.upload_image(b64)

    def upload_image(self, b64_image):
        """上传图片"""
        self.headers['referer'] = 'https://user.qzone.qq.com/' + str(self.uin)
        self.headers['origin'] = 'https://user.qzone.qq.com'

        res = requests.post(url="https://up.qzone.qq.com/cgi-bin/upload/cgi_upload_image",
                            params={"g_tk": self.gtk2, "qzonetoken": self.qzone_token, "uin": self.uin},
                            data={
                                "filename": "filename",
                                "zzpanelkey": "",
                                "uploadtype": "1",
                                "albumtype": "7",
                                "exttype": "0",
                                "skey": self.cookie_dict["skey"],
                                "zzpaneluin": self.uin,
                                "p_uin": self.uin,
                                "uin": self.uin,
                                "p_skey": self.cookie_dict['p_skey'],
                                "output_type": "json",
                                "qzonetoken": self.qzone_token,
                                "refer": "shuoshuo",
                                "charset": "utf-8",
                                "output_charset": "utf-8",
                                "upload_hd": "1",
                                "hd_width": "2048",
                                "hd_height": "10000",
                                "hd_quality": "96",
                                "backUrls": "http://upbak.photo.qzone.qq.com/cgi-bin/upload/cgi_upload_image,http://119.147.64.75/cgi-bin/upload/cgi_upload_image",
                                "url": "https://up.qzone.qq.com/cgi-bin/upload/cgi_upload_image?g_tk=" + self.gtk2,
                                "base64": "1",
                                "picfile": b64_image,
                            })
        if res.status_code == 200:
            return eval(res.text[res.text.find('{'):res.text.rfind('}') + 1])
        else:
            raise Exception("上传图片失败")

    def publish_emotion(self, text='', images=None, image_type='path'):
        """发表说说
        :return: 说说tid
        :except: 发表失败
        """

        if images is None:
            images = []

        # 检查qzone_token是否存在
        if self.qzone_token == "":
            self.refresh_qzone_token(attempt=10)

        base64_images = images

        # 包装request
        self.headers['referer'] = 'https://user.qzone.qq.com/' + str(self.uin)
        self.headers['origin'] = 'https://user.qzone.qq.com'

        post_data = {

            "syn_tweet_verson": "1",
            "paramstr": "1",
            "who": "1",
            "con": text,
            "feedversion": "1",
            "ver": "1",
            "ugc_right": "1",
            "to_sign": "0",
            "hostuin": self.uin,
            "code_version": "1",
            "format": "json",
            "qzreferrer": "https://user.qzone.qq.com/" + str(self.uin)
        }

        if len(images) > 0:
            # 转换成base64
            if image_type == 'path':
                base64_images = [image_base64(image) for image in images]

            # 挨个上传图片
            pic_bos = []
            richvals = []
            for base64_image in base64_images:
                uploadresult = self.upload_image(base64_image)
                picbo, richval = get_picbo_and_richval(uploadresult)
                pic_bos.append(picbo)
                richvals.append(richval)

            post_data['pic_bo'] = ','.join(pic_bos)
            post_data['richtype'] = '1'
            post_data['richval'] = '\t'.join(richvals)

        res = requests.post(
            url="https://user.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_publish_v6",
            params={
                'g_tk': self.gtk2,
                'qzonetoken': self.qzone_token,
                'uin': self.uin,
            },
            cookies=self.cookie_dict,
            data=post_data)
        if res.status_code == 200:
            return res.json()['tid']
        else:
            raise Exception("发表说说失败: " + res.text)

    def delete_emotion(self, tid):
        """删除说说
        :return: 请求结果
        :except: 删除说说失败
        """

        # 检查qzone_token是否存在
        if self.qzone_token == "":
            self.refresh_qzone_token(attempt=10)

        self.headers['referer'] = 'https://user.qzone.qq.com/' + str(self.uin)
        self.headers['origin'] = 'https://user.qzone.qq.com'
        self.headers["cookie"] = "; ".join(["{}={}".format(key, value) for key, value in self.cookie_dict.items()])

        post_data = {
            "uin": self.uin,
            "topicId": str(self.uin) + "_" + tid + "__1",
            "feedsType": 0,
            "feedsFlag": 0,
            "feedsKey": tid,
            "feedsAppid": 311,
            "feedsTime": int(datetime.now().timestamp()),
            "fupdate": 1,
            "ref": "feeds",
            "qzreferrer": "https://user.qzone.qq.com/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds_html_module?g_iframeUser=1&i_uin={}&i_login_uin={}&mode=4&previewV8=1&style=35&version=8&needDelOpr=true&transparence=true&hideExtend=false&showcount=5&MORE_FEEDS_CGI=http%3A%2F%2Fic2.s8.qzone.qq.com%2Fcgi-bin%2Ffeeds%2Ffeeds_html_act_all&refer=2&paramstring=os-winxp|100".format(
                self.uin, self.uin),
        }

        res = requests.post(
            url="https://h5.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_delete_v6",
            params={
                "g_tk": self.gtk2,
            },
            data=post_data,
            cookies=self.cookie_dict)
        if res.status_code == 200:
            if res.text.__contains__("请先登录空间"):
                raise Exception("删除失败:请先登录空间")
            return res.text
        else:
            raise Exception("删除失败: " + res.text)

    def update_emotion(self,tid,text=''):
        """更新说说(仅支持修改文字)"""

        # 检查qzone_token是否存在
        if self.qzone_token == "":
            self.refresh_qzone_token(attempt=10)

        # 包装request
        self.headers['referer'] = 'https://user.qzone.qq.com/' + str(self.uin)+"/infocenter"
        self.headers['origin'] = 'https://user.qzone.qq.com'

        
        post_data = {
            "syn_tweet_verson": "1",
            'tid':tid,
            "paramstr": "1",
            'pic_template':'',
            'richtype':'',
            'richval':'',
            'special_url':'',
            'subrichtype':'',
            "con": text,
            "feedversion": "1",
            "ver": "1",
            "ugc_right": "1",
            "to_sign": "0",
            'ugcright_id':tid,
            "hostuin": self.uin,
            "code_version": "1",
            "format": "fs",
            "qzreferrer": "https://user.qzone.qq.com/" + str(self.uin)+"/infocenter"
        }

        res = requests.post(
            url="https://user.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_update",
            params={
                'g_tk': self.gtk2
            },
            headers=self.headers,
            cookies=self.cookie_dict,
            data=post_data)
        if res.status_code == 200:
            pass
        else:
            raise Exception("发表说说失败: " + res.text)



    def tid_valid(self, tid):
        """检查tid是否有效
        :param tid: 说说id
        :return: True/False
        """
        url = EMOTION_INFO_API.format(int(time.time()), self.uin, tid)
        # print(url)
        res = requests.get(url=url)
        # print(res.text)
        json_obj = json.loads(res.text.replace("_Callback(", "")[:-3])
        # print(json_obj)

        return json_obj['data'][0]['current']['newdata'].__contains__('LIKE')

    def get_traffic_data(self,tid):
        """获取点赞量、评论量、转发量"""
        url = EMOTION_INFO_API.format(int(time.time()), self.uin, tid)
        # print(url)
        res = requests.get(url=url)
        # print(res.text)
        respobj = json.loads(res.text.replace("_Callback(", "")[:-3])
        # print(respobj)

        if not respobj['data'][0]['current']['newdata'].__contains__('LIKE'):
            # raise Exception("tid 无效:",tid)
            return (-1,-1,-1)
        

        # 检查newdata是否完整，不完整则结束跟踪，valid设置为0
        crt_newdata = dict(respobj["data"][0]["current"]["newdata"])
        # print(crt_newdata)
        if crt_newdata.__contains__("LIKE") and crt_newdata.__contains__("PRD") and crt_newdata.__contains__(
                "CS") and crt_newdata.__contains__("ZS"):  # 点赞，浏览，评论，转发
            like_amt = 0
            read_amt = 0
            comment_amt = 0
            forward_amt = 0

            like_amt = crt_newdata["LIKE"]
            read_amt = crt_newdata["PRD"]
            comment_amt = crt_newdata["CS"]
            forward_amt = crt_newdata["ZS"]

            return (like_amt,comment_amt,forward_amt)

        return (-1,-1,-1)
