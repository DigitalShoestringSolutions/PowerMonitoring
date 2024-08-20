import aiohttp
import logging
import aiohttp_jinja2
import json
import upload_stats
import base64

routes = aiohttp.web.RouteTableDef()

logger = logging.getLogger("stats_collector.ui")

exchange_token_key = aiohttp.web.AppKey("exchange_token", str)
# exchange_token_body_key = aiohttp.web.AppKey("exchange_token_body", str)

LINKED_COMPANY_FILE = "./data/linked_company"


def decode_jwt_payload(jwt):
    if isinstance(jwt, str):
        jwt = bytes(jwt, "utf-8")

    b64_header, b64_payload, b64_jwt_signature = jwt.split(b".")
    return json.loads(
        base64.urlsafe_b64decode(b64_payload + b"==")
    )  # add extra == padding as they are stripped in generation


@routes.get("/")
@aiohttp_jinja2.template("dashboard.jinja2")
async def home_page(request):
    return {"text": "hello in template"}


@routes.get("/logs")
@aiohttp_jinja2.template("logs.jinja2")
async def home_page(request):
    return {"text": "hello in template"}


@routes.get("/report")
@aiohttp_jinja2.template("report_issue.jinja2")
async def home_page(request):
    return {"text": "hello in template"}


@routes.get("/stats")
@aiohttp_jinja2.template("transmitted_stats.jinja2")
async def home_page(request):
    return {"text": "hello in template"}


@routes.get("/link")
@aiohttp_jinja2.template("link.jinja2")
async def link_page(request):
    output = {"status": "new"}

    try:
        payload = decode_jwt_payload(request.app[upload_stats.id_token_key])
        output["linked_to"] = {"org":payload["org"],"dep":payload["dep"]}
        output["status"] = "linked"
    except:
        # ignore if failed to access
        pass

    return output


@routes.post("/link")
@aiohttp_jinja2.template("link.jinja2")
async def link_page_post(request):
    linked_to = None
    
    try:
        payload = decode_jwt_payload(request.app[upload_stats.id_token_key])
        linked_to = {"org": payload["org"], "dep": payload["dep"]}
    except:
        # ignore if failed to access
        pass

    data = await request.post()
    link_code = data["link_code"]
    try:
        id_token = request.app[upload_stats.id_token_key]
    except KeyError:
        return {
            "linked_to": linked_to,
            "link_code": link_code,
            "error": "Error: Couldn't access anonymous registration for this deployment. If you've just started this solution for the first time, try again in a few minutes.",
            "status": "error",
        }

    body = {"code": link_code, "id_token": id_token}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://platform.digitalshoestring.net/api/deployments/link-flow/associate",
            ssl=False,
            json=body,
        ) as resp:
            if resp.status == 200:
                resp_body = await resp.json()
                try:
                    exchange_token = resp_body["exchange_token"]
                    request.app[exchange_token_key] = exchange_token
                    exchange_token_body = decode_jwt_payload(exchange_token)
                    # request.app[exchange_token_body_key] = exchange_token_body

                    return {
                        "conf_code": resp_body["confirm_code"],
                        "org_name": exchange_token_body["org"],
                        "deployment_name": exchange_token_body["dep"],
                        "status": "confirm",
                    }
                except ValueError:
                    return {
                        "linked_to": linked_to,
                        "link_code": link_code,
                        "error": "Error: server response did not have the expected fields",
                        "status": "error",
                    }
            else:
                resp_body = await resp.json()
                return {
                    "linked_to": linked_to,
                    "link_code": link_code,
                    "error": resp_body.get(
                        "detail",
                        f"Error: Got status code {resp.status} -- {json.dumps(resp_body)}.",
                    ),
                    "status": "error",
                }


@routes.post("/link/exchange")
async def exchange_ajax(request):
    exchange_token = request.app[exchange_token_key]
    body = {"exchange_token": exchange_token}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://platform.digitalshoestring.net/api/deployments/link-flow/exchange",
            ssl=False,
            json=body,
        ) as resp:
            if resp.status == 200:
                resp_body = await resp.json()
                new_id_token = resp_body["new_id_token"]
                await upload_stats.update_id_token(request.app,new_id_token)
                return aiohttp.web.Response(status=200)
            else:
                resp_body = await resp.json()
                return aiohttp.web.json_response(resp_body, status=resp.status)


@routes.post("/link/cancel")
@aiohttp_jinja2.template("link_cancel.jinja2")
async def cancel_link_page(request):
    exchange_token = request.app[exchange_token_key]
    body = {"exchange_token": exchange_token}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://platform.digitalshoestring.net/api/deployments/link-flow/cancel-exchange",
            ssl=False,
            json=body,
        ) as resp:
            if resp.status == 200:
                return {"result":"ok"}
            else:
                resp_body = await resp.json()
                return {
                    "result": "error",
                    "error": resp_body.get(
                        "detail",
                        f"Error: Got status code {resp.status} -- {json.dumps(resp_body)}.",
                    ),
                }
