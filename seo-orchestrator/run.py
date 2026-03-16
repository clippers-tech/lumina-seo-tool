#!/usr/bin/env python3
"""
SEO Orchestrator — Runner Script
Usage:
    python run.py                           # Uses env vars
    python run.py --api-key YOUR_KEY        # Override API key
    python run.py --config path/to/sites.yaml
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import main

if __name__ == "__main__":
    main()
