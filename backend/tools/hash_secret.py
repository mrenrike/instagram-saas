"""Generate secrets and their hashes for the environment (items 1, 10).

    python -m backend.tools.hash_secret            # generate a new secret + its hash
    python -m backend.tools.hash_secret --key      # generate a SESSION_ENCRYPTION_KEY
    echo -n "existing" | python -m backend.tools.hash_secret --stdin

The plaintext is printed once, for you to paste into your password manager and into
whatever calls the admin endpoint. Only the hash needs to reach the server.
"""
import argparse
import base64
import os
import sys

# Importable without the app's environment being configured.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.security.secrets import generate_secret, hash_secret  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", action="store_true", help="generate a 32-byte base64 encryption key")
    parser.add_argument("--stdin", action="store_true", help="hash a secret read from stdin")
    args = parser.parse_args()

    if args.key:
        print(f"SESSION_ENCRYPTION_KEY={base64.b64encode(os.urandom(32)).decode()}")
        return 0

    if args.stdin:
        secret = sys.stdin.read().strip()
        if not secret:
            print("nada recebido no stdin", file=sys.stderr)
            return 1
        print(f"ADMIN_SECRET_HASH={hash_secret(secret)}")
        return 0

    secret = generate_secret(32)
    print("# Guarde o segredo abaixo no seu gerenciador de senhas — ele não é recuperável.")
    print(f"# Segredo (use no header Authorization: Bearer <segredo>):\n{secret}\n")
    print("# Cole apenas a linha abaixo no ambiente do servidor:")
    print(f"ADMIN_SECRET_HASH={hash_secret(secret)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
