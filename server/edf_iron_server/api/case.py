"""Case API"""

from aiohttp.web import Request
from edf_fusion.helper.aiohttp import get_guid, get_json_body, json_response
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.auth import Action, get_fusion_auth_api
from edf_fusion.server.event import get_fusion_evt_api

from .helper import prologue

_LOGGER = get_logger('server.api.case', root='iron')


async def create_case(request: Request):
    """Create case"""
    fusion_evt_api = get_fusion_evt_api(request)
    action = Action(name='create_case')
    _, storage = await prologue(request, action)
    body = await get_json_body(request)
    if not body:
        return json_response(status=400, message="Bad request")
    case = await storage.create_case(True, body)
    if not case:
        return json_response(status=400, message="Bad request")
    await fusion_evt_api.notify(category='create_case', case=case)
    return json_response(data=case.to_dict())


async def update_case(request: Request):
    """Update case"""
    case_guid = get_guid(request, 'case_guid')
    fusion_evt_api = get_fusion_evt_api(request)
    if not case_guid:
        return json_response(status=400, message="Invalid GUID")
    action = Action(
        name='update_case',
        change=True,
        update_case=True,
        context={'case_guid': case_guid},
    )
    _, storage = await prologue(request, action)
    body = await get_json_body(request)
    if not body:
        return json_response(status=400, message="Bad request")
    case = await storage.update_case(case_guid, body)
    if not case:
        return json_response(status=400, message="Bad request")
    await fusion_evt_api.notify(category='update_case', case=case)
    return json_response(data=case.to_dict())


async def retrieve_case(request: Request):
    """Retrieve case"""
    case_guid = get_guid(request, 'case_guid')
    if not case_guid:
        return json_response(status=400, message="Invalid GUID")
    action = Action(name='retrieve_case', context={'case_guid': case_guid})
    _, storage = await prologue(request, action)
    case = await storage.retrieve_case(case_guid)
    if not case:
        return json_response(status=404, message="Case not found")
    return json_response(data=case.to_dict())


async def delete_case(request: Request):
    """Delete case"""
    case_guid = get_guid(request, 'case_guid')
    if not case_guid:
        return json_response(status=400, message="Invalid GUID")
    action = Action(
        name='delete_case',
        change=True,
        delete=True,
        context={'case_guid': case_guid},
    )
    _, storage = await prologue(request, action)
    case = await storage.retrieve_case(case_guid)
    deleted = await storage.delete_case(case_guid)
    if not deleted:
        return json_response(status=400, message="Not deleted")
    fusion_evt_api = get_fusion_evt_api(request)
    await fusion_evt_api.notify(category='delete_case', case=case)
    return json_response()


async def enumerate_cases(request: Request):
    """Enumerate cases"""
    action = Action(name='enumerate_cases')
    identity, storage = await prologue(request, action)
    fusion_auth_api = get_fusion_auth_api(request)
    cases = [
        case
        async for case in storage.enumerate_cases()
        if fusion_auth_api.can_access_case(identity, case)
    ]
    return json_response(data=[case.to_dict() for case in cases])
