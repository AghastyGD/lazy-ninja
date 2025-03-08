import re

def to_kebab_case(name: str) -> str:
    """
    Convert a string from CamelCase, PascalCase, snake_case, or SCREAMING_SNAKE_CASE to kebab-case

    Args:
        name: String to convert

    Returns:
        Kebab-case string

    Examples:
        >>> to_kebab_case('CamelCase')
        'camel-case'
        >>> to_kebab_case('PascalCase')
        'pascal-case'
        >>> to_kebab_case('snake_case')
        'snake-case'
        >>> to_kebab_case('SCREAMING_SNAKE_CASE')
        'screaming-snake-case'
        >>> to_kebab_case('XMLHttpRequest')
        'xml-http-request'
    """
    # Handle acronyms first (e.g., XML, API)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    
    # Convert to lowercase and handle existing underscores
    return s2.lower().replace('_', '-').replace('--', '-')