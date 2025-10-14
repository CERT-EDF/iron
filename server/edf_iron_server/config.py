"""Iron Server Configuration"""

from dataclasses import dataclass
from ssl import SSLContext

from aiohttp import Fingerprint
from aiohttp.web import Application, Request
from edf_fusion.helper.config import load_ssl_config
from edf_fusion.helper.logging import get_logger
from edf_fusion.helper.serializing import Loadable
from edf_fusion.server.auth import FusionAuthAPIConfig
from edf_fusion.server.config import (
    FusionServerConfig,
    FusionStorageConfig,
    FusionSynchronizerConfig,
)
from edf_fusion.server.constant import FusionConstantAPIConfig
from edf_fusion.server.event import FusionEventAPIConfig
from edf_fusion.server.info import FusionInfoAPIConfig
from edf_iron_core.concept import Service
from yarl import URL

_LOGGER = get_logger('server.config', root='iron')
_IRON_CONFIG = '__iron_config'


@dataclass(kw_only=True)
class ConnectorConfig(Loadable):
    """Connector Config"""

    service: Service
    api_key: str
    api_ssl: Fingerprint | SSLContext | bool

    @classmethod
    def from_dict(cls, dct):
        api_ssl = load_ssl_config(dct['api_ssl'])
        return cls(
            service=Service(
                name=dct['name'],
                xref=dct.get('xref'),
                api_url=URL(dct['api_url']),
                metadata=dct.get('metadata', {}),
            ),
            api_key=dct['api_key'],
            api_ssl=api_ssl,
        )


@dataclass(kw_only=True)
class IronServerConfig(Loadable):
    """Iron Server Config"""

    server: FusionServerConfig
    storage: FusionStorageConfig
    auth_api: FusionAuthAPIConfig
    info_api: FusionInfoAPIConfig
    event_api: FusionEventAPIConfig
    constant_api: FusionConstantAPIConfig
    connectors: list[ConnectorConfig]
    synchronizer: FusionSynchronizerConfig

    @classmethod
    def from_dict(cls, dct):
        return cls(
            server=FusionServerConfig.from_dict(dct['server']),
            storage=FusionStorageConfig.from_dict(dct['storage']),
            auth_api=FusionAuthAPIConfig.from_dict(dct['auth_api']),
            info_api=FusionInfoAPIConfig.from_dict(dct['info_api']),
            event_api=FusionEventAPIConfig.from_dict(dct['event_api']),
            constant_api=FusionConstantAPIConfig.from_dict(
                dct['constant_api']
            ),
            connectors=[
                ConnectorConfig.from_dict(item) for item in dct['connectors']
            ],
            synchronizer=FusionSynchronizerConfig.from_dict(
                dct['synchronizer']
            ),
        )

    def setup(self, webapp: Application):
        """Setup webapp configuration"""
        _LOGGER.info("install webapp config...")
        webapp[_IRON_CONFIG] = self
        _LOGGER.info("webapp config installed.")


def get_iron_config(app_or_req: Application | Request) -> IronServerConfig:
    """Retrieve config from webapp context"""
    if isinstance(app_or_req, Request):
        app_or_req = app_or_req.app
    return app_or_req[_IRON_CONFIG]
