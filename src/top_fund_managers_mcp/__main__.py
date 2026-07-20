# -*- coding: utf-8 -*-
"""包入口。

  python -m top_fund_managers_mcp            # 启动 MCP stdio server
  python -m top_fund_managers_mcp search ...  # 等价于 CLI 子命令
"""

import sys

from .cli import CLI_SUBCOMMANDS, main as cli_main
from .server import mcp


def main():
    argv = sys.argv[1:]
    if argv and argv[0] in CLI_SUBCOMMANDS:
        cli_main()
    else:
        # 默认作为 MCP stdio server 启动
        mcp.run()


if __name__ == "__main__":
    main()
