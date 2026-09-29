#!/bin/bash
# UX-1114: a fresh container starts shallow and without the locked
# dependencies. The decision lives in session_start.py; this stays the
# one file settings.json names. Never fails the session.
python3 "$(dirname "${BASH_SOURCE[0]}")/session_start.py" || true
exit 0
