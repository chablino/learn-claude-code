# s12 Worktree + Task Isolation

## 核心理念
- 目录级隔离，任务ID协调
- Task = 控制平面
- Worktree = 执行平面

## 初始化
- detect_repo_root: 检测 git 仓库根目录
- REPO_ROOT: 仓库根 or 当前目录
- SYSTEM prompt: 指导 LLM 使用工具
- 全局实例
    - TASKS = TaskManager(.tasks/)
    - EVENTS = EventBus(.worktrees/events.jsonl)
    - WORKTREES = WorktreeManager(root, tasks, events)

## EventBus 事件总线
- 职责: 追加式生命周期事件记录
- 存储: .worktrees/events.jsonl (JSONL格式)
- emit() 发射事件
    - 参数: event, task, worktree, error
    - payload: {event, ts, task, worktree, ?error}
    - 追加写入文件 ("a"模式)
- list_recent() 查询近期事件
    - 参数: limit (默认20, 上限200)
    - 读取文件尾部N行
    - 解析JSON，解析失败记为 parse_error

## TaskManager 任务管理器
- 存储: .tasks/task_{id}.json (每任务一文件)
- 任务数据结构
    - id, subject, description
    - status: pending / in_progress / completed
    - owner, worktree
    - blockedBy[], created_at, updated_at
- 内部方法
    - _max_id(): 扫描文件名获取最大ID
    - _path(): 生成任务文件路径
    - _load() / _save(): 读写JSON
- create() 创建任务
    - 自增ID
    - 初始状态 pending
- get() 获取任务详情
- exists() 检查任务是否存在
- update() 更新状态/所有者
    - 校验 status 枚举值
- bind_worktree() 绑定 worktree
    - 设置 worktree 名称
    - pending 自动变为 in_progress
- unbind_worktree() 解绑 worktree
- list_all() 列出所有任务
    - 按ID排序
    - 状态标记: [ ] [>] [x]

## WorktreeManager 工作树管理器
- 存储: .worktrees/index.json
- worktree 数据结构
    - name, path, branch (wt/{name})
    - task_id, status, created_at
- 依赖注入: repo_root, tasks, events
- 内部方法
    - _is_git_repo(): 检测是否git仓库
    - _run_git(): 执行git命令 (超时120s)
    - _load_index() / _save_index()
    - _find(): 按名称查找 worktree
    - _validate_name(): 正则校验 [A-Za-z0-9._-]{1,40}
- create() 创建工作树
    - 校验: 名称合法 + 不重复 + task存在
    - emit worktree.create.before
    - git worktree add -b wt/{name} {path} {base_ref}
    - 写入 index.json
    - 绑定 task (如有)
    - emit worktree.create.after
    - 失败: emit worktree.create.failed
- list_all() 列出所有工作树
- status() 查看工作树git状态
    - git status --short --branch
- run() 在工作树中执行命令
    - 危险命令拦截
    - shell=True, 超时300s
    - 输出截断50000字符
- remove() 移除工作树
    - emit worktree.remove.before
    - git worktree remove [--force]
    - complete_task=True 时: 标记任务completed + 解绑
    - 更新 index 状态为 removed
    - emit worktree.remove.after
    - 失败: emit worktree.remove.failed
- keep() 保留工作树
    - 更新 index 状态为 kept
    - emit worktree.keep

## 基础工具函数
- safe_path(): 路径安全校验 (防逃逸)
- run_bash(): 执行shell命令
    - 危险命令拦截
    - 超时120s, 输出截断50000
- run_read(): 读取文件
    - 支持 limit 行数限制
- run_write(): 写入文件
    - 自动创建父目录
- run_edit(): 编辑文件
    - 精确文本替换 (仅首次匹配)

## TOOL_HANDLERS 工具路由表
- 基础工具: bash, read_file, write_file, edit_file
- 任务工具: task_create, task_list, task_get, task_update, task_bind_worktree
- 工作树工具: worktree_create, worktree_list, worktree_status, worktree_run, worktree_keep, worktree_remove, worktree_events

## TOOLS 工具Schema定义
- 15个工具的 name + description + input_schema
- 供 Anthropic API tool_use 协议使用

## agent_loop 主循环
- 调用 LLM (messages.create)
    - model, system, messages, tools, max_tokens=8000
- 停止条件: stop_reason != "tool_use"
- 工具执行流程
    - 遍历 response.content 中的 tool_use block
    - 从 TOOL_HANDLERS 查找 handler
    - 执行并捕获异常
    - 打印截断输出 (200字符)
    - 组装 tool_result 返回给 LLM

## __main__ 入口
- 打印 repo root
- 检查 git 可用性
- REPL 循环
    - 提示符: s12 >>
    - 退出: q / exit / 空 / Ctrl+C / EOF
    - 用户输入 -> history -> agent_loop
    - 打印 LLM 文本回复
