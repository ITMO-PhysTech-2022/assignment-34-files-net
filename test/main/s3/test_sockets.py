import pytest

import json
import random

from test.common.test import create, timeout, root_directory
from test.common.mock.fs import tmpcd, tmpfile, tmpdir
from test.main.process import spawn
from test.main.base import config, cleanup
from test.common.utils.primitives import random_line


class TestSockets:
    @pytest.mark.parametrize('lines', [1, 10, 100, 1000, 10000])
    def test_send_receive(self, lines):
        content = [random_line(10, 10, utf8=True) for _ in range(lines)]
        server, client = spawn(), spawn()
        with tmpcd(root_directory()), tmpfile('tasks/config.json') as config_file:
            config_file.write(json.dumps(config(False, -1, '$'), indent=2))
            with server, client:
                spec_send = timeout(client.handler, 15)
                spec_send.__name__ = 'run.send'
                spec_recv = timeout(server.handler, 15)
                spec_recv.__name__ = 'run.await-receive'

                def spec_run(who: str, *args):
                    if who == 'S':
                        return spec_recv(*args)
                    else:
                        return spec_send(*args)

                spec_run.__name__ = 'run.send+run.receive'
                runner = create(spec_run, '3.2#send+receive')
                runner.multitest(
                    runner.manual('C', f'exec data.lines = {content}', 1).just_returns(),
                    runner.manual('C', f'exec data.cursor = (0, 0)', 1).just_returns(),
                    runner.manual('S', f'await_receive 60000', 0).just_returns(),
                    runner.manual('C', f'send 127.0.0.1 60000', 2).returns(
                        [f'$  > Отправлено {lines} строк\n', ' > Ответ: Ok\n']
                    ),
                    runner.manual('S', f'exec None', 1).just_returns(),
                    runner.manual('S', f'exec None', 3).returns(
                        [f' > Принято {lines} строк\n', '$  > \'Done\'\n', '$  > \'Done\'\n']
                    ),
                    runner.manual('S', f'eval data.lines', 1).returns([f'$  > {repr(content)}\n'])
                )

            cleanup(runner, server, client)
