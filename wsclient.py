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
        url1 = constant.HTTP_LOGIN + "/cas/v1/tickets"
        data = "username=" + self.local_sn + "&password=" + self.local_sn + "&type=MOBILE"
        r1 = requests.post(url=url1, data=data)
        if r1.status_code != 201:
            return False
        # 2.st
        url2 = r1.headers['LOCATION']
        data = "service=" + constant.HTTP_LOGIN + "/sch/v1/tokens/android,2.3.3"
        r2 = requests.post(url=url2, data=data)
        if r2.status_code != 200:
            return False
        # 3.token
        url3 = constant.HTTP_LOGIN + "/sch/v1/tokens/android,2.3.3?ticket=" + r2.text
        r3 = requests.post(url=url3)
        if r3.status_code != 200:
            return False
        # 4.basetoken
        session_token = json.loads(r3.text)["token"]
        aa = str(time.time())
        cc = aa.split('.')[1]
        if len(cc) < 1:
            cc = cc + "000"
        elif len(cc) < 2:
            cc = cc + "00"
        else:
            cc = cc + "0"
        time_cc = aa.split('.')[0] + cc

        session_token = session_token + ":" + time_cc
        base_token = "Basic " + base64.b64encode(session_token)
        self.token = base_token

        #5.local_info
        url = constant.HTTP_URL + "/cxf/security/persons/" + self.local_sn
        headers = {"Content-Type": "application/json; charset=utf-8",
                   "authorization": base_token}
        rr = requests.get(url=url, headers=headers)
        if rr.status_code != 200:
            return False
        self.local_id = json.loads(rr.text)["userID"]

       #6. romote_info
        url = constant.HTTP_URL + "/cxf/security/persons/" + self.romet_sn
        headers = {"Content-Type": "application/json; charset=utf-8",
                   "authorization": base_token}
        rr = requests.get(url=url, headers=headers)
        if rr.status_code != 200:
            return False

        self.romet_id = json.loads(rr.text)["userID"]
        return True

def main():
    user_in = User_info("008613025411186", "502718100004")
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

