# drawing_server/log_utils.py
#==============================================
#   妥协写法
#   用于实现前端日志呈现
#   在多线程并发情况下可能会导致日志混乱
#==============================================

import threading

# 创建一个线程局部变量空间
# 这就像一个魔法盒子，不同线程（不同任务）往里放东西，互不干扰
_thread_locals = threading.local()

def init_logger(logger_func):
    """
    在任务开始时调用。
    logger_func: 就是 views.py 里那个能写数据库的函数
    """
    _thread_locals.logger = logger_func

def log(msg):
    """
    替代 print 的全局日志函数
    """
    # 检查当前线程有没有注册过 logger
    logger = getattr(_thread_locals, 'logger', None)
    
    if logger:
        # 如果有注册（说明是在后台任务线程里），就写入数据库
        logger(msg)
    else:
        # 如果没有注册（说明是普通调试），就直接打印到控制台
        print(msg)