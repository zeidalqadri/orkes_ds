#!/usr/bin/env python3
"""Arbos bot — thin shim. Core at ~/.arbos/core/"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.arbos"))
from core.engine import boot

boot(project_dir=Path(__file__).parent)
