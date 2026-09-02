import unittest
import sys
from unittest.mock import MagicMock, patch

# Mock heavy/missing dependencies
sys.modules["loguru"] = MagicMock()
sys.modules["ddgs"] = MagicMock()

from core.utils.web_search import WebSearch, perform_web_search

class TestWebSearch(unittest.TestCase):
    def setUp(self):
        self.config = {
            "plugins": {
                "web_search": {
                    "count": 2
                }
            }
        }
        self.searcher = WebSearch(self.config)

    @patch("core.utils.web_search.DDGS")
    def test_search_formatting(self, mock_ddgs_class):
        """Test that search results are correctly formatted with context tags."""
        # Mocking the context manager and the generator
        mock_ddgs_instance = mock_ddgs_class.return_value.__enter__.return_value
        mock_ddgs_instance.text.return_value = [
            {"title": "Result 1", "href": "http://example.com/1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "http://example.com/2", "body": "Snippet 2"}
        ]

        result = self.searcher.search("test query")

        # Verify context tags
        self.assertIn("<web_search_context>", result)
        self.assertIn("</web_search_context>", result)
        
        # Verify result content
        self.assertIn("Title: Result 1", result)
        self.assertIn("URL: http://example.com/1", result)
        self.assertIn("Snippet: Snippet 1", result)
        self.assertIn("---", result) # Separator

    @patch("core.utils.web_search.DDGS")
    def test_search_no_results(self, mock_ddgs_class):
        """Test handling of empty search results."""
        mock_ddgs_instance = mock_ddgs_class.return_value.__enter__.return_value
        mock_ddgs_instance.text.return_value = []

        result = self.searcher.search("nothing found")

        self.assertEqual(result, "No search results found via DuckDuckGo.")

    @patch("core.utils.web_search.DDGS")
    def test_search_exception(self, mock_ddgs_class):
        """Test handling of exceptions during search."""
        mock_ddgs_instance = mock_ddgs_class.return_value.__enter__.return_value
        mock_ddgs_instance.text.side_effect = Exception("Connection Timeout")

        result = self.searcher.search("fail query")

        self.assertIn("Search failed (DuckDuckGo): Connection Timeout", result)

    @patch("core.utils.web_search.WebSearch")
    def test_perform_web_search_helper(self, mock_websearch_class):
        """Verify the helper function initiates the search correctly."""
        mock_instance = mock_websearch_class.return_value
        mock_instance.search.return_value = "Mocked Result"

        result = perform_web_search("hello", self.config)

        mock_websearch_class.assert_called_once_with(self.config)
        mock_instance.search.assert_called_once_with("hello")
        self.assertEqual(result, "Mocked Result")

if __name__ == "__main__":
    unittest.main()
