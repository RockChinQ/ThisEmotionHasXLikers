# This Emotion Has X Likers

受到 [This-repo-has-N-stars](https://github.com/fslongjin/This-repo-has-1256-stars) 的启发  
做一个发表一条说说并自动监控和更新其点赞量、评论量、转发量到其内容的脚本

## 注意

短时间内进行多次编辑后，程序不再能正常编辑说说内容

## 使用

- 在`main.py`里更改`interval变量`,设置每次轮询检测数据间隔的秒数  
- 在`main.py`里更改`template变量`,设置说说内容模板,`{{likers}}` `{{comments}}` `{{forwards}}` `{{interval}}`将被分别替换为点赞量、评论量、转发量、间隔秒数
- 登录网页版QQ空间,F12打开`调试窗口`->`网络`,挨个包查找,找到请求头带有cookie的包,复制cookie内容
- 运行`python main.py`,输入QQ号,输入刚刚复制的cookie,输入1发表新说说
- 程序将发表说说并输出说说的tid
- 每`interval`秒轮询检测一次