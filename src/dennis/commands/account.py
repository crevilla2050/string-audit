"""
Forge account lifecycle commands.

Owns:
    - user create
    - user verify
    - login
    - logout

This module manages authentication and Forge account state.
Cryptographic identities belong to commands.identity.
"""

import urllib.request
import json
import getpass

import requests

from dennis.forge.config import save_config, load_config
from dennis.core.get_configuration import get_env_config

# user create
def register_account_commands(sub):
    user_cmd = sub.add_parser("user", help="User management")
    user_sub = user_cmd.add_subparsers(dest="user_command")
    user_sub.required = True
    user_create = user_sub.add_parser("create", help="Create a new user")
    user_create.add_argument("email")

    # user verify
    user_verify = user_sub.add_parser("verify", help="Verify user email")
    user_verify.add_argument("token")
    
    login_cmd = sub.add_parser("login", help="Authenticate with Dennis The Forge")

    login_cmd.add_argument(
        "--server",
        metavar="URL",
        help="Forge server URL (overrides configuration)"
    )

    login_cmd.add_argument("--email", required=True)
    login_cmd.add_argument("--token", help="Use existing token (for automation)")

    logout_cmd = sub.add_parser("logout", help="Clear stored authentication")


def handle_login(args):
    # ----------------------------------------
    # Resolve server configuration
    # ----------------------------------------
    env_cfg = get_env_config()

    api_prefix = env_cfg.get("api_prefix") or "/api"
    server = (
        getattr(args, "server", None)
        or env_cfg.get("server")
        or load_config().get("server")
    )

    if not server:
        raise SystemExit(
            "Server not configured. Use --server or set DENNIS_SERVER"
        )

    # ----------------------------------------
    # Existing token
    # ----------------------------------------
    if args.token:
        cfg = load_config()
        cfg["server"] = server
        cfg.setdefault("auth", {})
        cfg["auth"]["token"] = args.token
        save_config(cfg)

        print("✔ Token stored")
        return

    # ----------------------------------------
    # Password login
    # ----------------------------------------
    url = f"{server.rstrip('/')}{api_prefix}/auth/login"

    password = getpass.getpass("Password: ")

    payload = json.dumps({
        "email": args.email,
        "password": password
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(payload))
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())

    except Exception as e:
        raise SystemExit(f"Login failed: {e}")
    
    token = result.get("access_token")

    if not token:
        raise SystemExit("Login failed: no token returned")

    cfg = load_config()

    cfg["server"] = server

    cfg.setdefault("auth", {})
    cfg["auth"]["token"] = token

    save_config(cfg)

    if args.token:
        cfg = load_config()
        cfg["server"] = server
        cfg.setdefault("auth", {})
        cfg["auth"]["token"] = args.token
        save_config(cfg)

        print("✔ Token stored")
        return

    print("✔ Logged in successfully\n")
    # TODO(Launch): Remove token echo once authenticated CLI commands
    # consume the stored auth token from config instead of manual copy/paste.
    print(token)


def handle_logout(args):

        config = load_config()

        if "auth" in config:
            config["auth"] = {}

        save_config(config)
        print("✔ Logged out successfully")

def handle_user(args):

    env_cfg = get_env_config()
    api_prefix = env_cfg.get("api_prefix") or "/api"
    server = (
        getattr(args, "server", None)
        or env_cfg.get("server")
        or load_config().get("server")
    )

    if args.user_command == "create":

        if not server:
            raise SystemExit("Server not configured. Use --server or set DENNIS_SERVER")

        url = f"{server.rstrip('/')}{api_prefix}/auth/login"

        password = getpass.getpass("Password: ")

        payload = {
            "email": args.email,
            "password": password
        }

        try:
            print("URL:", url)
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if resp.status_code not in (200, 201):
                raise SystemExit(f"Error: {resp.text}")

            data = resp.json()

            print("✔ User created")
            print(f"Email: {data.get('email', args.email)}")

        except Exception as e:
            raise SystemExit(f"Error creating user: {e}")
    
    elif args.user_command == "verify":

        if not server:
            raise SystemExit("Server not configured")

        url = f"{server.rstrip('/')}{api_prefix}/auth/verify/{args.token}"

        try:
            resp = requests.get(url)

            if resp.status_code != 200:
                raise SystemExit(f"Verification failed: {resp.text}")

            print("✔ Email verified successfully")

        except Exception as e:
            raise SystemExit(f"Error verifying user: {e}")


