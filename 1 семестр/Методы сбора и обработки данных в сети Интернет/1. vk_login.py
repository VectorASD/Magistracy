import requests

"""
import ssl
context = ssl._create_unverified_context()
ssl.match_hostname = lambda void, host: None

import requests.packages.urllib3.connection as connection
from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.SecurityWarning)
def _ssl_wrap_socket(sock, **ka):
  #for k, v in ka.items(): print(k, "->", v)
  host = ka["server_hostname"]
  wrap = context.wrap_socket(sock, server_hostname = host)
  #print(wrap.version())
  return wrap
connection.ssl_wrap_socket = _ssl_wrap_socket
"""



#import logging
from base64 import b64encode, b64decode
#from threading import Thread
import time
from random import randint
import io
import hashlib
from urllib.parse import urlencode, parse_qs, urlparse, parse_qsl, urlunparse
import os

"""
from twocaptcha import TwoCaptcha
rucaptcha_key = "ApiKEY here"
def get_captcha_code(captcha_url):
    image = requests.get(captcha_url).content
    try:
        code = solver.normal(b64encode(image).decode("utf-8"))['code']
        logging.info("Каптча решена успешно")
        return code
    except Exception as error:
        print(error)
        logging.warning("Каптча не решена")
"""



def Error(Str): print(Str); exit()
#requests = None

#Аймырза Бисингалиев
#vk.com/id75238918

#Гузалия Ахметшина
#vk.com/guzaliya_akhmetshina

#GPath = __file__.rsplit("/", 1)[0] + "/"
#GPath = "Mazer/Knight/"
GPath = ""



def RawProxies():
    with open("proxy.txt", "r") as file: Arr = file.read().split("\n")
    Arr = [i for i in Arr if i]
    return Arr
def Proxies(raw = False):
    if raw: Arr = RawProxies()
    else:
        with open("ValidProxies.txt", "r") as file: Arr = file.read().split("\n")
        Arr = [i.split(" | S: ")[0] for i in Arr if i]
    if len(Arr) == 0: return
    Used = []
    while True:
        print("Начался новый круг использования прокси...")
        for i in range(len(Arr)):
            Proxy = Arr.pop(randint(0, len(Arr) - 1))
            Used.append(Proxy)
            yield Proxy
        Arr, Used = Used, []
#Proxies = Proxies()

class Looper():
    def __init__(self, Func):
        self.printer = []
        self.Func = Func
        Thread(target=self.Loop).start()
    def post(self, *Args):
        self.printer.append(Args)
    def Loop(self):
        while True:
            try: Args = self.printer.pop(0)
            except IndexError:
                time.sleep(0.01)
                continue
            self.Func(*Args)
class Filetron():
    def __init__(self, Name):
        self.file = open(Name, "a")
        self.post = Looper(self.write).post
    def write(self, Str):
        self.file.write(Str)
        self.file.write("\n")
        self.file.flush()
#print2 = Looper(print).post
#ValidProxies = Filetron("ValidProxies.txt").post
#InvalidProxies = Filetron("InvalidProxies.txt").post

#LOL = b'<!DOCTYPE html>\n<!--[if lt IE 7]> <html class="no-js ie6 oldie" lang="en-US"> <![endif]-->\n<!--[if IE 7]>    <html class="no-js ie7 oldie" lang="en-US"> <![endif]-->\n<!--[if IE 8]>    <html class="no-js ie8 oldie" lang="en-US"> <![endif]-->\n<!--[if gt IE 8]><!--> <html class="no-js" lang="en-US"> <!--<![endif]-->\n<head>\n\n<title>Please Wait... | Cloudflare</title>\n  \n<meta name="captcha-bypass" id="captcha-bypass" />\n<meta charset="UTF-8" />\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n<meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1" />\n<meta name="robots" content="noindex, nofollow" />\n<meta name="viewport" content="width=device-width,initial-scale=1" />\n<link rel="stylesheet" id="cf_styles-css" href="/cdn-cgi/styles/cf.errors.css" type="text/css" media="screen,projection" />\n<!--[if lt IE 9]><link rel="stylesheet" id=\'cf_styles-ie-css\' href="/cdn-cgi/styles/cf.errors.ie.css" type="text/css" media="screen,projection" /><![endif]-->\n<style type="text/css">body{margin:0;padding:0}</style>\n\n\n<!--[if gte IE 10]><!-->\n<script>\n  if (!navigator.cookieEnabled) {\n    window.addEventListener(\'DOMContentLoaded\', function () {\n      var cookieEl = document.getElementById(\'cookie-alert\');\n      cookieEl.style.display = \'block\';\n    })\n  }\n</script>\n<!--<![endif]-->\n\n\n  \n    <script type="text/javascript">\n    //<![CDATA[\n    (function(){\n      window._cf_chl_opt={\n        cvId: "2",\n        cType: "managed",\n        cNounce: "36873",\n        cRay: "6a5dbbadc8d74d53",\n        cHash: "12eb5d880eaafb9",\n        cFPWv: "b",\n        cTTimeMs: "1000",\n        cLt: "n",\n        cRq: {\n          ru: "aHR0cDovL3ZlY3RvcmFzZC5ydS9teWlw",\n          ra: "TW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzk1LjAuNDYzOC41NCBTYWZhcmkvNTM3LjM2IEVkZy85NS4wLjEwMjAuMzA=",\n          rm: "R0VU",\n          d: "251i6F89Z/E9TYONehmPWX98K7VoNbFFDvHOJdMOJO2w0XwW8Jdv4dyYML0YeacpKuUuus5b7cwARbkRdDVGIMJOrh8VKjidBjpp+svSfvy5p3djTJmWV5IK9OL7ap8ravxEAYJW2WxRqXFVUbYPwfnljGAPyJDgxU+ST3fWII5yPsU+Xr5mUvz6obOe7lQEcR1elFWs5RL9S7gaeLPtnjNNMgVtrkzX22xRbfgjw2TYBixSVIj6E9gtNooYNEmJc2m0Pfx7G7/6T87SGDbz0ytFEvgOjzFVstlg06zGchUhmILJ8xdQmQABfRfQkgGh2lDJnfaX/OOtYov2bFY4GBt4hJhoLgSsU8KBZX29IoGqQ2asaCLgpCiGuO620UHQ+b2gw4LiHy2ZU4M6Yx+mbPm4VWyqBWfbbKt/09qkov683+Ai0QMI2JQpsbeaqHkQsjqAX+88xETxjVMHhiwON0/wBFmjY0buaPpQsKGTYsIw2DQcO6kClFDRx2fHzFzhzUwiWae41qo1bIZRnDMwLEzK/xcZXlH8E/rkqVT+DftekuvWlKoFFUgxrJ99Scu9fM087tws3UJVrpq3qKK9cTnKkCo0wsW3OhrQ3SylkdkgCZhyO491tXFJWaNkBTnXfk/JWFHj+lt7rHynD/C9/rRIDgt+yPFG6ItmaMkbnThFPBw2T+V7kAaxNnEDcyjKxQGlvEQTqefiwBze2TsCLg==",\n          t: "MTYzNTUyNDQ0Ni4zNzUwMDA=",\n          m: "hZsxfjtKs41acgvztzCQNmL+iIFh8rI4c/TYN1hHf3Y=",\n          i1: "IKQjaBcngS+eXgtrk0+D5w==",\n          i2: "GZ6fOrlRn0gpppx9lNEoyg==",\n          zh: "QAIazokGw3bbMapRLH6M3WyeB2mlrn+ms48OJaAKozk=",\n          uh: "39hGhxkGAMIDy7R9Ko1afw4Y5W944D6HiTnY2zI+BIQ=",\n          hh: "FHgy/FNsdKDN2GbEnhZK8Ehg2sRWFcsQV++YqLxt68Y=",\n        }\n      };\n    }());\n    //]]>\n    </script>\n  \n\n<style type="text/css">\n  #cf-wrapper #spinner {width:69px; margin:  auto;}\n  #cf-wrapper #cf-please-wait{text-align:center}\n  .attribution {margin-top: 32px;}\n  .bubbles { background-color: #f58220; width:20px; height: 20px; margin:2px; border-radius:100%; display:inline-block; }\n  #cf-wrapper #challenge-form { padding-top:25px; padding-bottom:25px; }\n  #cf-hcaptcha-container { text-align:center;}\n  #cf-hcaptcha-container iframe { display: inline-block;}\n  @keyframes fader     { 0% {opacity: 0.2;} 50% {opacity: 1.0;} 100% {opacity: 0.2;} }\n  #cf-wrapper #cf-bubbles { width:69px; }\n  @-webkit-keyframes fader { 0% {opacity: 0.2;} 50% {opacity: 1.0;} 100% {opacity: 0.2;} }\n  #cf-bubbles > .bubbles { animation: fader 1.6s infinite;}\n  #cf-bubbles > .bubbles:nth-child(2) { animation-delay: .2s;}\n  #cf-bubbles > .bubbles:nth-child(3) { animation-delay: .4s;}\n</style>\n</head>\n<body>\n  <div id="cf-wrapper">\n    <div class="cf-alert cf-alert-error cf-cookie-error" id="cookie-alert" data-translate="enable_cookies">Please enable cookies.</div>\n    <div id="cf-error-details" class="cf-error-details-wrapper">\n      <div class="cf-wrapper cf-header cf-error-overview">\n      \n        <h1 data-translate="managed_challenge_headline">Please wait...</h1>\n        <h2 class="cf-subheadline"><span data-translate="managed_checking_msg">We are checking your browser...</span> vectorasd.ru</h2>\n      \n      </div>\n      \n      <div class="cf-section cf-highlight cf-captcha-container">\n        <div class="cf-wrapper">\n          <div class="cf-columns two">\n            <div class="cf-column">\n            \n              <div class="cf-highlight-inverse cf-form-stacked">\n                <form class="challenge-form managed-form" id="challenge-form" action="/myip?__cf_chl_managed_tk__=pmd_Mm8Bkjss49qX1umnNR2umLZ8A2uzhnA2sdk0KuMrDVw-1635524446-0-gqNtZGzNAvujcnBszQM9" method="POST" enctype="application/x-www-form-urlencoded">\n  \n    <div id=\'cf-please-wait\'>\n      <div id=\'spinner\'>\n        <div id="cf-bubbles">\n            <div class="bubbles"></div>\n            <div class="bubbles"></div>\n            <div class="bubbles"></div>\n        </div>\n      </div>\n      <p data-translate="please_wait" id="cf-spinner-please-wait">Please stand by, while we are checking your browser...</p>\n      <p data-translate="redirecting" id="cf-spinner-redirecting" style="display:none">Redirecting...</p>\n      </div>\n  \n  <input type="hidden" name="md" value="T6JlPP5ZrYZZMXy31ozag31KznVUcc8fwXgHN3lz.pM-1635524446-0-AXt_gh79AK181M23PbMqhw8u5-SqBSbG7Ru-CMtSgCfC2Ws_tWOdig2Z8f3v4dTSJYv-_MA6yxqxZtUvD8VVGlbJLyiOjTxmHn_4NJ8zU3ahZY1ji4H8nXHWxQvA74O3D8OPpUUDwlKGNUdIY9tQuXjZibb--79ds3mfjrKHYfWDW4B5S2aB2AdhoHh4Sjk9AewJNppdg9mbZXqfYH6hS8AcNBjnkuKFDfoQApfEJM6_sM65hSG90xGeDArF0hiEQX-cc7Yi0eLVvyHKj1hjk5wzmD95RtDNq588oDA66SjE2vCa-0fYmgRcbdwxGmU7zrnnkebqtgk3t2LoNO7cP81NzLbRSTwwQknYff2DsyaNWHIPbenNfdaBxWulfyFOUA9XQ3-q5QmSdC0emd3DoDKfsmfEGFvsaT1nKGO7Hlp3ZCf2oJQC5yp1VzS6AuF25WKwJu5qO21YzGqyA0_Ah4V9Tz6ZPKzTthGizvIIbjy-ULueGfqAgfWwNkmUybHa3HuEFMTzarg9Q27UTA9N2b1pG9pNfE78Uwx4uMUXk3Xo-p4JkvalwY8il7-SYN5VtKdj8Ce-aRIVmSzQr9upbRz-dg-JGEhj7P_1xJzd5KX_of4I4d2y5TpfcnzCdk8A-jcaqZq4dJHNLaQgs2AE5xtdlEx1LwQSqgLS4Z_C7BtGAbJuUTBT5x3llxT7V9UVFg" />\n  <input type="hidden" name="r" value="tJ7l_OVBFWGoXWJ.aSBGR8irhFgzNxR2Xre5Q8JTaXM-1635524446-0-AUbOgsyTWF22uHtX5LqJASbvPQZK4SLbi3lCQy96+r0LLRdP3uwqabtQ7QYflIvzjW23E6Y8SObmlNYcMjTGq7RFt0F2769mPKj/JYw68F/jbLMHZMxoQlg75nTL8xJ1pP4V9CT0NjF8cj8c9LhAjm2aAAh89iFpus+9PPu7MQ+xjd1LCO8wSMHZ7iNiHcxm97q7lYZ3gvV/oJqLvMYRY20WopMfTDnkd5NzN1PYhRkolgXhit/kjBNmuJZWxTyrs9mIieMrF+ayyTHEafOfvzNUgArn/AX+3KAhh/7wkOfrIw2p0eByS39R7O1D3pJmGtRNBSR0+6eQbkklBSIbQoxZrgnhoSltMmxtxScCWlOpyfhVKoU5FLAKGDi+jWt1Klmv6yBr5EVmS6bJp5LyfG1WH+8QM0PCtVeQTfG7mh6eKywmjsO/hbvSpqQKvNEM8J3wUOUCV5bNLjH6ALqKYFkp6av+nH1xWFxgmifcASt//tu1vTpre+4tEDuKBwO2bS3oOyLmTqUncOoiHVavtmb1tsEIK8XmPqQXFrGNTuNiC9BzMwmu1nS8KIevtHDcD4TJqdn/4i1FY+qHPiw3tdaV40bBOrMAUP+LO1AR63VF+j4gX5+MKEX2toW0g1jlc+CyESQ0bH+0lxlAKzR1d/72qtVhtkKG+i8x/s78RKjSLAKgHTcb0C0sW3oazmk7CwloOScgwAiBF1NU/odW91svNadXdJopPpQrAotwq/jjjYpGW1AzTQ4Mt4pKCyVIFg==">\n  <input type="hidden" name="cf_captcha_kind" value="h">\n  <input type="hidden" name="vc" value="6e058824fa232e713777903bc468ea03">\n  \n  <noscript id="cf-captcha-bookmark" class="cf-captcha-info">\n  <h1 data-translate="turn_on_js" style="color:#bd2426;">Please turn JavaScript on and reload the page.</h1>\n  </noscript>\n    <div id="no-cookie-warning" class="cookie-warning" data-translate="turn_on_cookies" style="display:none">\n      <p data-translate="turn_on_cookies" style="color:#bd2426;">Please enable Cookies and reload the page.</p>\n    </div>\n  <script type="text/javascript">\n  //<![CDATA[\n    var a = function() {try{return !!window.addEventListener} catch(e) {return !1} },\n      b = function(b, c) {a() ? document.addEventListener("DOMContentLoaded", b, c) : document.attachEvent("onreadystatechange", b)};\n      b(function(){\n        var cookiesEnabled=(navigator.cookieEnabled)? true : false;\n        if(!cookiesEnabled){\n          var q = document.getElementById(\'no-cookie-warning\');q.style.display = \'block\';\n        }\n      });\n  //]]>\n  </script>\n  <div id="trk_captcha_js" style="background-image:url(\'/cdn-cgi/images/trace/captcha/nojs/h/transparent.gif?ray=6a5dbbadc8d74d53\')"></div>\n</form>\n  \n  <script type="text/javascript">\n    //<![CDATA[\n    (function(){\n        var isIE = /(MSIE|Trident\\/|Edge\\/)/i.test(window.navigator.userAgent);\n        var trkjs = isIE ? new Image() : document.createElement(\'img\');\n        trkjs.setAttribute("src", "/cdn-cgi/images/trace/managed/js/transparent.gif?ray=6a5dbbadc8d74d53");\n        trkjs.id = "trk_managed_js";\n        trkjs.setAttribute("alt", "");\n        document.body.appendChild(trkjs);\n        var cpo=document.createElement(\'script\');\n        cpo.type=\'text/javascript\';\n        cpo.src="/cdn-cgi/challenge-platform/h/b/orchestrate/managed/v1?ray=6a5dbbadc8d74d53";\n        document.getElementsByTagName(\'head\')[0].appendChild(cpo);\n    }());\n    //]]>\n    </script>\n  \n\n\n              </div>\n            </div>\n\n            <div class="cf-column">\n              <div class="cf-screenshot-container">\n              \n                <span class="cf-no-screenshot"></span>\n              \n              </div>\n            </div>\n          </div>\n        </div>\n      </div>\n\n      <div class="cf-section cf-wrapper">\n        <div class="cf-columns two">\n          <div class="cf-column">\n            <h2 data-translate="why_captcha_headline">Why do I have to complete a CAPTCHA?</h2>\n            \n            <p data-translate="why_captcha_detail">Completing the CAPTCHA proves you are a human and gives you temporary access to the web property.</p>\n          </div>\n\n          <div class="cf-column">\n            <h2 data-translate="resolve_captcha_headline">What can I do to prevent this in the future?</h2>\n            \n\n            <p data-translate="resolve_captcha_antivirus">If you are on a personal connection, like at home, you can run an anti-virus scan on your device to make sure it is not infected with malware.</p>\n\n            <p data-translate="resolve_captcha_network">If you are at an office or shared network, you can ask the network administrator to run a scan across the network looking for misconfigured or infected devices.</p>\n            \n              \n              <p data-translate="resolve_captcha_privacy_pass"> Another way to prevent getting this page in the future is to use Privacy Pass. You may need to download version 2.0 now from the <a rel="noopener noreferrer" href="https://chrome.google.com/webstore/detail/privacy-pass/ajhmfdgkijocedmfjonnpjfojldioehi">Chrome Web Store</a>.</p>\n              \n            \n          </div>\n        </div>\n      </div>\n      <a href="http://kachtus.net/hundredfoldhunger.php?coid=35" style="display: none;">table</a>\n\n      <div class="cf-error-footer cf-wrapper w-240 lg:w-full py-10 sm:py-4 sm:px-8 mx-auto text-center sm:text-left border-solid border-0 border-t border-gray-300">\n  <p class="text-13">\n    <span class="cf-footer-item sm:block sm:mb-1">Cloudflare Ray ID: <strong class="font-semibold">6a5dbbadc8d74d53</strong></span>\n    <span class="cf-footer-separator sm:hidden">&bull;</span>\n    <span class="cf-footer-item sm:block sm:mb-1"><span>Your IP</span>: 179.127.174.58</span>\n    <span class="cf-footer-separator sm:hidden">&bull;</span>\n    <span class="cf-footer-item sm:block sm:mb-1"><span>Performance &amp; security by</span> <a rel="noopener noreferrer" href="https://www.cloudflare.com/5xx-error-landing" id="brand_link" target="_blank">Cloudflare</a></span>\n    \n  </p>\n</div><!-- /.error-footer -->\n\n\n    </div>\n  </div>\n\n  <script type="text/javascript">\n  window._cf_translation = {};\n  \n  \n</script>\n\n\n</body>\n</html>\n'
#for i in LOL.decode("utf-8").split("\n"): print(i)
#exit()

def CheckProxy(N, MyIP, proxy):
    N = "%s.)" % N
    print2(N, proxy)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.30"}
    proxyDict = {"http": "http://" + proxy, "https": "https://" + proxy}
    Time = time.time()
    #https://api.vk.com/method/METHOD_NAME?PARAMETERS&access_token=ACCESS_TOKEN&v=5.131
    try:
        Obj = requests.get("https://vectorasd.ru/myip", headers=headers, proxies=proxyDict, timeout=10).content
        if Obj.count(b"Please Wait... | Cloudflare"):return InvalidProxies(proxy + " | Не пройдено облако")
        try: Obj = eval(Obj)
        except:
            Str = Obj.strip(b" \n")
            if Str.count(b"Maximum number of open connections reached."): return InvalidProxies(proxy + " | Maximum number of open connections reached")
            if Str.count(b"This message was created by Kerio Control Proxy"): return InvalidProxies(proxy + " | Kerio Control Proxy Error")
            return InvalidProxies(proxy + " | (!!!) Таинственный мусор в ответе: %s" % Str)
    except Exception as e:
        e = str(e)
        if e.count(" Read timed out. "): return InvalidProxies(proxy + " | Read timed out (10s)")
        if e.count(" timed out. (connect timeout="): return InvalidProxies(proxy + " | Connection timed out (10s)")
        if e.count(" [WinError 10061] "): return InvalidProxies(proxy + " | Timeout (10s)")
        if e.count("Remote end closed connection without response"): return InvalidProxies(proxy + " | Remote end closed connection without response")
        if e.count("Удаленный хост принудительно разорвал существующее подключение"): return InvalidProxies(proxy + " | Удаленный хост принудительно разорвал существующее подключение")
        
        print2(N, "Ошибка прокси:", e)
        print2(N, "Прошло секунд:", time.time() - Time)
        return InvalidProxies(proxy + " | (!!!) Ошибка: " + e)
    IPs = Obj[0].split(",")
    print2(N, "IP:", IPs)
    #print2("UA:", Obj[1])
    #print2("Time:", Obj[2], "  Timestamp:", Obj[3])
    print2(N, "Прошло секунд:", time.time() - Time)
    if MyIP in IPs:
        print2(N, "Invalid")
        InvalidProxies(proxy + " | Палит IP: " + Obj[0])
    else:
        print2(N, "Valid")
        ValidProxies(proxy + " | S: %s | IPs: %s" % (time.time() - Time, IPs))

def ProxyChecker():
    countThreads = 50
    Arr = RawProxies()
    MyIP = eval(requests.get("http://vectorasd.ru/myip").content)[0]
    print2("Мой IP:", MyIP)
    for N in range(0, len(Arr), countThreads):
        PArr = Arr[N : N + countThreads]
        print2("Новая порция прокси:", PArr)
        Threads = [Thread(target=CheckProxy, args=[i, MyIP, P]) for i, P in enumerate(PArr)]
        for i in Threads: i.start()
        for i in Threads: i.join()
    print2("END")
    time.sleep(3)
    exit()
#proxy = "41.222.209.9:808"
#proxyDict = {"http": "http://" + proxy, "https": "https://" + proxy}
#headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.30"}
#print(requests.get("http://vectorasd.ru/myip", headers=headers, proxies=proxyDict, timeout=10).content)
#exit()

#ProxyChecker()

#solver = TwoCaptcha(rucaptcha_key)
#print(solver)









def Captcher(rawImg):
    root = tkinter.Tk()
    root.title("GUI на Python")
    root.geometry("400x240")
    frame = tkinter.Frame(root)
    frame.grid()
    #label = tkinter.Label(frame, text="Hello, World!").grid(row=1,column=1)
    #but = tkinter.Button(frame, text="Кнопка").grid(row=1, column=2)
    captcha = tkinter.Label(root)
    captcha.grid(row=1, column=1)
    #image = Image.open(io.BytesIO(requests.get("https://api.vk.com/captcha.php?sid=195416780563").content))
    image = Image.open(io.BytesIO(rawImg))
    image = image.resize((image.size[0] * 3, image.size[1] * 3))
    photo = ImageTk.PhotoImage(image)
    captcha.configure(image=photo)
    message = tkinter.StringVar()
    message_entry = tkinter.Entry(root, textvariable=message)
    message_entry.grid(row=2, column=1)
    root.mainloop()
    return message.get()



class Base():
  def __init__(self):
    try:
      with open(GPath + "Users.pyobj") as file: self.Base = eval(file.read())
    except OSError: self.Base = [{}, {}]
    try:
      with open(GPath + "Memes.pyobj") as file: self.Memes = list(map(eval, file.read().split("\n")))
    except OSError: self.Memes = []
    self.MemList = set()
    for Block in self.Memes:
      for File in Block: self.MemList.add(File[0])
    print("MemList:", self.MemList)
  def Save(self):
    with open(GPath + "Users.pyobj", "w") as file: file.write(str(self.Base))
  def Save2(self):
    with open(GPath + "Memes.pyobj", "w") as file: file.write("\n".join(map(str, self.Memes)))
  def Check(self, login, password):
    LP = (login, password)
    try: return self.Base[0][LP]
    except KeyError: return None
  def Add(self, login, password, Token):
    LP = (login, password)
    self.Base[0][LP] = Token
    self.Save()
  def CheckPhoto(self, Path):
    with open(Path, "rb") as file: data = file.read()
    Hash = hashlib.md5(data).hexdigest()
    try: return self.Base[1][Hash], data, Hash
    except KeyError: return None, data, Hash
  def AddPhoto(self, Obj, Hash):
    self.Base[1][Hash] = Obj
    self.Save()
  def AddMem(self, Block):
    self.Memes.append(Block)
    self.Save2()
Base = Base()



"""
<form method="post" action="/login?act=authcheck_code&hash=1638568727_160050520ac26157a0" novalidate>
    <input type="text" name="code" class="textfield" autocomplete="one-time-code" autocorrect="off" autocapitalize="off" />
    <input type="checkbox" class="checkbox" name="remember" value="1" checked="checked" />
    <input class="button" type="submit" value="Отправить код" />
    <a href="/login?act=authcheck&api_hash=944d9ccf893b4e1a98&help_opened" rel="noopener">Проблема с получением кода?</a>
</form>
"""

from urllib.parse import urlparse, parse_qs

def check_url(url):
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    print("URL:", url)
    print("    params:", params)
    #try: return params["session_token"][0]
    #except KeyError: pass
# url = r"https://id.vk.com/not_robot_captcha?domain=vk.com&session_token=SESSION_TOKEN&variant=popup&blank=1"
# print("token:", check_url(url)); exit()

def Bot():
  def Check(response):
    if "error" in response:
      Err = response["error"]
      if Err == "need_validation":
        Type = response["validation_type"]
        if Type == "2fa_sms":
          sid, phone, url = response["validation_sid"], response["phone_mask"], response["redirect_uri"]
          print("2fa авторизация!")
          print("Телефон:", phone)
          resp = session.get(url)
          #with open(GPath + "AuthDoc.html", "wb") as file: file.write(resp.content)
          #print("Ответ:", resp.content)
          url = "/".join(url.split("/")[:3]) + resp.content.split(b'<form method="post" action="', 1)[1].split(b'"', 1)[0].decode("utf-8", errors = "replace")
          print("URL:", url)
          values = {
            "code": input("Введите код: "),
            "remember": int(True),
          }
          resp = session.post(url, values)
          Str = resp.content.decode("cp1251", errors = "replace").replace("<b>", "").replace("</b>", "")
          if not Str.count("Пожалуйста, не копируйте данные из адресной строки для сторонних сайтов. Таким образом Вы можете потерять доступ к Вашему аккаунту."):
            print("Странная ответочка:", Str)
          #print(resp.url.split("#", 1))
          Dict = parse_qs(resp.url.split("#", 1)[1])
          #print(Dict)
          success = Dict["success"][0] == "1"
          if success: return Dict["access_token"][0], int(Dict["user_id"][0])
          else: print("Проваль [>;/] :", resp.url.split("#", 1), Dict)
        else: print("    2fa:", response)
      elif Err == "invalid_client": print("    Нельзя войти:", response)
      elif Err == "need_captcha":
        print("    Нарвался на капчу:", response)
        sid, url = response["captcha_sid"], response["captcha_img"]
        print("SID:", sid)
        print("url:", url)
        #Code = Captcher(session.get(url).content)
        # Раньше: https://api.vk.com/captcha.php?sid=195416780563
        # Сейчас: https://vk.com/captcha.php?sid=808911851158&source=api-oauth&app_id=2274003&device_id=&resized=1

        # image = requests.get(url).content
        # with open("captcha.png", "wb") as file: file.write(image)
        # Code = input("Ввод кода: ")
        # print("Code:", Code)

        try: token = NewCaptchaLogin(response["redirect_uri"])
        except ImportError:
          print("1. Откройте url:", response["redirect_uri"])
          print("2. Решите каптчу")
          url = input("3. Введите url, изменённое каптчей: ")
          token = check_url(url)
        if token is None: raise ValueError("Не обнаружен session_token!")

        return token
      else: print("    Неизвестный тип ошибки:", response)
    elif "access_token" in response:
      print("    Вход удался:", response)
      return response["access_token"], response["user_id"]
    else: print("    Необрабатываемое исключение:", response)

  def CaptchaLogin(sid, Key):
    raise ValueError("Данный способ is deprecated!")
    response = session.get("%s&username=%s&password=%s&captcha_sid=%s&captcha_key=%s" % (api_request, login, password, sid, Key)).json()
    return Check(response)

  def NewCaptchaLogin(redirect_url):
    from yandex_browser_driver import run
    import asyncio

    return asyncio.run(run(redirect_url, check_url))

  def TryLogin():
    token = Base.Check(login, password)
    if token is not None:
      print("BASE!")
      return token
    print("NET!")
    print("Akk:", login, password)
    response = session.get("%s&username=%s&password=%s" % (api_request, login, password)).json()
    token = Check(response)
    if token is not None: Base.Add(login, password, token)
    print("Результат:", token)
    return token

  def Method(Methodd, Data):
    time.sleep(Sleep)
    if type(Data) is dict: Data = urlencode(Data)
    Str = api_request2 % (Methodd, Data, Token)
    if requests != None: Obj = session.get(Str).json()
    else:
      Obj = None
      if Methodd == "wall.get": Obj = json.loads('{"response":{"count":420489,"items":[{"id":665580,"from_id":443878614,"owner_id":-51651959,"date":1636221723,"type":"post","marked_as_ads":0,"post_type":"post","text":"Массаж расслабляющий, релакс, классика. Женщинам, девушкам. Возможен выезд к вам. Пишите, звоните. Индивидуальный подход. Натуральные масла.","post_source":{"type":"vk"},"comments":{"can_post":1,"count":0,"groups_can_post":true},"likes":{"can_like":1,"count":0,"user_likes":0,"can_publish":0},"reposts":{"count":0,"user_reposted":0},"is_favorite":false,"donut":{"is_donut":false},"ads_easy_promote":{"type":2,"text":"Что-то пошло не так.","label_text":"","button_text":"","is_ad_not_easy":false},"short_text_rate":0.800000,"hash":"wvOM0CHjE1ewUpSoeyWRwOOy7LI"}],"next_from":"2"}}')
      if Methodd == "likes.add": Obj = {"response": {"likes": 1}}
      if Methodd == "photos.getWallUploadServer": Obj = json.loads('{"response":{"album_id":-14,"upload_url":"https:\/\/pu.vk.com\/c516136\/ss2254\/upload.php?act=do_add&mid=75238918&aid=-14&gid=51651959&hash=11f37dba3b29f94ac720ecf52738d990&rhash=a36dd77d49af93e95a81b84517429e1b&swfupload=1&api=1&wallphoto=1","user_id":75238918}}')
      if Methodd == "wall.post": Obj = {"response": {"post_id": 665588}}
      if Obj is None:
        print("Method:", Methodd)
        print(Str)
        exit()
    if "error" in Obj:
      Obj = Obj["error"]
      if "captcha_sid" in Obj:
        sid, img = Obj["captcha_sid"], Obj["captcha_img"]
        img = session.get(img).content
        with open(GPath + "Captcha.jpg", "wb") as file: file.write(img)
        Code = input("Ввод капчи: ")
        return Method(Methodd, "%s&captcha_sid=%s&captcha_key=%s" % (Data, sid, Code))
      Code, Msg = Obj["error_code"], Obj["error_msg"]
      if Code in (15, 214): return "%s:%s" % (Code, Msg)
    if "response" not in Obj: Error("Ошибка %s: %s" % (Method, Obj))
    if len(Obj) > 1: print("Дополнительная инфа в:", Method, Obj)
    return Obj["response"]

  def Like(Type, owner, item, Key = None):
    Str = "type=%s&owner_id=%s&item_id=%s" % (Type, owner, item)
    if Key != None: Str += "&access_key=%s" % Key
    print("    Произвожу лайк...")
    Obj = Method("likes.add", Str)
    print("    Новое число лайков:", Obj["likes"])

  def UploadServer(owner):
    print("  Получение url загрузочного сервера...")
    Obj = Method("photos.getWallUploadServer", "group_id=%s" % abs(owner))
    if Obj["user_id"] != UID: Error("Парадокс загрузочного сервера с UID: %s" % Obj)
    return Obj["album_id"], Obj["upload_url"]

  def SavePhoto(owner, data):
    Obj = Method("photos.saveWallPhoto", {"group_id": abs(owner), "server": data["server"], "photo": data["photo"], "hash": data["hash"]})
    return Obj

  def Uploader(owner, Path):
    Obj, Data, Hash = Base.CheckPhoto(Path)
    if Obj == None:
      album, url = UploadServer(owner)
      print("  Загрузка нового изображения на сервер...")
      with open(Path, "rb") as file:
        Obj = session.post(url, files = {"photo": file}).json()
      #Obj["us"] = (album, url)
      #print(Obj)
      Obj = SavePhoto(owner, Obj)
      Base.AddPhoto(Obj, Hash)
    else: print("  Изображение уже есть на сервере...")
    #print(Obj)
    Obj = Obj[0]
    return "photo%s_%s" % (Obj["owner_id"], Obj["id"])

  def GroupPost(owner, text, Path):
    Obj = {"owner_id": owner, "message": text}
    if Path:
      Zn = Uploader(owner, Path)
      Obj["attachments"] = Zn
    print("  Создание записи...")
    Obj = Method("wall.post", Obj)
    if type(Obj) == str:
      print("  🔥😡🔥 Ошибка: " + Obj)
      return True
    print("  Создана запись:", Obj["post_id"])
    return False

  def Filtor(URL):
    url_parts = list(urlparse(URL))
    query = dict(parse_qsl(url_parts[4]))
    del query["c_uniq_tag"]
    del query["type"]
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)

  def GroupPost2(owner, NameS):
    Names, Blocks = [], []
    for Name in NameS:
      Res = Uploader(owner, Path + Name)
      Sizes = Base.CheckPhoto(Path + Name)[0][0]["sizes"]
      Sizes = [Filtor(Size["url"]) for Size in Sizes]
      Names.append(Res)
      Blocks.append((Name, Res, Sizes))
    Names = ",".join(Names)
    print(Names)
    Obj = {"owner_id": -owner, "attachments": Names}
    print("  Создание записи...")
    Obj = Method("wall.post", Obj)
    if type(Obj) == str:
      print("  🔥😡🔥 Ошибка: " + Obj)
      return True
    print("  Создана запись:", Obj["post_id"])
    
    """
    Obj = Method("wall.get", "owner_id=%s&offset=%s&count=%s" % (-owner, 1, 1))
    if type(Obj) == str:
      print("  🔥😡🔥 Ошибка: " + Obj)
      return
    print(Obj)
    print("•" * 60)
    for N, Attach in enumerate(Obj["items"][0]["attachments"]):
      print(N, Attach["photo"]["sizes"])
      print("•" * 60)
    """
    Base.AddMem(Blocks)
    return False

  def TestPosts(domain, offset, count):
    domain = domain.split("vk.com/")[-1]
    print("•Группа:", domain)
    Obj = Method("wall.get", "domain=%s&offset=%s&count=%s" % (domain, offset, count))
    if type(Obj) == str:
      print("  🔥😡🔥 Ошибка: " + Obj)
      return
    print("  Число записей в ней:", Obj["count"])
    print("  Проверка первых %s записей:" % count)
    Raz = True
    Limit = 3
    for Item in Obj["items"]:
      if Item["type"] != "post": continue
      #print(Item)
      #print(Item.keys())
      print("    id: %s; from: %s; date: %s" % (Item["id"], Item["from_id"], Item["date"]))
      GID = Item["owner_id"]
      if Item["from_id"] != UID: continue
      Raz = False
      like = Item["likes"]["can_like"] == 1
      print("    Число лайков:", Item["likes"]["count"], " ", "(можно лайкнуть)" if like else "(уже лайкнуто)")
      if like:
        if Limit > 0: Like("post", Item["owner_id"], Item["id"], Item.get("access_key"))
        else: print("  🤮 WTF?!")
        Limit -= 1
    print("  ID группы:", GID)
    if Raz and count > 5:
      print("  Можно создать запись!")
      Err = GroupPost(GID, Message, Image)
      if Err: return
      TestPosts(domain, offset, 5)
    if not Raz: print("  ☠️🤟☠️")

  def Memotron():
    nonlocal Path
    Path = GPath + "Мемы/"
    print("• Число - добавляет картинки,\n  • 'x' - пропускает,\n  • 'r' - отменяет,\n  • 'y' - отправляет,\n  • 'e' - выход")
    Arr = sorted(os.listdir(Path))
    Arr = [i for i in Arr if i not in Base.MemList]
    Selected, Pos, Begin, Len = [], 0, 0, len(Arr)
    if not Selected: exit("Happy end!")
    while True:
      print("~" * 60)
      print("Выбранные картинки (%s):" % len(Selected))
      for i in Selected: print("  •", i)
      if Pos < Len: print("Картинка на очереде:", Arr[Pos])
      else: print("Картинки закончились")
      Str = input("Ввод: ").lower()
      if Str == "x":
        print("Картинка пропущена")
        Pos += 1
        continue
      if Str == "r":
        print("Сброс")
        Pos, Selected = Begin, []
        continue
      if Str == "y":
        if input("Точно? [Y/n]: ").lower() != "y": continue
        #Selected = [Path + Name for Name in Selected]
        #print(Selected)
        GroupPost2(209308518, Selected)
        Selected, Begin = [], Pos
        if Pos >= Len: exit("Happy end!")
        continue
      if Str == "e": exit()
      try: Ch = int(Str)
      except ValueError:
        print("Введено не число :/")
        continue
      for i in range(Ch):
        if Pos >= Len: break
        Selected.append(Arr[Pos])
        Pos += 1

  api_request = "https://oauth.vk.com/token?grant_type=password&client_id=2274003&client_secret=hHbZxrka2uZ6jB1inYsH"
  #https://api.vk.com/method/METHOD_NAME?PARAMETERS&access_token=ACCESS_TOKEN&v=5.131
  api_request2 = "https://api.vk.com/method/%s?%s&access_token=%s&v=5.131"
  login, password = "ahmetshina_g@mail.ru", "7ZvqWw1O" # попытка ввести это в браузер, вообще не требует пароль, а сразу кидает на восстановление VK ;'-}
  if requests != None: session = requests.session()
  token = TryLogin()
  if token is None: Error("Увы, но не удалось войти :/")
  Token, UID = token
  print("token: %s...%s" % (Token[:16], Token[-16:]))
  print("UID:", UID)
  Sleep = 0.25
  R = 1
  if R == 0:
    Path = GPath + "PostRecord3/"
    with open(Path + "message.txt") as file: Message = file.read()
    with open(Path + "groups.txt") as file: Groups = file.read().split("\n")
    Image = Path + "img.jpg"
    for Group in Groups:
      print("_" * 72)
      TestPosts(Group, 0, 20)
  else: Memotron()

#174595517
#https://vk.com/stikeerboot
Bot()
#QbYic1K3lEV5kTGiqlq2
