import random
import requests
import json
from app.ext import scheduler, db
from app.models import SpiderInclude
from flask import current_app
from datetime import datetime

ua_list = [
            "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
            "Mozilla/5.0 (iPod; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
            "Mozilla/5.0 (Linux; U; Android 2.3.7; en-us; Nexus One Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
            "MQQBrowser/26 Mozilla/5.0 (Linux; U; Android 2.3.7; zh-cn; MB200 Build/GRJ22; CyanogenMod-7) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
            "Opera/9.80 (Android 2.3.4; Linux; Opera Mobi/build-1107180945; U; en-GB) Presto/2.8.149 Version/11.10",
            "Mozilla/5.0 (Linux; U; Android 3.0; en-us; Xoom Build/HRI39) AppleWebKit/534.13 (KHTML, like Gecko) Version/4.0 Safari/534.13",
            "Mozilla/5.0 (BlackBerry; U; BlackBerry 9800; en) AppleWebKit/534.1+ (KHTML, like Gecko) Version/6.0.0.337 Mobile Safari/534.1+",
            "Mozilla/5.0 (SymbianOS/9.4; Series60/5.0 NokiaN97-1/20.0.019; Profile/MIDP-2.1 Configuration/CLDC-1.1) AppleWebKit/525 (KHTML, like Gecko) BrowserNG/7.1.18124",
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0; HTC; Titan)",
            "UCWEB7.0.2.37/28/999",
            "NOKIA5700/ UCWEB7.0.2.37/28/999",
            "Openwave/ UCWEB7.0.2.37/28/999",
            "Mozilla/4.0 (compatible; MSIE 6.0; ) Opera/UCWEB7.0.2.37/28/999",
            "Mozilla/6.0 (iPhone; CPU iPhone OS 8_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/8.0 Mobile/10A5376e Safari/8536.25",
        ]


def baidu_result_count(kw):
    baidu_search_url = 'http://www.baidu.com/s?wd={}&pn=0&rn=1&tn=json'.format(kw)
    # print(baidu_search_url)
    user_agent = random.choice(ua_list)
    headers = {'User-Agent': user_agent, 'Host': 'www.baidu.com'}
    cookies =  {"Cookie":'BDORZ=27315'}
    try:
        r = requests.get(baidu_search_url, headers=headers, timeout=3)
        r.encoding = 'utf-8'
        content = json.loads(r.text)
        # print(content)
        if content and content['feed'] and content['feed']['entry']:
            total = content['feed']['all']
            return total
    except Exception as e:
        print(e)
        return 0
    return 0

def task_include():
    with scheduler.app.app_context():
        # keywords = db.session.query(Keyword).all()
        domain = current_app.config.get('H3BLOG_DOMAIN')
        domain = domain.replace('http://','').replace('https://', '')
        num = baidu_result_count('site:{}'.format(domain))
        si = SpiderInclude()
        si.search_engine = '百度'
        si.num = num
        si.time_label = datetime.now().strftime('%Y-%m-%d')
        db.session.add(si)
        db.session.commit()
        