#!/bin/bash

foms_dir="/home/appuser/foms"
js_dir="src/static/js"
htmx_file="htmx.min.js"
htmx_cdn_url="https://cdn.jsdelivr.net/npm/htmx.org@4.0.0/dist/htmx.min.js"

cd $foms_dir

if [[ ! -d "$js_dir" ]]; then
    mkdir -p $js_dir
fi

if [[ ! -f "${js_dir}/${htmx_file}" ]]; then
    curl -L $htmx_cdn_url -o ${js_dir}/$htmx_file
fi

uv sync
