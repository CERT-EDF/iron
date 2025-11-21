"""Iron Client"""

from dataclasses import dataclass
from uuid import UUID

from edf_fusion.client import FusionClient
from edf_fusion.concept import Case
from edf_fusion.helper.logging import get_logger
from edf_iron_core.concept import Service


_LOGGER = get_logger('client', root='test')


@dataclass(kw_only=True)
class IronClient:
    """Iron Client"""

    fusion_client: FusionClient

    async def create_case(self, case: Case) -> Case | None:
        """Create a case"""
        _LOGGER.info("creating case %s", case.guid)
        endpoint = '/api/case'
        return await self.fusion_client.post(
            endpoint, concept=case, concept_cls=Case
        )

    async def update_case(self, case: Case) -> Case | None:
        """Update an existing case"""
        _LOGGER.info("updating case %s", case.guid)
        endpoint = f'/api/case/{case.guid}'
        return await self.fusion_client.put(
            endpoint, concept=case, concept_cls=Case
        )

    async def delete_case(self, case_guid: UUID) -> bool:
        """Delete an existing case"""
        _LOGGER.info("deleting case %s", case_guid)
        endpoint = f'/api/case/{case_guid}'
        return await self.fusion_client.delete(endpoint)

    async def retrieve_case(self, case_guid: UUID) -> Case | None:
        """Retrieve case information"""
        _LOGGER.info("retrieving case %s", case_guid)
        endpoint = f'/api/case/{case_guid}'
        return await self.fusion_client.get(
            endpoint, concept_cls=Case
        )

    async def enumerate_cases(self) -> list[Case]:
        """Enumerate cases"""
        _LOGGER.info("enumerating cases")
        endpoint = '/api/cases'
        return await self.fusion_client.get(
            endpoint, concept_cls=Case
        )

    async def enumerate_services(self) -> list[Service] | None:
        """Enumerate services"""
        endpoint = '/api/services'
        return await self.fusion_client.get(endpoint, concept_cls=Service)

    async def enumerate_service_cases(
        self, service: Service
    ) -> list[Case] | None:
        """Enumerate service cases"""
        endpoint = f'/api/service/{service.name}/cases'
        return await self.fusion_client.get(endpoint, concept_cls=Case)

    async def sync_service_case(
        self, service: Service, case_guid: UUID
    ) -> Case | None:
        """Sync service case"""
        _LOGGER.info("syncing case %s in service %s", case_guid, service.name)
        endpoint = f'/api/service/{service.name}/case/{case_guid}'
        return await self.fusion_client.post(endpoint, concept_cls=Case)

    async def delete_service_case(
        self, service: Service, case_guid: UUID
    ) -> bool:
        """Delete service case"""
        _LOGGER.info("deleting case %s in service %s", case_guid, service.name)
        endpoint = f'/api/service/{service.name}/case/{case_guid}'
        return await self.fusion_client.delete(endpoint)

    async def probe_service_case(
        self, service: Service, case_guid: UUID
    ) -> Case | None:
        """Probe service case"""
        endpoint = f'/api/service/{service.name}/case/{case_guid}'
        return await self.fusion_client.get(endpoint, concept_cls=Case)

    async def attach_service_case(
        self, service: Service, case_guid: UUID, next_case_guid: UUID
    ) -> Case | None:
        """Attach service case"""
        _LOGGER.info(
            "attaching case %s in service %s to %s",
            case_guid,
            service.name,
            next_case_guid,
        )
        endpoint = f'/api/service/{service.name}/case/{case_guid}/attach/{next_case_guid}'
        return await self.fusion_client.put(endpoint, concept_cls=Case)
