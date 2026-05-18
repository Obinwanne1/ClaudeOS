"""Flask application factory."""
import logging
import logging.handlers
from pathlib import Path

from flask import Flask
from flask_cors import CORS

from core.config import get_settings
from core.api.middleware import register_middleware
from core.api.routes.system import system_bp


def create_app() -> Flask:
    settings = get_settings()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.CLAUDEOS_SECRET_KEY

    # CORS — allow dashboard origin
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Logging
    _setup_logging(settings)

    # Rate limiter
    from core.api.limiter import limiter
    limiter.init_app(app)

    # Middleware
    register_middleware(app)

    # Run DB migrations (idempotent — CREATE IF NOT EXISTS)
    _run_migrations()

    # Routes — Phase 1
    app.register_blueprint(system_bp)

    # Auth + Admin blueprints
    from core.api.routes.auth_routes import auth_bp
    from core.api.routes.admin_routes import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # Routes — Phase 2+ (registered lazily when modules exist)
    _register_optional_blueprints(app)

    # Workflow Scheduler — start after blueprints registered
    _start_scheduler(app)

    # Pre-load ChromaDB + sentence-transformers in background.
    # Without this, the first memory request blocks a Flask worker for 30-60s on Windows.
    _warmup_vector_store()

    return app


def _run_migrations():
    """Apply all SQL migrations in order (idempotent)."""
    migrations_dir = Path(__file__).parent.parent.parent / "memory" / "db" / "migrations"
    if not migrations_dir.exists():
        return
    from core.database import run_migration
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        try:
            run_migration(sql_file)
        except Exception as e:
            logging.getLogger("claudeos.api").warning("Migration %s failed: %s", sql_file.name, e)


def _register_optional_blueprints(app: Flask):
    try:
        from core.api.routes.memory import memory_bp
        app.register_blueprint(memory_bp)
    except ImportError:
        pass

    try:
        from core.api.routes.agents import agents_bp
        app.register_blueprint(agents_bp)
    except ImportError:
        pass

    try:
        from core.api.routes.workflows import workflows_bp
        app.register_blueprint(workflows_bp)
    except ImportError:
        pass

    try:
        from core.api.routes.projects import projects_bp
        app.register_blueprint(projects_bp)
    except ImportError:
        pass

    try:
        from core.api.routes.outputs import outputs_bp
        app.register_blueprint(outputs_bp)
    except ImportError:
        pass

    try:
        from core.api.routes.sync import sync_bp
        app.register_blueprint(sync_bp)
    except ImportError:
        pass

    try:
        from core.api.routes.tickets import tickets_bp
        app.register_blueprint(tickets_bp)
    except ImportError:
        pass


def _warmup_vector_store():
    """Pre-load ChromaDB + sentence-transformers in a daemon thread.
    Prevents first memory request from blocking for 30-60s on Windows."""
    import threading
    def _warm():
        try:
            from memory.vector_store import _init
            _init()
        except Exception:
            pass
    threading.Thread(target=_warm, daemon=True, name="vs-warmup").start()


def _start_scheduler(app: Flask):
    try:
        from workflows.scheduler import init_scheduler
        init_scheduler()
        import atexit
        from workflows.scheduler import shutdown_scheduler
        atexit.register(shutdown_scheduler)
    except ImportError:
        pass
    except Exception as e:
        import logging
        logging.getLogger("claudeos.api").warning("Scheduler init failed: %s", e)


def _setup_logging(settings):
    log_dir = Path(settings.LOG_PATH)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    fh = logging.handlers.RotatingFileHandler(
        log_dir / "api.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(fh)
    root.addHandler(ch)
