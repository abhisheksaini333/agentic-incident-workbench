import argparse
import json
import os
import signal
import threading
import uvicorn
from .settings import Settings
from .database import open_store
from .auth import AuthManager
from .api import create_app
from .simulator import Simulator
from .simulator_api import create_simulator_app
from .simulator_client import SimulatorClient
from .runners import runner_for
from .model_client import ModelClient
from .worker import Worker
from .demo import seed_demo


def main():
    parser = argparse.ArgumentParser(description="Incident Workbench components")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, port in [("api", 8085), ("simulator", 8086)]:
        command = sub.add_parser(name)
        command.add_argument("--host", default="127.0.0.1")
        command.add_argument("--port", type=int, default=port)
    worker = sub.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    sub.add_parser("seed")
    args = parser.parse_args()
    if args.command == "simulator":
        simulator = Simulator(os.getenv("SIMULATOR_DB", "data/simulator.db"))
        try:
            app = create_simulator_app(
                simulator,
                os.environ["SIMULATOR_KEY"],
                os.environ["SIMULATOR_ADMIN_KEY"],
            )
            uvicorn.run(app, host=args.host, port=args.port)
        finally:
            simulator.close()
        return
    settings = Settings.from_env()
    store = open_store(settings.database_url)
    tools = SimulatorClient(
        settings.simulator_url,
        settings.simulator_key,
        settings.simulator_admin_key or None,
    )
    auth = AuthManager(store, settings.jwt_secret)
    model = (
        ModelClient(os.environ["MODEL_URL"], os.environ["MODEL_KEY"])
        if os.getenv("MODEL_URL") and os.getenv("MODEL_KEY")
        else None
    )
    try:
        if args.command == "seed":
            print(json.dumps(seed_demo(auth, tools, os.environ["DEMO_PASSWORD"])))
        elif args.command == "api":
            uvicorn.run(
                create_app(store, auth, tools, model_enabled=model is not None),
                host=args.host,
                port=args.port,
            )
        else:
            worker = Worker(
                store, lambda incident: runner_for(store, tools, incident, model)
            )
            if args.once:
                print(json.dumps({"worked": worker.once()}))
            else:
                stop = threading.Event()
                for signum in [signal.SIGINT, signal.SIGTERM]:
                    signal.signal(signum, lambda *_: stop.set())
                worker.run(stop)
    finally:
        tools.close()
        if model is not None:
            model.close()
        store.close()
