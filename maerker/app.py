#!/usr/bin/env python3
# print("in app.py", __name__, __package__)
from pathlib import Path
import importlib

from flask import Flask


# from lib import config, database

# from .lib import config, database
from .lib import config
from .lib import database
from .lib import filters
# from . import lib
# from knoerden import lib
# from lib import config
# from knoerden.lib import config
# import knoerden.lib.database as database
# from . lib import config, database

def create_app(conf=None):
    if conf is None:
        conf = config.init(config)
    app = Flask(__name__)
    app.config.from_mapping(conf)
    if app.config["DEBUG"]:
            app.jinja_env.auto_reload = True
    app.teardown_appcontext(database.close_db)
    register_blueprints(app)
    filters.init_filters(app)
    return app

def register_blueprints(app):
    dir = Path(__file__).parent/"blueprints"
    for path in dir.glob("*.py"):
        name = path.name[:-3] # Remove .py
        if name.isidentifier():
            name = ".blueprints." + name
            module = importlib.import_module(name, package="knoerden")
            if hasattr(module, "blueprint"):
                app.register_blueprint(module.blueprint)

def main():
    conf = config.init(config)
    app = create_app(conf)
    app.run("0.0.0.0")

app = create_app()

if __name__ == "__main__":
    main()
