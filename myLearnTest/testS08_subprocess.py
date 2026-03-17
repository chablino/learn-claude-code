import subprocess

print("👨‍💼 Python总裁：秘书，你去系统命令行里帮我查一下，咱们现在的 Python 是什么版本？")

# 1. 总裁下达指令，外勤秘书 (subprocess) 出发！
# 这相当于你自己在键盘上敲下 "python --version" 然后回车
secretary_report = subprocess.run(
    "ls /bin",  # 要敲的命令
    capture_output=True,      # 总裁要求：把屏幕上弹出来的黑底白字给我抄回来！
    text=True,                # 总裁要求：翻译成我能直接读懂的文字 (String)
    shell=True                   # 这条命令要在 bash 里执行
)

print("\n🏃‍♂️ (秘书跑到操作系统里执行了命令，并拿着结果跑了回来...)\n")

# 2. 秘书汇报工作
print("📩 秘书汇报：")

# stdout (Standard Output) 就是正常的输出信息
if secretary_report.stdout:
    print(f"👉 正常情报 (stdout): {secretary_report.stdout.strip()}")

# stderr (Standard Error) 就是飘红的报错信息
if secretary_report.stderr:
    print(f"🚨 报错情报 (stderr): {secretary_report.stderr.strip()}")

print("\n👨‍💼 Python总裁：很好，我知道了，退下吧。")