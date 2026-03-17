# s03: TodoWrite (待办写入)

`s01 > s02 > [ s03 ] s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"没有计划的 agent 走哪算哪"* -- 先列步骤再动手, 完成率翻倍。

## 问题

多步任务中, 模型会丢失进度 -- 重复做过的事、跳步、跑偏。对话越长越严重: 工具结果不断填满上下文, 系统提示的影响力逐渐被稀释。一个 10 步重构可能做完 1-3 步就开始即兴发挥, 因为 4-10 步已经被挤出注意力了。

## 解决方案

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> | Tools   |
| prompt |      |       |      | + todo  |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                          |
              +-----------+-----------+
              | TodoManager state     |
              | [ ] task A            |
              | [>] task B  <- doing  |
              | [x] task C            |
              +-----------------------+
                          |
              if rounds_since_todo >= 3:
                inject <reminder> into tool_result
```

## 工作原理

1. TodoManager 存储带状态的项目。同一时间只允许一个 `in_progress`。

```python
class TodoManager:
    def update(self, items: list) -> str:
        validated, in_progress_count = [], 0
        for item in items:
            status = item.get("status", "pending")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item["id"], "text": item["text"],
                              "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress")
        self.items = validated
        return self.render()
```

2. `todo` 工具和其他工具一样加入 dispatch map。

```python
TOOL_HANDLERS = {
    # ...base tools...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

3. nag reminder: 模型连续 3 轮以上不调用 `todo` 时注入提醒。

```python
if rounds_since_todo >= 3 and messages:
    last = messages[-1]
    if last["role"] == "user" and isinstance(last.get("content"), list):
        last["content"].insert(0, {
            "type": "text",
            "text": "<reminder>Update your todos.</reminder>",
        })
```

"同时只能有一个 in_progress" 强制顺序聚焦。nag reminder 制造问责压力 -- 你不更新计划, 系统就追着你问。

## 相对 s02 的变更

| 组件           | 之前 (s02)       | 之后 (s03)                     |
|----------------|------------------|--------------------------------|
| Tools          | 4                | 5 (+todo)                      |
| 规划           | 无               | 带状态的 TodoManager           |
| Nag 注入       | 无               | 3 轮后注入 `<reminder>`        |
| Agent loop     | 简单分发         | + rounds_since_todo 计数器     |

## 试一试

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Refactor the file hello.py: add type hints, docstrings, and a main guard`
2. `Create a Python package with __init__.py, utils.py, and tests/test_utils.py`
3. `Review all Python files and fix any style issues`

```json
{
  "id": "gen-1772871029-ruSrrtvXZO2fixkr6oko",
  "model": "stepfun/step-3.5-flash:free",
  "object": "chat.completion",
  "provider": "StepFun",
  "created": 1772871029,
  "choices": [
    {
      "index": 0,
      "finish_reason": "tool_calls",
      "message": {
        "role": "assistant",
        "content": "I'll help you refactor the hello.py file by adding type hints, docstrings, and a main guard. Let me first read the file to see its current content.",
        "reasoning": "The user wants me to refactor a file called \"hello.py\" by:\n1. Adding type hints\n2. Adding docstrings\n3. Adding a main guard\n\nFirst, I need to read the file to see its current content, then refactor it accordingly. Let me start by reading the file.",
        "tool_calls": [
          {
            "id": "call_1b6fba005bf344299ca84922",
            "type": "function",
            "function": {
              "name": "read_file",
              "arguments": "{\"path\": \"hello.py\"}"
            }
          }
        ]
      }
    }
  ],
  "usage": {
    "prompt_tokens": 627,
    "completion_tokens": 124,
    "total_tokens": 751,
    "completion_tokens_details": {
      "reasoning_tokens": 66,
      "audio_tokens": 0,
      "image_tokens": 0
    },
    "cost": 0
  }
}
```

```python
resp = ChatCompletion(id='gen-1772871029-ruSrrtvXZO2fixkr6oko', 
                      choices=[
                        Choice(
                          finish_reason='tool_calls', 
                          index=0, 
                          logprobs=None, 
                          message=ChatCompletionMessage(
                            content="I'll help you refactor the hello.py file by adding type hints, docstrings, and a main guard. Let me first read the file to see its current content.", 
                            refusal=None, 
                            role='assistant', 
                            annotations=None, 
                            audio=None, 
                            function_call=None, 
                            tool_calls=[ ChatCompletionMessageFunctionToolCall(
                              id='call_1b6fba005bf344299ca84922', 
                              function=Function(
                                arguments='{"path": "hello.py"}', 
                                name='read_file'
                              ), 
                              type='function', 
                              index=0
                            )
                                       ], 
                            reasoning='The user wants me to refactor a file called "hello.py" by:\n1. Adding type hints\n2. Adding docstrings\n3. Adding a main guard\n\nFirst, I need to read the file to see its current content, then refactor it accordingly. Let me start by reading the file.', 
                            reasoning_details=[{'type': 'reasoning.text', 'text': 'The user wants me to refactor a file called "hello.py" by:\n1. Adding type hints\n2. Adding docstrings\n3. Adding a main guard\n\nFirst, I need to read the file to see its current content, then refactor it accordingly. Let me start by reading the file.', 'format': 'unknown', 'index': 0}]
                          )回到message, 
                          native_finish_reason='tool_calls'
                        )回到Choice
                      ]回到choices, 
                      created=1772871029, 
                      model='stepfun/step-3.5-flash:free', 
                      object='chat.completion', 
                      service_tier=None, 
                      system_fingerprint=None, 
                      usage=CompletionUsage(completion_tokens=124, 
                                            prompt_tokens=627, 
                                            total_tokens=751,                         
                                            completion_tokens_details=CompletionTokensDetails(
                                              accepted_prediction_tokens=None, 
                                              audio_tokens=0, 
                                              reasoning_tokens=66, 
                                              rejected_prediction_tokens=None, 
                                              image_tokens=0
                                            ), 
                                            prompt_tokens_details=PromptTokensDetails(
                                              audio_tokens=0, 
                                              cached_tokens=0, 
                                              cache_write_tokens=0, 
                                              video_tokens=0
                                            ), 
                                            cost=0, 
                                            is_byok=False, 
                                            cost_details={'upstream_inference_cost': 0, 'upstream_inference_prompt_cost': 0, 'upstream_inference_completions_cost': 0}), provider='StepFun')
```

```python
user:	'Refactor the file hello.py: add type hints, docstrings, and a main guard'

assistant:	[TextBlock(text="I'll help you refactor the hello.py file by adding type hints, docstr...ead the file to see its current content."), ToolUseBlock(name='read_file', id='call_1b6fba005bf344299ca84922')]

user:	[{'type': 'tool_result', 'tool_use_id': 'call_1b6fba005bf344299ca84922', 'content': 'print("Hello, World!")'}]

assistant:	[ToolUseBlock(name='todo', id='call_50b35cfd9aac4b0480c1b6b0')]

user:	[{'type': 'tool_result', 'tool_use_id': 'call_50b35cfd9aac4b0480c1b6b0', 'content': '[>] #1: Refactor hello.py: add type hints, docstrings, and main guard\n\n(0/1 completed)'}]

assistant:	[TextBlock(text="Now I'll refactor the file by adding proper structure with type hints, docstrings, and a main guard."), ToolUseBlock(name='edit_file', id='call_1390712534f84ca68af588c5')]

user:	[{'type': 'tool_result', 'tool_use_id': 'call_1390712534f84ca68af588c5', 'content': 'Edited hello.py'}]

assistant:	[ToolUseBlock(name='todo', id='call_2b63e795af6a4060b40620a7')]

user:	[{'type': 'tool_result', 'tool_use_id': 'call_2b63e795af6a4060b40620a7', 'content': '[x] #1: Refactor hello.py: add type hints, docstrings, and main guard\n\n(1/1 completed)'}]

assistant:	[TextBlock(text='Done! I\'ve refactored `hello.py` with:\n\n- **Module docstring** at ...erly structured for a standalone script.')]

```

```python
user:	Review all Python files and fix any style issues

assistant:	content="I'll help you review and fix style issues in all Python files. Let me start by creating a plan and then executing it."
Function(arguments='{"items": [{"id": "find_python_files", "status": "in_progress", "text": "Find all Python files in the project"}, {"id": "check_style", "status": "pending", "text": "Check for style issues using flake8/black"}, {"id": "fix_style", "status": "pending", "text": "Fix identified style issues"}, {"id": "verify_fixes", "status": "pending", "text": "Verify all issues are resolved"}]}',
name='todo')

user:		content = [{'type': 'tool_result', 'tool_use_id': 'call_2c5395b92c8b4191a769344a', 'content': '[>] #find_python_files: Find all Python files in the project\n[ ] #check_style: Check for style issues using flake8/black\n[ ] #fix_style: Fix identified style issues\n[ ] #verify_fixes: Verify all issues are resolved\n\n(0/4 completed)'}]

assistant:	content=None
Function(arguments='{"command": "find /Users/chablino/study/Ai/learn-claude-code-main -name \\"*.py\\" -type f | head -20"}',
name='bash')

user:	content = [{'type': 'tool_result', 'tool_use_id': 'call_f1f2b5d4efde48ada826d9e7', 'content': '/Users/chablino/study/Ai/learn-claude-code-main/hello.py\n/Users/chablino/study/Ai/learn-claude-code-main/test/testS03.py\n/Users/chablino/study/Ai/learn-claude-code-main/test/testSafePath.py\n/Users/chablino/study/Ai/learn-claude-code-main/test/testCommand.py\n/Users/chablino/study/Ai/learn-claude-code-main/test/testSynSugar.py\n/Users/chablino/study/Ai/learn-claude-code-main/tests/test_utils.py\n/Users/chablino/study/Ai/learn-claude-code-main/__init__.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s_full.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s03_todo_write.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s06_context_compact.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s08_background_tasks.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s01_agent_loop.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s04_subagent.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s02_tool_use.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s07_task_system.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/__init__.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s09_agent_teams.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/openai_compat.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s05_skill_loading.py\n/Users/chablino/study/Ai/learn-claude-code-main/agents/s10_team_protocols.py'}]

assistant:	content=None
Function(arguments='{"command": "which flake8"}',
name='bash')

user:	content = [{'type': 'tool_result', 'tool_use_id': 'call_4601f3e51eed4547a563b374', 'content': '(no output)'}]

assistant:content=None
Function(arguments='{"command": "which black"}',
name='bash')

user:	content = [{'type': 'text', 'text': '<reminder>Update your todos.</reminder>'}, {'type': 'tool_result', 'tool_use_id': 'call_03527669ae654a259d5e0a09', 'content': '(no output)'}]

assistant:	content=None
Function(arguments='{"items": [{"id": "find_python_files", "status": "completed", "text": "Find all Python files in the project"}, {"id": "install_tools", "status": "in_progress", "text": "Install style checking tools (flake8/black)"}, {"id": "check_style", "status": "pending", "text": "Check for style issues using flake8/black"}, {"id": "fix_style", "status": "pending", "text": "Fix identified style issues"}, {"id": "verify_fixes", "status": "pending", "text": "Verify all issues are resolved"}]}',
name='todo')

user:	content = [{'type': 'tool_result', 'tool_use_id': 'call_051d606f65334a9fa1d22a31', 'content': '[x] #find_python_files: Find all Python files in the project\n[>] #install_tools: Install style checking tools (flake8/black)\n[ ] #check_style: Check for style issues using flake8/black\n[ ] #fix_style: Fix identified style issues\n[ ] #verify_fixes: Verify all issues are resolved\n\n(1/5 completed)'}]

assistant:	content=None
Function(arguments='{'command': 'pip install flake8 black'}',
name='bash')

user:	content = [{'type': 'tool_result', 'tool_use_id': 'call_a996168a3c954fc599894f92', 'content': 'Collecting flake8\n  Downloading flake8-7.3.0-py2.py3-none-any.whl.metadata (3.8 kB)\nC...mplete download (0 bytes/13 kB, attempt 1)'}]

assistant:

.
.
.
  
```

流程

1. 先问一个问题，问题被加到message
2. 带着message进入循环，进入与大模型交流api，在内部将message转化为openai格式然后发送给大模型
3. 在内部收到回复，在内部根据回复是文本还是工具，处理成textblock和tooluseblock
4. 出来，textblock被加入到message，tooluseblock先运行工具，同时拿到运行的输出，将输出作为tool_result加入到message
5. 再次带着message循环进agent_loop，重复

