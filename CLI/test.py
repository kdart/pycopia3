
"""


"""

import unittest


from pycopia import IO
from pycopia import UI
from pycopia import CLI


class TestCommands(CLI.BaseCommands):

    def f(self, argv):
        """command"""
        return argv[0]


class CLITests(unittest.TestCase):

    def setUp(self):
        pass

    def test_build_CLI(self):
        cli = CLI.get_cli(TestCommands)
        #print(dir(cli))
        cli.interact()



if __name__ == '__main__':
    unittest.main()
