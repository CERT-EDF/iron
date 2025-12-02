"""Configuration"""

from dataclasses import dataclass
from typing import Self

from aiohttp.web import Application, Request
from edf_fusion.helper.config import Fingerprint, SSLContext, load_ssl_config
from edf_fusion.helper.logging import get_logger
from edf_fusion.helper.serializing import Loadable
from edf_fusion.server.auth import FusionAuthAPIConfig
from edf_fusion.server.case import FusionCaseAPIConfig
from edf_fusion.server.config import FusionServerConfig, FusionStorageConfig
from edf_fusion.server.info import FusionInfoAPIConfig

_LOGGER = get_logger('config', root='iron_x_iris')
_PROXY_CONFIG = '__proxy_config'


@dataclass(kw_only=True)
class IRISClientConfig(Loadable):
    """DFIR IRIS client configuration"""

    api_url: str
    api_key: str
    api_ssl: Fingerprint | SSLContext | bool
    api_as_admin: bool
    unmanaged_uids: set[int]
    case_customer_id: int
    case_template_id: int | None
    case_classification_id: int | None
    update_case_acs: bool
    update_case_summary: bool
    append_case_custom_attributes: bool

    @classmethod
    def from_dict(cls, dct: dict) -> Self:
        return cls(
            api_url=dct['api_url'],
            api_key=dct['api_key'],
            api_ssl=load_ssl_config(dct['api_ssl']),
            api_as_admin=dct['api_as_admin'],
            unmanaged_uids=set(dct['unmanaged_uids']),
            case_customer_id=dct['case_customer_id'],
            case_template_id=dct.get('case_template_id'),
            case_classification_id=dct.get('case_classification_id'),
            update_case_acs=dct.get('update_case_acs', True),
            update_case_summary=dct.get('update_case_summary', True),
            append_case_custom_attributes=dct.get(
                'append_case_custom_attributes', True
            ),
        )


@dataclass(kw_only=True)
class IronProxyConfig(Loadable):
    """Iron proxy configuration"""

    server: FusionServerConfig
    storage: FusionStorageConfig
    auth_api: FusionAuthAPIConfig
    case_api: FusionCaseAPIConfig
    info_api: FusionInfoAPIConfig
    iris_client: IRISClientConfig

    @classmethod
    def from_dict(cls, dct: dict) -> Self:
        return cls(
            server=FusionServerConfig.from_dict(dct['server']),
            storage=FusionStorageConfig.from_dict(dct['storage']),
            auth_api=FusionAuthAPIConfig.from_dict(dct['auth_api']),
            case_api=FusionCaseAPIConfig.from_dict(dct['case_api']),
            info_api=FusionInfoAPIConfig.from_dict(dct['info_api']),
            iris_client=IRISClientConfig.from_dict(dct['iris_client']),
        )

    def setup(self, webapp: Application):
        """Register config in webapp context"""
        webapp[_PROXY_CONFIG] = self


def get_proxy_config(app_or_req: Application | Request) -> IronProxyConfig:
    """Retrieve config from request webapp context"""
    if isinstance(app_or_req, Request):
        app_or_req = app_or_req.app
    return app_or_req[_PROXY_CONFIG]
