"""Iron Proxy API module"""

from aiohttp.web import Application, HTTPFound, HTTPNotFound, Request, get
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.storage import get_fusion_storage

from ..config import get_proxy_config
from .case import (
    attach_case_impl,
    create_case_impl,
    delete_case_impl,
    enumerate_cases_impl,
    retrieve_case_impl,
    update_case_impl,
)

_LOGGER = get_logger('api', root='iron_x_iris')


async def _redirect(request: Request):
    config = get_proxy_config(request)
    storage = get_fusion_storage(request)
    case_guid = request.match_info['case_guid']
    case = await storage.retrieve_case(case_guid)
    if not case:
        raise HTTPNotFound()
    url = '/'.join(
        [
            config.iris_client.api_url.rstrip('/'),
            f'case?cid={case.iris_id}',
        ]
    )
    _LOGGER.info("redirecting to %s", url)
    raise HTTPFound(url)


def setup_redirect(webapp: Application):
    """Setup redirect"""
    webapp.add_routes([get('/case/{case_guid}', _redirect)])
