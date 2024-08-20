from aiohttp import web
import aiohttp_jinja2
import jinja2
import logging

import tasks
import database

import pages.api
import pages.ui


app = web.Application()
# set up templating
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("./templates"))
# Set log level
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("aiosqlite").setLevel(logging.INFO)
logging.getLogger("aiohttp").setLevel(logging.INFO)
# Routes
app.add_routes(pages.api.routes)
app.add_routes(pages.ui.routes)
# Background Tasks
app.cleanup_ctx.append(database.init)
app.cleanup_ctx.append(tasks.create_background_task)

web.run_app(app, port=80)
