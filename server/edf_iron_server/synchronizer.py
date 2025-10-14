"""Iron Synchronizer"""

from argparse import ArgumentParser
from pathlib import Path

from edf_fusion.concept import Case
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.storage import SyncStorage
from edf_fusion.server.synchronizer import FusionSynchronizer

from .__version__ import version
from .config import IronServerConfig
from .storage import Storage

_LOGGER = get_logger('synchronizer', root='iron')


async def _sync_case_impl(storage: Storage, case: Case, directory: Path):
    sync_storage = SyncStorage(case=case, directory=directory)
    sync_storage.information.mkdir(parents=True, exist_ok=True)
    case.to_filepath(sync_storage.information / 'metadata.json')


def _parse_args():
    parser = ArgumentParser(description="Iron Synchronizer")
    parser.add_argument(
        '--config',
        '-c',
        type=Path,
        default=Path('iron.yml'),
        help="Configuration file",
    )
    return parser.parse_args()


def app():
    """Application entrypoint"""
    _LOGGER.info("Iron Synchronizer %s", version)
    args = _parse_args()
    config = IronServerConfig.from_filepath(args.config)
    synchronizer = FusionSynchronizer(
        config=config.synchronizer,
        storage=Storage(config=config.storage),
        sync_case_impl=_sync_case_impl,
    )
    synchronizer.run()


if __name__ == '__main__':
    app()
