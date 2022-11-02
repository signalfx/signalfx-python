#!/usr/bin/env bash
set +ex

project_dir="$(dirname "${BASH_SOURCE[0]}")/.."
cd $project_dir
docker build --build-arg PROTOC_VERSION=3.5.1 -f scripts/DOCKERFILE.genproto -t signalfx-python-genproto .
docker run signalfx-python-genproto cat /usr/src/signalfx-python/signal_fx_protocol_buffers_pb2.py > signalfx/generated_protocol_buffers/signal_fx_protocol_buffers_pb2.py
