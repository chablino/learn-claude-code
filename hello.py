"""A simple hello world script."""

from pathlib import Path

path = Path.cwd()

def main() -> None:
    """Print a greeting message."""
    print("Hello, World!")
    print(f"Current working directory: {path}")


if __name__ == "__main__":
    main()
