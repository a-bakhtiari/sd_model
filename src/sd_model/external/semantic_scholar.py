"""Semantic Scholar API client for paper verification and discovery.

API Documentation: https://api.semanticscholar.org/api-docs/
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests


@dataclass
class Paper:
    """Represents a paper from Semantic Scholar."""
    paper_id: str
    title: str
    authors: List[str]
    year: Optional[int]
    citation_count: int
    url: str
    abstract: Optional[str] = None
    venue: Optional[str] = None
    fields_of_study: List[str] = None


class SemanticScholarClient:
    """Client for Semantic Scholar Academic Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[Path] = None):
        """Initialize Semantic Scholar client.

        Args:
            api_key: S2 API key (defaults to SEMANTIC_SCHOLAR_API_KEY env var)
            cache_dir: Directory for caching responses (defaults to .cache/semantic_scholar)
        """
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.cache_dir = cache_dir or Path(".cache/semantic_scholar")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._last_request_time = 0
        self._min_request_interval = 1.0  # Respect rate limits (1 req/sec without key, 10/sec with key)
        if self.api_key:
            self._min_request_interval = 0.1  # 10 requests per second

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _retry_with_backoff(self, func, max_retries: int = 3):
        """Retry a function with exponential backoff on rate limit errors.

        Args:
            func: Function to retry (should return requests.Response)
            max_retries: Maximum number of retry attempts

        Returns:
            Response object from successful request

        Raises:
            Exception if all retries fail
        """
        for attempt in range(max_retries + 1):
            try:
                response = func()

                # Handle 429 specifically
                if response.status_code == 429:
                    if attempt < max_retries:
                        # Exponential backoff: 2, 4, 8 seconds
                        wait_time = 2 ** (attempt + 1)
                        print(f"Rate limit hit (429), waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        response.raise_for_status()  # Raise on final attempt

                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as e:
                if attempt < max_retries and (e.response.status_code == 429 or e.response.status_code >= 500):
                    wait_time = 2 ** (attempt + 1)
                    print(f"HTTP error {e.response.status_code}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                raise

        raise Exception("Max retries exceeded")

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a given key."""
        # Use hash of key to avoid filesystem issues
        import hashlib
        hashed = hashlib.md5(cache_key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def _read_cache(self, cache_key: str, max_age_days: int = 30) -> Optional[Dict]:
        """Read from cache if not expired."""
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            return None

        # Check age
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(days=max_age_days):
            return None

        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_cache(self, cache_key: str, data: Dict):
        """Write to cache."""
        cache_path = self._get_cache_path(cache_key)
        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def verify_paper(
        self,
        title: str,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None
    ) -> Optional[Paper]:
        """Verify a paper exists in Semantic Scholar and return metadata.

        Args:
            title: Paper title
            authors: List of author names (optional, helps matching)
            year: Publication year (optional, helps matching)

        Returns:
            Paper object if found and matched, None otherwise
        """
        cache_key = f"verify:{title}:{authors}:{year}"
        cached = self._read_cache(cache_key)
        if cached:
            return Paper(**cached) if cached.get("found") else None

        # Search by title
        query = title
        if year:
            query += f" {year}"

        results = self.search_papers(query, limit=5)

        # Try to match by title similarity and year
        for paper in results:
            title_match = self._fuzzy_match(title.lower(), paper.title.lower())
            year_match = (year is None or paper.year is None or abs(paper.year - year) <= 1)

            if title_match > 0.8 and year_match:
                # Found a match
                result = {
                    "found": True,
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "citation_count": paper.citation_count,
                    "url": paper.url,
                    "abstract": paper.abstract,
                    "venue": paper.venue,
                    "fields_of_study": paper.fields_of_study or [],
                }
                self._write_cache(cache_key, result)
                return paper

        # No match found
        self._write_cache(cache_key, {"found": False})
        return None

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Simple fuzzy string matching (Jaccard similarity on words)."""
        words1 = set(s1.split())
        words2 = set(s2.split())
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        fields: Optional[List[str]] = None
    ) -> List[Paper]:
        """Search for papers matching a query.

        Args:
            query: Search query string
            limit: Maximum number of results
            fields: Fields to return (defaults to basic set)

        Returns:
            List of Paper objects
        """
        cache_key = f"search:{query}:{limit}"
        cached = self._read_cache(cache_key)
        if cached:
            return [Paper(**p) for p in cached]

        if fields is None:
            fields = ["title", "authors", "year", "citationCount", "abstract", "venue", "fieldsOfStudy"]

        self._rate_limit()

        try:
            # Use retry wrapper for resilience against rate limits
            response = self._retry_with_backoff(
                lambda: requests.get(
                    f"{self.BASE_URL}/paper/search",
                    headers=self._get_headers(),
                    params={
                        "query": query,
                        "limit": limit,
                        "fields": ",".join(fields),
                    },
                    timeout=30,
                )
            )
            data = response.json()

            papers = []
            for item in data.get("data", []):
                paper = self._parse_paper(item)
                if paper:
                    papers.append(paper)

            # Cache results
            self._write_cache(cache_key, [self._paper_to_dict(p) for p in papers])
            return papers

        except Exception as e:
            print(f"Semantic Scholar search error: {e}")
            return []

    def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """Get detailed information about a specific paper.

        Args:
            paper_id: Semantic Scholar paper ID

        Returns:
            Paper object with detailed information
        """
        cache_key = f"paper:{paper_id}"
        cached = self._read_cache(cache_key)
        if cached:
            return Paper(**cached)

        self._rate_limit()

        try:
            # Use retry wrapper for resilience against rate limits
            response = self._retry_with_backoff(
                lambda: requests.get(
                    f"{self.BASE_URL}/paper/{paper_id}",
                    headers=self._get_headers(),
                    params={
                        "fields": "title,authors,year,citationCount,abstract,venue,fieldsOfStudy,externalIds"
                    },
                    timeout=30,
                )
            )
            data = response.json()

            paper = self._parse_paper(data)
            if paper:
                self._write_cache(cache_key, self._paper_to_dict(paper))
            return paper

        except Exception as e:
            print(f"Semantic Scholar paper fetch error: {e}")
            return None

    def get_recommendations(self, paper_id: str, limit: int = 10) -> List[Paper]:
        """Get paper recommendations based on a paper.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of recommendations

        Returns:
            List of recommended papers
        """
        cache_key = f"recommendations:{paper_id}:{limit}"
        cached = self._read_cache(cache_key)
        if cached:
            return [Paper(**p) for p in cached]

        self._rate_limit()

        try:
            # Use retry wrapper for resilience against rate limits
            response = self._retry_with_backoff(
                lambda: requests.get(
                    f"{self.BASE_URL}/paper/{paper_id}/recommendations",
                    headers=self._get_headers(),
                    params={
                        "limit": limit,
                        "fields": "title,authors,year,citationCount,abstract"
                    },
                    timeout=30,
                )
            )
            data = response.json()

            papers = []
            for item in data.get("recommendedPapers", []):
                paper = self._parse_paper(item)
                if paper:
                    papers.append(paper)

            self._write_cache(cache_key, [self._paper_to_dict(p) for p in papers])
            return papers

        except Exception as e:
            print(f"Semantic Scholar recommendations error: {e}")
            return []

    def _parse_paper(self, data: Dict) -> Optional[Paper]:
        """Parse paper data from API response."""
        try:
            paper_id = data.get("paperId")
            if not paper_id:
                return None

            authors = [
                author.get("name", "Unknown")
                for author in data.get("authors", [])
            ]

            return Paper(
                paper_id=paper_id,
                title=data.get("title", "Untitled"),
                authors=authors,
                year=data.get("year"),
                citation_count=data.get("citationCount", 0),
                url=f"https://www.semanticscholar.org/paper/{paper_id}",
                abstract=data.get("abstract"),
                venue=data.get("venue"),
                fields_of_study=data.get("fieldsOfStudy"),
            )
        except Exception:
            return None

    def _paper_to_dict(self, paper: Paper) -> Dict:
        """Convert Paper to dict for caching."""
        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "citation_count": paper.citation_count,
            "url": paper.url,
            "abstract": paper.abstract,
            "venue": paper.venue,
            "fields_of_study": paper.fields_of_study,
        }
