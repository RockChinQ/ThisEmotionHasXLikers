from time import sleep
from tkinter.tix import Tree
import QzoneMgr


interval=5

template="""这条说说有
{{likers}}个点赞
{{comments}}条评论
{{forwards}}次转发
试试看！"""

def cookie_invalidated_callback():
    print("cookie已失效")

def get_emotion_content(likers,comments,forwards,interval):
    global template

    result=template

    result=result.replace('{{likers}}',str(likers))
    result=result.replace('{{comments}}',str(comments))
    result=result.replace('{{forwards}}',str(forwards))
    result=result.replace('{{interval}}',str(interval))
    return result

if __name__=='__main__':
    uin=int(input('QQ号:'))
    cookie=input('QQ空间cookie:')

    #登录
    oper=QzoneMgr.QzoneOperator(uin,cookie,keepalive=True,cookie_invalidated_callback=cookie_invalidated_callback)

    tid=input("跟踪tid,输入1发表新说说:")
    # 发表说说
    if tid=='1':
        tid=oper.publish_emotion(get_emotion_content(0,0,0,10))
    else:
        if oper.tid_valid(tid):
            print("可用的说说tid")
        else:
            raise Exception('tid 无效')
    print(tid)

    ls_traffic=(0,0,0)
    # 开始检测
    while True:
        sleep(interval)
        traffic=oper.get_traffic_data(tid)
        print("检测流量:",traffic)
        if traffic[0]==-1:
            print("检测流量失败")
        else:
            if traffic != ls_traffic:
                print("更新说说内容")
                oper.update_emotion(tid,get_emotion_content(traffic[0],traffic[1],traffic[2],interval))
                ls_traffic=traffic