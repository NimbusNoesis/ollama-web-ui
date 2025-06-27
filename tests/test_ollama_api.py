import types

def dummy_function(x: int, y: int) -> int:
    """Add numbers

    Args:
        x: first
        y: second
    Returns:
        sum
    """
    return x + y


def make_response_with_tool():
    class Msg:
        def __init__(self):
            self.tool_calls = [{'id': '1', 'function': {'name': 'dummy_function', 'arguments': '{"x": 2, "y": 3}'}}]
            self.content = 'answer'
    return types.SimpleNamespace(message=Msg())


def test_function_to_tool_definition():
    from app.api.ollama_api import OllamaAPI
    tool = OllamaAPI._function_to_tool_definition(dummy_function)
    assert tool['function']['name'] == 'dummy_function'
    assert 'x' in tool['function']['parameters']['properties']


def test_process_tool_calls_and_add_results():
    from app.api.ollama_api import OllamaAPI
    response = make_response_with_tool()
    res = OllamaAPI.process_tool_calls(response, {'dummy_function': dummy_function})
    assert res['1']['output'] == 5
    messages = [{'role': 'user', 'content': 'hi'}]
    updated = OllamaAPI.add_tool_results_to_messages(messages, response, res)
    assert updated[-1]['role'] == 'tool'
    assert '5' in updated[-1]['content']


def test_extract_tags_from_name():
    from app.api.ollama_api import OllamaAPI
    tags = OllamaAPI.extract_tags_from_name('codellama-7b')
    assert 'code' in tags and 'small' in tags

