# s12_worktree_task_isolation

## 核心架构：控制平面 + 执行平面

### 控制平面 (Control Plane) - TaskManager（任务管理器）
- 持久化目录：.tasks/task_{id}.json
- 任务状态机：pending → in_progress → completed
- 核心方法
    - create(subject) → 创建任务，status=pending
    - update(task_id, status, owner) → 更新状态/负责人
    - bind_worktree(task_id, worktree) → 绑定worktree，自动推进到in_progress
    - unbind_worktree(task_id) → 解绑worktree字段
    - list_all() → 列出所有任务及状态标记
    - get(task_id) / exists(task_id) → 查询
- 内部方法
    - _load/_save → JSON读写单个任务文件
    - _max_id → 扫描文件名获取最大ID
    - _path → task_id映射到文件路径

### 执行平面 (Execution Plane) - WorktreeManager（工作树管理器）
- 持久化：.worktrees/index.json（注册表）
- Worktree状态机：absent → active → removed | kept
- 依赖注入
    - self.tasks → TaskManager实例（双向绑定）
    - self.events → EventBus实例（生命周期记录）
- 核心方法
    - create(name, task_id) → git worktree add + 写index + 调用tasks.bind_worktree
    - remove(name, complete_task) → git worktree remove + 可选调用tasks.update(completed) + tasks.unbind_worktree，不删除目录
    - keep(name) → 标记status=kept，不删除目录
    - run(name, command) → subprocess在worktree目录执行命令（cwd隔离）
    - status(name) → 在worktree目录执行git status
    - list_all() → 读取index.json展示所有worktree
- 内部方法
    - _run_git → 封装git子进程调用
    - _load_index/_save_index → index.json读写
    - _find(name) → 按名称查找worktree条目
    - _validate_name → 正则校验名称合法性

### 可观测层 (Observability) - EventBus（事件总线）
- 持久化：.worktrees/events.jsonl（追加写入）
- 核心方法
    - emit(event, task, worktree, error) → 追加一行JSON事件
    - list_recent(limit) → 读取最近N条事件
- 事件类型
    - worktree.create.before / after / failed
    - worktree.remove.before / after / failed
    - worktree.keep
    - task.completed

## 类之间的关系

### WorktreeManager 聚合 TaskManager
- create时：调用 tasks.bind_worktree() 绑定任务
- remove时：调用 tasks.update(completed) + tasks.unbind_worktree() 完成任务
- create前：调用 tasks.exists() 校验任务存在

### WorktreeManager 聚合 EventBus
- 每个生命周期节点（create/remove/keep）前后都调用 events.emit()
- 异常时也emit failed事件

### TaskManager 与 EventBus 无直接关系
- TaskManager不知道EventBus的存在
- 事件发射由WorktreeManager作为协调者统一触发

## 辅助工具函数（模块级）

### 文件操作
- safe_path(p) → 路径安全校验，防止逃逸
- run_read(path) → 读文件
- run_write(path, content) → 写文件
- run_edit(path, old_text, new_text) → 替换文件内容

### 命令执行
- run_bash(command) → 在WORKDIR执行shell命令
- 危险命令黑名单过滤

### 环境检测
- detect_repo_root(cwd) → git rev-parse获取仓库根目录

## LLM Agent 循环

### agent_loop(messages)
- 调用 Anthropic API（OpenAI兼容）
- 解析tool_use响应 → 查TOOL_HANDLERS字典 → 执行对应函数
- 将结果作为tool_result回传 → 循环直到stop_reason != tool_use

### TOOL_HANDLERS 字典
- 将17个工具名映射到具体函数调用
- 分三组
    - 基础工具：bash, read_file, write_file, edit_file
    - 任务工具：task_create, task_list, task_get, task_update, task_bind_worktree
    - Worktree工具：worktree_create, worktree_list, worktree_status, worktree_run, worktree_keep, worktree_remove, worktree_events

## 全局单例与初始化顺序
- REPO_ROOT = detect_repo_root() → 仓库根目录
- TASKS = TaskManager(REPO_ROOT/.tasks) → 先创建
- EVENTS = EventBus(REPO_ROOT/.worktrees/events.jsonl) → 再创建
- WORKTREES = WorktreeManager(REPO_ROOT, TASKS, EVENTS) → 最后创建，注入前两者