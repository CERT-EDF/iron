#!/usr/bin/env python3
"""Iron Test Client"""

from argparse import ArgumentParser
from asyncio import run
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from edf_fusion.client import (
    FusionAuthAPIClient,
    FusionCaseAPIClient,
    FusionClient,
    FusionClientConfig,
    FusionEventAPIClient,
    create_session,
)
from edf_fusion.helper.logging import get_logger
from edf_fusion.helper.serializing import Loadable
from edf_neon_core.concept import Case


_LOGGER = get_logger('subscribe', root='test')


async def _playbook(fusion_client: FusionClient, case_guid: UUID):
    fusion_case_api_client = FusionCaseAPIClient(
        case_cls=Case, fusion_client=fusion_client
    )
    case = await fusion_case_api_client.retrieve_case(case_guid)
    fusion_event_api_client = FusionEventAPIClient(fusion_client=fusion_client)
    async for event in fusion_event_api_client.subscribe(case.guid):
        _LOGGER.info("%s", event)


@dataclass(kw_only=True)
class TestConfig(Loadable):
    """Test configuration"""

    url: str
    key: str

    @classmethod
    def from_dict(cls, dct):
        return cls(url=dct['url'], key=dct['key'])


def _parse_args():
    parser = ArgumentParser()
    parser.add_argument('config', type=Path, help="Test configuration")
    parser.add_argument('case_guid', type=UUID, help="Case GUID")
    args = parser.parse_args()
    args.config = TestConfig.from_filepath(args.config)
    return args


async def app():
    """Application entrypoint"""
    args = _parse_args()
    config = FusionClientConfig(
        api_url=args.config.url, api_key=args.config.key
    )
    session = create_session(config, unsafe=True)
    async with session:
        fusion_client = FusionClient(config=config, session=session)
        fusion_auth_api_client = FusionAuthAPIClient(
            fusion_client=fusion_client
        )
        identity = await fusion_auth_api_client.is_logged()
        if not identity:
            return
        _LOGGER.info("logged as: %s", identity)
        try:
            await _playbook(fusion_client, args.case_guid)
        except:
            _LOGGER.exception("exception raised!")


if __name__ == '__main__':
    run(app())
