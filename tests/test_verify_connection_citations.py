#!/usr/bin/env python3
"""
Verify connection citations using Semantic Scholar API and LLM validation.

This is a standalone test script that uses the pipeline verification module.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from sd_model.external.semantic_scholar import SemanticScholarClient
from sd_model.llm.client import LLMClient
from sd_model.pipeline.citation_verification import verify_llm_generated_citations


def main():
    # Paths
    artifacts_dir = repo_root / "projects" / "oss_model" / "artifacts"
    citations_path = artifacts_dir / "connection_citations.json"
    output_path = repo_root / "tests" / "connection_citations_verified.json"
    debug_path = repo_root / "tests" / "connection_citations_verification_debug.txt"

    # Initialize clients
    print("Initializing Semantic Scholar client...")
    s2_client = SemanticScholarClient()

    print("Initializing LLM client...")
    llm_client = LLMClient()

    if not llm_client.enabled:
        print("ERROR: LLM client not enabled. Check your .env file for DEEPSEEK_API_KEY")
        sys.exit(1)

    print()

    # Verify citations
    verify_llm_generated_citations(
        citations_path=citations_path,
        output_path=output_path,
        s2_client=s2_client,
        llm_client=llm_client,
        debug_path=debug_path
    )


if __name__ == "__main__":
    main()
