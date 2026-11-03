import argparse
import os

from waitress import serve

from app import create_app
from config import DATA_PATH

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "5000"
WAITRESS_THREADS = 4
DEVELOPMENT_CONFIG = {
    "DEBUG": True,
    "TEMPLATES_AUTO_RELOAD": True,
    "SEND_FILE_MAX_AGE_DEFAULT": 0,
}

app = create_app()


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="Relatório web dos times.")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Ativa a recarga automática para desenvolvimento.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse_arguments(argv)

    host = os.environ.get("HOST", DEFAULT_HOST)
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print(f"Relatório dos times disponível em http://{host}:{port}", flush=True)

    if arguments.dev:
        development_app = create_app(DEVELOPMENT_CONFIG)
        development_app.run(
            host=host,
            port=port,
            debug=True,
            use_debugger=False,
            extra_files=[str(DATA_PATH)],
        )
    else:
        serve(app, host=host, port=port, threads=WAITRESS_THREADS)


if __name__ == "__main__":
    main()
