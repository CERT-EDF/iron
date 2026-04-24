"""Iron Server App"""

from argparse import ArgumentParser
from pathlib import Path

from aiohttp.web import Application, Request, run_app
from edf_fusion.concept import Constant, Identity, Info
from edf_fusion.helper.config import ConfigError
from edf_fusion.helper.logging import get_logger
from edf_fusion.helper.redis import setup_redis
from edf_fusion.server.auth import (
    Access,
    Action,
    FusionAuthAPI,
    get_fusion_auth_api,
)
from edf_fusion.server.case import ActionDeleteCase, ActionUpdateCase
from edf_fusion.server.constant import FusionConstantAPI
from edf_fusion.server.event import FusionEventAPI
from edf_fusion.server.info import FusionInfoAPI
from edf_fusion.server.storage import get_fusion_storage
from edf_iron_core.concept import Event

from .__version__ import version
from .api import setup_api
from .config import IronServerConfig
from .connector import setup_connectors
from .storage import Storage

_LOGGER = get_logger('server', root='iron')


async def _authorize_impl(
    request: Request, action: Action, identity: Identity
) -> bool:
    storage = get_fusion_storage(request)
    case_guid = action.context.get('case_guid')
    if not case_guid:
        return True
    case = await storage.retrieve_case(case_guid)
    if not case:
        _LOGGER.warning("case not found!")
        return False
    fusion_auth_api = get_fusion_auth_api(request)
    access = fusion_auth_api.can_access_case(identity, case)
    if not access or (action.change and access != Access.CHANGE):
        return False
    if action.change and case.closed:
        if isinstance(action, (ActionDeleteCase, ActionUpdateCase)):
            # allow closed case deletion
            # allow closed case update to reopen case
            # (Case.update will prevent closed case modification if not reopen)
            return True
        _LOGGER.warning("case closed!")
        return False
    return True


async def _init_app(config: IronServerConfig):
    webapp = Application(client_max_size=config.server.client_max_size)
    config.setup(webapp)
    redis = setup_redis(webapp, config.server.redis_url)
    setup_connectors(webapp, config.connectors)
    fusion_auth_api = FusionAuthAPI(
        redis=redis, config=config.auth_api, authorize_impl=_authorize_impl
    )
    fusion_auth_api.setup(webapp)
    info = Info(api='iron', version=version)
    fusion_info_api = FusionInfoAPI(info=info, config=config.info_api)
    fusion_info_api.setup(webapp)
    fusion_event_api = FusionEventAPI(
        redis=redis, config=config.event_api, event_cls=Event
    )
    fusion_event_api.setup(webapp)
    fusion_constant_api = FusionConstantAPI(
        config=config.constant_api, constant_cls=Constant
    )
    fusion_constant_api.setup(webapp)
    setup_api(webapp)
    storage = Storage(redis=redis, config=config.storage)
    storage.setup(webapp)
    return webapp


def _parse_args():
    parser = ArgumentParser(description="Iron Server")
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
    _LOGGER.info("Iron Server %s", version)
    args = _parse_args()
    config = IronServerConfig.from_filepath(args.config)
    try:
        run_app(
            app=_init_app(config),
            host=config.server.host,
            port=config.server.port,
            handle_signals=True,
        )
    except ConfigError as exc:
        _LOGGER.error("configuration error: %s", exc)


if __name__ == '__main__':
    app()
