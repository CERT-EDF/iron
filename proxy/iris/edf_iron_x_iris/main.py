"""Iron x DFIR IRIS Proxy"""

from argparse import ArgumentParser, Namespace
from pathlib import Path

from aiohttp.web import Application, Request, run_app
from edf_fusion.concept import Case, Identity, Info
from edf_fusion.helper.config import ConfigError
from edf_fusion.helper.logging import get_logger
from edf_fusion.helper.redis import setup_redis
from edf_fusion.server.auth import (
    Access,
    Action,
    FusionAuthAPI,
    get_fusion_auth_api,
)
from edf_fusion.server.case import (
    ActionDeleteCase,
    ActionUpdateCase,
    FusionCaseAPI,
)
from edf_fusion.server.info import FusionInfoAPI
from edf_fusion.server.storage import get_fusion_storage

from .__version__ import version
from .api import (
    attach_case_impl,
    create_case_impl,
    delete_case_impl,
    enumerate_cases_impl,
    retrieve_case_impl,
    setup_redirect,
    update_case_impl,
)
from .client import setup_iris_client
from .config import IronProxyConfig
from .storage import Storage

_LOGGER = get_logger('main', root='iron_x_iris')


async def _authorize_impl(
    request: Request,
    action: Action,
    identity: Identity,
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


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Iron x DFIR IRIS Proxy")
    parser.add_argument(
        '--config',
        '-c',
        type=Path,
        default=Path('proxy.yml'),
        help="Proxy configuration file",
    )
    return parser.parse_args()


async def _init_app(config: IronProxyConfig) -> Application:
    webapp = Application(client_max_size=config.server.client_max_size)
    config.setup(webapp)
    redis = setup_redis(webapp, config.server.redis_url)
    fusion_auth_api = FusionAuthAPI(
        redis=redis,
        config=config.auth_api,
        authorize_impl=_authorize_impl,
    )
    fusion_auth_api.setup(webapp)
    info = Info(api='helium', version=version)
    fusion_info_api = FusionInfoAPI(info=info, config=config.info_api)
    fusion_info_api.setup(webapp)
    fusion_case_api = FusionCaseAPI(
        config=config.case_api,
        case_cls=Case,
        attach_case_impl=attach_case_impl,
        create_case_impl=create_case_impl,
        update_case_impl=update_case_impl,
        delete_case_impl=delete_case_impl,
        retrieve_case_impl=retrieve_case_impl,
        enumerate_cases_impl=enumerate_cases_impl,
    )
    fusion_case_api.setup(webapp)
    storage = Storage(redis=redis, config=config.storage)
    storage.setup(webapp)
    setup_iris_client(webapp)
    setup_redirect(webapp)
    return webapp


# pylint: disable=W0702


def app():
    """Iron x DFIR IRIS proxy entrypoint"""
    _LOGGER.info("Iron x DFIR IRIS Proxy %s", version)
    args = _parse_args()
    try:
        config = IronProxyConfig.from_filepath(args.config)
    except:
        _LOGGER.exception("invalid configuration file: %s", args.config)
        return
    if not config:
        _LOGGER.error("failed to load configuration file: %s", args.config)
        return
    try:
        run_app(
            app=_init_app(config),
            host=config.server.host,
            port=config.server.port,
            handle_signals=True,
        )
    except ConfigError as exc:
        _LOGGER.error("configuration error: %s", exc)
