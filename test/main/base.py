import pytest

from test.common.test import TestBase, timeout
from test.main.process import Process


def config(show: bool, margin: int, prefix: str):
    return {
        'display': {
            'show': show,
            'margin': margin
        },
        'prefix': prefix
    }


def cleanup(runner: TestBase, process: Process):
    spec_stop = timeout(process.wait, 2)
    spec_stop.__name__ = 'main.stop'
    runner.set_spec(spec_stop)
    runner.run(runner.manual().just_returns())

    if process.exitcode() != 0:
        runner.report_re(f'1:runs/exitcode', None, process.full_log(1))
        pytest.fail(f'Процесс завершился с ошибкой')

    runner.cleanup()


def show_transform(show_src: str):
    return f'ShowDummy(lambda x, y: main.report(({show_src})(x, y)))'
