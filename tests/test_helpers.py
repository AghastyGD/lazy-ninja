import pytest
from lazy_ninja.helpers import to_kebab_case

@pytest.mark.parametrize("input_str,expected", [
    ("PostComments", "post-comments"),
    ("UserProfile", "user-profile"),
    ("APIKey", "api-key"),
    ("snake_case", "snake-case"),
    ("SCREAMING_SNAKE_CASE", "screaming-snake-case"),
    ("camelCase", "camel-case"),
    ("PascalCase", "pascal-case"),
    ("simpleword", "simpleword"),
    ("TwoWords", "two-words"),
    ("ManyManyWords", "many-many-words"),
    ("ABC", "abc"),
    ("XMLHttpRequest", "xml-http-request"),
])
def test_to_kebab_case(input_str, expected):
    """Test to_kebab_case function with various input formats"""
    result = to_kebab_case(input_str)
    print(f"Input: {input_str}, Expected: {expected}, Got: {result}")  # Debug print
    assert result == expected