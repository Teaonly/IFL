import os
import sys
import json
import uuid
import signal

from abc import ABC
import yaml
import argparse
from dotenv import load_dotenv

from IFL.provider.modules_factory import create_provider
from IFL.utils import ( apply_patch, readfile_with_linenumber, content_from_input,
                           print_tag, print_line, print_tag_end, print_warning,
                           confirm_from_input, display_search_replace )

def signal_handler(sig, frame):
    print("\nInterrupt signal received, program exiting...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Load environment variables
        load_dotenv()

    except KeyboardInterrupt:
        print("\nProgram interrupted by user, exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Program execution error: {e}")
        sys.exit(1)
