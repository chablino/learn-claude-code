# s06: Context Compact (上下文压缩)

`s01 > s02 > s03 > s04 > s05 > [ s06 ] | s07 > s08 > s09 > s10 > s11 > s12`

> *"上下文总会满, 要有办法腾地方"* -- 三层压缩策略, 换来无限会话。

## 问题

上下文窗口是有限的。读一个 1000 行的文件就吃掉 ~4000 token; 读 30 个文件、跑 20 条命令, 轻松突破 100k token。不压缩, 智能体根本没法在大项目里干活。

## 解决方案

三层压缩, 激进程度递增:

```
Every turn:
+------------------+
| Tool call result |
+------------------+
        |
        v
[Layer 1: micro_compact]        (silent, every turn)
  Replace tool_result > 3 turns old
  with "[Previous: used {tool_name}]"
        |
        v
[Check: tokens > 50000?]
   |               |
   no              yes
   |               |
   v               v
continue    [Layer 2: auto_compact]
              Save transcript to .transcripts/
              LLM summarizes conversation.
              Replace all messages with [summary].
                    |
                    v
            [Layer 3: compact tool]
              Model calls compact explicitly.
              Same summarization as auto_compact.
```

## 工作原理

1. **第一层 -- micro_compact**: 每次 LLM 调用前, 将旧的 tool result 替换为占位符。

```python
def micro_compact(messages: list) -> list:
    tool_results = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for j, part in enumerate(msg["content"]):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    tool_results.append((i, j, part))
    if len(tool_results) <= KEEP_RECENT:
        return messages
    for _, _, part in tool_results[:-KEEP_RECENT]:
        if len(part.get("content", "")) > 100:
            part["content"] = f"[Previous: used {tool_name}]"
    return messages
```

2. **第二层 -- auto_compact**: token 超过阈值时, 保存完整对话到磁盘, 让 LLM 做摘要。

```python
def auto_compact(messages: list) -> list:
    # Save transcript for recovery
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    # LLM summarizes
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity..."
            + json.dumps(messages, default=str)[:80000]}],
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Compressed]\n\n{response.content[0].text}"},
        {"role": "assistant", "content": "Understood. Continuing."},
    ]
```

3. **第三层 -- manual compact**: `compact` 工具按需触发同样的摘要机制。

4. 循环整合三层:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Layer 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Layer 2
        response = client.messages.create(...)
        # ... tool execution ...
        if manual_compact:
            messages[:] = auto_compact(messages)       # Layer 3
```

完整历史通过 transcript 保存在磁盘上。信息没有真正丢失, 只是移出了活跃上下文。

## 相对 s05 的变更

| 组件           | 之前 (s05)       | 之后 (s06)                     |
|----------------|------------------|--------------------------------|
| Tools          | 5                | 5 (基础 + compact)             |
| 上下文管理     | 无               | 三层压缩                       |
| Micro-compact  | 无               | 旧结果 -> 占位符               |
| Auto-compact   | 无               | token 阈值触发                 |
| Transcripts    | 无               | 保存到 .transcripts/           |

## 试一试

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Read every Python file in the agents/ directory one by one` (观察 micro-compact 替换旧结果)
2. `Keep reading files until compression triggers automatically`
3. `Use the compact tool to manually compress the conversation`

```
content="I'll help you read every Python file in the agents/ directory. Let me start by finding all Python files in that directory."
Function(arguments='{"command": "find agents/ -name \\"*.py\\" -type f | sort"}',
name='bash')
```

**进入client.messages.create 前** 
message = [{}]

**进入client.messages.create 后**
发送给大模型的消息：oai = [ {}, {}, {}, {}... ]

**大模型返回的消息，在client.messages.create内部**
ChatCompletionMessage(content="I'll help you read every Python file in the agents/ directory. Let me start by finding all Python files in that directory.",
refusal=None,
role='assistant',
annotations=None,
audio=None,
function_call=None,
tool_calls=[ChatCompletionMessageFunctionToolCall(id='call_e92c46cc7ee4497bb1190b69',
function=Function(arguments='{"command": "find agents/ -name \\"*.py\\" -type f | sort"}',
name='bash'),
type='function',
index=0)],
reasoning='The user wants me to read every Python file in the agents/ directory one by one. I need to first check if there is an agents/ directory and what Python files are in it, then read them sequentially.\n\nLet me start by listing the files in the agents/ directory to see what Python files are there.',
reasoning_details=[{'type': 'reasoning.text', 'text': 'The user wants me to read every Python file in the agents/ directory one by one. I need to first check if there is an agents/ directory and what Python files are in it, then read them sequentially.\n\nLet me start by listing the files in the agents/ directory to see what Python files are there.', 'format': 'unknown', 'index': 0}]),
native_finish_reason='tool_calls')]
tool_calls等于一个列表，说明内部可以有多个工具调用

**在client.messages.create内部**
blocks = [TextBlock(msg.content) | ToolUseBlock(tc.id, tc.function.name, input_dict)] #input_dict被__repr__隐藏
[TextBlock(text="I'll help you read every Python file in the agents/ directory. Let me...ding all Python files in that directory."), ToolUseBlock(name='bash', id='call_e92c46cc7ee4497bb1190b69')]
👇变成
AnthropicResponse(blocks, stop_reason)类

**在client.messages.create外部**
message = [{"role":"user", "content":""},{"role":"assistant", "content":[TextBlock(msg.content) | ToolUseBlock(tc.id, tc.function.name, input_dict)], {"role":"user", "content":[{'type': 'tool_result', 'tool_use_id': 'call_e92c46cc7ee4497bb1190b69', 'content': 'agents/__init__.py\nagents/openai_compat.py\nagents/s_full.py\nagents/s01_agent_loop.py\n...s.py\nagents/s12_worktree_task_isolation.py'}]}]

有三种message = [用户输入, 模型回复, 工具调用结果, ...]

1. 用户输入 {"role":"user", "content":""}
2. 模型回复 {"role":"assistant", "content":[TextBlock(msg.content) or ToolUseBlock(tc.id, tc.function.name, input_dict)]
3. 工具调用结果 {"role":"user", "content":[{'type': 'tool_result', 'tool_use_id': 'call_e92c46cc7ee4497bb1190b69', 'content':'agents/__init__.py\nagents/openai_compat.py\nagents/s_full.py\nagents/s01_agent_loop.py\n...s.py\nagents/s12_worktree_task_isolation.py'}, {另一个工具调用结果信息}]}
