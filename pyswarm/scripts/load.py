import os

from dotenv import load_dotenv


def load_env(env_path=None):
    """
    Loads environment variables from a .env file into os.environ.
    If env_path is None, loads from default .env in current directory.
    """
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment variables from {env_path or '.env'}.")
    for k, v in os.environ.items():
        if 'API_KEY' in k or 'TOKEN' in k or 'SECRET' in k:
            print(f"{k} = {v[:4]}... (hidden)")

if __name__ == "__main__":
    load_env()
