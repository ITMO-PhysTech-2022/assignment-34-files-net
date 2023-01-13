import os
import pathlib
import shutil
import time

import pytest

import json
import random

from test.common.test import create, timeout, root_directory
from test.common.mock.fs import tmpcd, tmpfile, tmpdir
from test.main.process import spawn
from test.main.base import config, cleanup
from test.common.utils.primitives import random_line


class TestBonus:
    @pytest.mark.parametrize('lines', [1, 10, 100])
    @pytest.mark.parametrize('count', [1, 7, 15])
    def test_send_receive(self, lines, count):
        server, client = spawn(auto_exit=True), spawn(auto_exit=True)
        with tmpcd(root_directory()), tmpfile('tasks/config.json') as config_file, \
                tmpdir(server.resources / 'tmp/send-receive', keep=True) as tmp:
            config_file.write(json.dumps(config(False, -1, '$'), indent=2))
            for item in os.listdir(tmp.path):
                path = tmp.path / item
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    os.remove(tmp.path / item)

            content = [
                [random_line(10, 10, utf8=True) for _ in range(lines)]
                for _ in range(count)
            ]
            for file in range(len(content)):
                content[file] = '\n'.join(content[file]).encode('utf-8')
                with open(tmp.loc(f'{file + 1}'), 'wb') as input_file:
                    input_file.write(content[file])
            time.sleep(2)
            tmp.loc('out').mkdir(exist_ok=True)

            with server, client:
                spec_send = timeout(client.handler, 15)
                spec_send.__name__ = 'run.execute[send]'
                spec_recv = timeout(server.handler, 15)
                spec_recv.__name__ = 'run.execute[receive]'

                def spec_run(who: str, *args):
                    if who == 'S':
                        return spec_recv(*args)
                    else:
                        return spec_send(*args)

                spec_run.__name__ = 'run.execute[send+receive]'
                runner = create(spec_run, '3.B#send+receive')

                if not (server.resources / 'scripts/send.s').exists() or \
                        not (server.resources / 'scripts/receive.s').exists():
                    msg = 'Скрипт `send.s` и/или `receive.s` не найден'
                    runner.report_wa(f'{runner.test_name}/exits.script', None, None, msg)
                    pytest.fail(msg)
                else:
                    runner.multitest(
                        runner.manual('S', f'exec main.vars["PATH"] = {repr(str(tmp.path))}', 1).just_returns(),
                        runner.manual('S', f'exec main.vars["COUNT"] = {count}', 1).just_returns(),
                        runner.manual('S', f'execute {server.resources / "scripts/receive.s"}', 0).just_returns(),

                        runner.manual('C', f'exec main.vars["PATH"] = {repr(str(tmp.path / "out"))}', 1).just_returns(),
                        runner.manual('C', f'exec main.vars["COUNT"] = {count}', 1).just_returns(),
                        runner.manual('C', f'execute {server.resources / "scripts/send.s"}', 0).just_returns(),
                    )

                time.sleep(2)
                for file in range(count):
                    output_path = tmp.loc(f'out/{file + 1}')
                    if not output_path.exists():
                        msg = f'Файл `out/{file + 1}` не был создан после выполнения скрипта'
                        runner.report_wa(f'{runner.test_name}/exists.output', None, None, msg)
                        pytest.fail(msg)
                    else:
                        with open(output_path, 'rb') as output_file:
                            output = output_file.read()
                        output = output.replace(b'\r', b'')
                        if output.endswith(b'\n'):
                            output = output.removesuffix(b'\n')
                        if output != content[file]:
                            msg = 'Ожидался другой ответ'
                            runner.report_wa(f'{runner.test_name}/check', None, output, msg + 
                                             f' на тесте {content[file].decode("utf-8")}')
                            pytest.fail(msg)

            cleanup(runner, server, client)
