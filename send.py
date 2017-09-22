#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append("/var/www/YNsifaSendCmd")
import web
import wsclient
web.config.debug = False
urls = (
    '/', 'code',
    '/login', "login",
    '/send', "send"
)

app = web.application(urls, globals())
application = app.wsgifunc()
session = web.session.Session(app, web.session.DiskStore('/var/www/YNsifaSendCmd/sessions/'), initializer={'SN_local_ID': "", "SN_local_token": "", "SN_romate_ID": "", "rom_recv": [], "use_obj" : None})
render = web.template.render('/var/www/YNsifaSendCmd/templates/')

class recv:
    def GET(self):
        return render.recv(session.rom_recv)

class send:
    def POST(self):
        i = web.input()
        hh = i.loc_send
        aa = session.use_obj.local_id
        bb = session.use_obj.token
        print "1"
        ws = wsclient.WebSocketClient(aa, bb)
        print "2"
        ws.setDaemon(True)
        print "3"
        ws.start()
        print "4"
        time.sleep(2)
        ws.on_send(session.use_obj.romet_id, hh)
        print "5"
        ws.add_handler(ws.on_recv)
        time_out = 5
        while time_out:
            if ws.result != None:
                break
            time.sleep(1)
            time_out -= 1

        dd_show = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        if ws.result == None:
            r_show = "未回到回应"
        else:
            r_show = ws.result

        cc = str(dd_show) + "  发送: " + str(hh.decode('utf-8')) + "    接收： " + str(r_show)
        #cc = "aaa"
        ws.sub_handler(ws.on_recv)
        session.rom_recv.append(cc)
        return render.send(session.SN_local_ID, session.SN_romate_ID, session.rom_recv)        


class code:
    def GET(self):
        print "aaaa"
        session.SN_local_ID = ""
        session.SN_local_token = ""
        session.SN_romate_ID = ""
        session.rom_recv = []
        info_show = "云南司法环境--欢迎使用结果查询！"
        return render.code(info_show)

class login:
    def POST(self):
        user = web.input()
        session.use_obj = wsclient.User_info(user.SN_loc, user.SN_rom)
        login_flag = session.use_obj.login()
        print login_flag
        if login_flag:
            session.SN_local_ID = session.use_obj.local_id
            session.SN_local_token = session.use_obj.token
            session.SN_romate_ID = session.use_obj.romet_id
            session.rom_recv.append("显示接收信息")
            print session.SN_local_ID, session.SN_local_token, session.SN_romate_ID
            return render.send(session.SN_local_ID, session.SN_romate_ID, session.rom_recv)
        else:
            info_show = "用户不存在或远端用户不存在，请确认后重新输入！"
            session.SN_local_ID = ""
            session.SN_local_token = ""
            session.SN_romate_ID = ""
            session.rom_recv = ""
            return render.code(info_show)

if __name__ == "__main__":
    app.run()
