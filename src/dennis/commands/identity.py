import json
import base64
from dennis.core.identity import derive_key_id_from_public_key_bytes

from dennis.forge.config import load_config, save_config
from pathlib import Path

def resolve_identity_paths(name: str):
    keys_dir = Path.home() / ".dennis" / "keys"
    private_path = keys_dir / f"{name}.key"
    public_path = keys_dir / f"{name}.pub"

    if not private_path.exists():
        raise SystemExit(f"Identity key not found: {private_path}")

    if not public_path.exists():
        raise SystemExit(f"Identity public key not found: {public_path}")

    return private_path, public_path


def load_identity(pub_path: Path) -> dict:
    try:
        identity = json.loads(pub_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to read identity file: {pub_path} ({e})")

    public_key_b64 = identity.get("public_key")
    if not public_key_b64:
        raise SystemExit(f"Identity file missing public_key: {pub_path}")

    try:
        public_key_bytes = base64.b64decode(public_key_b64)
    except Exception:
        raise SystemExit(f"Identity file has invalid public_key encoding: {pub_path}")

    enriched = dict(identity)
    enriched["derived_key_id"] = derive_key_id_from_public_key_bytes(public_key_bytes)
    return enriched

def register_identity_commands(sub):
    identity_cmd = sub.add_parser("identity", help="Identity management")
    identity_sub = identity_cmd.add_subparsers(dest="identity_command", required=True)

    identity_use = identity_sub.add_parser("use", help="Set active identity")
    identity_use.add_argument("name", help="Identity key name (without extension)")

    identity_sub.add_parser("current", help="Show active identity")
    identity_sub.add_parser("list", help="List available identities")

def handle_identity(args):

        cfg = load_config()
        active_name = cfg.get("identity", {}).get("active")

        if args.identity_command == "use":
            name = args.name
            _, pub_path = resolve_identity_paths(name)
            identity = load_identity(pub_path)

            save_config({
                "identity": {
                    "active": name
                }
            })

            print(f"[Dennis] Active identity set to: {name} ({identity['derived_key_id']})")
            return

        elif args.identity_command == "current":
            if not active_name:
                raise SystemExit("No active identity. Use: dennis identity use <key>")

            _, pub_path = resolve_identity_paths(active_name)
            identity = load_identity(pub_path)

            print(f"name: {active_name}")
            print(f"id: {identity['derived_key_id']}")
            print(f"key: ed25519:{identity['derived_key_id']}")
            return

        elif args.identity_command == "list":
            keys_dir = Path.home() / ".dennis" / "keys"
            pub_files = sorted(keys_dir.glob("*.pub")) if keys_dir.exists() else []

            if not pub_files:
                print("No identities found.")
                return

            for pub_path in pub_files:
                name = pub_path.stem
                marker = "*" if name == active_name else " "
                try:
                    identity = load_identity(pub_path)
                    derived_key_id = identity["derived_key_id"]
                except SystemExit:
                    derived_key_id = "invalid"

                print(f"{marker} {name:<10} {derived_key_id}")
            return