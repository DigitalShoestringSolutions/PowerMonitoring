from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status, Query

import config

app = FastAPI()


@lru_cache
def get_settings():
    return config.get_settings()


@app.get("/{full_path:path}")
async def catch_get(
        request: Request,
        response: Response,
        full_path: str,
        settings: Annotated[dict, Depends(get_settings)]
):
    return await handle_catch(request, response, full_path, "get", settings)


@app.post("/{full_path:path}")
async def catch_post(
        request: Request,
        response: Response,
        full_path: str,
        settings: Annotated[dict, Depends(get_settings)]
):
    return await handle_catch(request, response, full_path, "post", settings)


async def handle_catch(
        request: Request,
        response: Response,
        path: str,
        method: str,
        settings):

    clean_path = path.strip('/').lstrip('/')

    for route_name, route_entry in settings['routes'].items():
        if route_entry["path"].strip('/').lstrip('/') == clean_path:
            return await call_route(route_name, route_entry,request.query_params)

    response.status_code = status.HTTP_404_NOT_FOUND
    return {"type": "error", "message": "no route defined", "details": {"method": method, "path": path}}


async def call_route(name, entry,args={}):
    print(args)
