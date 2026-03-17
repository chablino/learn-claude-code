import os

from openai import OpenAI

client = OpenAI(
    api_key="codex_46625e6d5a398096ad2842a5db1ec2ddfdf12178fdea3a68",
    base_url="https://codex.xxworld.org/v1",
)

response = client.responses.create(
    model="gpt-5.2-codex",
    input="给我一个 3 步接入摘要。"
)

print(response.output_text)