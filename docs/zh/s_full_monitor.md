# s_full.py 全流程模拟追踪

> 模拟场景：用户输入 "Create a README and a test file for project X, use a teammate for README"
> 工作目录：`/home/user/project-x`

---

# 1. 程序启动 (`__main__`)

<details>
<summary>初始化全局对象</summary>

```
WORKDIR = Path("/home/user/project-x")
MODEL = "stepfun/step-3.5-flash:free"
```

依次构造全局实例：

| 变量       | 类                  | 关键初始状态                             |
| ---------- | ------------------- | ---------------------------------------- |
| `TODO`     | `TodoManager`       | `items = []`                             |
| `SKILLS`   | `SkillLoader`       | 扫描 `skills/` 目录                      |
| `TASK_MGR` | `TaskManager`       | 💾 创建 `.tasks/` 目录                    |
| `BG`       | `BackgroundManager` | `tasks = {}, notifications = Queue()`    |
| `BUS`      | `MessageBus`        | 💾 创建 `.team/inbox/` 目录               |
| `TEAM`     | `TeammateManager`   | 💾 创建 `.team/` 目录，加载 `config.json` |

💾 磁盘写入：创建目录 `.tasks/`、`.team/`、`.team/inbox/`

<details>
<summary>📁 文件快照</summary>

```
/home/user/project-x/
├── .tasks/          (空目录)
├── .team/
│   └── inbox/       (空目录)
└── skills/          (假设不存在 → SKILLS.skills = {})
```

</details>

### 1.1 SkillLoader 初始化

```python
skills_dir = Path("/home/user/project-x/skills")
skills_dir.exists() → False
self.skills = {}
```

分支走向：`skills/` 不存在 → 跳过扫描 → `descriptions()` 返回 `"(no skills)"`

### 1.2 SYSTEM prompt 构建

```python
SYSTEM = "You are a coding agent at /home/user/project-x. Use tools to solve tasks.\n..."
# Skills: (no skills)
```

### 1.3 进入 REPL 循环

```python
history = []
query = input(...)  # 用户输入: "Create a README and a test file for project X, use a teammate for README"
```

```python
history = [
    {"role": "user", "content": "Create a README and a test file for project X, use a teammate for README"}
]
```

调用 → `agent_loop(history)`

</details>

---

# 2. agent_loop — 第 1 轮

<details>
<summary>预处理阶段（compression / bg drain / inbox check）</summary>

## 2.1 microcompact(messages)

```python
messages 长度 = 1
扫描 tool_result 部分 → indices = []
len(indices) = 0 ≤ 3 → 直接 return，不做任何清理
```

分支走向：`len(indices) <= 3` → 提前返回

## 2.2 estimate_tokens 检查

```python
estimate_tokens(messages) ≈ len('...') // 4 ≈ 30
30 < TOKEN_THRESHOLD(100000) → 不触发 auto_compact
```

分支走向：不压缩

## 2.3 BG.drain()

```python
notifications Queue 为空 → notifs = [] → 不注入 background-results
```

## 2.4 BUS.read_inbox("lead")

```python
path = .team/inbox/lead.jsonl → 不存在 → return []
inbox = [] → 不注入 inbox 消息
```

</details>

<details>
<summary>LLM 调用 → 返回 3 个 tool_use</summary>

## 2.5 LLM 响应（模拟）

LLM 返回 `stop_reason = "tool_use"`，content 包含 3 个 tool_use block：

| #    | tool_name     | input                                                        |
| ---- | ------------- | ------------------------------------------------------------ |
| 1    | `task_create` | `{"subject": "Write README.md", "description": "Create project README for project X"}` |
| 2    | `task_create` | `{"subject": "Write tests", "description": "Create test_main.py for project X"}` |
| 3    | `TodoWrite`   | `{"items": [{"content":"Create README","status":"in_progress","activeForm":"task_create"},{"content":"Create tests","status":"pending","activeForm":"task_create"}]}` |

</details>

<details>
<summary>工具执行</summary>

## 2.6 tool: task_create("Write README.md")

```python
TASK_MGR._next_id():
    ids = [int(f.stem.split("_")[1]) for f in .tasks/glob("task_*.json")]
    → ids = [] → return max([], default=0) + 1 = 1

task = {
    "id": 1,
    "subject": "Write README.md",
    "description": "Create project README for project X",
    "status": "pending",
    "owner": None,
    "blockedBy": [],
    "blocks": []
}
```

💾 `TASK_MGR._save(task)` → 写入 `.tasks/task_1.json`

<details>
<summary>📁 文件快照 — .tasks/task_1.json</summary>

```json
{
  "id": 1,
  "subject": "Write README.md",
  "description": "Create project README for project X",
  "status": "pending",
  "owner": null,
  "blockedBy": [],
  "blocks": []
}
```

</details>

输出: `'{\n  "id": 1, ...}'`

---

## 2.7 tool: task_create("Write tests")

```python
TASK_MGR._next_id():
    ids = [1] → max = 1 → return 2

task = {
    "id": 2,
    "subject": "Write tests",
    "description": "Create test_main.py for project X",
    "status": "pending",
    "owner": None,
    "blockedBy": [],
    "blocks": []
}
```

💾 写入 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Write tests",
  "description": "Create test_main.py for project X",
  "status": "pending",
  "owner": null,
  "blockedBy": [],
  "blocks": []
}
```

</details>

---

## 2.8 tool: TodoWrite

```python
TODO.update(items):
    validated = [], ip = 0
    
    Item 0: content="Create README", status="in_progress", activeForm="task_create"
        → status == "in_progress" → ip = 1
        → validated.append({...})
    
    Item 1: content="Create tests", status="pending", activeForm="task_create"
        → validated.append({...})
    
    len(validated) = 2 ≤ 20 ✓
    ip = 1 ≤ 1 ✓
    
    self.items = validated
    return self.render()
```

`render()` 输出:
```
[>] Create README <- task_create
[ ] Create tests
(0/2 completed)
```

### 变量状态

```python
used_todo = True
rounds_without_todo = 0  (因为 used_todo → reset)
manual_compress = False
```

</details>

<details>
<summary>Nag 检查 & 消息追加</summary>

## 2.9 Nag reminder 检查

```python
rounds_without_todo = 0 (刚 reset)
TODO.has_open_items() → True (2 items, none completed)
rounds_without_todo(0) < 3 → 不触发 nag
```

分支走向：不插入 reminder

results 被追加到 messages:
```python
messages.append({"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "...", "content": "{task_1 json}"},
    {"type": "tool_result", "tool_use_id": "...", "content": "{task_2 json}"},
    {"type": "tool_result", "tool_use_id": "...", "content": "[>] Create README..."}
]})
```

</details>

---

# 3. agent_loop — 第 2 轮

<details>
<summary>预处理 → LLM 返回 spawn_teammate + background_run</summary>

## 3.1 microcompact

```python
扫描 messages → 找到 1 组 tool_result (3个 part)
len(indices) = 3 ≤ 3 → 不清理
```

## 3.2 estimate_tokens → ≈ 800 < 100000 → 不压缩

## 3.3 BG.drain() → [] → 无通知

## 3.4 BUS.read_inbox("lead") → [] → 无消息

## 3.5 LLM 响应（模拟）

LLM 返回 `stop_reason = "tool_use"`：

| #    | tool_name        | input                                                        |
| ---- | ---------------- | ------------------------------------------------------------ |
| 1    | `spawn_teammate` | `{"name": "writer", "role": "docs", "prompt": "Write README.md for project X. Subject: Write README.md. Desc: Create project README for project X. Claim task #1 first."}` |
| 2    | `background_run` | `{"command": "find . -name '*.py' -not -path './.tasks/*'", "timeout": 30}` |

</details>

<details>
<summary>工具执行</summary>

## 3.6 tool: spawn_teammate("writer", "docs", ...)

```python
TEAM._find("writer") → None (members = [])

member = {"name": "writer", "role": "docs", "status": "working"}
self.config["members"].append(member)
```

💾 `TEAM._save()` → 写入 `.team/config.json`

<details>
<summary>📁 文件快照 — .team/config.json</summary>

```json
{
  "team_name": "default",
  "members": [
    {
      "name": "writer",
      "role": "docs",
      "status": "working"
    }
  ]
}
```

</details>

启动 `threading.Thread(target=self._loop, args=("writer", "docs", "Write README.md..."))` → 后台线程开始

输出: `"Spawned 'writer' (role: docs)"`

---

## 3.7 tool: background_run("find . -name '*.py' ...")

```python
BG.run(command, timeout=30):
    tid = uuid4()[:8] → 假设 "a1b2c3d4"
    self.tasks["a1b2c3d4"] = {"status": "running", "command": "find ...", "result": None}
    启动 Thread → _exec("a1b2c3d4", "find ...", 30)
```

输出: `"Background task a1b2c3d4 started: find . -name '*.py' -not -path './.tasks/*'"`

### 变量状态

```python
used_todo = False
rounds_without_todo = 0 + 1 = 1
manual_compress = False
```

Nag 检查: `TODO.has_open_items()=True`, `rounds_without_todo=1 < 3` → 不触发

</details>

---

# 4. Teammate "writer" 后台线程 — 工作阶段

<details>
<summary>writer 线程初始化 & 第 1 轮工具调用</summary>

## 4.1 线程启动

```python
name = "writer", role = "docs"
sys_prompt = "You are 'writer', role: docs, team: default, at /home/user/project-x. ..."
messages = [{"role": "user", "content": "Write README.md for project X. Claim task #1 first."}]
```

## 4.2 Inbox 检查

```python
BUS.read_inbox("writer"):
    path = .team/inbox/writer.jsonl → 不存在 → return []
inbox = [] → 无消息
```

## 4.3 LLM 调用 → writer 的 LLM 返回 claim_task + write_file

| #    | tool_name    | input                                                        |
| ---- | ------------ | ------------------------------------------------------------ |
| 1    | `claim_task` | `{"task_id": 1}`                                             |
| 2    | `write_file` | `{"path": "README.md", "content": "# Project X\n\nA sample project.\n\n## Getting Started\n\n..."}` |

## 4.4 tool: claim_task(1)

```python
TASK_MGR.claim(1, "writer"):
    task = _load(1) → 读取 .tasks/task_1.json
    task["owner"] = "writer"
    task["status"] = "in_progress"
    _save(task)
```

💾 更新 `.tasks/task_1.json`

<details>
<summary>📁 文件快照 — .tasks/task_1.json</summary>

```json
{
  "id": 1,
  "subject": "Write README.md",
  "description": "Create project README for project X",
  "status": "in_progress",
  "owner": "writer",
  "blockedBy": [],
  "blocks": []
}
```

</details>

输出: `"Claimed task #1 for writer"`

---

## 4.5 tool: write_file("README.md", ...)

```python
run_write("README.md", "# Project X\n..."):
    fp = safe_path("README.md") → /home/user/project-x/README.md
    fp.parent.mkdir(parents=True, exist_ok=True)  # 已存在
    fp.write_text("# Project X\n\nA sample project.\n\n## Getting Started\n\n...")
```

💾 写入 `README.md`

<details>
<summary>📁 文件快照 — README.md</summary>

```markdown
# Project X

A sample project.

## Getting Started

Run `python main.py` to start.
```

</details>

输出: `"Wrote 78 bytes to README.md"`

</details>

<details>
<summary>writer 第 2 轮 → send_message + idle</summary>

## 4.6 writer LLM 第 2 轮 → send_message + idle

| #    | tool_name      | input                                                        |
| ---- | -------------- | ------------------------------------------------------------ |
| 1    | `send_message` | `{"to": "lead", "content": "README.md done. Task #1 complete."}` |
| 2    | `idle`         | `{}`                                                         |

## 4.7 tool: send_message("lead", ...)

```python
BUS.send("writer", "lead", "README.md done. Task #1 complete.", "message"):
    msg = {
        "type": "message",
        "from": "writer",
        "content": "README.md done. Task #1 complete.",
        "timestamp": 1711000100.0
    }
```

💾 追加写入 `.team/inbox/lead.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/lead.jsonl</summary>

```json
{"type": "message", "from": "writer", "content": "README.md done. Task #1 complete.", "timestamp": 1711000100.0}
```

</details>

## 4.8 tool: idle

```python
idle_requested = True
output = "Entering idle phase."
```

`break` 跳出内层 for 循环 → 进入 IDLE PHASE

## 4.9 writer 进入 idle

```python
self._set_status("writer", "idle")
```

💾 更新 `.team/config.json`

<details>
<summary>📁 文件快照 — .team/config.json</summary>

```json
{
  "team_name": "default",
  "members": [
    {
      "name": "writer",
      "role": "docs",
      "status": "idle"
    }
  ]
}
```

</details>

</details>

---

# 5. agent_loop — 第 3 轮（无 TodoWrite → rounds_without_todo 递增）

<details>
<summary>预处理 → background 结果到达 + inbox 消息到达</summary>

## 5.1 microcompact

```python
扫描所有 tool_result parts → indices 现在有 5 个 part (来自第1轮3个 + 第2轮2个)
len(indices) = 5 > 3 → 清理前 5-3=2 个:
    indices[0].content = "[cleared]"  (原 task_1 json, len > 100)
    indices[1].content = "[cleared]"  (原 task_2 json, len > 100)
```

分支走向：`len(indices) > 3` → 清理旧 tool_result

## 5.2 estimate_tokens → ≈ 2500 < 100000 → 不压缩

## 5.3 BG.drain()

后台 `find` 命令已完成，`_exec` 已将结果放入 Queue:

```python
notifs = [
    {
        "task_id": "a1b2c3d4",
        "status": "completed",
        "result": "./main.py\n./utils.py"
    }
]
```

注入消息:
```python
messages.append({"role": "user", "content": "<background-results>\n[bg:a1b2c3d4] completed: ./main.py\n./utils.py\n</background-results>"})
messages.append({"role": "assistant", "content": "Noted background results."})
```

## 5.4 BUS.read_inbox("lead")

💾 读取并清空 `.team/inbox/lead.jsonl`

```python
inbox = [
    {"type": "message", "from": "writer", "content": "README.md done. Task #1 complete.", "timestamp": 1711000100.0}
]
```

💾 `path.write_text("")` → 清空 `lead.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/lead.jsonl</summary>

```
(空文件)
```

</details>

注入消息:
```python
messages.append({"role": "user", "content": "<inbox>[{\"type\":\"message\",\"from\":\"writer\",...}]</inbox>"})
messages.append({"role": "assistant", "content": "Noted inbox messages."})
```

</details>

<details>
<summary>LLM 调用 → task_update + write_file + load_skill</summary>

## 5.5 LLM 响应

| #    | tool_name     | input                                                        |
| ---- | ------------- | ------------------------------------------------------------ |
| 1    | `task_update` | `{"task_id": 1, "status": "completed"}`                      |
| 2    | `write_file`  | `{"path": "test_main.py", "content": "import unittest\n\nclass TestMain(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n\nif __name__ == '__main__':\n    unittest.main()\n"}` |
| 3    | `load_skill`  | `{"name": "testing"}`                                        |

## 5.6 tool: task_update(1, status="completed")

```python
TASK_MGR.update(1, status="completed"):
    task = _load(1) → task_1.json
    task["status"] = "completed"
    
    # 完成时检查依赖解除:
    for f in .tasks/glob("task_*.json"):
        t = json.loads(f.read_text())
        if 1 in t.get("blockedBy", []):  # task_2.blockedBy = [] → 不匹配
            pass
    
    _save(task)
```

💾 更新 `.tasks/task_1.json`

<details>
<summary>📁 文件快照 — .tasks/task_1.json</summary>

```json
{
  "id": 1,
  "subject": "Write README.md",
  "description": "Create project README for project X",
  "status": "completed",
  "owner": "writer",
  "blockedBy": [],
  "blocks": []
}
```

</details>

---

## 5.7 tool: write_file("test_main.py", ...)

```python
run_write("test_main.py", "import unittest\n..."):
    fp = safe_path("test_main.py") → /home/user/project-x/test_main.py
    fp.write_text(...)
```

💾 写入 `test_main.py`

<details>
<summary>📁 文件快照 — test_main.py</summary>

```python
import unittest

class TestMain(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
```

</details>

输出: `"Wrote 137 bytes to test_main.py"`

---

## 5.8 tool: load_skill("testing")

```python
SKILLS.load("testing"):
    self.skills.get("testing") → None
    return "Error: Unknown skill 'testing'. Available: "
```

分支走向：skill 不存在 → 返回错误

### 变量状态

```python
used_todo = False
rounds_without_todo = 1 + 1 = 2
manual_compress = False
```

Nag: `has_open_items()=True`, `rounds_without_todo=2 < 3` → 不触发

</details>

---

# 6. agent_loop — 第 4 轮（触发 Nag Reminder）

<details>
<summary>预处理 → LLM → task_update + claim_task（仍无 TodoWrite）</summary>

## 6.1 预处理

- microcompact: indices 增长，清理更多旧 tool_result
- estimate_tokens: ≈ 4000 < 100000
- BG.drain(): []
- BUS.read_inbox("lead"): []

## 6.2 LLM 响应

| #    | tool_name     | input                                     |
| ---- | ------------- | ----------------------------------------- |
| 1    | `task_update` | `{"task_id": 2, "status": "in_progress"}` |
| 2    | `claim_task`  | `{"task_id": 2}`                          |

## 6.3 tool: task_update(2, status="in_progress")

```python
task = _load(2)
task["status"] = "in_progress"
_save(task)
```

💾 更新 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Write tests",
  "description": "Create test_main.py for project X",
  "status": "in_progress",
  "owner": null,
  "blockedBy": [],
  "blocks": []
}
```

</details>

## 6.4 tool: claim_task(2)

```python
TASK_MGR.claim(2, "lead"):
    task["owner"] = "lead"
    task["status"] = "in_progress"  # 已经是
    _save(task)
```

💾 更新 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Write tests",
  "description": "Create test_main.py for project X",
  "status": "in_progress",
  "owner": "lead",
  "blockedBy": [],
  "blocks": []
}
```

</details>

## 6.5 Nag Reminder 触发

```python
used_todo = False
rounds_without_todo = 2 + 1 = 3
TODO.has_open_items() → True (items[0] in_progress, items[1] pending)
rounds_without_todo(3) >= 3 → ✅ 触发 nag!
```

```python
results.insert(0, {
    "type": "text",
    "text": "<reminder>Update your todos.</reminder>"
})
```

分支走向：nag 条件满足 → 插入 reminder 到 results 头部

</details>

---

# 7. agent_loop — 第 5 轮（TodoWrite 更新 + compress + shutdown）

<details>
<summary>LLM 响应 → TodoWrite + task_update + compress + shutdown_request</summary>

## 7.1 预处理

- microcompact: 继续清理
- estimate_tokens: ≈ 6000 < 100000
- BG.drain(): []
- BUS.read_inbox("lead"): []

## 7.2 LLM 响应

| #    | tool_name          | input                                                        |
| ---- | ------------------ | ------------------------------------------------------------ |
| 1    | `TodoWrite`        | `{"items": [{"content":"Create README","status":"completed","activeForm":"done"},{"content":"Create tests","status":"completed","activeForm":"done"}]}` |
| 2    | `task_update`      | `{"task_id": 2, "status": "completed"}`                      |
| 3    | `compress`         | `{}`                                                         |
| 4    | `shutdown_request` | `{"teammate": "writer"}`                                     |

## 7.3 tool: TodoWrite (更新)

```python
TODO.update(items):
    Item 0: content="Create README", status="completed", activeForm="done" → ok
    Item 1: content="Create tests", status="completed", activeForm="done" → ok
    ip = 0 (无 in_progress) ✓
    self.items = validated
```

`render()`:
```
[x] Create README
[x] Create tests

(2/2 completed)
```

```python
used_todo = True → rounds_without_todo = 0
```

---

## 7.4 tool: task_update(2, status="completed")

```python
task = _load(2)
task["status"] = "completed"

# 检查依赖解除: 遍历所有 task_*.json
# task_1.blockedBy = [] → 不含 2
# task_2 是自己 → 不含 2
# 无需解除

_save(task)
```

💾 更新 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Write tests",
  "description": "Create test_main.py for project X",
  "status": "completed",
  "owner": "lead",
  "blockedBy": [],
  "blocks": []
}
```

</details>

---

## 7.5 tool: compress

```python
handler = TOOL_HANDLERS["compress"] → lambda: "Compressing..."
manual_compress = True
output = "Compressing..."
```

---

## 7.6 tool: shutdown_request("writer")

```python
handle_shutdown_request("writer"):
    req_id = uuid4()[:8] → 假设 "x9y8z7w6"
    shutdown_requests["x9y8z7w6"] = {"target": "writer", "status": "pending"}
    
    BUS.send("lead", "writer", "Please