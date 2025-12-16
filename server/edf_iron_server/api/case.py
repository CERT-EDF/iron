"""Case API"""

from aiohttp.web import Request
from edf_fusion.concept import Identity
from edf_fusion.helper.aiohttp import get_guid, get_json_body, json_response
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.auth import get_fusion_auth_api
from edf_fusion.server.event import get_fusion_evt_api
from edf_fusion.server.storage import get_fusion_storage

from ..storage import Storage

_LOGGER = get_logger('server.api.case', root='iron')


async def prologue(
    request: Request, operation: str, context: dict
) -> tuple[Identity, Storage]:
    """Determine if authorized and retrieve storage"""
    fusion_auth_api = get_fusion_auth_api(request)
    identity = await fusion_auth_api.authorize(
        request, operation, context=context
    )
    storage = get_fusion_storage(request)
    return identity, storage


async def create_case(request: Request):
    """Create case"""
    fusion_evt_api = get_fusion_evt_api(request)
    _, storage = await prologue(request, 'create_case', {})
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
    _, storage = await prologue(
        request, 'update_case', {'case_guid': case_guid}
    )
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
    _, storage = await prologue(
        request, 'retrieve_case', {'case_guid': case_guid}
    )
    case = await storage.retrieve_case(case_guid)
    if not case:
        return json_response(status=404, message="Case not found")
    return json_response(data=case.to_dict())


async def delete_case(request: Request):
    """Delete case"""
    case_guid = get_guid(request, 'case_guid')
    if not case_guid:
        return json_response(status=400, message="Invalid GUID")
    _, storage = await prologue(
        request,
        'delete_case',
        {'case_guid': case_guid, 'is_delete_op': True},
    )
    case = await storage.retrieve_case(case_guid)
    deleted = await storage.delete_case(case_guid)
    if not deleted:
        return json_response(status=400, message="Not deleted")
    fusion_evt_api = get_fusion_evt_api(request)
    await fusion_evt_api.notify(category='delete_case', case=case)
    return json_response()


async def enumerate_cases(request: Request):
    """Enumerate cases"""
    identity, storage = await prologue(request, 'enumerate_cases', {})
    fusion_auth_api = get_fusion_auth_api(request)
    cases = [
        case
        async for case in storage.enumerate_cases()
        if fusion_auth_api.can_access_case(identity, case)
    ]
    return json_response(data=[case.to_dict() for case in cases])
