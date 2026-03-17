from pathlib import Path

# WORKDIR = Path("/Users/chablino/study/Ai/learn-claude-code-main")
WORKDIR = Path.cwd()


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_read(path: str, limit: int = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
        # return len("\n".join(lines))
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    # print(WORKDIR)
    # path = safe_path("滕王阁序1.txt")
    # print(run_read(path, 5))
    # print(run_write("../testFolder/test.txt", "Hello, Hwei!"))

    # path = safe_path("testFolder/test.txt")
    # content = path.read_text()
    # path.write_text(content.replace('h', 'H'))

    content = "djasksjfndslkjieojqeqo"
    print(content.replace("q", "p"))
