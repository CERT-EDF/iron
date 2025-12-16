"""Service API"""

from aiohttp.web import Request
from edf_fusion.helper.aiohttp import get_guid, json_response
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.auth import get_fusion_auth_api
from edf_fusion.server.event import get_fusion_evt_api

from ..connector import IronConnector, get_connectors
from .case import prologue

_LOGGER = get_logger('server.api.service', root='iron')


def _get_connector(request: Request) -> tuple[str, IronConnector | None]:
    service_name = request.match_info['service_name']
    iron_connectors = get_connectors(request)
    return service_name, iron_connectors.get(service_name)


async def enumerate_services(request: Request):
    """enumerate cconfigured services"""
    await prologue(request, 'enumerate_services', {})
    iron_connectors = get_connectors(request)
    services = [
        iron_connector.config.service.to_dict()
        for iron_connector in iron_connectors.values()
    ]
    return json_response(data=services)


async def attach_service_case(request: Request):
    """Attach service case"""
    case_guid = get_guid(request, 'case_guid')
    next_case_guid = get_guid(request, 'next_case_guid')
    if not case_guid or not next_case_guid:
        return json_response(status=400, message="Invalid GUID")
    service_name, iron_connector = _get_connector(request)
    if not iron_connector:
        return json_response(status=400, message="Bad service")
    identity, _ = await prologue(
        request,
        'attach_service_case',
        context={
            'service_name': service_name,
            'prev_case_guid': case_guid,
            # check that user can access local case
            'case_guid': next_case_guid,
        },
    )
    # check that user can access service case
    fusion_auth_api = get_fusion_auth_api(request)
    svc_case = await iron_connector.case_api.retrieve_case(case_guid)
    if svc_case:
        if svc_case.managed:
            return json_response(
                status=400, message="Cannot attach managed case"
            )
        can_access = fusion_auth_api.can_access_case(identity, svc_case)
        if not can_access:
            return json_response(
                status=403, message="Cannot access service case"
            )
    # perform 'attach' operation (even if case does not exists)
    svc_case = await iron_connector.case_api.attach_case(
        case_guid, next_case_guid
    )
    if not svc_case:
        return json_response(status=404, message="Case not found")
    fusion_evt_api = get_fusion_evt_api(request)
    await fusion_evt_api.notify(
        category='service_attach_case',
        case=svc_case,
        ext={'service': service_name},
    )
    return json_response(data=svc_case.to_dict())


async def delete_service_case(request: Request):
    """Delete service case"""
    case_guid = get_guid(request, 'case_guid')
    if not case_guid:
        return json_response(status=400, message="Invalid GUID")
    service_name, iron_connector = _get_connector(request)
    if not iron_connector:
        return json_response(status=400, message="Bad service")
    await prologue(
        request,
        'delete_service_case',
        context={
            'service_name': service_name,
            'case_guid': case_guid,
            'is_delete_op': True,
        },
    )
    deleted = await iron_connector.case_api.delete_case(case_guid)
    if not deleted:
        return json_response(status=400, message="Not deleted")
    fusion_evt_api = get_fusion_evt_api(request)
    svc_case = await iron_connector.case_api.retrieve_case(case_guid)
    await fusion_evt_api.notify(
        category='service_delete_case',
        case=svc_case,
        ext={'service': service_name},
    )
    return json_response()


async def enumerate_service_cases(request: Request):
    """Enumerate service unmanaged cases"""
    service_name, iron_connector = _get_connector(request)
    if not iron_connector:
        return json_response(status=400, message="Bad service")
    identity, _ = await prologue(
        request,
        'enumerate_service_cases',
        context={'service_name': service_name},
    )
    fusion_auth_api = get_fusion_auth_api(request)
    cases = await iron_connector.case_api.enumerate_cases()
    cases = [
        case
        for case in cases
        if not case.managed and fusion_auth_api.can_access_case(identity, case)
    ]
    return json_response(data=cases)


async def probe_service_case(request: Request):
    """Probe service case"""
    case_guid = get_guid(request, 'case_guid')
    if not case_guid:
        return json_response(status=400, message="Invalid GUID")
    service_name, iron_connector = _get_connector(request)
    if not iron_connector:
        return json_response(status=400, message="Bad service")
    await prologue(
        request,
        'probe_service_case',
        context={'service_name': service_name, 'case_guid': case_guid},
    )
    case = await iron_connector.case_api.retrieve_case(case_guid)
    if not case:
        return json_response(status=404, message="Case not found")
    return json_response(data=case.to_dict())


async def sync_service_case(request: Request):
    """Sync service case (create or update if needed)"""
    case_guid = get_guid(request, 'case_guid')
    if not case_guid:
        return json_response(status=400, message="Invalid GUID")
    service_name, iron_connector = _get_connector(request)
    if not iron_connector:
        return json_response(status=400, message="Bad service")
    _, storage = await prologue(
        request,
        'sync_service_case',
        context={'service_name': service_name, 'case_guid': case_guid},
    )
    case = await storage.retrieve_case(case_guid)
    svc_case = await iron_connector.case_api.retrieve_case(case_guid)
    if svc_case:
        svc_case = await iron_connector.case_api.update_case(case)
        category = 'service_update_case'
    else:
        svc_case = await iron_connector.case_api.create_case(case)
        category = 'service_create_case'
    if not svc_case:
        return json_response(status=500, message="Service error")
    fusion_evt_api = get_fusion_evt_api(request)
    await fusion_evt_api.notify(
        category=category, case=svc_case, ext={'service': service_name}
    )
    return json_response(data=svc_case.to_dict())
