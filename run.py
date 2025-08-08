#!/usr/bin/env python3
"""Runner script for the interview application."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interviewer.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())