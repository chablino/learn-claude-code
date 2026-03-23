import sys
import time

# 固定两位数，方便用两个退格字符精确覆盖
sys.stdout.write("剩余秒数: 10")
sys.stdout.flush()

for i in range(2, 10, 2):
    time.sleep(0.5)
    # \b\b 把光标左移两格，然后写入新数字
    sys.stdout.write("\b" + f"{i:01d}")
    sys.stdout.flush()

print("\n完成")