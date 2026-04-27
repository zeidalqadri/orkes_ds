#!/usr/bin/env python3
"""Arbos bot — thin shim. Core at ~/.opencode-bot/core/"""
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.opencode-bot"))
from core.engine import boot

boot(project_dir=Path(__file__).parent)
