import json
import urllib.request
import requests
from pathlib import Path
from dennis.forge.config import load_config


"""
Project-related CLI commands.
"""

def projects_list(server, api_prefix, token):

    api_prefix = api_prefix or "/api"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(
        f"{server}{api_prefix}/projects",
        headers=headers,
        timeout=30
    )

    r.raise_for_status()

    payload = r.json()

    if not payload:
        print("No projects found.")
        return

    print(json.dumps(payload, indent=2))


def projects_deleted(server, api_prefix, token):
    
    if api_prefix is None:
        api_prefix = "/api"

    url = f"{server}{api_prefix}/projects/deleted"
    # print("DEBUG URL:", url)


    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())

        if not data:
            print("No deleted projects.")
            return

        for p in data:
            print(f"{p['uuid_project']}  {p['name']}")

    except Exception as e:
        print("Error:", e)

def projects_restore(server, api_prefix, token, project_id, with_artifacts=False, no_artifacts=False):

    if api_prefix is None:
        api_prefix = "/api"

    # --------------------------------------------------------
    # 1. TRY TO FETCH ARTIFACT COUNT
    # --------------------------------------------------------
    artifact_count = None

    try:
        artifacts_url = f"{server}{api_prefix}/projects/{project_id}/artifacts"

        req = urllib.request.Request(artifacts_url)
        req.add_header("Authorization", f"Bearer {token}")

        with urllib.request.urlopen(req) as res:
            artifacts = json.loads(res.read().decode())

        artifact_count = len(artifacts)

    except Exception:
        # silently ignore if endpoint not available
        artifact_count = None

    # --------------------------------------------------------
    # 2. DECIDE RESTORE STRATEGY
    # --------------------------------------------------------
    restore_artifacts = with_artifacts

    if not with_artifacts and not no_artifacts:

        if artifact_count is not None and artifact_count > 0:

            print(f"This project has {artifact_count} artifacts associated with it.")
            print("Do you want to restore them as well? (y/N)")

            choice = input("> ").strip().lower()

            restore_artifacts = choice == "y"

    if no_artifacts:
        restore_artifacts = False

    # --------------------------------------------------------
    # 3. CALL BACKEND
    # --------------------------------------------------------
    url = f"{server}{api_prefix}/projects/{project_id}/restore"

    payload = json.dumps({
        "restore_artifacts": restore_artifacts
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())

        # --------------------------------------------------------
        # 4. UX OUTPUT
        # --------------------------------------------------------
        print("✔ Project restored")

        if restore_artifacts:
            if artifact_count is not None:
                print(f"✔ Restored {artifact_count} artifacts")
            else:
                print("✔ Artifacts restored")

        else:
            if artifact_count:
                print("(artifacts not restored)")

    except Exception as e:
        print("Error:", e)


def register_projects_commands(sub):
    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    projects_cmd = sub.add_parser("projects", help="Manage projects")
    projects_sub = projects_cmd.add_subparsers(dest="subcommand")
    projects_sub.required = True

    # projects list
    projects_sub.add_parser("list", help="List projects")

    # projects delete
    delete_cmd = projects_sub.add_parser("delete", help="Delete a project")
    delete_cmd.add_argument("project_id")

    # projects rename
    rename_cmd = projects_sub.add_parser("rename", help="Rename a project")
    rename_cmd.add_argument("project_id")
    rename_cmd.add_argument("new_name")

    # projects activate
    activate_cmd = projects_sub.add_parser("activate", help="Set active project")
    activate_cmd.add_argument("project_id")

    # projects deleted
    projects_sub.add_parser("deleted", help="List deleted projects")

    # projects restore
    restore_cmd = projects_sub.add_parser("restore", help="Restore a project")
    restore_cmd.add_argument("project_id")
    restore_cmd.add_argument("--with-artifacts", action="store_true", help="Restore associated artifacts")
    restore_cmd.add_argument("--no-artifacts", action="store_true", help="Do not restore associated artifacts")
    
    pass

def handle_projects(args):

    cfg = load_config()

    if args.subcommand == "list":

        return projects_list(
            cfg["server"],
            cfg.get("api_prefix"),
            cfg.get("auth", {}).get("token")
        )

    elif args.subcommand == "deleted":

        return projects_deleted(
            cfg["server"],
            cfg.get("api_prefix"),
            cfg.get("auth", {}).get("token")
        )

    elif args.subcommand == "restore":

        return projects_restore(
            server=cfg["server"],
            api_prefix=cfg.get("api_prefix"),
            token=cfg.get("auth", {}).get("token"),
            project_id=args.project_id,
            with_artifacts=args.with_artifacts,
            no_artifacts=args.no_artifacts
        )

    print("Unknown projects subcommand:", args.subcommand)
    return 1