import pymysql.cursors

###URLS
# WS_URL = "ws://mxcloud.meetsoon.net/push/subscribe"
# HTTP_LOGIN = "http://cas.meetsoon.net"
# HTTP_URL= "http://mxcloud.meetsoon.net"

WS_URL = "ws://116.52.253.210:9999/push/subscribe"
HTTP_LOGIN = "http://116.52.253.210:9999"
HTTP_URL= "116.52.253.210:9999"

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
#connection = pymysql.connect(**configPublic)
connection = pymysql.connect(**configYNsifa)

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