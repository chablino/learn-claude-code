import os
from dotenv import load_dotenv

# 默认写法：如果 .zshrc 里有，就听 .zshrc 的 (不覆盖)
# load_dotenv() 

# 霸道写法：不管 .zshrc 里写了什么，统统用我当前项目 .env 里的值覆盖掉！
load_dotenv(override=True)

print(os.getenv("OPENROUTER_BASE_URL"))