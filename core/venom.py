import importlib
import logging
import os
import sys
from datetime import datetime

import uvicorn
from fastapi import FastAPI, APIRouter, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import PackageLoader, Environment, ChoiceLoader
from pydantic import ValidationError
from sqlalchemy.exc import DatabaseError

from core.api.tests.unittests import TestRunner
from core.configurations import Configuration
from core.database import Database
from core.logs import Logger
from core.messages import Messages

API_PACKAGES = [os.path.join("core", "api"), "api"]

logger = logging.getLogger(__name__)
app = None
cfg = None
database = None
templates = None
messages = None
server_mode = None


def run():
    # load application configuration
    global cfg
    cfg = Configuration(filename=sys.argv[1] if len(sys.argv) > 1 else None)

    global server_mode
    server_mode = cfg["core.server.mode"]
    if server_mode not in ["dev", "tests", "prod"]:
        raise SystemExit(f"Invalid server mode {server_mode}. Supported modes: [dev, tests, prod]")

    # load application messages
    global messages
    messages = Messages()

    # configure global logger
    Logger().configure()

    # load templates
    global templates
    loaders = get_templates_packages_loaders(packages=API_PACKAGES)
    templates = Environment(loader=ChoiceLoader(loaders), keep_trailing_newline=True)

    # initialize database connection
    global database
    database = Database(
        url=cfg["core.database.url"],
        pool_size=cfg["core.database.pool_size"],
        max_overflow=cfg["core.database.max_overflow"]
    )

    if cfg["core.database.apply_migrations"]:
        logger.info("Applying database migrations...")
        database.apply_migrations()

    if server_mode.lower() == "tests":
        global app
        app = create_app(disable_logging=True)

        # enable application logger
        logger.disabled = False

        # override oauth dependencies when running tests cases
        from core.api.oauth2.schemes import oauth2
        app.dependency_overrides[oauth2] = lambda: True

        # initiate TestRunner class
        test_runner = TestRunner()

        logger.info("Truncating database tables...")
        database.truncate_tables()

        logger.info("Starting tests...")
        test_runner.run()
        return

    # run application via uvicorn server
    uvicorn.run(
        app="core.venom:create_app",
        host=cfg["core.server.host"],
        port=cfg["core.server.port"],
        factory=True,
        log_level=logging.WARNING
    )


def create_app(disable_logging=False):
    # initialize FastAPI application
    global app
    app = FastAPI()

    # update application logger disabled state
    logger.disabled = disable_logging

    # mount APIRouters
    mount_api_routers(asgi_app=app, packages=API_PACKAGES)

    allow_origins = getattr(cfg, "core.server.cors.origins")
    allow_credentials = getattr(cfg, "core.server.cors.allow_credentials")
    allow_methods = getattr(cfg, "core.server.cors.allow_methods")
    allow_headers = getattr(cfg, "core.server.cors.allow_headers")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers
    )

    @app.middleware("http")
    async def handle_request(request: Request, call_next):
        return await handle_http_middleware(request=request, call_next=call_next)

    @app.exception_handler(ValidationError)
    async def handle_validation_exception(request: Request, exc: ValidationError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=jsonable_encoder(exc.errors()))

    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    host = getattr(cfg, "core.server.host")
    port = getattr(cfg, "core.server.port")
    logger.info(f"Server listening on http://{host}:{port}")
    return app


def mount_api_routers(asgi_app, packages):
    for package in packages:
        for root, dirs, files in os.walk(package):
            for filename in files:
                if filename != "api.py":
                    continue

                api_package = root.replace(os.path.sep, ".").strip(".")
                api_file = api_package + "." + filename.rstrip(".py")

                # import api router module
                module = importlib.import_module(name=api_file, package=api_package)
                router = getattr(module, "app", None)

                if isinstance(router, APIRouter):
                    logger.info(f"Mounting API router package \"{api_package}\"...")
                    asgi_app.include_router(router)
    return asgi_app


def get_templates_packages_loaders(packages):
    loaders = []
    for package in packages:
        for root, dirs, files in os.walk(package):
            for directory in dirs:
                if directory == "templates" and directory in dirs:
                    loader = PackageLoader(root.replace(os.path.sep, ".").strip("."), "templates")
                    loaders.append(loader)
    return loaders


async def handle_http_middleware(request, call_next):
    start_request_on = datetime.now()

    if hasattr(database, "Session"):
        request.state.session = database.Session()

    response = await call_next(request)

    try:
        try:
            # at the end always commit
            request.state.session.commit()
        except DatabaseError as e:
            logger.exception(e)
            request.state.session.rollback()
    finally:
        request.state.session.close()
        if hasattr(database, "Session"):
            database.Session.remove()

    end_request_on = datetime.now()
    request_time = round((end_request_on - start_request_on).total_seconds() * 1000)
    remote_addr = request.url.hostname
    method = request.method
    path = request.url.path
    http_version = request.scope.get("http_version")
    server_protocol = f"{request.url.scheme.upper()}/{http_version}"
    status_code = response.status_code

    # log request duration
    logger.info(f"{remote_addr} [{server_protocol}] \"{method} {path}\" {status_code} ({request_time} ms)")

    return response
