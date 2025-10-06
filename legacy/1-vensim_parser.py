"""
Thin wrapper to maintain backward compatibility.
Delegates to the modular pipeline implementation.
"""

from pathlib import Path
from sd_model.pipeline.parse import parse_mdl


def main():
    mdl_path = Path("/Users/alibakhtiari/Desktop/Thesis/SD_model/untitled.mdl")
    result = parse_mdl(mdl_path, Path("connections.json"), api_key=None, model="deepseek-chat")
    print(f"Saved {len(result.get('connections', []))} connections to connections.json")


if __name__ == "__main__":
    main()
