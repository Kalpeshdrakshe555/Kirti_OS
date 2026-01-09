import os

structure = {
    "Kirti_OS": {
        "config": ["settings.yaml", "models_registry.py", "secrets_manager.py"],
        "core": ["__init__.py", "event_loop.py", "resource_guardian.py", "circuit_breaker.py", "router.py"],
        "brains": ["__init__.py", "left_brain_logic.py", "right_brain_vision.py", "browser_fallback.py"],
        "memory": ["__init__.py", "vector_cache.py", "conversation_log.py", "usage_ledger.py"],
        "interfaces": ["__init__.py", "telegram_bot.py", "voice_io.py"],
        "tools": ["__init__.py", "automation.py", "web_search.py", "file_ops.py"],
        "utils": ["__init__.py", "logger.py", "helpers.py"]
    }
}

def create_structure(base_path, struct):
    for name, content in struct.items():
        path = os.path.join(base_path, name)
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            print(f"📂 Created: {path}")
            create_structure(path, content)
        elif isinstance(content, list):
            os.makedirs(path, exist_ok=True)
            print(f"📂 Created: {path}")
            for file in content:
                with open(os.path.join(path, file), 'w') as f:
                    if file.endswith(".py"): f.write(f'"""\nModule: {file}\nKirti OS God Mode\n"""\n')
                print(f"  📄 Created: {file}")

if __name__ == "__main__":
    create_structure(".", structure)
    print("\n✅ New Architecture Ready!")