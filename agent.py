import os
import requests
from pathlib import Path

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "nvidia/nemotron-3.5-lightning:free"

OUTPUT = Path.home() / "storage/shared/Movies/YouTubeAgent"
OUTPUT.mkdir(parents=True, exist_ok=True)

def generate_script(topic):
    if not API_KEY:
        print("API key missing!")
        return

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tum ek professional Hindi YouTube script writer ho. "
                    "Natural Hindi mein engaging script likho. "
                    "Hook, introduction, main explanation, examples "
                    "aur conclusion shamil karo."
                )
            },
            {
                "role": "user",
                "content": (
                    "YouTube video topic: " + topic +
                    "\nHindi mein lagbhag 1000 shabdon ki script likho."
                )
            }
        ],
        "max_tokens": 1800,
        "reasoning": {"enabled": False}
    }

    try:
        response = requests.post(
            url, headers=headers, json=data, timeout=120
        )
        print("Status:", response.status_code)
        result = response.json()

        if not response.ok:
            print(result)
            return

        content = result["choices"][0]["message"].get("content")

        if not content:
            print("AI ne text nahi diya. Dobara try karo.")
            print(result)
            return

        filename = "".join(
            c if c.isalnum() or c in "-_ " else "_"
            for c in topic
        ).strip().replace(" ", "_")[:60]

        path = OUTPUT / (filename + ".txt")
        path.write_text(content, encoding="utf-8")

        print("\nSCRIPT READY!")
        print("Saved at:", path)
        print("\nPreview:\n")
        print(content[:1500])

    except Exception as error:
        print("Error:", error)

if __name__ == "__main__":
    topic = input("Video ka topic likho: ").strip()
    if topic:
        generate_script(topic)
    else:
        print("Topic khaali hai.")
