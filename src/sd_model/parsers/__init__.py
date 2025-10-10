"""MDL Parsers - Extract structure from Vensim MDL files.

This module provides deterministic Python-based parsing of MDL files,
replacing the LLM-based extraction with faster and more accurate parsing.
"""

from .python_parser import extract_variables, extract_connections

__all__ = ["extract_variables", "extract_connections"]
