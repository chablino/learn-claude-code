from pathlib import Path
import re
import yaml

p = Path.cwd() / "skills"
skills = {}
lines = []

# def _parse_frontmatter(text: str) -> tuple:
#         """Parse YAML frontmatter between --- delimiters."""
#         match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
#         if not match:
#             return {}, text
#         meta = {}
#         print(match.group(1).strip().splitlines())
#         for line in match.group(1).strip().splitlines():
#             if ":" in line:
#                 key, val = line.split(":", 1)
#                 meta[key.strip()] = val.strip()
#         return meta, match.group(2).strip()

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """使用 PyYAML 解析 --- 之间的元数据"""
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    
    yaml_text = match.group(1).strip()
    body_text = match.group(2).strip()
    
    try:
        # safe_load 可以完美解析多行字符串 '|' 并且更安全
        meta = yaml.safe_load(yaml_text) 
        # 防止 yaml_text 为空时 safe_load 返回 None
        if meta is None:
            meta = {}
    except yaml.YAMLError as e:
        print(f"YAML 解析错误: {e}")
        meta = {}
    print(type(meta))
    return meta, body_text

for f in sorted(p.rglob("SKILL.md")):
    text = f.read_text()
    meta, body = _parse_frontmatter(text)
    # print(meta)
    # print(f.parent.name)
    # name = meta.get("name", f.parent.name)
    name = meta.get("name", f.parent.name)
    skills[name] = {"meta": meta, "body": body}
    # print(skills)

for name, skill in skills.items():
    desc = skill["meta"].get("description", "No description")
    tags = skill["meta"].get("tags", "")
    line = f"  - {name}: {desc}"
    if tags:
        line += f" [{tags}]"
    lines.append(line)
    # print(line)

# print("\n".join(lines))



# a = '''          salah          
# dia s
# jon es
# wir    z             
# '''
# print(a)