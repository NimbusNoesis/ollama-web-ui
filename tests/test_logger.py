import pytest
import logging


def test_set_log_level_and_get_logger():
    from app.utils import logger as log_mod
    log = log_mod.get_logger()
    log_mod.set_log_level('DEBUG')
    assert log.level == logging.DEBUG
    log_mod.set_log_level('INFO')
    assert log.level == logging.INFO


def test_exception_handler():
    from app.utils import logger as log_mod

    @log_mod.exception_handler
    def fail(x):
        raise ValueError('bad')

    with pytest.raises(ValueError) as exc:
        fail(1)
    assert 'Error in test_exception_handler' in str(exc.value)


def test_error_handler():
    from app.utils import logger as log_mod
    err = ValueError('oops')
    info = log_mod.ErrorHandler.handle_error(err, 'ctx')
    assert info['status'] == 'error'
    assert 'ctx' in info['message']

    with pytest.raises(ValueError):
        log_mod.ErrorHandler.handle_error(err, raise_error=True)

