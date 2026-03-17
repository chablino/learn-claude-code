# print([i for i in range(10, 0, -1)])

# print(sorted([i for i in range(10, 0, -1)], reverse=True))
# print(sorted([i for i in range(10, 0, -1)]))

from pathlib import Path
import random


# path = Path("/home/zxy/Downloads")

# result =[path/f"task_{a}.json" for a in random.sample(range(1, 11), 10)]
# print(sorted(result, key = lambda x: int(x.stem.split("_")[1])))

# for i in random(0, 10):
#     print(i)
# print(a[1])

print(list(set([1,1,1,1,2,2,3])))