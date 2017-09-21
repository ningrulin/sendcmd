# -*- coding: utf-8 -*-

'''
Created on Apr 1, 2016

@author: Guijie Wang / 王桂杰
'''
import time
import json
import uuid
import threading
import traceback
import thread
import requests
import base64
import constant
import websocket
import hashlib
import pymysql.cursors
import logging





###SQLconfig
configYNsifa = {
    'host': '116.52.253.210',
    'port': 3306,
    'user': 'root',
    'password': 'QWerASdf12#$',
    'db': 'mxsuser',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}
configPublic = {
    'host': 'rds94shy9735xhk329mvpublic.mysql.rds.aliyuncs.com',
    'port': 3306,
    'user': 'mxsuser',
    'password': 'mxspassword',
    'db': 'mxsuser',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# Connect to the database
connection = pymysql.connect(**configPublic)
#connection = pymysql.connect(**configYNsifa)


# do sql

def get_remote_id(remote_sn):

    try:
        with connection.cursor() as cursor:
            # search
            sql = 'SELECT userEntity_userID FROM mxsuser.account WHERE NAME =' + remote_sn
            cursor.execute(sql)
            # get result
            result = cursor.fetchone()
            userid = result['userEntity_userID']
            print (userid)
        # commit
        connection.commit()

    finally:
        connection.close()

    return userid

class WebSocketClient(threading.Thread):
    def __init__(self, user_num, basic_token):
        threading.Thread.__init__(self)
        self._handlers = []
        self.user_num = user_num
        self.ws = None
        self.basic_token = basic_token
        self.lock = threading.Lock()
        self.running_state = False
        self.result = None

    def set_basic_token(self, basic_token):
        self.basic_token = basic_token

    def add_handler(self, handler):
        self._handlers.append(handler)
        return self

    def sub_handler(self, handler):
        self._handlers.remove(handler)
        return self

    def fire(self, **kwargs):
        for handler in self._handlers:
            handler(**kwargs)

    def on_send(self, recv_id, send_cmd):
        id = str(uuid.uuid1())
        recv_list = []
        recv_list.append(recv_id)
        data = {"type" : "pub_req",
                "id" : id,
                "event":{"receivers" : recv_list,
                         "notify":{"name":"mx.remoteshell.request",
                                   "pub_type":"online",
                                   "nty_type":"app",
                                   "cmd": send_cmd
                                   }
                         }
                }
        data = json.dumps(data)
        self.ws.send(data)

    def on_message(self, ws,  message):
        try:
            json_data = json.loads(message)
            body = json_data.get("event", {})
            notify_id = body.get("id", "")
            notify = {"type": "notify_res",
                      "id": notify_id}
            send_h = json.dumps(notify)
            try:
                ws.send(send_h)
            except:
                if self.running_state:
                    print("The webSocket is off.")
                else:
                    print("WebSocket is closed normally.")

            self.fire(message=message, user_num=self.user_num, basic_token=self.basic_token)
        except Exception as e:
            print e

    def on_error(self, ws, error):
        print("WebSocket has an error " + str(error))

    def on_close(self, ws):
        if self.running_state:
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(constant.WS_URL,
                                             keep_running=True,
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close)
            self.ws.on_open = self.on_open
            self.ws.run_forever()
        else:
            print("WebSocket ### normal closed ###")

    def on_open(self, ws):
        auth_req = {"type": "identify_req",
                    "token": self.basic_token}
        params = json.dumps(auth_req)

        ws.send(params)
        heart_req = {"type": "heartbeat"}
        heart_params = json.dumps(heart_req)

        def run(*args):
            time_sleep = 0
            while 1:
                try:
                    time_sleep += 1
                    time.sleep(1)
                    if time_sleep == 30:
                        ws.send(heart_params)
                        time_sleep = 0
                except:
                    print traceback.format_exc()
                    print self.user_num

        thread.start_new_thread(run, ())

    def run(self):
        try:
            self.running_state = True
            websocket.enableTrace(False)
            # WebSocket.enableTrace(True)
            # 是否打印日志到屏幕
            # print ("Run WebSocketThread")
            self.ws = websocket.WebSocketApp(constant.WS_URL, keep_running=True,
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close)
            self.ws.on_open = self.on_open
            self.ws.run_forever()
        except:
            print traceback.format_exc()

    def stop(self):
        if isinstance(self.ws, websocket.WebSocketApp):
            self.running_state = False
            self.ws.close()

    def on_recv(self, **kwargs):
        if "message" in kwargs:
            json_data = json.loads(kwargs["message"])
            event = json_data.get("event", {})
            event_name = event.get("name", "")

            if event_name == "mx.remoteshell.response":
                self.result = event["result"]

class User_info(object):
    def __init__(self, local_sn, romte_sn):
        self.token = None
        self.uid = None
        self.romet_id = None
        self.local_id = None
        self.local_sn = local_sn
        self.romet_sn = romte_sn


    def login(self):
        url = constant.HTTP_LOGIN + "/mhauth/login"

        data = {"username": self.local_sn,
                "type": "box",
                "appkey": "10011801",}
        data = json.dumps(data)
        headers = {"Host": constant.HTTP_CAS_URL,
                   "Content-Type": "text/html; charset=utf-8"}
        r = requests.post(url, headers=headers, data=data)
        if r.status_code != 401:
            return False

        # get the dict mm = {"nonce": value1, "Digest realm": value2}
        c1 = r.headers
        dd = c1["Www-Authenticate"]
        kk = dd.split(',')
        mm = {}
        tt0 = kk[0].split('=')[0].strip()
        len1 = len(kk[0].split('=')[1].strip())
        mm.update({tt0: kk[0].split('=')[1].strip()[1:len1 - 1]})
        tt1 = kk[1].split('=')[0].strip()
        len2 = len(kk[1].split('=')[1].strip())
        mm.update({tt1: kk[1].split('=')[1].strip()[1:len2 - 1]})

        # start md5,get respone
        u_name = self.local_sn

        cc = mm['nonce']
        pwd = cc[int(u_name[4])] + cc[int(u_name[5])] + cc[int(u_name[6])] + cc[int(u_name[7])] + cc[int(u_name[8])] + cc[int(u_name[9])] + cc[int(u_name[10])] + cc[int(u_name[11])]
        ha1_str = u_name + ":" + mm['Digest realm'] + ":" + pwd
        has1 = hashlib.md5()
        has1.update(ha1_str)
        HA1 = has1.hexdigest()

        ha2_str = HA1 + mm['nonce']
        has2 = hashlib.md5()
        has2.update(ha2_str)
        HA2 = has2.hexdigest()

        # get service_token
        auth_str = "Digest username=" + "\"" + u_name + "\"" + ',' + 'realm=' + "\"" + mm['Digest realm'] + "\"" + "," + \
                   "nonce=" + "\"" + mm['nonce'] + "\"" + ',' + 'response=' + "\"" + HA2 + "\""
        headers = {"Host": constant.HTTP_CAS_URL,
                   "authorization": auth_str,
                   "Content-Type": "text/html; charset=utf-8"}

        r = requests.post(url, headers=headers)
        if r.status_code != 200:
            return False

        print r.text


        # get basetoken
        service_token = json.loads(r.text)["token"]
        time_stamp = str(int(round(time.time() * 1000)))
        self.token = 'Basic ' + base64.b64encode(service_token + ":" + time_stamp + ":" + "v1")

        print self.token

        # get local_id

        url = constant.HTTP_CAS + "/mhauth/account"
        headers = {"Host": constant.HTTP_URL,
                   'authorization': self.token,
                   "Content-Type": "application/json; charset=utf-8"}
        data = {
            "version": "3.3.0"
        }
        data = json.dumps(data)
        r = requests.post(url, headers=headers, data=data)
        self.local_id = json.loads(r.text)["userid"]
        re_sn = self.romet_sn
        re_id = get_remote_id(re_sn)
        self.romet_id = re_id
        return True

        #get remote_id





def main():
    user_in = User_info("502725100024", "502718100004")
    if user_in.login():
        ws = WebSocketClient(user_in.local_id, user_in.token)
        ws.setDaemon(True)
        ws.start()
        time.sleep(2)
        send_cmd = "cd /sdcard/"
        ws.on_send(user_in.romet_id, send_cmd=send_cmd)

        ws.add_handler(ws.on_recv)
        time.sleep(30)
        print "haha"
        ws.sub_handler(ws.on_recv)

if __name__ == '__main__':
    main()

