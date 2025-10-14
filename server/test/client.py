#!/usr/bin/env python3
"""Iron Server Test"""
from asyncio import run
from uuid import UUID

from aiohttp import ClientResponse, ClientSession, CookieJar
from edf_fusion.concept import Case
from edf_fusion.helper.logging import get_logger
from edf_iron_core.concept import Service

_LOGGER = get_logger('client', root='test')


async def _get_data(response: ClientResponse) -> dict | None:
    body = await response.json()
    if body.get('status') != 200:
        return None
    data = body.get('data')
    _LOGGER.info("response data: %s", data)
    return data


async def _enumerate_services(session: ClientSession) -> list[Service] | None:
    async with session.get('/api/services') as response:
        data = await _get_data(response)
        if not data:
            return None
        return [Service.from_dict(item) for item in data]


async def _create_case(session: ClientSession) -> Case | None:
    case = Case(
        tsid='#1337',
        name='MANAGED CASE',
        description="A managed case for testing",
        acs={'DFIR'},
    )
    async with session.post('/api/case', json=case.to_dict()) as response:
        data = await _get_data(response)
        if not data:
            return None
        return Case.from_dict(data['case'])


async def _update_case(session: ClientSession, case: Case) -> Case | None:
    case.tsid = "#0000"
    endpoint = f'/api/case/{case.guid}'
    async with session.put(endpoint, json=case.to_dict()) as response:
        data = await _get_data(response)
        if not data:
            return None
        return Case.from_dict(data['case'])


async def _retrieve_case(
    session: ClientSession, case_guid: UUID
) -> Case | None:
    endpoint = f'/api/case/{case_guid}'
    async with session.get(endpoint) as response:
        data = await _get_data(response)
        if not data:
            return None
        return Case.from_dict(data['case'])


async def _enumerate_cases(session: ClientSession) -> list[Case] | None:
    async with session.get('/api/cases') as response:
        data = await _get_data(response)
        if not data:
            return None
        return [Case.from_dict(item) for item in data]


async def _playbook(session: ClientSession):
    # enumerate services
    services = await _enumerate_services(session)
    _LOGGER.info("enumerated services: %s", services)
    # create case
    case = await _create_case(session)
    _LOGGER.info("created case: %s", case)
    # update case
    case = await _update_case(session, case)
    _LOGGER.info("updated case: %s", case)
    # retrieve case
    case = await _retrieve_case(session, case.guid)
    _LOGGER.info("retrieved case: %s", case)
    # enumerate cases
    cases = await _enumerate_cases(session)
    _LOGGER.info("enumerated cases: %s", cases)


async def _login(session: ClientSession) -> dict | None:
    json = {'data': {'username': 'test', 'password': 'test'}}
    async with session.post('/api/auth/login', json=json) as response:
        body = await response.json()
        if body.get('status') != 200:
            return None
        return body.get('data')


async def _logout(session: ClientSession) -> bool:
    async with session.get('/api/auth/logout') as response:
        body = await response.json()
        return body.get('status') == 200


async def _app():
    async with ClientSession(
        base_url='http://127.0.0.1:10000',
        cookie_jar=CookieJar(unsafe=True),
    ) as session:
        result = await _login(session)
        if not result:
            _LOGGER.error("login failure")
            return
        _LOGGER.info("login success")
        try:
            _LOGGER.info("running playbook...")
            await _playbook(session)
        finally:
            await _logout(session)
            _LOGGER.info("logout")


if __name__ == '__main__':
    run(_app())
