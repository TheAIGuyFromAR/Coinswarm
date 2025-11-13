import os

from dotenv import dotenv_values


def save_env_keys(env_path=None, out_path=None):
    """
    Saves all current environment variables containing 'API_KEY', 'TOKEN', or 'SECRET' to a .env file.
    If env_path is given, loads from that file first (to preserve existing values).
    If out_path is not given, saves to .env in current directory.
    """
    env = dict(os.environ)
    filtered = {k: v for k, v in env.items() if 'API_KEY' in k or 'TOKEN' in k or 'SECRET' in k}
    if env_path:
        filtered = {**dotenv_values(env_path), **filtered}
    out_path = out_path or '.env'
    with open(out_path, 'w') as f:
        for k, v in filtered.items():
            f.write(f"{k}={v}\n")
    print(f"Saved {len(filtered)} API keys/secrets to {out_path}.")

if __name__ == "__main__":
    save_env_keys()
