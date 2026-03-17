def universal_logger(func, a, b):
    # 用 *args 和 **kw 接收任意参数（打包）
    def inner_box(a, b):
        print(f"准备执行函数：{func.__name__}")

        # 用 *args 和 **kw 把参数原封不动地传给原函数（解包）
        result = func(a, b)

        print("执行完毕！")
        return result

    return inner_box


@universal_logger
def calculate_sum(a, b):
    return a + b


print(calculate_sum(10, b=20))

# def logger_wrapper(func):
#     def inner_box(item):
#         print("【系统日志】开始执行...")
#         func(item)
#         print("【系统日志】执行结束！")
#     return inner_box

# # 见证奇迹的时刻：直接贴标签！
# @logger_wrapper
# def say_hello(item):
#     print(f"你好，{item}")

# # 运行（它会自动带上包装盒的功能）
# say_hello("小明")

# 1. 定义贴膜小哥（接收一个普通函数 func）
# def logger_wrapper(func):
#     def inner_box(item):
#         print("【系统日志】开始执行...")
#         func(item)  # 执行原本的手机功能
#         print("【系统日志】执行结束！")
#     return inner_box  # 把包装好的新手机还给你

# def say_hello(item):
#     print(f"你好，{item}")

# # 2. 手动包装（极其啰嗦）
# say_hello = logger_wrapper(say_hello)

# # 3. 运行
# say_hello("小明")
