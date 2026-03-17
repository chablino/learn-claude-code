#!/usr/bin/env python3
"""
s08_background_tasks.py - Background Tasks (带时间观测探针版)
"""

import os
import subprocess
import threading
import uuid
from pathlib import Path
import time

from dotenv import load_dotenv
from openai_compat import Anthropic

load_dotenv(override=True)

WORKDIR = Path.cwd()
client = Anthropic()
MODEL = os.environ.get("MODEL_ID", "stepfun/step-3.5-flash:free")

SYSTEM = f"You are a coding agent at {WORKDIR}. Use background_run for long-running commands."


# -- BackgroundManager: threaded execution + notification queue --
class BackgroundManager:
    def __init__(self):
        self.tasks = {}  # task_id -> {status, result, command}
        self._notification_queue = []  # completed task results
        self._lock = threading.Lock()

    def run(self, command: str) -> str:
        """Start a background thread, return task_id immediately."""
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {
            "status": "running",
            "result": None,
            "command": command,
        }
        
        # 👇 [探针 1] 记录主线程按下发令枪的绝对时间
        start_gun_time = time.time()
        
        thread = threading.Thread(
            target=self._execute, args=(task_id, command, start_gun_time), daemon=True
        )
        thread.start()
        return f"Background task {task_id} started: {command[:80]}"

    def _execute(self, task_id: str, command: str, start_gun_time: float):
        """Thread target: run subprocess, capture output, push to queue."""
        # 👇 [探针 2] 记录后台 Python 线程真正苏醒的时间
        thread_wake_time = time.time()
        
        try:
            # 👇 [探针 3] 记录真正发包给操作系统的时刻
            process_start_time = time.time()
            
            r = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            # 👇 [探针 4] 操作系统进程执行完毕交还控制权的时刻
            process_end_time = time.time()
            
            output = (r.stdout + r.stderr).strip()[:50000]
            status = "completed"
        except subprocess.TimeoutExpired:
            process_end_time = time.time()
            output = "Error: Timeout (300s)"
            status = "timeout"
        except Exception as e:
            process_end_time = time.time()
            output = f"Error: {e}"
            status = "error"
            
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["result"] = output or "(no output)"
        
        # 🧮 计算具体的耗时切片
        thread_delay = thread_wake_time - start_gun_time      # 被 Debugger 冻结的时间通常在这里
        process_delay = process_start_time - thread_wake_time # OS 和 Conda 启动的时间通常在这里
        total_time = process_end_time - start_gun_time        # 总物理耗时
        
        with self._lock:
            self._notification_queue.append(
                {
                    "task_id": task_id,
                    "status": status,
                    "command": command[:80],
                    "result": (output or "(no output)")[:500],
                    # 👇 将计时数据作为信件的附件塞进去
                    "timing": {
                        "thread_delay": thread_delay,
                        "process_delay": process_delay,
                        "total_time": total_time
                    }
                }
            )

    def check(self, task_id: str = None) -> str:
        """Check status of one task or list all."""
        if task_id:
            t = self.tasks.get(task_id)
            if not t:
                return f"Error: Unknown task {task_id}"
            return f"[{t['status']}] {t['command'][:60]}\n{t.get('result') or '(running)'}"
        lines = []
        for tid, t in self.tasks.items():
            lines.append(f"{tid}: [{t['status']}] {t['command'][:60]}")
        return "\n".join(lines) if lines else "No background tasks."

    def drain_notifications(self) -> list:
        """Return and clear all pending completion notifications."""
        with self._lock:
            notifs = list(self._notification_queue)
            self._notification_queue.clear()
        return notifs


BG = BackgroundManager()


# -- Tool implementations (省略部分未修改代码，保持原样) --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR, capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        c = fp.read_text()
        if old_text not in c:
            return f"Error: Text not found in {path}"
        fp.write_text(c.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"

TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "background_run": lambda **kw: BG.run(kw["command"]),
    "check_background": lambda **kw: BG.check(kw.get("task_id")),
}

TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command (blocking).",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "background_run",
        "description": "Run command in background thread. Returns task_id immediately.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "check_background",
        "description": "Check background task status. Omit task_id to list all.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
        },
    },
]


def agent_loop(messages: list):
    while True:
        notifs = BG.drain_notifications() 
        if notifs and messages:
            # 👇👇👇 专门为了观测时间重写了日志输出格式 👇👇👇
            print_text = ""
            notif_text_for_llm = ""
            
            for n in notifs:
                t = n.get('timing', {})
                print_text += f"\n✅ [bg:{n['task_id']}] {n['status']}: {n['result']}\n"
                if t:
                    print_text += f"   ├─ 命令: {n['command']}\n"
                    print_text += f"   ├─ 线程苏醒卡顿: {t.get('thread_delay', 0):.4f} 秒\n"
                    print_text += f"   ├─ OS进程启动卡顿: {t.get('process_delay', 0):.4f} 秒\n"
                    print_text += f"   └─ 实际执行总耗时: {t.get('total_time', 0):.4f} 秒\n"
                
                # 给大模型看的内容保持原样，不用包含咱们的物理时间探针
                notif_text_for_llm += f"[bg:{n['task_id']}] {n['status']}: {n['result']}\n"

            print(f"\n📥 [邮箱提醒] 主线程在这一轮循环发现了信件！内容是：{print_text}\n")
            # 👆👆👆 👆👆👆
            
            messages.append(
                {
                    "role": "user",
                    "content": f"<background-results>\n{notif_text_for_llm}\n</background-results>",
                }
            )
            messages.append(
                {"role": "assistant", "content": "Noted background results."}
            )
            
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
            
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = (
                        handler(**block.input)
                        if handler
                        else f"Unknown tool: {block.name}"
                    )
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block.name}: {str(output)[:200]}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    }
                )
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms08 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()