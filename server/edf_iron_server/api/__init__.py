"""Iron Server Routes"""

from aiohttp.web import Application, delete, get, post, put

from .case import (
    create_case,
    delete_case,
    enumerate_cases,
    retrieve_case,
    update_case,
)
from .service import (
    attach_service_case,
    delete_service_case,
    enumerate_service_cases,
    enumerate_services,
    probe_service_case,
    sync_service_case,
)


def setup_api(webapp: Application):
    """Setup API endppoints"""
    webapp.add_routes(
        [
            post('/api/case', create_case),
            put('/api/case/{case_guid}', update_case),
            delete('/api/case/{case_guid}', delete_case),
            get('/api/case/{case_guid}', retrieve_case),
            get('/api/cases', enumerate_cases),
            post(
                '/api/service/{service_name}/case/{case_guid}',
                sync_service_case,
            ),
            delete(
                '/api/service/{service_name}/case/{case_guid}',
                delete_service_case,
            ),
            put(
                '/api/service/{service_name}/case/{case_guid}/attach/{next_case_guid}',
                attach_service_case,
            ),
            get(
                '/api/service/{service_name}/case/{case_guid}',
                probe_service_case,
            ),
            get('/api/service/{service_name}/cases', enumerate_service_cases),
            get('/api/services', enumerate_services),
        ]
    )
