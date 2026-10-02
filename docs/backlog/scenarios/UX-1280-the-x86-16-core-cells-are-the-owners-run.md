# UX-1280: the x86 16-core cells of the builders-and-auto default are the owner's run, and it is written down

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1014 | **Found by:** split out of UX-1014 at round 166 (2026-10-02): Ruslan has not run his 16-core Intel host and asked for the steps as their own row | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** owner:an x86 16-core host

**Guard:** none — open, no guard named yet

## Motivation

UX-1014's table has Graviton cells only (16 Cortex-A72, 31 GB). An
x86 host with 16 cores puts the knee in a different place: faster cores
and, with SMT, threads that are not cores. Only the owner's machine
can read those cells, so the run is written down here as steps.

## Decomposition

Input classes: the six `graviton_arms.sh` legs (`pairs`, `cap3`,
`mixed8`, `twogiants`, `widechain`, `memgiant`) on one x86 host with 16
cores. Journey: UX-1014's shape x host x arm table in
`docs/guides/real-project.md`.

## Required Fix

The owner runs the six legs below on the 16-core Intel host and sends
back two things per leg: the `::notice` lines and `arms/builds.txt`.
The session pastes each into UX-1014's table with the host line and
says, per shape, whether the default holds or loses.

Prerequisites (Ubuntu 22.04/24.04, run as a user with `sudo`):

```sh
sudo apt-get install -y bubblewrap lzip gcc make python3-venv time
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0   # 24.04 only
git clone https://github.com/rmorozov/buildstream-graph-analysis && cd buildstream-graph-analysis
python3 -m venv ~/bga-venv && . ~/bga-venv/bin/activate
pip install 'BuildStream==2.8.1' 'buildstream-plugins==2.8.0' && pip install -e .
sudo mkdir -p /nix && sudo chown "$(id -u):$(id -g)" /nix
examples/stage_cpp_toolchain.sh
```

The x86_64 BuildStream wheel bundles `buildbox-casd`, so the Graviton
workflow's "Stage buildbox" step is not needed.

The legs: close other work first, since a busy desktop is noise.

```sh
lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core'; free -g    # the host line
for leg in pairs cap3 mixed8 twogiants widechain memgiant; do
    OUT="$PWD/arms-$leg" examples/11-serial-giant/graviton_arms.sh "$leg" 2>&1 | tee "x86-$leg.log"
done
grep -h '::notice' x86-*.log; cat arms-*/builds.txt
```

Send back the host line, the `grep` output and the `cat` output.
`memgiant` sizes itself to the host's RAM, and an `autocap failed` line
on it is the UX-1134 reading, not a broken run.

## Out of Scope

Graviton cells and the real-project cell, which stay in UX-1014.

## Acceptance Test

UX-1014's table carries an x86 row per shape, each wall with the
owner's log name and host line, and each shape names whether the
default holds.

## Outcome
