#!/bin/sh
. .venv/bin/activate
python -u -m flask --app main run --host=0.0.0.0 -p ${PORT:-5000} --debug