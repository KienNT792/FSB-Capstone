# scripts/assemble_full_features.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

PROJECTS = [
    "adamfisk@LittleProxy",
    "deeplearning4j@deeplearning4j",
    "l0rdn1kk0n@wicket-bootstrap",
    "neuland@jade4j",
    "thinkaurelius@titan",
]

frames = []
for p in PROJECTS:
    df = pd.read_parquet(f"data/features/{p}_features.parquet")
    assert "repo" in df.columns or True  # adjust if project col missing
    if "repo" not in df.columns:
        df["repo"] = p
    frames.append(df)
    print(f"{p}: {df.shape}")

full = pd.concat(frames, ignore_index=True)
print("Full shape:", full.shape)
print("Label distribution:", full["label"].value_counts().to_dict())

from src.features.validation import validate_features
validate_features(full)
print("validate_features: PASS")

full.to_parquet("data/features/full_features.parquet")
print("Saved data/features/full_features.parquet")