"""Web search tool for the interview agent."""

import warnings
from typing import List

from pydantic import BaseModel

# Suppress all warnings from external libraries during import and execution
warnings.filterwarnings("ignore")

# Import DuckDuckGo search with warnings suppressed
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from ddgs import DDGS


class SearchResult(BaseModel):
    """A single search result."""

    title: str
    snippet: str
    url: str


class SearchResults(BaseModel):
    """Collection of search results."""

    query: str
    results: List[SearchResult]
    total_results: int


def search_web(query: str, max_results: int = 5) -> SearchResults:
    """
    Search the web using DuckDuckGo and return structured results.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        SearchResults object with query and results
    """
    # Suppress all warnings during search operation
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        try:
            # Use DuckDuckGo search library
            ddgs = DDGS()
            search_results = ddgs.text(query, max_results=max_results)

            results = []
            for result in search_results:
                # Extract information from DuckDuckGo result
                title = result.get("title", "No Title")
                snippet = result.get("body", "No description available")
                url = result.get("href", "")

                if title and snippet:
                    results.append(SearchResult(title=title, snippet=snippet, url=url))

            return SearchResults(
                query=query, results=results, total_results=len(results)
            )

        except Exception as e:
            # Return empty results on error, don't crash the agent
            return SearchResults(query=query, results=[], total_results=0)


def search_interview_topics(topic: str, interview_type: str = "") -> SearchResults:
    """
    Search for interview-related information on a specific topic.

    Args:
        topic: The topic to search for
        interview_type: Optional interview type context (technical, behavioral, etc.)

    Returns:
        SearchResults object with relevant interview information
    """
    # Craft search query for interview context
    if interview_type:
        query = f"{topic} interview questions {interview_type} data science"
    else:
        query = f"{topic} interview questions data science"

    return search_web(query, max_results=3)


def search_current_trends(technology_or_field: str) -> SearchResults:
    """
    Search for current trends and developments in a technology or field.

    Args:
        technology_or_field: The technology or field to research

    Returns:
        SearchResults object with current trend information
    """
    query = f"{technology_or_field} trends 2024 2025 latest developments"
    return search_web(query, max_results=4)


def search_company_info(company_name: str) -> SearchResults:
    """
    Search for recent information about a company.

    Args:
        company_name: Name of the company to research

    Returns:
        SearchResults object with company information
    """
    # Try multiple targeted queries to get comprehensive company information
    queries = [
        f'"{company_name}" company information overview',
        f'"{company_name}" business model products services',
        f'"{company_name}" company history background',
        f'"{company_name}" industry sector market',
        f'"{company_name}" company size employees location',
        f'"{company_name}" recent news developments',
        f'"{company_name}" acquisition funding investment',
    ]

    all_results = []
    for query in queries:
        try:
            results = search_web(query, max_results=2)
            all_results.extend(results.results)
        except Exception:
            continue

    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        if result.url not in seen_urls:
            seen_urls.add(result.url)
            unique_results.append(result)

    return SearchResults(
        query=f"Company information for {company_name}",
        results=unique_results[:5],  # Limit to 5 best results
        total_results=len(unique_results),
    )
