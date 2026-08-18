def get_env_config():
    import os

    api_prefix = os.getenv("API_PREFIX")
    server = os.getenv("DENNIS_SERVER")

    if api_prefix is None:
        api_prefix = "/api"

    return {
        "server": server,
        "api_prefix": api_prefix
    }