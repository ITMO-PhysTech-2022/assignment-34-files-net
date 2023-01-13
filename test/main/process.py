from __future__ import annotations

import pytest

import os
import sys
import inspect
from subprocess import Popen, PIPE

import re
from typing import Callable

from test.common.mock.fs import tmpcd, tmpfile
from test.common.test import root_directory, timeout

_dev_mode = '''
@greedy
def _cmd_exec(line: str):
    exec(line)
    return 'Done'

@greedy
def _cmd_eval(line: str):
    result = eval(line)
    return result
    
@greedy
def _cmd_debug(line: str):
    return line

from tasks.core.command import ShowDummy
'''


class Process:
    def __init__(self, auto_exit: bool = True):
        self.process: Popen | None = None
        self.auto_exit = auto_exit
        self.root = root_directory()
        self.resources = self.root / 'resources'
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        pythonpath = os.environ.get('PYTHONPATH', '')
        if pythonpath != '':
            pythonpath += os.pathsep
        os.environ['PYTHONPATH'] = f'{pythonpath}{self.root}'

        self.path = 'tasks/main.py'
        self.commands = self.root / 'tasks/driver/files/commands.py'
        with open(self.root / 'tasks/main.py', encoding='utf-8') as main_py:
            main = main_py.read()
            if not re.findall(r'tasks[^\'"]+config\.json', main):
                self.root /= 'tasks'
                self.path = 'main.py'
        self.tmpcommands = tmpfile(self.commands)

    def __enter__(self):
        commands = self.tmpcommands.__enter__()
        with tmpcd(self.root):
            commands.write('\n' + _dev_mode, append=True)
            self.process = Popen(
                [sys.executable, self.path],
                stdin=PIPE, stdout=PIPE, stderr=PIPE,
                text=True, encoding='utf-8'
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.auto_exit:
            self.process.communicate('exit\n')
            code = self.process.poll()
            if code is None:
                pytest.fail('Процесс не завершился после `exit`')
        self.tmpcommands.__exit__(exc_type, exc_val, exc_tb)

    def write(self, data: str):
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def read(self, expect_lines: int):
        return [self.process.stdout.readline() for _ in range(expect_lines)]

    def handler(self, command: str, expect_lines: int):
        self.write(command + '\n')
        return self.read(expect_lines)

    def custom_handler(self, callback: Callable):
        def _handle(command: str, expect_lines: int):
            result = self.handler(command, expect_lines)
            return callback(result)

        return _handle

    def wait(self):
        self.process.wait()

    def exitcode(self):
        return self.process.poll()

    def remaining_log(self, stream_id: int):
        if self.process.poll() is None:
            return None
        stream = self.process.stdout if stream_id == 0 else self.process.stderr
        return stream.read()


spawn = Process
