# 单线程
# import time

# def boil_soup():
#     print("🍲 厨师长：开始熬鸡汤... (需要等5秒)")
#     time.sleep(5)  # 模拟耗时任务，这里程序会彻底卡住5秒
#     print("🍲 厨师长：鸡汤终于熬好了！")

# print("--- 单线程测试开始 ---")
# boil_soup() # 厨师长去熬汤了

# # 下面这行代码，必须等上面熬完汤才能执行
# print("👨‍🍳 厨师长：现在终于有空去招呼客人了。")

# 多线程
import time
import threading

class BackgroundManager:
    def __init__(self):
        # 邮箱：用来存放后台跑完的结果
        self._notification_queue = []
        # 锁：防止主线程和后台线程同时抢夺“邮箱”导致数据崩溃
        self._lock = threading.Lock()

    def _run_in_background(self, task_name, cost_time):
        """这是帮厨（后台线程）真正干活的函数"""
        print(f"\n   [后台] 帮厨开始执行: {task_name} (预计耗时 {cost_time} 秒)...")
        time.sleep(cost_time)  # 模拟耗时，比如跑 npm install
        
        result_msg = f"任务 [{task_name}] 已经大功告成！"
        
        # ⚠️ 关键点：帮厨准备往邮箱里塞结果了，必须先上锁！
        with self._lock:  
            self._notification_queue.append(result_msg)
        # with 语句结束，自动解锁。

    def spawn(self, task_name, cost_time):
        """主线程调用这个方法，把任务甩给后台"""
        # 招募一个帮厨（创建线程），并告诉他要干什么
        thread = threading.Thread(target=self._run_in_background, args=(task_name, cost_time))
        thread.start() # 踹一脚，去干活吧！

    def drain_queue(self):
        """主线程调用这个方法，安全地把邮箱里的结果一次性拿走"""
        # ⚠️ 关键点：主线程准备读邮箱了，也必须先上锁！
        with self._lock:
            # 把当前邮箱里的信件全部拿出来
            results = list(self._notification_queue)
            # 清空邮箱，等下次新信件
            self._notification_queue.clear()
        # 解锁
        return results

# ==========================================
# 下面是模拟智能体的主循环 (Agent Loop)
# ==========================================

print("=== 智能体启动 ===")
manager = BackgroundManager()

# 1. 智能体决定派发两个耗时任务 (spawn A, spawn B)
manager.spawn("npm install", 4)      # 耗时4秒
manager.spawn("docker build", 2)     # 耗时2秒

# 2. 智能体的主循环开始 (Agent Loop)
for i in range(5):
    print(f"\n[主线程] Agent 正在进行第 {i+1} 次思考/与用户聊天...")
    time.sleep(1) # 模拟处理其他事情耗时1秒
    
    # 3. 在下一次调用 LLM 之前，清空队列，看看有没有后台任务完成了 (drain queue)
    finished_tasks = manager.drain_queue()
    
    if finished_tasks:
        print(f"   [主线程] 收到后台传来的好消息：")
        for msg in finished_tasks:
            print(f"   -> 注入上下文: {msg}")
    else:
        print("   [主线程] 后台暂时没有任务完成，我继续干别的。")

print("\n=== 智能体运行结束 ===")