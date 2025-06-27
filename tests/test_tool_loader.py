import sys
import types


def test_tool_loader_basic(tmp_path, monkeypatch):
    from app.utils import tool_loader as tl
    tools_dir = tmp_path / 'tools'
    tools_dir.mkdir()
    monkeypatch.setattr(tl.ToolLoader, 'get_tools_dir', lambda: str(tools_dir))

    impl_code = (
        'def sample(a: int, b: int) -> int:\n'
        '    """Add two numbers"""\n'
        '    return a + b\n'
    )
    tl.ToolLoader.save_tool_implementation('sample', impl_code)
    module = types.ModuleType('app.tools.sample')
    exec(impl_code, module.__dict__)
    sys.modules['app.tools.sample'] = module

    definition = {
        'function': {
            'name': 'sample',
            'description': 'Add',
            'parameters': {
                'type': 'object',
                'properties': {'a': {'type': 'number'}, 'b': {'type': 'number'}},
                'required': ['a', 'b'],
            },
        }
    }
    tl.ToolLoader.save_tool_definition('sample', definition)

    assert 'sample' in tl.ToolLoader.list_available_tools()
    func, defn = tl.ToolLoader.load_tool_function('sample')
    assert callable(func)
    assert defn['function']['name'] == 'sample'

    all_tools = tl.ToolLoader.load_all_tools()
    assert func in all_tools

    func_map = tl.ToolLoader.load_all_tool_functions()
    assert 'sample' in func_map

    result = tl.ToolLoader.execute_tool('sample', {'a': 2, 'b': 3})
    assert result == 5

    code = tl.ToolLoader.get_tool_implementation('sample')
    assert 'def sample' in code

