from functools import lru_cache
import logging
import traceback
import importlib
import asyncio

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import config

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)


@lru_cache
def get_settings():
    return config.get_settings()


async def catch_request(request):
    data, status = await handle_catch(request, request.path_params['full_path'], request.method, request.app.state.settings)
    return JSONResponse(data, status_code=status)


routes = [
    Route("/{full_path:path}", endpoint=catch_request,
          methods=['GET', 'POST']),
]

app = Starlette(routes=routes)
app.state.settings = get_settings()


async def handle_catch(
    request,
    path,
    method,
    settings
):

    print(f"{path},{method}")
    clean_path = path.strip('/').lstrip('/')

    for route_name, route_entry in settings['routes'].items():
        if route_entry["path"].strip('/').lstrip('/') == clean_path and method.lower() in (m.lower() for m in route_entry["methods"]):
            return await call_route(route_name, route_entry, request.query_params, settings['config'])

    return {"type": "error", "message": "no route defined", "details": {"method": method, "path": path}}, 404


async def call_route(name, entry, query_params, global_config):
    module_name = entry["module"]
    function_name = entry["function"]
    full_module_name = f"analysis_modules.{module_name}"
    entry_config = entry.get("config", {})

    try:
        module = importlib.import_module(full_module_name)
        logger.debug(f"Imported {module_name}")
        function = getattr(module, function_name, None)
        if function:
            function_response = function({"params": query_params, "config": entry_config, "global_config": global_config})

            if asyncio.iscoroutine(function_response):
                result = await function_response
            else:
                result = function_response

            return result, 200
        else:
            return {"type": "error", "message": "couldn't find function"}, 500
    except ModuleNotFoundError:
        logger.error(
            f"Unable to import module {module_name}. Service Module may not function as intended")
        logger.error(traceback.format_exc())
        return {"type": "error", "message": "unable to import module"}, 500
    except:
        logger.error(traceback.format_exc())
        return {"type": "error", "message": "Something went wrong"}, 500
