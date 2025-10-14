#!/usr/bin/env python3
"""Iron Client Test"""

from argparse import ArgumentParser
from asyncio import run

from edf_fusion.client import (
    FusionAuthAPIClient,
    FusionClient,
    FusionClientConfig,
    create_session,
)
from edf_fusion.helper.logging import get_logger
from yarl import URL

from edf_iron_client import IronClient

_LOGGER = get_logger('client', root='test')


async def _playbook(fusion_client: FusionClient):
    iron_client = IronClient(fusion_client=fusion_client)
    services = await iron_client.enumerate_services()
    _LOGGER.info("services:")
    for service in services:
        _LOGGER.info("- %s", service)


def _parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--port', '-p', type=int, default=10000, help="Server port"
    )
    return parser.parse_args()


async def app():
    """Application entrypoint"""
    args = _parse_args()
    config = FusionClientConfig(api_url=URL(f'http://127.0.0.1:{args.port}/'))
    session = create_session(config, unsafe=True)
    async with session:
        fusion_client = FusionClient(config=config, session=session)
        fusion_auth_api_client = FusionAuthAPIClient(
            fusion_client=fusion_client
        )
        identity = await fusion_auth_api_client.login('test', 'test')
        if not identity:
            return
        _LOGGER.info("logged as: %s", identity)
        try:
            await _playbook(fusion_client)
        finally:
            await fusion_auth_api_client.logout()


if __name__ == '__main__':
    run(app())
