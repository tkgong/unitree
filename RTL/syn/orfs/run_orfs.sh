#!/bin/sh
# run_orfs.sh - the full OpenROAD flow (synth, floorplan, place, CTS, route, finish) on one ALU wrapped in pipeline
# registers, nangate45, 1 ns clock, in the openroad/orfs docker image; outputs under RTL/syn/orfs/work/<design>.
#   sh run_orfs.sh alu_lend_32 | alu_mul31          (run from anywhere; the repo must be at ~/unitree)
set -e
D=$1; REPO=$HOME/unitree
mkdir -p $REPO/RTL/syn/orfs/work/$D
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$REPO:/work" openroad/orfs:latest bash -c \
  "cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/work/RTL/syn/orfs/$D/config.mk WORK_HOME=/work/RTL/syn/orfs/work/$D finish" \
  > $REPO/RTL/syn/orfs/work/$D/make.log 2>&1
tail -3 $REPO/RTL/syn/orfs/work/$D/make.log
