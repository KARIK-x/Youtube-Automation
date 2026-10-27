"""Config loading."""
import os, yaml
from pathlib import Path
from dotenv import load_dotenv

def load_config(path="config.yaml"):
    load_dotenv(Path(path).parent / ".env")
    with open(path) as f:
        return yaml.safe_load(f)

def project_root():
    return Path(__file__).resolve().parents[3]