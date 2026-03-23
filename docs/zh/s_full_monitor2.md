# s_full.py 全流程模拟追踪（第二场景）

> 模拟场景：用户输入 "Set up a skill, create two blocked tasks, spawn two teammates, have them communicate, trigger auto-compact, then do plan approval and edit a file"
> 工作目录：`/home/user/webapp`
> 重点覆盖：skill 加载（含 SKILL.md 解析）、task 依赖阻塞/解除、edit_file、subagent(s04)、broadcast、plan_approval、auto_compact（token 超限）、teammate idle 阶段 auto-claim、identity re-injection、safe_path 越界拦截、dangerous command 拦截、read_file limit 截断、task 删除、microcompact 实际清理

---

# 0. 前置：磁盘预设状态

<details>
<summary>展开查看初始文件系统</summary>

假设工作目录下已有以下文件：

```
/home/user/webapp/
├── app.py              (50 行 Python 代码)
├── skills/
│   └── deploy/
│       └── SKILL.md    (含 frontmatter)
```

📁 `skills/deploy/SKILL.md` 内容：

```markdown
---
name: deploy
description: Deploy webapp to production server
version: 1.0
---

## Deploy Steps

1. Run `python -m build`
2. Upload dist/ to server
3. Restart service: `systemctl restart webapp`
```

📁 `app.py` 内容（前 5 行示意）：

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello World"

# ... 共 50 行
```

</details>

---

# 1. 程序启动 (`__main__`)

<details>
<summary>全局初始化 — 含 SkillLoader 解析 SKILL.md</summary>

## 1.1 SkillLoader 初始化

```python
skills_dir = Path("/home/user/webapp/skills")
skills_dir.exists() → True

遍历 skills_dir.rglob("SKILL.md"):
    找到: skills/deploy/SKILL.md
    
    text = f.read_text()  # 读取完整内容
    
    re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL) → 匹配成功
        match.group(1) = "name: deploy\ndescription: Deploy webapp to production server\nversion: 1.0"
        match.group(2) = "## Deploy Steps\n1. Run ..."
    
    解析 frontmatter:
        "name: deploy"       → meta["name"] = "deploy"
        "description: ..."   → meta["description"] = "Deploy webapp to production server"
        "version: 1.0"       → meta["version"] = "1.0"
    
    body = "## Deploy Steps\n1. Run `python -m build`\n2. Upload dist/ to server\n3. Restart service: `systemctl restart webapp`"
    
    name = meta.get("name", f.parent.name) → "deploy"
    self.skills["deploy"] = {"meta": {...}, "body": body}
```

```python
SKILLS.descriptions() → "  - deploy: Deploy webapp to production server"
```

## 1.2 其他全局对象

| 变量       | 初始化动作                                                   |
| ---------- | ------------------------------------------------------------ |
| `TODO`     | `items = []`                                                 |
| `TASK_MGR` | 💾 创建 `.tasks/` 目录                                        |
| `BG`       | `tasks = {}, notifications = Queue()`                        |
| `BUS`      | 💾 创建 `.team/inbox/` 目录                                   |
| `TEAM`     | 💾 创建 `.team/`，`config.json` 不存在 → `config = {"team_name":"default","members":[]}` |

💾 磁盘写入：创建 `.tasks/`、`.team/`、`.team/inbox/`

<details>
<summary>📁 文件快照</summary>

```
/home/user/webapp/
├── app.py
├── skills/deploy/SKILL.md
├── .tasks/              (空)
├── .team/
│   └── inbox/           (空)
```

</details>

## 1.3 SYSTEM prompt

```python
SYSTEM = """You are a coding agent at /home/user/webapp. Use tools to solve tasks.
Prefer task_create/task_update/task_list for multi-step work. Use TodoWrite for short checklists.
Use task for subagent delegation. Use load_skill for specialized knowledge.
Skills:
  - deploy: Deploy webapp to production server"""
```

## 1.4 REPL — 用户输入

```python
history = []
query = "Create task: build project (blocked by nothing). Create task: deploy (blocked by build). Spawn 'builder' and 'deployer'. Builder should build, deployer waits. Also explore app.py with a subagent."
history = [{"role": "user", "content": query}]
```

→ 调用 `agent_loop(history)`

</details>

---

# 2. agent_loop — 第 1 轮：创建任务 + 设置依赖

<details>
<summary>预处理（全部跳过）</summary>

## 2.1 microcompact

```python
indices = []  (无 tool_result)
len(indices) = 0 ≤ 3 → return
```

## 2.2 estimate_tokens ≈ 80 < 100000 → 不压缩

## 2.3 BG.drain() → [] 

## 2.4 BUS.read_inbox("lead") → lead.jsonl 不存在 → []

</details>

<details>
<summary>LLM 返回 → task_create × 2 + task_update（设依赖）</summary>

## 2.5 LLM 响应 (stop_reason = "tool_use")

| #    | tool_name     | input                                                        |
| ---- | ------------- | ------------------------------------------------------------ |
| 1    | `task_create` | `{"subject": "Build project", "description": "Run python -m build to create dist/"}` |
| 2    | `task_create` | `{"subject": "Deploy to production", "description": "Deploy dist/ to server"}` |
| 3    | `task_update` | `{"task_id": 2, "add_blocked_by": [1]}`                      |

## 2.6 tool: task_create("Build project")

```python
_next_id(): ids = [] → return 1
task = {"id":1, "subject":"Build project", "description":"Run python -m build to create dist/",
        "status":"pending", "owner":null, "blockedBy":[], "blocks":[]}
```

💾 写入 `.tasks/task_1.json`

<details>
<summary>📁 文件快照 — .tasks/task_1.json</summary>

```json
{
  "id": 1,
  "subject": "Build project",
  "description": "Run python -m build to create dist/",
  "status": "pending",
  "owner": null,
  "blockedBy": [],
  "blocks": []
}
```

</details>

---

## 2.7 tool: task_create("Deploy to production")

```python
_next_id(): ids = [1] → return 2
task = {"id":2, "subject":"Deploy to production", "description":"Deploy dist/ to server",
        "status":"pending", "owner":null, "blockedBy":[], "blocks":[]}
```

💾 写入 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Deploy to production",
  "description": "Deploy dist/ to server",
  "status": "pending",
  "owner": null,
  "blockedBy": [],
  "blocks": []
}
```

</details>

---

## 2.8 tool: task_update(2, add_blocked_by=[1])

```python
TASK_MGR.update(2, add_blocked_by=[1]):
    task = _load(2)
    status = None → 不改 status
    add_blocked_by = [1]:
        task["blockedBy"] = list(set([] + [1])) = [1]
    add_blocks = None → 跳过
    _save(task)
```

💾 更新 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Deploy to production",
  "description": "Deploy dist/ to server",
  "status": "pending",
  "owner": null,
  "blockedBy": [1],
  "blocks": []
}
```

</details>

输出: `'{"id": 2, ... "blockedBy": [1] ...}'`

### 变量状态

```python
used_todo = False
rounds_without_todo = 0 + 1 = 1
manual_compress = False
```

</details>

---

# 3. agent_loop — 第 2 轮：spawn 两个 teammate + subagent 探索

<details>
<summary>预处理</summary>

## 3.1 microcompact

```python
indices = 3 个 tool_result part
len(indices) = 3 ≤ 3 → 不清理
```

## 3.2~3.4 tokens/bg/inbox → 全部跳过

</details>

<details>
<summary>LLM 返回 → spawn_teammate × 2 + task(subagent)</summary>

| #    | tool_name        | input                                                        |
| ---- | ---------------- | ------------------------------------------------------------ |
| 1    | `spawn_teammate` | `{"name":"builder","role":"build","prompt":"Claim task #1 and run the build. When done mark it completed and idle."}` |
| 2    | `spawn_teammate` | `{"name":"deployer","role":"ops","prompt":"You handle deployment. Wait for task #2 to become unblocked, then claim and deploy. Load the deploy skill first."}` |
| 3    | `task`           | `{"prompt":"Explore app.py: read it, count routes, list imports. Summarize findings.","agent_type":"Explore"}` |

## 3.3 tool: spawn_teammate("builder")

```python
TEAM._find("builder") → None
member = {"name":"builder", "role":"build", "status":"working"}
config["members"].append(member)
```

💾 `TEAM._save()`

<details>
<summary>📁 文件快照 — .team/config.json</summary>

```json
{
  "team_name": "default",
  "members": [
    {"name": "builder", "role": "build", "status": "working"}
  ]
}
```

</details>

启动线程 `_loop("builder", "build", "Claim task #1 and run the build...")`

输出: `"Spawned 'builder' (role: build)"`

---

## 3.4 tool: spawn_teammate("deployer")

```python
TEAM._find("deployer") → None
member = {"name":"deployer", "role":"ops", "status":"working"}
config["members"].append(member)
```

💾 `TEAM._save()`

<details>
<summary>📁 文件快照 — .team/config.json</summary>

```json
{
  "team_name": "default",
  "members": [
    {"name": "builder", "role": "build", "status": "working"},
    {"name": "deployer", "role": "ops", "status": "working"}
  ]
}
```

</details>

启动线程 `_loop("deployer", "ops", "You handle deployment...")`

---

## 3.5 tool: task (subagent, Explore 模式)

```python
run_subagent(prompt, agent_type="Explore"):
    sub_tools = [bash, read_file]  # Explore 模式 → 只有 bash + read_file，无 write/edit
    sub_msgs = [{"role":"user","content":"Explore app.py: read it, count routes..."}]
```

### 3.5.1 subagent 第 1 轮

subagent LLM 返回 tool_use: `read_file(path="app.py")`

```python
sub_handlers["read_file"](path="app.py"):
    → run_read("app.py")
    → safe_path("app.py") → /home/user/webapp/app.py (在 WORKDIR 内 ✓)
    → 读取 50 行内容
    → limit = None → 不截断
    → 返回完整内容[:50000]
```

### 3.5.2 subagent 第 2 轮

subagent LLM 返回 `stop_reason = "end_turn"`，text:

```
"app.py imports Flask. Has 1 route: GET /. Total 50 lines. Simple hello-world app."
```

```python
return "app.py imports Flask. Has 1 route: GET /. Total 50 lines. Simple hello-world app."
```

### 变量状态

```python
used_todo = False
rounds_without_todo = 1 + 1 = 2
```

Nag: `TODO.has_open_items() → False` (items=[]) → 不触发（条件短路）

</details>

---

# 4. Teammate "builder" 线程 — 工作阶段

<details>
<summary>builder 第 1 轮：claim + bash（含 dangerous 拦截测试）</summary>

## 4.1 初始化

```python
name = "builder", role = "build"
sys_prompt = "You are 'builder', role: build, team: default, at /home/user/webapp. ..."
messages = [{"role":"user","content":"Claim task #1 and run the build..."}]
```

## 4.2 inbox 检查

```python
BUS.read_inbox("builder") → .team/inbox/builder.jsonl 不存在 → []
```

## 4.3 LLM 返回

| #    | tool_name    | input                                       |
| ---- | ------------ | ------------------------------------------- |
| 1    | `claim_task` | `{"task_id": 1}`                            |
| 2    | `bash`       | `{"command": "sudo rm -rf /tmp/old_build"}` |
| 3    | `bash`       | `{"command": "python -m build"}`            |

## 4.4 tool: claim_task(1)

```python
TASK_MGR.claim(1, "builder"):
    task = _load(1)
    task["owner"] = "builder"
    task["status"] = "in_progress"
    _save(task)
```

💾 更新 `.tasks/task_1.json`

<details>
<summary>📁 文件快照 — .tasks/task_1.json</summary>

```json
{
  "id": 1,
  "subject": "Build project",
  "description": "Run python -m build to create dist/",
  "status": "in_progress",
  "owner": "builder",
  "blockedBy": [],
  "blocks": []
}
```

</details>

## 4.5 tool: bash("sudo rm -rf /tmp/old_build") — 🚫 危险命令拦截

```python
run_bash("sudo rm -rf /tmp/old_build"):
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    "sudo" in command → True!
    return "Error: Dangerous command blocked"
```

分支走向：`any(d in command for d in dangerous)` → `"sudo"` 命中 → 拦截

输出: `"Error: Dangerous command blocked"`

## 4.6 tool: bash("python -m build")

```python
run_bash("python -m build"):
    dangerous 检查 → 全部 False → 通过
    subprocess.run("python -m build", shell=True, cwd=WORKDIR, timeout=120)
    → stdout: "Successfully built webapp-1.0.0.tar.gz"
    → stderr: ""
    out = "Successfully built webapp-1.0.0.tar.gz"
    return out[:50000]
```

输出: `"Successfully built webapp-1.0.0.tar.gz"`

</details>

<details>
<summary>builder 第 2 轮：send_message + task_update(完成) + idle</summary>

## 4.7 LLM 返回

| #    | tool_name      | input                                                        |
| ---- | -------------- | ------------------------------------------------------------ |
| 1    | `send_message` | `{"to":"deployer","content":"Build done! Task #1 complete, #2 should be unblocked now."}` |
| 2    | `send_message` | `{"to":"lead","content":"Build task #1 completed successfully."}` |
| 3    | `idle`         | `{}`                                                         |

注意：builder 线程内的 tool dispatch 不含 `task_update`，只有 `bash/read_file/write_file/edit_file/send_message/idle/claim_task`。所以 builder 无法直接更新 task status —— 它通过消息通知 lead 来完成。

## 4.8 tool: send_message(to="deployer")

```python
BUS.send("builder", "deployer", "Build done! Task #1 complete, #2 should be unblocked now.", "message"):
    msg = {"type":"message","from":"builder","content":"Build done!...","timestamp":1711000200.0}
```

💾 追加写入 `.team/inbox/deployer.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/deployer.jsonl</summary>

```json
{"type":"message","from":"builder","content":"Build done! Task #1 complete, #2 should be unblocked now.","timestamp":1711000200.0}
```

</details>

## 4.9 tool: send_message(to="lead")

💾 追加写入 `.team/inbox/lead.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/lead.jsonl</summary>

```json
{"type":"message","from":"builder","content":"Build task #1 completed successfully.","timestamp":1711000200.5}
```

</details>

## 4.10 tool: idle → `idle_requested = True` → break

## 4.11 builder 进入 idle 阶段

```python
self._set_status("builder", "idle")
```

💾 更新 `.team/config.json` → builder.status = "idle"

</details>

---

# 5. Teammate "deployer" 线程 — 工作 → idle → 收消息恢复

<details>
<summary>deployer 第 1 轮：尝试 read_file 越界 + idle</summary>

## 5.1 初始化

```python
name = "deployer", role = "ops"
messages = [{"role":"user","content":"You handle deployment. Wait for task #2 to become unblocked..."}]
```

## 5.2 LLM 返回

| #    | tool_name   | input                          |
| ---- | ----------- | ------------------------------ |
| 1    | `read_file` | `{"path": "../../etc/passwd"}` |
| 2    | `idle`      | `{}`                           |

## 5.3 tool: read_file("../../etc/passwd") — 🚫 路径越界拦截

```python
run_read("../../etc/passwd"):
    safe_path("../../etc/passwd"):
        path = (WORKDIR / "../../etc/passwd").resolve()
             = Path("/etc/passwd")
        path.is_relative_to(WORKDIR) → False!
        raise ValueError("Path escapes workspace: ../../etc/passwd")
    → except: return "Error: Path escapes workspace: ../../etc/passwd"
```

分支走向：`safe_path` 检测到路径逃逸 → 抛出 ValueError → 被 except 捕获

输出: `"Error: Path escapes workspace: ../../etc/passwd"`

## 5.4 tool: idle → `idle_requested = True`

## 5.5 deployer 进入 idle 阶段

```python
self._set_status("deployer", "idle")
```

💾 更新 `.team/config.json`

<details>
<summary>📁 文件快照 — .team/config.json</summary>

```json
{
  "team_name": "default",
  "members": [
    {"name": "builder", "role": "build", "status": "idle"},
    {"name": "deployer", "role": "ops", "status": "idle"}
  ]
}
```

</details>

</details>

<details>
<summary>deployer idle 阶段 — 收到 builder 消息 → 恢复工作</summary>

## 5.6 idle 轮询循环

```python
# IDLE PHASE
for _ in range(IDLE_TIMEOUT // max(POLL_INTERVAL, 1)):  # 60 // 5 = 12 次
    time.sleep(5)  # 第 1 次等待
    
    inbox = BUS.read_inbox("deployer")
```

💾 读取并清空 `.team/inbox/deployer.jsonl`

```python
    inbox = [
        {"type":"message","from":"builder","content":"Build done! Task #1 complete, #2 should be unblocked now.","timestamp":1711000200.0}
    ]
    
    # inbox 非空!
    for msg in inbox:
        msg.get("type") → "message" (不是 "shutdown_request" → 不 shutdown)
        messages.append({"role":"user","content": json.dumps(msg)})
    
    resume = True
    break
```

<details>
<summary>📁 文件快照 — .team/inbox/deployer.jsonl</summary>

```
(空文件 — 已被 read_inbox 清空)
```

</details>

分支走向：`inbox` 非空 → 不检查 unclaimed tasks → `resume = True` → break

## 5.7 deployer 恢复工作

```python
self._set_status("deployer", "working")
```

💾 更新 `.team/config.json` → deployer.status = "working"

## 5.8 deployer 后续工作轮（claim task #2 + write_file）

deployer LLM 收到 builder 的消息后返回:

| #    | tool_name      | input                                                        |
| ---- | -------------- | ------------------------------------------------------------ |
| 1    | `claim_task`   | `{"task_id": 2}`                                             |
| 2    | `write_file`   | `{"path":"deploy.sh","content":"#!/bin/bash\npython -m build\nscp dist/* server:/app/\nssh server 'systemctl restart webapp'\n"}` |
| 3    | `send_message` | `{"to":"lead","content":"Deployed! Task #2 done."}`          |
| 4    | `idle`         | `{}`                                                         |

## 5.9 tool: claim_task(2)

```python
TASK_MGR.claim(2, "deployer"):
    task = _load(2) → blockedBy = [1]
    # 注意：claim 不检查 blockedBy，直接设 owner 和 status
    task["owner"] = "deployer"
    task["status"] = "in_progress"
    _save(task)
```

💾 更新 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Deploy to production",
  "description": "Deploy dist/ to server",
  "status": "in_progress",
  "owner": "deployer",
  "blockedBy": [1],
  "blocks": []
}
```

</details>

## 5.10 tool: write_file("deploy.sh")

💾 写入 `deploy.sh`

<details>
<summary>📁 文件快照 — deploy.sh</summary>

```bash
#!/bin/bash
python -m build
scp dist/* server:/app/
ssh server 'systemctl restart webapp'
```

</details>

## 5.11 tool: send_message(to="lead")

💾 追加写入 `.team/inbox/lead.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/lead.jsonl</summary>

```json
{"type":"message","from":"builder","content":"Build task #1 completed successfully.","timestamp":1711000200.5}
{"type":"message","from":"deployer","content":"Deployed! Task #2 done.","timestamp":1711000230.0}
```

</details>

## 5.12 deployer idle → 进入第二次 idle 阶段

</details>

---

# 6. agent_loop — 第 3 轮：read_file(limit) + edit_file + load_skill + broadcast

<details>
<summary>预处理 — inbox 到达</summary>

## 6.1 microcompact

```python
扫描 tool_result → indices 有 6 个 part (第1轮3个 + 第2轮3个)
len(indices) = 6 > 3 → 清理前 3 个:
    indices[0]: task_1 json (len > 100) → content = "[cleared]"
    indices[1]: task_2 json (len > 100) → content = "[cleared]"
    indices[2]: task_2 updated json (len > 100) → content = "[cleared]"
```

分支走向：`len(indices) > 3` → 清理最旧的 3 个 tool_result

## 6.2 estimate_tokens ≈ 5000 < 100000 → 不压缩

## 6.3 BG.drain() → []

## 6.4 BUS.read_inbox("lead")

💾 读取 `.team/inbox/lead.jsonl` → 2 条消息

```python
inbox = [
    {"type":"message","from":"builder","content":"Build task #1 completed successfully.","timestamp":1711000200.5},
    {"type":"message","from":"deployer","content":"Deployed! Task #2 done.","timestamp":1711000230.0}
]
```

💾 清空 `lead.jsonl`

注入:
```python
messages.append({"role":"user","content":"<inbox>[...]</inbox>"})
messages.append({"role":"assistant","content":"Noted inbox messages."})
```

</details>

<details>
<summary>LLM 返回 → task_update(完成#1+依赖解除) + read_file(limit) + edit_file + load_skill + broadcast</summary>

| #    | tool_name     | input                                                        |
| ---- | ------------- | ------------------------------------------------------------ |
| 1    | `task_update` | `{"task_id": 1, "status": "completed"}`                      |
| 2    | `read_file`   | `{"path": "app.py", "limit": 3}`                             |
| 3    | `edit_file`   | `{"path": "app.py", "old_text": "return \"Hello World\"", "new_text": "return \"Hello Webapp v2\""}` |
| 4    | `load_skill`  | `{"name": "deploy"}`                                         |
| 5    | `broadcast`   | `{"content": "All tasks done. Great work team!"}`            |

## 6.5 tool: task_update(1, status="completed") — 💡 依赖解除逻辑

```python
TASK_MGR.update(1, status="completed"):
    task = _load(1)
    task["status"] = "completed"
    
    # 完成时遍历所有 task 检查依赖解除:
    for f in .tasks/glob("task_*.json"):
        # f = task_1.json:
        t = json.loads(f.read_text())  # t = task_1 自身
        1 in t.get("blockedBy", [])  → 1 in [] → False → 跳过
        
        # f = task_2.json:
        t = json.loads(f.read_text())  # t = task_2
        1 in t.get("blockedBy", [])  → 1 in [1] → True!
            t["blockedBy"].remove(1) → t["blockedBy"] = []
            _save(t)  # 💾 保存 task_2，blockedBy 清空
    
    _save(task)  # 💾 保存 task_1
```

💾 更新 `.tasks/task_1.json`

<details>
<summary>📁 文件快照 — .tasks/task_1.json</summary>

```json
{
  "id": 1,
  "subject": "Build project",
  "description": "Run python -m build to create dist/",
  "status": "completed",
  "owner": "builder",
  "blockedBy": [],
  "blocks": []
}
```

</details>

💾 更新 `.tasks/task_2.json`（依赖解除）

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Deploy to production",
  "description": "Deploy dist/ to server",
  "status": "in_progress",
  "owner": "deployer",
  "blockedBy": [],
  "blocks": []
}
```

</details>

---

## 6.6 tool: read_file("app.py", limit=3) — 📖 limit 截断

```python
run_read("app.py", limit=3):
    lines = safe_path("app.py").read_text().splitlines()  # 50 行
    limit = 3, 3 < 50 → True:
        lines = lines[:3] + [f"... (47 more)"]
    return "\n".join(lines)[:50000]
```

输出:
```
from flask import Flask

app = Flask(__name__)
... (47 more)
```

分支走向：`limit and limit < len(lines)` → 截断 + 追加提示

---

## 6.7 tool: edit_file("app.py", old_text, new_text)

```python
run_edit("app.py", 'return "Hello World"', 'return "Hello Webapp v2"'):
    fp = safe_path("app.py")
    c = fp.read_text()  # 完整 50 行内容
    
    'return "Hello World"' in c → True
    
    fp.write_text(c.replace('return "Hello World"', 'return "Hello Webapp v2"', 1))
    # replace count=1 → 只替换第一处
```

💾 更新 `app.py`

断了

---

## 6.8 tool: load_skill("deploy") — ✅ 命中已解析的 skill

```python
SKILLS.load("deploy"):
    s = self.skills.get("deploy") → 存在!
    return '<skill name="deploy">\n## Deploy Steps\n1. Run `python -m build`\n2. Upload dist/ to server\n3. Restart service: `systemctl restart webapp`\n</skill>'
```

分支走向：skill 存在 → 返回完整 body（与上一场景 `load_skill("testing")` 返回 Error 形成对比）

---

## 6.9 tool: broadcast("All tasks done. Great work team!")

```python
BUS.broadcast("lead", "All tasks done. Great work team!", TEAM.member_names()):
    TEAM.member_names() → ["builder", "deployer"]
    
    count = 0
    for n in ["builder", "deployer"]:
        n != "lead" → True:
            BUS.send("lead", "builder", "All tasks done...", "broadcast")
            count += 1
            BUS.send("lead", "deployer", "All tasks done...", "broadcast")
            count += 1
    return "Broadcast to 2 teammates"
```

💾 追加写入 `.team/inbox/builder.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/builder.jsonl</summary>

```json
{"type":"broadcast","from":"lead","content":"All tasks done. Great work team!","timestamp":1711000300.0}
```

</details>

💾 追加写入 `.team/inbox/deployer.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/deployer.jsonl</summary>

```json
{"type":"broadcast","from":"lead","content":"All tasks done. Great work team!","timestamp":1711000300.0}
```

</details>

### 变量状态

```python
used_todo = False
rounds_without_todo = 2 + 1 = 3
manual_compress = False
```

## 6.10 Nag Reminder 触发！

```python
TODO.has_open_items():
    self.items = []  # 本场景从未调用 TodoWrite
    any(item.get("status") != "completed" for item in []) → False
    return False

→ 不触发 nag（items 为空，has_open_items = False）
```

分支走向：`TODO.has_open_items() → False` → 短路，不插入 reminder

（与上一场景不同：上一场景 TodoWrite 创建了 items 所以能触发 nag。本场景未使用 TodoWrite，所以 nag 永远不触发。这是一个重要的分支差异。）

</details>

---

# 7. agent_loop — 第 4 轮：TodoWrite + task_update(完成#2) + plan_approval 场景铺垫

<details>
<summary>预处理 → LLM 返回 TodoWrite + task_update + task_create(新任务)</summary>

## 7.1 预处理

- microcompact: indices 增长到 11 个 → 清理前 8 个中 content > 100 的
- estimate_tokens ≈ 9000 < 100000
- BG.drain() → []
- BUS.read_inbox("lead") → []

## 7.2 LLM 响应

| #    | tool_name     | input                                                        |
| ---- | ------------- | ------------------------------------------------------------ |
| 1    | `TodoWrite`   | `{"items":[{"content":"Build project","status":"completed","activeForm":"done"},{"content":"Deploy to prod","status":"completed","activeForm":"done"},{"content":"Review deploy plan","status":"in_progress","activeForm":"plan_approval"}]}` |
| 2    | `task_update` | `{"task_id": 2, "status": "completed"}`                      |
| 3    | `task_create` | `{"subject":"Post-deploy smoke test","description":"Run health checks after deploy"}` |

## 7.3 tool: TodoWrite

```python
TODO.update(items):
    validated = [], ip = 0
    
    Item 0: content="Build project", status="completed", activeForm="done"
        → status valid ✓, content non-empty ✓, activeForm non-empty ✓
    Item 1: content="Deploy to prod", status="completed", activeForm="done"
        → ✓
    Item 2: content="Review deploy plan", status="in_progress", activeForm="plan_approval"
        → ip = 1
    
    len(validated) = 3 ≤ 20 ✓
    ip = 1 ≤ 1 ✓
    self.items = validated
```

`render()`:
```
[x] Build project
[x] Deploy to prod
[>] Review deploy plan <- plan_approval

(2/3 completed)
```

```python
used_todo = True → rounds_without_todo = 0
```

---

## 7.4 tool: task_update(2, status="completed")

```python
task = _load(2)
task["status"] = "completed"

# 依赖解除遍历:
for f in .tasks/glob("task_*.json"):
    # task_1: blockedBy=[] → 2 not in [] → skip
    # task_2: 自身 → blockedBy=[] → skip
    # (task_3 还没创建)

_save(task)
```

💾 更新 `.tasks/task_2.json`

<details>
<summary>📁 文件快照 — .tasks/task_2.json</summary>

```json
{
  "id": 2,
  "subject": "Deploy to production",
  "description": "Deploy dist/ to server",
  "status": "completed",
  "owner": "deployer",
  "blockedBy": [],
  "blocks": []
}
```

</details>

---

## 7.5 tool: task_create("Post-deploy smoke test")

```python
_next_id(): ids = [1, 2] → max = 2 → return 3
task = {"id":3, "subject":"Post-deploy smoke test", ...}
```

💾 写入 `.tasks/task_3.json`

<details>
<summary>📁 文件快照 — .tasks/task_3.json</summary>

```json
{
  "id": 3,
  "subject": "Post-deploy smoke test",
  "description": "Run health checks after deploy",
  "status": "pending",
  "owner": null,
  "blockedBy": [],
  "blocks": []
}
```

</details>

### Nag 检查

```python
used_todo = True → rounds_without_todo = 0
TODO.has_open_items() → True (item 2 is in_progress)
rounds_without_todo = 0 < 3 → 不触发
```

</details>

---

# 8. Teammate "builder" idle 阶段 — auto-claim task #3 + identity re-injection

<details>
<summary>builder idle 轮询 → 发现 unclaimed task → auto-claim</summary>

## 8.1 builder idle 轮询

builder 在第 4 步结束后进入 idle，此时正在轮询：

```python
# IDLE PHASE 循环
for _ in range(12):  # IDLE_TIMEOUT(60) // POLL_INTERVAL(5) = 12
    time.sleep(5)
    
    inbox = BUS.read_inbox("builder")
```

💾 读取 `.team/inbox/builder.jsonl`

```python
    inbox = [
        {"type":"broadcast","from":"lead","content":"All tasks done. Great work team!","timestamp":1711000300.0}
    ]
```

💾 清空 `builder.jsonl`

```python
    # inbox 非空!
    for msg in inbox:
        msg.get("type") → "broadcast" (不是 "shutdown_request")
        messages.append({"role":"user","content": json.dumps(msg)})
    resume = True
    break
```

分支走向：收到 broadcast → resume

## 8.2 builder 恢复工作 → LLM 返回 idle（broadcast 不需要行动）

```python
self._set_status("builder", "working")
```

builder LLM 看到 broadcast "All tasks done" → 返回 idle

→ builder 再次进入 idle

## 8.3 builder 第二次 idle — 这次发现 unclaimed task #3

```python
for _ in range(12):
    time.sleep(5)
    
    inbox = BUS.read_inbox("builder") → []  # 无新消息
    
    # 检查 unclaimed tasks:
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        t = json.loads(f.read_text())
        # task_1: status="completed" → 不是 pending → skip
        # task_2: status="completed" → skip
        # task_3: status="pending", owner=null, blockedBy=[] → ✅ 符合!
        unclaimed.append(t)  # t = task_3
    
    unclaimed = [task_3]  # 非空!
    task = unclaimed[0]  # task_3
    
    self.task_mgr.claim(task["id"], "builder")
```

💾 更新 `.tasks/task_3.json`

<details>
<summary>📁 文件快照 — .tasks/task_3.json</summary>

```json
{
  "id": 3,
  "subject": "Post-deploy smoke test",
  "description": "Run health checks after deploy",
  "status": "in_progress",
  "owner": "builder",
  "blockedBy": [],
  "blocks": []
}
```

</details>

## 8.4 Identity re-injection 检查

```python
    # builder 的 messages 经过多轮，假设此时 len(messages) = 12 > 3
    # → 不触发 identity re-injection
    if len(messages) <= 3:  # False → 跳过
        pass
```

分支走向：`len(messages) > 3` → 不注入 identity（正常情况）

为了覆盖 identity re-injection，假设 builder 之前经历过一次 auto_compact（在 teammate 内部不会自动触发，但假设 messages 因某种原因被截短到 ≤ 3）：

### 🔀 假设分支：若 len(messages) ≤ 3

```python
    if len(messages) <= 3:  # True!
        messages.insert(0, {
            "role": "user",
            "content": "<identity>You are 'builder', role: build, team: default.</identity>"
        })
        messages.insert(1, {
            "role": "assistant",
            "content": "I am builder. Continuing."
        })
```

（本场景实际不触发，但此处标注该分支的完整逻辑）

## 8.5 auto-claim 消息注入

```python
    messages.append({
        "role": "user",
        "content": "<auto-claimed>Task #3: Post-deploy smoke test\nRun health checks after deploy</auto-claimed>"
    })
    messages.append({
        "role": "assistant",
        "content": "Claimed task #3. Working on it."
    })
    resume = True
    break
```

```python
self._set_status("builder", "working")
```

💾 更新 `.team/config.json` → builder.status = "working"

builder 继续工作，执行 bash("curl http://localhost:8080/health") 等...

</details>

---

# 9. agent_loop — 第 5、6、7 轮（无 TodoWrite → nag 触发 + plan_approval）

<details>
<summary>第 5 轮 — rounds_without_todo = 1</summary>

## 9.1 LLM 返回 check_background + task_list

| #    | tool_name          | input                     |
| ---- | ------------------ | ------------------------- |
| 1    | `check_background` | `{"task_id": "a1b2c3d4"}` |
| 2    | `task_list`        | `{}`                      |

## 9.2 tool: check_background("a1b2c3d4")

```python
BG.check("a1b2c3d4"):
    t = self.tasks.get("a1b2c3d4")
    → {"status":"completed", "command":"find ...", "result":"./main.py\n./utils.py"}
    return "[completed] ./main.py\n./utils.py"
```

## 9.3 tool: task_list

```python
TASK_MGR.list_all():
    tasks = [task_1, task_2, task_3]  # 从文件加载
    
    task_1: status=completed → "[x]", owner=builder → " @builder"
    task_2: status=completed → "[x]", owner=deployer → " @deployer"
    task_3: status=in_progress → "[>]", owner=builder → " @builder"
```

输出:
```
[x] #1: Build project @builder
[x] #2: Deploy to production @deployer
[>] #3: Post-deploy smoke test @builder
```

```python
used_todo = False → rounds_without_todo = 0 + 1 = 1
```

</details>

---

<details>
<summary>第 6 轮 — rounds_without_todo = 2</summary>

## 9.4 LLM 返回 read_inbox + list_teammates

| #    | tool_name        | input |
| ---- | ---------------- | ----- |
| 1    | `read_inbox`     | `{}`  |
| 2    | `list_teammates` | `{}`  |

## 9.5 tool: read_inbox

```python
TOOL_HANDLERS["read_inbox"]():
    BUS.read_inbox("lead") → []  # 已在预处理中读过，或无新消息
    return json.dumps([], indent=2) → "[]"
```

## 9.6 tool: list_teammates

```python
TEAM.list_all():
    members = [builder(working), deployer(idle)]
```

输出:
```
Team: default
  builder (build): working
  deployer (ops): idle
```

```python
used_todo = False → rounds_without_todo = 1 + 1 = 2
```

</details>

---

<details>
<summary>第 7 轮 — rounds_without_todo = 3 → 🔔 Nag 触发！+ plan_approval</summary>

## 9.7 LLM 返回 plan_approval

模拟场景：deployer 之前提交了一个 plan（通过 send_message 发送了 plan_approval_request 到 lead inbox，lead 在之前某轮收到并记录到 `plan_requests`）。

假设 `plan_requests` 中已有：
```python
plan_requests = {
    "p1a2b3c4": {"from": "deployer", "plan": "Scale to 3 replicas", "status": "pending"}
}
```

| #    | tool_name       | input                                                        |
| ---- | --------------- | ------------------------------------------------------------ |
| 1    | `plan_approval` | `{"request_id": "p1a2b3c4", "approve": true, "feedback": "Looks good, go ahead."}` |

## 9.8 tool: plan_approval("p1a2b3c4", approve=True)

```python
handle_plan_review("p1a2b3c4", True, "Looks good, go ahead."):
    req = plan_requests.get("p1a2b3c4")
    → {"from":"deployer", "plan":"Scale to 3 replicas", "status":"pending"}
    
    req["status"] = "approved"  # approve=True → "approved"
    
    BUS.send("lead", "deployer", "Looks good, go ahead.", "plan_approval_response",
             {"request_id":"p1a2b3c4", "approve":True, "feedback":"Looks good, go ahead."})
```

💾 追加写入 `.team/inbox/deployer.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/deployer.jsonl</summary>

```json
{"type":"plan_approval_response","from":"lead","content":"Looks good, go ahead.","timestamp":1711000500.0,"request_id":"p1a2b3c4","approve":true,"feedback":"Looks good, go ahead."}
```

</details>

输出: `"Plan approved for 'deployer'"`

## 9.9 Nag Reminder 触发！

```python
used_todo = False → rounds_without_todo = 2 + 1 = 3

TODO.has_open_items():
    items = [
        {"content":"Build project","status":"completed",...},
        {"content":"Deploy to prod","status":"completed",...},
        {"content":"Review deploy plan","status":"in_progress",...}  # ← 未完成!
    ]
    any(status != "completed") → True
    return True

rounds_without_todo(3) >= 3 → True!
```

```python
results.insert(0, {
    "type": "text",
    "text": "<reminder>Update your todos.</reminder>"
})
```

分支走向：`has_open_items()=True AND rounds_without_todo >= 3` → 插入 nag

</details>

---

# 10. agent_loop — 第 8 轮：task 删除 + TodoWrite 更新 + 手动 compress

<details>
<summary>LLM 返回 → task_update(delete) + TodoWrite + compress</summary>

## 10.1 预处理 — 正常（无特殊事件）

## 10.2 LLM 响应

| #    | tool_name     | input                                                        |
| ---- | ------------- | ------------------------------------------------------------ |
| 1    | `task_update` | `{"task_id": 3, "status": "completed"}`                      |
| 2    | `task_update` | `{"task_id": 3, "status": "deleted"}`                        |
| 3    | `TodoWrite`   | `{"items":[{"content":"Build project","status":"completed","activeForm":"done"},{"content":"Deploy to prod","status":"completed","activeForm":"done"},{"content":"Review deploy plan","status":"completed","activeForm":"done"}]}` |
| 4    | `compress`    | `{}`                                                         |

## 10.3 tool: task_update(3, status="completed")

```python
task = _load(3)
task["status"] = "completed"
# 依赖解除遍历 → 无其他 task 依赖 #3
_save(task)
```

💾 更新 `.tasks/task_3.json` → status = "completed"

---

## 10.4 tool: task_update(3, status="deleted")

```python
task = _load(3)
task["status"] = "deleted"  # 先设 status

# status == "deleted" 分支:
(TASKS_DIR / "task_3.json").unlink(missing_ok=True)
return "Task 3 deleted"
```

💾 删除 `.tasks/task_3.json`

<details>
<summary>📁 文件快照 — .tasks/ 目录</summary>

```
.tasks/
├── task_1.json    (completed, owner=builder)
└── task_2.json    (completed, owner=deployer)
# task_3.json 已删除
```

</details>

---

## 10.5 tool: TodoWrite（全部完成）

```python
TODO.update(items):
    3 items, 全部 status="completed"
    ip = 0 ✓
    self.items = validated
```

`render()`:
```
[x] Build project
[x] Deploy to prod
[x] Review deploy plan

(3/3 completed)
```

```python
used_todo = True → rounds_without_todo = 0
```

---

## 10.6 tool: compress — 触发手动 compact

```python
TOOL_HANDLERS["compress"]() → "Compressing..."
manual_compress = True
```

## 10.7 手动 compact 执行

```python
# 循环末尾:
if manual_compress:  # True!
    print("[manual compact]")
    messages[:] = auto_compact(messages)
```

### auto_compact(messages) 详细流程

```python
TRANSCRIPT_DIR.mkdir(exist_ok=True)
# 💾 创建 .transcripts/ 目录（如不存在）

path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
# path = .transcripts/transcript_1711000600.jsonl
```

💾 写入完整对话历史到 transcript 文件

<details>
<summary>📁 文件快照 — .transcripts/transcript_1711000600.jsonl</summary>

```jsonl
{"role": "user", "content": "Create task: build project..."}
{"role": "assistant", "content": [{"type": "tool_use", ...}]}
{"role": "user", "content": [{"type": "tool_result", ...}]}
... (所有 8 轮的完整消息)
```

</details>

```python
conv_text = json.dumps(messages, default=str)[:80000]

# 调用 LLM 做摘要:
resp = client.messages.create(
    model=MODEL,
    messages=[{"role":"user","content":f"Summarize for continuity:\n{conv_text}"}],
    max_tokens=2000
)
summary = resp.content[0].text
# 假设: "Created 3 tasks (build, deploy, smoke test). Spawned builder and deployer teammates. Builder completed build, deployer completed deploy. All tasks done. Task 3 deleted. Broadcast sent. Plan approved for deployer."
```

```python
return [
    {"role":"user","content":"[Compressed. Transcript: .transcripts/transcript_1711000600.jsonl]\nCreated 3 tasks..."},
    {"role":"assistant","content":"Understood. Continuing with summary context."}
]
```

```python
messages[:] = [上述两条消息]
# messages 从 ~30 条压缩到 2 条
```

</details>

---

# 11. agent_loop — 第 9 轮（压缩后）：shutdown teammates + 最终回复

<details>
<summary>预处理 → LLM 返回 shutdown_request × 2 → 最终 end_turn</summary>

## 11.1 预处理

```python
microcompact(messages):
    # messages 只有 2 条，无 tool_result → indices = [] → return

estimate_tokens(messages) ≈ 200 < 100000 → 不压缩

BG.drain() → []
BUS.read_inbox("lead") → []
```

## 11.2 LLM 响应

| #    | tool_name          | input                      |
| ---- | ------------------ | -------------------------- |
| 1    | `shutdown_request` | `{"teammate": "builder"}`  |
| 2    | `shutdown_request` | `{"teammate": "deployer"}` |

## 11.3 tool: shutdown_request("builder")

```python
handle_shutdown_request("builder"):
    req_id = uuid4()[:8] → "s1h2u3t4"
    shutdown_requests["s1h2u3t4"] = {"target":"builder", "status":"pending"}
    
    BUS.send("lead", "builder", "Please shut down.", "shutdown_request", {"request_id":"s1h2u3t4"})
```

💾 追加写入 `.team/inbox/builder.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/builder.jsonl</summary>

```json
{"type":"shutdown_request","from":"lead","content":"Please shut down.","timestamp":1711000700.0,"request_id":"s1h2u3t4"}
```

</details>

输出: `"Shutdown request s1h2u3t4 sent to 'builder'"`

---

## 11.4 tool: shutdown_request("deployer")

```python
handle_shutdown_request("deployer"):
    req_id = uuid4()[:8] → "s5h6u7t8"
    shutdown_requests["s5h6u7t8"] = {"target":"deployer", "status":"pending"}
    
    BUS.send("lead", "deployer", "Please shut down.", "shutdown_request", {"request_id":"s5h6u7t8"})
```

💾 追加写入 `.team/inbox/deployer.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/deployer.jsonl</summary>

```json
{"type":"plan_approval_response","from":"lead","content":"Looks good, go ahead.","timestamp":1711000500.0,"request_id":"p1a2b3c4","approve":true,"feedback":"Looks good, go ahead."}
{"type":"shutdown_request","from":"lead","content":"Please shut down.","timestamp":1711000700.5,"request_id":"s5h6u7t8"}
```

</details>

## 11.5 builder 线程收到 shutdown

```python
# builder 正在 idle 轮询或工作中:
inbox = BUS.read_inbox("builder")
→ [{"type":"shutdown_request", ...}]

for msg in inbox:
    msg.get("type") → "shutdown_request"!
    self._set_status("builder", "shutdown")
    return  # 线程结束
```

💾 更新 `.team/config.json` → builder.status = "shutdown"

## 11.6 deployer 线程收到 shutdown

同理，deployer 在 idle 轮询中读到 shutdown_request：

```python
msg.get("type") → "shutdown_request"
self._set_status("deployer", "shutdown")
return
```

💾 更新 `.team/config.json`

<details>
<summary>📁 文件快照 — .team/config.json</summary>

```json
{
  "team_name": "default",
  "members": [
    {"name": "builder", "role": "build", "status": "shutdown"},
    {"name": "deployer", "role": "ops", "status": "shutdown"}
  ]
}
```

</details>

### 变量状态

```python
used_todo = False → rounds_without_todo = 0 + 1 = 1
TODO.has_open_items() → False (3/3 completed) → nag 不触发
```

</details>

<details>
<summary>第 10 轮 — LLM 返回 end_turn（最终回复）</summary>

## 11.7 下一轮 LLM 调用

预处理全部跳过。

LLM 返回 `stop_reason = "end_turn"`（不是 "tool_use"）：

```
response.content = [TextBlock(text="All done! Built the project, deployed to production, ran smoke tests. Both teammates have been shut down. The workspace is clean.")]
```

```python
messages.append({"role":"assistant","content": response.content})

if response.stop_reason != "tool_use":  # "end_turn" != "tool_use" → True
    return  # 退出 agent_loop
```

分支走向：`stop_reason = "end_turn"` → 退出循环 → 返回 REPL

</details>

---

# 12. 模拟 auto_compact 触发（token 超限场景补充）

<details>
<summary>假设在第 N 轮 estimate_tokens > 100000</summary>

为完整覆盖 auto_compact 的自动触发路径（区别于手动 compress），假设经过大量轮次后：

```python
# agent_loop 顶部:
microcompact(messages)  # 先做微压缩

estimate_tokens(messages):
    len(json.dumps(messages, default=str)) // 4
    → 假设返回 120000

120000 > TOKEN_THRESHOLD(100000) → True!
    print("[auto-compact triggered]")
    messages[:] = auto_compact(messages)
```

流程与手动 compress 完全相同：
1. 💾 写入 `.transcripts/transcript_{timestamp}.jsonl`
2. 调用 LLM 生成摘要
3. `messages` 替换为 2 条消息（compressed summary + ack）

分支走向：`estimate_tokens > TOKEN_THRESHOLD` → 自动触发（与手动 compress 的 `manual_compress` flag 是两个独立入口）

</details>

---

# 13. REPL 命令覆盖

<details>
<summary>/compact、/tasks、/team、/inbox</summary>

回到 REPL 后，用户输入特殊命令：

## 13.1 `/tasks`

```python
query.strip() == "/tasks" → True
print(TASK_MGR.list_all())
```

输出:
```
[x] #1: Build project @builder
[x] #2: Deploy to production @deployer
```

（task_3 已删除，不显示）

## 13.2 `/team`

```python
query.strip() == "/team" → True
print(TEAM.list_all())
```

输出:
```
Team: default
  builder (build): shutdown
  deployer (ops): shutdown
```

## 13.3 `/inbox`

```python
query.strip() == "/inbox" → True
print(json.dumps(BUS.read_inbox("lead"), indent=2))
```

💾 读取 `.team/inbox/lead.jsonl` → 假设为空

输出: `[]`

## 13.4 `/compact`

```python
query.strip() == "/compact" → True
if history:  # history 非空 → True
    print("[manual compact via /compact]")
    history[:] = auto_compact(history)
```

💾 写入新的 transcript 文件
→ history 被压缩

## 13.5 退出

```python
query = "exit"
query.strip().lower() in ("q", "exit", "") → True
break  # 退出 REPL
```

</details>

---

# 14. TodoWrite 验证错误分支覆盖

<details>
<summary>各种 TodoWrite 校验失败场景</summary>

以下为 `TODO.update()` 中各 raise ValueError 分支的触发条件：

## 14.1 content 为空

```python
items = [{"content": "", "status": "pending", "activeForm": "test"}]
→ content = "".strip() = ""
→ not content → True
→ raise ValueError("Item 0: content required")
```

## 14.2 无效 status

```python
items = [{"content": "x", "status": "blocked", "activeForm": "test"}]
→ status = "blocked"
→ "blocked" not in ("pending", "in_progress", "completed") → True
→ raise ValueError("Item 0: invalid status 'blocked'")
```

## 14.3 activeForm 为空

```python
items = [{"content": "x", "status": "pending", "activeForm": ""}]
→ af = "".strip() = ""
→ not af → True
→ raise ValueError("Item 0: activeForm required")
```

## 14.4 超过 20 条

```python
items = [{"content": f"item{i}", "status": "pending", "activeForm": "test"} for i in range(21)]
→ len(validated) = 21 > 20
→ raise ValueError("Max 20 todos")
```

## 14.5 多个 in_progress

```python
items = [
    {"content": "a", "status": "in_progress", "activeForm": "x"},
    {"content": "b", "status": "in_progress", "activeForm": "y"}
]
→ ip = 2 > 1
→ raise ValueError("Only one in_progress allowed")
```

这些 ValueError 在 agent_loop 中被 try/except 捕获：

```python
try:
    output = handler(**block.input)
except Exception as e:
    output = f"Error: {e}"
# → output = "Error: Only one in_progress allowed"
# 该错误字符串作为 tool_result 返回给 LLM
```

</details>

---

# 15. plan_approval 错误分支

<details>
<summary>未知 request_id</summary>

```python
handle_plan_review("nonexistent_id", True, "ok"):
    req = plan_requests.get("nonexistent_id")
    → None
    return "Error: Unknown plan request_id 'nonexistent_id'"
```

分支走向：`req is None` → 直接返回错误

</details>

---

# 16. plan_approval reject 分支

<details>
<summary>approve=False 路径</summary>

```python
# 假设 plan_requests["r1e2j3"] = {"from": "deployer", "plan": "...", "status": "pending"}

handle_plan_review("r1e2j3", False, "Too risky, revise the plan."):
    req = plan_requests["r1e2j3"]  # 存在
    
    approve = False → req["status"] = "rejected"
    
    BUS.send("lead", "deployer", "Too risky, revise the plan.", "plan_approval_response",
             {"request_id": "r1e2j3", "approve": False, "feedback": "Too risky, revise the plan."})
    
    return "Plan rejected for 'deployer'"
```

💾 追加写入 `.team/inbox/deployer.jsonl`

<details>
<summary>📁 文件快照 — .team/inbox/deployer.jsonl（追加）</summary>

```json
{"type":"plan_approval_response","from":"lead","content":"Too risky, revise the plan.","timestamp":1711000800.0,"request_id":"r1e2j3","approve":false,"feedback":"Too risky, revise the plan."}
```

</details>

</details>

---

# 17. TeammateManager 重复 spawn + 状态检查

<details>
<summary>spawn 已存在且非 idle/shutdown 的 teammate</summary>

## 17.1 spawn 正在 working 的 teammate

```python
TEAM.spawn("builder", "build", "new prompt"):
    member = self._find("builder")
    → {"name":"builder", "role":"build", "status":"working"}
    
    member["status"] not in ("idle", "shutdown"):
        "working" not in ("idle", "shutdown") → True
    
    return "Error: 'builder' is currently working"
```

分支走向：状态不允许 → 返回错误，不启动新线程

## 17.2 spawn 已 shutdown 的 teammate（重新激活）

```python
TEAM.spawn("builder", "build", "new task prompt"):
    member = self._find("builder")
    → {"name":"builder", "role":"build", "status":"shutdown"}
    
    member["status"] in ("idle", "shutdown") → True!
    member["status"] = "working"
    member["role"] = "build"
```

💾 `TEAM._save()` → config.json 更新 builder.status = "working"

启动新线程 `_loop("builder", "build", "new task prompt")`

输出: `"Spawned 'builder' (role: build)"`

分支走向：已存在但 shutdown → 复用 member 对象，重新启动

</details>

---

# 18. Teammate idle 超时 → 自动 shutdown

<details>
<summary>idle 阶段 12 次轮询全部无消息无任务 → shutdown</summary>

```python
# deployer idle 阶段:
self._set_status("deployer", "idle")
resume = False

for _ in range(12):  # IDLE_TIMEOUT(60) // POLL_INTERVAL(5) = 12
    time.sleep(5)
    
    inbox = BUS.read_inbox("deployer") → []  # 每次都为空
    
    # 检查 unclaimed tasks:
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        t = json.loads(f.read_text())
        # task_1: completed → skip
        # task_2: completed → skip
        # (task_3 已删除)
    unclaimed = []  # 空
    
    # 继续下一次轮询...

# 12 次循环全部结束，resume 仍为 False:
if not resume:  # True!
    self._set_status("deployer", "shutdown")
    return  # 线程自然结束
```

💾 更新 `.team/config.json` → deployer.status = "shutdown"

分支走向：`not resume` → idle 超时 → 自动 shutdown（区别于收到 shutdown_request 的主动 shutdown）

</details>

---

# 19. Teammate 线程 LLM 调用异常

<details>
<summary>client.messages.create 抛出异常 → 线程 shutdown</summary>

```python
# _loop 内部:
try:
    response = client.messages.create(
        model=MODEL,
        system=sys_prompt,
        messages=messages,
        tools=tools,
        max_tokens=8000,
    )
except Exception:  # 网络错误、API 限流等
    self._set_status(name, "shutdown")
    return  # 线程结束
```

分支走向：`except Exception` → 直接 shutdown，不重试

💾 更新 `.team/config.json` → 该 teammate status = "shutdown"

</details>

---

# 20. bash 超时分支

<details>
<summary>命令执行超过 120 秒</summary>

```python
run_bash("sleep 300"):
    dangerous 检查 → 通过
    subprocess.run("sleep 300", shell=True, timeout=120)
    → 抛出 subprocess.TimeoutExpired
    
except subprocess.TimeoutExpired:
    return "Error: Timeout (120s)"
```

分支走向：`TimeoutExpired` → 返回超时错误

</details>

---

# 21. BackgroundManager — 后台任务异常分支

<details>
<summary>后台命令执行失败</summary>

```python
BG._exec(tid, "invalid_command_xyz", 120):
    try:
        r = subprocess.run("invalid_command_xyz", shell=True, ...)
        # shell=True 时不会抛异常，而是 stderr 有内容
        output = (r.stdout + r.stderr).strip()
        # → "/bin/sh: invalid_command_xyz: command not found"
        self.tasks[tid].update({"status": "completed", "result": output})
    except Exception as e:
        # 仅在极端情况（如 timeout）才走这里
        self.tasks[tid].update({"status": "error", "result": str(e)})
    
    self.notifications.put({
        "task_id": tid,
        "status": self.tasks[tid]["status"],
        "result": self.tasks[tid]["result"][:500]
    })
```

### 超时场景

```python
BG.run("sleep 300", timeout=10):
    tid = "bg_timeout"
    # _exec 中:
    subprocess.run("sleep 300", timeout=10)
    → TimeoutExpired 异常
    
    except Exception as e:
        self.tasks["bg_timeout"] = {"status": "error", "result": "Command 'sleep 300' timed out after 10 seconds"}
    
    notifications.put({"task_id":"bg_timeout", "status":"error", "result":"Command 'sleep 300' timed out..."})
```

分支走向：`except Exception` → status = "error"

下一轮 agent_loop 中 `BG.drain()` 会取出该通知并注入 messages：

```python
notifs = [{"task_id":"bg_timeout", "status":"error", "result":"Command 'sleep 300' timed out..."}]
txt = "[bg:bg_timeout] error: Command 'sleep 300' timed out..."
messages.append({"role":"user","content":"<background-results>\n[bg:bg_timeout] error: ...\n</background-results>"})
```

</details>

---

# 22. check_background — 无参数 vs 未知 ID

<details>
<summary>两个分支</summary>

## 22.1 无参数 — 列出所有

```python
BG.check(tid=None):
    # tid 为 None → 列出全部
    return "\n".join(
        f"{k}: [{v['status']}] {v['command'][:60]}"
        for k, v in self.tasks.items()
    )
    # → "a1b2c3d4: [completed] find . -name '*.py' -not -path './.tasks/*'"
    # 若 tasks 为空 → return "No bg tasks."
```

## 22.2 未知 ID

```python
BG.check(tid="nonexistent"):
    t = self.tasks.get("nonexistent") → None
    → return "Unknown: nonexistent"
```

</details>

---

# 23. TOOL_HANDLERS["idle"] — lead 不能 idle

<details>
<summary>lead 调用 idle</summary>

```python
TOOL_HANDLERS["idle"]():
    return "Lead does not idle."
```

该字符串作为 tool_result 返回给 LLM，LLM 会理解 lead 角色不支持 idle。

</details>

---

# 24. subagent 50 轮上限 + 失败分支

<details>
<summary>subagent 循环耗尽 + resp 为 None</summary>

## 24.1 正常耗尽 30 轮

```python
run_subagent(prompt, "Explore"):
    resp = None
    for _ in range(30):
        resp = client.messages.create(...)
        # 假设每轮都返回 tool_use，持续 30 轮
        if resp.stop_reason != "tool_use":
            break
        # ... 处理 tool_use ...
    
    # 循环结束，resp 是最后一次响应
    # resp.content 可能包含 text block
    return "".join(b.text for b in resp.content if hasattr(b, "text")) or "(no summary)"
```

## 24.2 resp 为 None（首次调用就异常）

```python
run_subagent(prompt, "Explore"):
    resp = None
    for _ in range(30):
        resp = client.messages.create(...)  # 假设抛异常被外层捕获
        # 实际上这里没有 try/except，异常会向上传播
        # 但如果循环体内某种原因 resp 始终为 None:
    
    if resp:  # None → False
        ...
    return "(subagent failed)"
```

分支走向：`resp` 为 falsy → 返回 `"(subagent failed)"`

</details>

---

# 25. Teammate 工作阶段 50 轮上限

<details>
<summary>_loop 内层 for 循环耗尽</summary>

```python
# _loop 内:
for _ in range(50):
    # ... LLM 调用 + tool 执行 ...
    if response.stop_reason != "tool_use":
        break
    # ... 
    if idle_requested:
        break

# 如果 50 轮都是 tool_use 且从未 idle:
# for 循环自然结束 → 直接进入 IDLE PHASE
self._set_status(name, "idle")
```

分支走向：50 轮耗尽 → 不 break → 自然落入 idle 阶段

</details>

---

# 最终磁盘状态汇总

<details>
<summary>展开查看完整文件系统</summary>

| 路径                                       | 类型     | 内容摘要                                                     |
| ------------------------------------------ | -------- | ------------------------------------------------------------ |
| `.tasks/task_1.json`                       | 文件     | `{"id":1, "subject":"Build project", "status":"completed", "owner":"builder", "blockedBy":[], "blocks":[]}` |
| `.tasks/task_2.json`                       | 文件     | `{"id":2, "subject":"Deploy to production", "status":"completed", "owner":"deployer", "blockedBy":[], "blocks":[]}` |
| `.tasks/task_3.json`                       | ❌ 已删除 | —                                                            |
| `.team/config.json`                        | 文件     | `{"team_name":"default","members":[{"name":"builder","role":"build","status":"shutdown"},{"name":"deployer","role":"ops","status":"shutdown"}]}` |
| `.team/inbox/lead.jsonl`                   | 文件     | `(空)`                                                       |
| `.team/inbox/builder.jsonl`                | 文件     | `(空 — shutdown_request 已被读取)`                           |
| `.team/inbox/deployer.jsonl`               | 文件     | 可能残留最后一条 plan_approval_response（取决于 deployer 是否在 shutdown 前读取） |
| `.transcripts/transcript_1711000600.jsonl` | 文件     | 手动 compress 时保存的完整对话历史                           |
| `.transcripts/transcript_1711000900.jsonl` | 文件     | `/compact` REPL 命令触发的第二次 transcript                  |
| `app.py`                                   | 文件     | 第 7 行已从 `return "Hello World"` 改为 `return "Hello Webapp v2"` |
| `README.md`                                | ❌ 不存在 | 本场景未创建（上一场景的产物）                               |
| `deploy.sh`                                | 文件     | deployer 创建的部署脚本                                      |
| `skills/deploy/SKILL.md`                   | 文件     | 原始 skill 文件，未修改                                      |

</details>

---

# 全流程覆盖清单

<details>
<summary>本场景覆盖 vs 上一场景覆盖对比</summary>

| 流程/分支                               |    上一场景     |                本场景                 |
| --------------------------------------- | :-------------: | :-----------------------------------: |
| SkillLoader 解析 SKILL.md frontmatter   | ❌ 无 skill 文件 |          ✅ 解析 deploy skill          |
| load_skill 成功                         |  ❌ 返回 Error   |           ✅ 返回 skill body           |
| task 依赖 blockedBy 设置                |        ❌        |      ✅ task_2 blocked by task_1       |
| task 完成时依赖解除                     |        ❌        | ✅ task_1 完成 → task_2.blockedBy 清空 |
| task 删除 (status="deleted")            |        ❌        |             ✅ task_3 删除             |
| edit_file                               |        ❌        |             ✅ app.py 编辑             |
| read_file limit 截断                    |        ❌        |         ✅ limit=3 截断 50 行          |
| safe_path 越界拦截                      |        ❌        |          ✅ ../../etc/passwd           |
| dangerous command 拦截                  |        ❌        |              ✅ sudo 拦截              |
| subagent (Explore 模式，只读工具)       |        ❌        |         ✅ 只有 bash+read_file         |
| broadcast                               |        ❌        |        ✅ 广播给 2 个 teammate         |
| plan_approval (approve)                 |        ❌        |                   ✅                   |
| plan_approval (reject)                  |        ❌        |                   ✅                   |
| plan_approval 未知 ID                   |        ❌        |                   ✅                   |
| teammate idle → 收消息恢复              |        ❌        |     ✅ deployer 收到 builder 消息      |
| teammate idle → auto-claim              |        ❌        |      ✅ builder auto-claim task_3      |
| teammate idle → 超时 shutdown           |        ❌        |                   ✅                   |
| teammate LLM 异常 → shutdown            |        ❌        |                   ✅                   |
| teammate 重复 spawn (working 状态拒绝)  |        ❌        |                   ✅                   |
| teammate 重复 spawn (shutdown 状态复用) |        ❌        |                   ✅                   |
| identity re-injection 条件分析          |        ❌        |            ✅ (含假设分支)             |
| 手动 compress (tool)                    |        ❌        |                   ✅                   |
| auto_compact (token 超限)               |        ❌        |             ✅ (补充说明)              |
| microcompact 实际清理                   |    ❌ 未超 3     |         ✅ 清理旧 tool_result          |
| nag reminder 触发                       |        ✅        |                   ✅                   |
| nag 不触发 (items 为空)                 |        ❌        |                   ✅                   |
| TodoWrite 校验错误 (5 种)               |        ❌        |                   ✅                   |
| bash 超时                               |        ❌        |                   ✅                   |
| bg task 超时/错误                       |        ❌        |                   ✅                   |
| check_background 无参数/未知 ID         |        ❌        |                   ✅                   |
| lead idle 拒绝                          |        ❌        |                   ✅                   |
| subagent 30 轮耗尽 / 失败               |        ❌        |                   ✅                   |
| teammate 50 轮工作耗尽                  |        ❌        |                   ✅                   |
| REPL /compact /tasks /team /inbox       |        ❌        |                   ✅                   |
| REPL 退出 (exit)                        |        ❌        |                   ✅                   |
| shutdown_request 协议                   |   ✅ (未完成)    |                ✅ 完整                 |
| 两个 teammate 互相通信                  |        ❌        |          ✅ builder→deployer           |

</details>