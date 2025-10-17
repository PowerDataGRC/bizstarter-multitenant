#!/bin/sh
. .venv/bin/activate
export SECRET_KEY='891a654a27219713534d1e0f170dadd7'
export GOOGLE_CLIENT_ID='YOUR_GOOGLE_CLIENT_ID'
export GOOGLE_CLIENT_SECRET='YOUR_GOOGLE_CLIENT_SECRET'
python -u -m flask --app main run --host=0.0.0.0 -p ${PORT:-5000} --debug
