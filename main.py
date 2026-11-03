import argparse
import os

from waitress import serve

from app import create_app
from config import DATA_PATH


app = create_app()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Relatório web dos times.")
    parser.add_argument("--dev", action="store_true", help="Ativa a recarga automática para desenvolvimento.")
    args = parser.parse_args(argv)

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    development = {"DEBUG": True, "TEMPLATES_AUTO_RELOAD": True, "SEND_FILE_MAX_AGE_DEFAULT": 0}
    application = create_app(development) if args.dev else app
    print(f"Relatório dos times disponível em http://{host}:{port}", flush=True)
    if args.dev:
        application.run(host=host, port=port, debug=True, use_debugger=False,
                        extra_files=[str(DATA_PATH)])
    else:
        serve(application, host=host, port=port, threads=4)


if __name__ == "__main__":
    main()
