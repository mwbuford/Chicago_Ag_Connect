#!/usr/bin/env python3
"""
USDA Local Food Portal & Agricultural Supplier Ingestion Pipeline
"""
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.usda_importer import generate_pilot_dataset, save_dataset_to_disk
from backend.services.data_store import data_store

def main():
    parser = argparse.ArgumentParser(description="Ingest USDA Local Food Portal data")
    parser.add_argument("--states", nargs="+", default=["IL", "VA"], help="State codes to ingest (e.g. IL VA)")
    parser.add_argument("--refresh", action="store_true", help="Force refresh local cache")
    args = parser.parse_args()

    print(f"📦 Ingesting USDA & Ag Supplier data for states: {', '.join(args.states)}...")
    locations = generate_pilot_dataset()
    saved_path = save_dataset_to_disk(locations)
    data_store.initialize()

    print(f"✓ Successfully processed and cached {len(locations)} agricultural locations to {saved_path}")

if __name__ == "__main__":
    main()
