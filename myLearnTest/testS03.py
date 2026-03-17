lines = [
    "This is a test.",
    "It should be joined with newlines.",
    "The result should be a single string.",
]

print(lines)  # This will print the list as-is, which is not what we want
print("\n".join(lines))
