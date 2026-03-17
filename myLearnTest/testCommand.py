import os
import subprocess


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


if __name__ == "__main__":
    command = "cat > 滕王阁序1.txt << 'EOF'\n豫章故郡，洪都新府。星分翼轸，地接衡庐。\n\n时维九月，序属三秋。\nEOF"
    print(f"\033[33m$ {command}\033[0m")
    output = run_bash(command)
    print(output[:200])
