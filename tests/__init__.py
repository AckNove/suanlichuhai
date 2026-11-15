# -*- coding: utf-8 -*-
"""CCGS 后端测试包：共享临时数据库环境（不污染 data/runtime）。"""
from __future__ import annotations

import os
import shutil
import tempfile

_UNIT_TEST_SEED_TOKEN = "seed:demo"  # 仅用于提示，测试不依赖具体种子备注
_ENV_KEYS = ("CCGS_DB_PATH", "CCGS_SEED", "CCGS_BACKUP_DIR")


class TempEnv:
    """临时目录 + CCGS_DB_PATH/CCGS_BACKUP_DIR 环境变量，退出时恢复并清理。"""

    def __enter__(self):
        self._saved = {key: os.environ.get(key) for key in _ENV_KEYS}
        self.root = tempfile.mkdtemp(prefix="ccgs_test_")
        self.db_path = os.path.join(self.root, "app.db")
        os.environ["CCGS_DB_PATH"] = self.db_path
        os.environ["CCGS_SEED"] = "0"
        os.environ["CCGS_BACKUP_DIR"] = os.path.join(self.root, "backups")
        return self

    def __exit__(self, exc_type, exc, traceback):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.root, ignore_errors=True)
        return False
