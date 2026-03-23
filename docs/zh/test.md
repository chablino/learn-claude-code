```markdown
# 场景：创建任务 + 创建 worktree 并绑定（含文件快照）

## 初始磁盘状态

- `.tasks/` 目录存在，内部为空
- `.worktrees/index.json` 内容为 `{"worktrees": []}`
- `.worktrees/events.jsonl` 文件为空（0字节）

---

## 用户输入

> "帮我创建一个auth重构任务，然后开个worktree"

---

## 第一轮：LLM 决定先创建任务

### agent_loop(messages) 进入 while True

- **messages 当前内容：**

```json
[
  {
    "role": "user",
    "content": "帮我创建一个auth重构任务，然后开个worktree"
  }
]
```

- 调用 `client.messages.create()` → 发送给 LLM
- LLM 返回 `stop_reason = "tool_use"`
- 遍历 `response.content` 找到 `tool_use` block：
  - `block.id` = `"toolu_01ABC"`
  - `block.name` = `"task_create"`
  - `block.input` = `{"subject": "Implement auth refactor"}`

### 分发到 TOOL_HANDLERS["task_create"]

- 实际调用：`TASKS.create("Implement auth refactor")`

### 进入 TaskManager.create()

- `self._next_id` 当前值 = `1`
- 构造 task 字典：

```json
{
  "id": 1,
  "subject": "Implement auth refactor",
  "status": "pending",
  "worktree": "",
  "owner": "",
  "created_at": 1719000000.0,
  "updated_at": 1719000000.0
}
```

- 调用 `self._save(task)`

### 进入 TaskManager._save()

- 调用 `self._path(1)` → 返回 `Path(".tasks/task_1.json")`
- `json.dump(task)` 写入文件
- 💾 **磁盘写入：** `.tasks/task_1.json`

### _save() 返回 → create() 继续

- `self._next_id += 1`（变为 `2`）
- 返回 task 的 JSON 字符串给 agent_loop

### 📁 文件快照：`.tasks/task_1.json`（新建）

```json
{
  "id": 1,
  "subject": "Implement auth refactor",
  "status": "pending",
  "worktree": "",
  "owner": "",
  "created_at": 1719000000.0,
  "updated_at": 1719000000.0
}
```

### agent_loop 处理工具结果

- 将 LLM 的 assistant 消息追加到 messages
- 将工具结果包装为 `tool_result` 追加到 messages
- **messages 当前内容：**

```json
[
  {"role": "user", "content": "帮我创建一个auth重构任务，然后开个worktree"},
  {"role": "assistant", "content": [tool_use block: task_create]},
  {"role": "user", "content": [tool_result: task JSON]}
]
```

- `continue` → 回到 while True 顶部，再次调用 LLM

---

## 第二轮：LLM 决定创建 worktree

### agent_loop 再次调用 LLM

- LLM 看到任务已创建（id=1），决定继续创建 worktree
- LLM 返回 `stop_reason = "tool_use"`
- 遍历 `response.content` 找到 `tool_use` block：
  - `block.id` = `"toolu_02DEF"`
  - `block.name` = `"worktree_create"`
  - `block.input` = `{"branch": "auth-refactor", "task_id": 1}`

### 分发到 TOOL_HANDLERS["worktree_create"]

- 实际调用：`WORKTREES.create("auth-refactor", task_id=1)`

### 进入 WorktreeManager.create()

- 读取 `.worktrees/index.json` → `{"worktrees": []}`
- 生成 worktree 记录：

```json
{
  "branch": "auth-refactor",
  "path": ".worktrees/auth-refactor",
  "task_id": 1,
  "created_at": 1719000001.0
}
```

- 追加到 `index["worktrees"]` 列表
- 写入 `.worktrees/index.json`
- 💾 **磁盘写入：** `.worktrees/index.json`

### 写入事件日志

- 构造事件：

```json
{"event": "worktree_created", "branch": "auth-refactor", "task_id": 1, "ts": 1719000001.0}
```

- 追加写入 `.worktrees/events.jsonl`
- 💾 **磁盘写入：** `.worktrees/events.jsonl`

### 绑定任务

- 调用 `TASKS.update(1, worktree="auth-refactor")`

### 进入 TaskManager.update()

- 调用 `self._load(1)`
  - 读取 `.tasks/task_1.json` → 得到 task 字典
- 修改字段：`task["worktree"] = "auth-refactor"`
- 更新 `task["updated_at"] = 1719000002.0`
- 调用 `self._save(task)`
  - 写入 `.tasks/task_1.json`
  - 💾 **磁盘写入：** `.tasks/task_1.json`（覆盖）

### 📁 文件快照：`.tasks/task_1.json`（更新后）

```json
{
  "id": 1,
  "subject": "Implement auth refactor",
  "status": "pending",
  "worktree": "auth-refactor",
  "owner": "",
  "created_at": 1719000000.0,
  "updated_at": 1719000002.0
}
```

### 📁 文件快照：`.worktrees/index.json`（更新后）

```json
{
  "worktrees": [
    {
      "branch": "auth-refactor",
      "path": ".worktrees/auth-refactor",
      "task_id": 1,
      "created_at": 1719000001.0
    }
  ]
}
```

### 📁 文件快照：`.worktrees/events.jsonl`（追加后）

```json
{"event": "worktree_created", "branch": "auth-refactor", "task_id": 1, "ts": 1719000001.0}
```

### WorktreeManager.create() 返回

- 返回结果字符串给 agent_loop

### agent_loop 处理工具结果

- 将 assistant 消息和 tool_result 追加到 messages
- `continue` → 回到 while True 顶部，再次调用 LLM

---

## 第三轮：LLM 生成最终回复

### agent_loop 再次调用 LLM

- LLM 判断两个操作都已完成
- 返回 `stop_reason = "end_turn"`
- `response.content[0].text`：

> ✅ 已完成：
> 1. 创建任务 #1「Implement auth refactor」
> 2. 创建 worktree `auth-refactor` 并绑定到任务 #1

### agent_loop 退出

- `stop_reason != "tool_use"` → `break` 跳出 while True
- 打印最终回复
- 函数返回

---

## 最终磁盘状态

| 文件                      | 状态                               |
| ------------------------- | ---------------------------------- |
| `.tasks/task_1.json`      | ✅ 已创建并更新（含 worktree 绑定） |
| `.worktrees/index.json`   | ✅ 已更新（含 1 条 worktree 记录）  |
| `.worktrees/events.jsonl` | ✅ 已追加 1 行事件                  |
```