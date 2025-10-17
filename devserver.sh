#!/bin/bash
set -e
source .venv/bin/activate
export FLASK_APP=main:create_app()
flask run --host=0.0.0.0 --port=${PORT:-8080}
