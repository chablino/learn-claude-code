# s05: Skills (技能加载)

`s01 > s02 > s03 > s04 > [ s05 ] s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"用到什么知识, 临时加载什么知识"* -- 通过 tool_result 注入, 不塞 system prompt。

## 问题

你希望智能体遵循特定领域的工作流: git 约定、测试模式、代码审查清单。全塞进系统提示太浪费 -- 10 个技能, 每个 2000 token, 就是 20,000 token, 大部分跟当前任务毫无关系。

## 解决方案

```
System prompt (Layer 1 -- always present):
+--------------------------------------+
| You are a coding agent.              |
| Skills available:                    |
|   - git: Git workflow helpers        |  ~100 tokens/skill
|   - test: Testing best practices     |
+--------------------------------------+

When model calls load_skill("git"):
+--------------------------------------+
| tool_result (Layer 2 -- on demand):  |
| <skill name="git">                   |
|   Full git workflow instructions...  |  ~2000 tokens
|   Step 1: ...                        |
| </skill>                             |
+--------------------------------------+
```

第一层: 系统提示中放技能名称 (低成本)。第二层: tool_result 中按需放完整内容。

## 工作原理

1. 每个技能是一个目录, 包含 `SKILL.md` 文件和 YAML frontmatter。

```
skills/
  pdf/
    SKILL.md       # ---\n name: pdf\n description: Process PDF files\n ---\n ...
  code-review/
    SKILL.md       # ---\n name: code-review\n description: Review code\n ---\n ...
```

2. SkillLoader 递归扫描 `SKILL.md` 文件, 用目录名作为技能标识。

```python
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        for f in sorted(skills_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}

    def get_descriptions(self) -> str:
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "")
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'."
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"
```

3. 第一层写入系统提示。第二层不过是 dispatch map 中的又一个工具。

```python
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Skills available:
{SKILL_LOADER.get_descriptions()}"""

TOOL_HANDLERS = {
    # ...base tools...
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}
```

模型知道有哪些技能 (便宜), 需要时再加载完整内容 (贵)。

## 相对 s04 的变更

| 组件           | 之前 (s04)       | 之后 (s05)                     |
|----------------|------------------|--------------------------------|
| Tools          | 5 (基础 + task)  | 5 (基础 + load_skill)          |
| 系统提示       | 静态字符串       | + 技能描述列表                 |
| 知识库         | 无               | skills/\*/SKILL.md 文件        |
| 注入方式       | 无               | 两层 (系统提示 + result)       |

## 试一试

```sh
cd learn-claude-code
python agents/s05_skill_loading.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `What skills are available?`
2. `Load the agent-builder skill and follow its instructions`
3. `I need to do a code review -- load the relevant skill first`
4. `Build an MCP server using the mcp-builder skill`

```
`What skills are available?`

content="I have access to several specialized skills:\n\n1. **agent-builder** - Build AI agents with custom capabilities\n2. **code-review** - Perform comprehensive code reviews (security, performance, maintainability)\n3. **mcp-builder** - Create MCP (Model Context Protocol) servers to extend Claude's capabilities\n4. **pdf** - Process PDF files (extract text, create PDFs, merge documents)\n\nYou can use `load_skill` to load any of these skills before working on tasks that require specialized knowledge. For example, if you need to review code, load the code-review skill."
```

```
Load the agent-builder skill and follow its instructions

content=None
Function(arguments='{"name": "agent-builder"}',
name='load_skill')

content="I've successfully loaded the **agent-builder** skill. This skill provides a comprehensive framework for building AI agents based on the principle that the model already knows how to be an agent - our job is simply to provide the right capabilities, knowledge, and context.\n\nThe agent builder follows these core principles:\n- **Simple loop**: Model sees context + capabilities, decides to act or respond\n- **3 key elements**: Capabilities (what it can DO), Knowledge (what it KNOWS), Context (what has happened)\n- **Start minimal**: 3-5 capabilities, add complexity only when needed\n- **Trust the model**: Don't over-engineer or pre-specify workflows\n\nTo build an agent, I need to understand:\n\n1. **Purpose**: What should this agent accomplish?\n2. **Domain**: What world does it operate in? (customer service, research, operations, creative, etc.)\n3. **Essential actions**: What 3-5 capabilities are critical?\n4. **Expertise needed**: What domain knowledge should it access?\n5. **Trust level**: What decisions can be delegated to the model?\n\nWhat kind of agent would you like me to help you build? Please describe the agent's purpose and domain, and we can start designing it using the agent-builder framework."

```

```
content="The **code-review** skill is now loaded! I'm ready to perform comprehensive code reviews focusing on:\n\n- **Security**: Injection vulnerabilities, auth issues, data exposure\n- **Correctness**: Logic errors, race conditions, error handling\n- **Performance**: N+1 queries, memory issues, inefficient algorithms\n- **Maintainability**: Naming, complexity, duplication, dead code\n- **Testing**: Coverage, edge cases, mocking, assertions\n\n**Please provide:**\n- The code you want reviewed (file contents or repository path)\n- Any specific concerns or areas of focus\n- The programming language(s) used\n- Context about what the code is supposed to do\n\nI'll conduct a thorough review and provide structured feedback with specific line references, impact assessments, and suggested fixes."
```

```
content=None
Function(arguments='{"name": "mcp-builder"}',
name='load_skill')

content="Great! I have the MCP builder skill loaded. I can help you build an MCP server.\n\nBefore I create the server, I need to know what functionality you'd like to expose to Claude. MCP servers can provide:\n\n- **Tools**: Functions Claude can call (like API endpoints, calculations, data operations)\n- **Resources**: Data Claude can read (like files, database records, configurations)\n- **Prompts**: Pre-built prompt templates\n\n**What would you like your MCP server to do?** Some examples:\n\n1. Weather API integration - get weather for cities\n2. Database access - query a database from Claude\n3. File operations - read/write files in a controlled way\n4. Custom calculations - perform specific computations\n5. External service integration - interact with any API\n6. Something else?\n\nPlease describe the purpose and I'll build a complete MCP server with proper error handling, security considerations, and testing setup."
```

