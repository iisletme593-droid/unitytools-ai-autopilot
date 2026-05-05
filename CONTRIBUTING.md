# Contributing

Thanks for helping UnityTools improve.

Good first contributions:
- Add more Unity command handlers.
- Improve Ollama/local model prompts.
- Port V1 tools such as vision scoring or scene profiles.
- Improve docs, examples, screenshots, and tests.

Development loop:

```powershell
pip install -e .
python -m compileall unitytools tests
python tests/test_chat_server.py
unitytools status
```

Please do not commit `.env`, API keys, Unity `Library/`, or generated build folders.
