from datetime import date

from app.browser import parse_explicit_youtube_request, _validate_query


def test_latest_song_command_becomes_year_scoped_youtube_search():
    query = parse_explicit_youtube_request(
        "Open YouTube, search for the latest song and play that"
    )
    assert query == f"latest song official music video {date.today().year}"


def test_specific_song_command_extracts_search_terms():
    assert parse_explicit_youtube_request(
        "Play Kesariya on YouTube"
    ) == "Kesariya"


def test_unrelated_youtube_question_does_not_execute_browser():
    assert parse_explicit_youtube_request("Tell me about YouTube") is None


def test_non_youtube_play_request_does_not_execute_browser():
    assert parse_explicit_youtube_request("Play music") is None


def test_query_validation_rejects_urls_and_invalid_values():
    assert _validate_query(" latest song  ") == "latest song"
    for query in ("", "  ", "x" * 161, None, "song\nmalicious", "https://example.com"):
        try:
            _validate_query(query)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected query rejection for {query!r}")
