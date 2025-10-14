"""Iron Connector"""

from dataclasses import dataclass
from functools import cached_property

from aiohttp.web import Application, Request
from edf_fusion.client import (
    FusionCaseAPIClient,
    FusionClient,
    FusionClientConfig,
    create_session,
)
from edf_fusion.concept import Case
from edf_fusion.helper.logging import get_logger

from .config import ConnectorConfig

_LOGGER = get_logger('server.connector', root='iron')
_IRON_CONNECTORS = '__iron_connectors'


@dataclass(kw_only=True)
class IronConnector:
    """Iron Connector"""

    config: ConnectorConfig
    fusion_client: FusionClient | None = None

    @cached_property
    def name(self) -> str:
        """Connector service name"""
        return self.config.service.name

    @cached_property
    def case_api(self) -> FusionCaseAPIClient:
        """Case API"""
        return FusionCaseAPIClient(
            case_cls=Case, fusion_client=self.fusion_client
        )

    async def client_ctx(self, _app: Application):
        """Iron connector client context"""
        client_config = FusionClientConfig(
            api_url=self.config.service.api_url,
            api_key=self.config.api_key,
            api_ssl=self.config.api_ssl,
        )
        session = create_session(client_config)
        async with session:
            self.fusion_client = FusionClient(
                config=client_config, session=session
            )
            yield
            self.fusion_client = None


def setup_connectors(webapp: Application, connectors: list[ConnectorConfig]):
    """Setup webapp connectors"""
    _LOGGER.info("install iron connectors...")
    # instanciate and register iron connectors from config
    iron_connectors = {
        connector_config.service.name: IronConnector(config=connector_config)
        for connector_config in connectors
    }
    webapp[_IRON_CONNECTORS] = iron_connectors
    # clients
    for iron_connector in iron_connectors.values():
        webapp.cleanup_ctx.append(iron_connector.client_ctx)
    _LOGGER.info("iron connectors installed.")


def get_connectors(request: Request) -> dict[str, IronConnector]:
    """Retrieve iron connectors from request"""
    return request.app[_IRON_CONNECTORS]
