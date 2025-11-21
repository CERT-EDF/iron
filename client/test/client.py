#!/usr/bin/env python3
"""Iron Client Test"""

from argparse import ArgumentParser
from asyncio import run

from edf_fusion.client import (
    FusionAuthAPIClient,
    FusionClient,
    FusionClientConfig,
    FusionConstantAPIClient,
    FusionInfoAPIClient,
    create_session,
)
from edf_fusion.concept import Case, Constant
from edf_fusion.helper.logging import get_logger
from yarl import URL

from edf_iron_client import IronClient

_LOGGER = get_logger('client', root='test')


async def _test_retrieve_info(fusion_client: FusionClient):
    fusion_info_api_client = FusionInfoAPIClient(fusion_client=fusion_client)
    info = await fusion_info_api_client.info()
    _LOGGER.info("retrieved info: %s", info)


async def _test_retrieve_constant(fusion_client: FusionClient):
    fusion_constant_api_client = FusionConstantAPIClient(
        constant_cls=Constant, fusion_client=fusion_client
    )
    constant = await fusion_constant_api_client.constant()
    _LOGGER.info("retrieved constant: %s", constant)


async def _test_case_lifecycle(iron_client: IronClient):
    # create case
    case = await iron_client.create_case(
        Case(tsid=None, name='T', description='D', acs={'test'})
    )
    _LOGGER.info("created case: %s", case)
    # update case
    case.report = 'test case report'
    case = await iron_client.update_case(case)
    _LOGGER.info("updated case: %s", case)
    # retrieve case
    case = await iron_client.retrieve_case(case.guid)
    _LOGGER.info("retrieved case: %s", case)
    # enumerate cases
    cases = await iron_client.enumerate_cases()
    _LOGGER.info("enumerated cases: %s", cases)
    # delete case
    deleted = await iron_client.delete_case(case.guid)
    _LOGGER.info("case deleted: %s", deleted)
    # enumerate cases
    cases = await iron_client.enumerate_cases()
    _LOGGER.info("enumerated cases: %s", cases)


async def _test_service_lifecycle(
    iron_client: IronClient, case: Case, service_name: str
):
    services = await iron_client.enumerate_services()
    _LOGGER.info("retrieved services: %s", services)
    services = [service for service in services if service.name == service_name]
    if not services:
        _LOGGER.error("cannot find carbon service to perform tests!")
        return
    service = services[0]
    # probe for case
    probed_case = await iron_client.probe_service_case(service, case.guid)
    if probed_case:
        _LOGGER.warning(
            "case %s already exist in service %s", case.guid, service.name
        )
        return
    # sync service case
    synced_case = await iron_client.sync_service_case(service, case.guid)
    _LOGGER.info("synced case: %s", synced_case)
    # probe again
    probed_case = await iron_client.probe_service_case(service, case.guid)
    _LOGGER.info("probed case: %s", probed_case)
    if not probed_case:
        _LOGGER.warning(
            "cannot find case %s in service %s", case.guid, service.name
        )
        return
    # delete service case
    deleted = await iron_client.delete_service_case(service, case.guid)
    _LOGGER.info("case deleted: %s", deleted)
    # probe again
    probed_case = await iron_client.probe_service_case(service, case.guid)
    _LOGGER.info("probed case: %s", probed_case)
    if probed_case:
        _LOGGER.error(
            "case %s still exist in service %s", case.guid, service.name
        )


async def _playbook(fusion_client: FusionClient, service_name: str):
    iron_client = IronClient(fusion_client=fusion_client)
    await _test_retrieve_info(fusion_client)
    await _test_retrieve_constant(fusion_client)
    await _test_case_lifecycle(iron_client)
    case = await iron_client.create_case(
        Case(tsid=None, name='T', description='D', acs={'test'})
    )
    _LOGGER.info("created case: %s", case)
    input("execution paused, press enter to continue!")
    await _test_service_lifecycle(iron_client, case, service_name)
    await iron_client.delete_case(case.guid)


def _parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--api-url',
        type=URL,
        default=URL('http://iron.domain.lan/'),
        help="API URL",
    )
    parser.add_argument(
        '--service-name',
        default='carbon',
        help="Service name to use for testing",
    )
    return parser.parse_args()


async def app():
    """Application entrypoint"""
    args = _parse_args()
    config = FusionClientConfig(api_url=args.api_url)
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
            await _playbook(fusion_client, args.service_name)
        finally:
            await fusion_auth_api_client.logout()


if __name__ == '__main__':
    run(app())
