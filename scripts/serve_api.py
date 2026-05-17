import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from waitress import serve
from core.api.app import create_app

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
serve(create_app(), host="0.0.0.0", port=port, threads=16, connection_limit=200, channel_timeout=30)
