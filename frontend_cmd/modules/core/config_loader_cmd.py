# CMD_Frontend/modules/core/config_loader_cmd.py
import os
from . import shared_state_cmd as g
import config_cmd as config

def _to_bool(value):
    return str(value).lower() in ('true', '1', 't', 'y', 'yes')

def load_and_parse_config():
    g.FLASK_HOST = getattr(config, 'FLASK_HOST', '0.0.0.0')
    g.FLASK_PORT = int(getattr(config, 'FLASK_PORT', 6003))
    g.WEBSERVER_DISABLE_HTTPS = _to_bool(getattr(config, 'WEBSERVER_DISABLE_HTTPS', False))
    g.SERVER_ADDRESS = getattr(config, 'SERVER_ADDRESS', "127.0.0.1:6001")