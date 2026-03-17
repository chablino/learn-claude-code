import threading
import subprocess
import queue
import time
import sys

def background_worker(task_name, sleep_seconds, result_queue, start_gun_time):
    """这是后台帮厨线程，负责调起系统进程并记录微秒级的时间戳"""
    # 记录线程苏醒并开始干活的时间
    thread_wake_time = time.time()
    
    # 构造跨平台的 sleep 命令：python -c "import time; time.sleep(5)"
    cmd = [sys.executable, "-c", f"import time; time.sleep({sleep_seconds})"]
    
    # 记录系统进程真正开始调用的时间
    process_start_time = time.time()
    subprocess.run(cmd)
    process_end_time = time.time()
    
    # 将包含详细时间戳的“信件”塞入队列
    result_queue.put({
        "task_name": task_name,
        "sleep": sleep_seconds,
        "thread_delay": thread_wake_time - start_gun_time,      # 线程启动延迟
        "process_delay": process_start_time - thread_wake_time, # 系统分配进程的延迟
        "total_time": process_end_time - start_gun_time         # 总耗时
    })

def main():
    print("🚀 主线程：系统预热中...")
    q = queue.Queue()
    
    # 我们用 5, 7, 9 秒，但为了更快看到结果，你可以改成 0.5, 0.7, 0.9 体验极速竞态
    tasks = [
        ("Task-A", 5.0),
        ("Task-B", 7.0),
        ("Task-C", 9.0)
    ]
    
    print("\n🔫 主线程：发令枪响！瞬间同时启动所有后台任务...")
    start_gun_time = time.time()
    
    # 瞬间爆发，把所有线程扔进 OS 调度池
    for name, sleep_sec in tasks:
        t = threading.Thread(
            target=background_worker, 
            args=(name, sleep_sec, q, start_gun_time)
        )
        t.daemon = True # 设为守护线程
        t.start()
        print(f"[{time.time() - start_gun_time:.4f}s] 主线程：已将 {name} ({sleep_sec}s) 扔进线程池")

    # 模拟 Agent 的 while True 轮询邮箱
    print("\n📥 主线程：进入死循环，开始高频查收信箱...\n")
    completed_tasks = 0
    
    while completed_tasks < len(tasks):
        try:
            # 相当于 notifs = BG.drain_notifications()
            # 设置极短的 timeout，模拟主线程的不等待特性
            result = q.get(timeout=0.2) 
            
            completed_tasks += 1
            print(f"✅ [查收成功] 收到 {result['task_name']} 的结果！")
            print(f"   ├─ 预期 Sleep: {result['sleep']} 秒")
            print(f"   ├─ 线程启动卡顿: {result['thread_delay']:.4f} 秒")
            print(f"   ├─ OS分配进程卡顿: {result['process_delay']:.4f} 秒")
            print(f"   └─ 实际真实总耗时: {result['total_time']:.4f} 秒\n")
            
        except queue.Empty:
            # 邮箱是空的，主线程继续转圈圈（这里用打印一个点代替 LLM 请求）
            print(".", end="", flush=True)

    print(f"\n🎉 主线程：所有任务查收完毕！总运行时间: {time.time() - start_gun_time:.4f} 秒")

if __name__ == "__main__":
    main()