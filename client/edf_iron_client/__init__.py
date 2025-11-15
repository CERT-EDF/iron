"""Iron Client"""

from dataclasses import dataclass
from uuid import UUID

from edf_fusion.client import FusionClient
from edf_fusion.concept import Case
from edf_iron_core.concept import Service


@dataclass(kw_only=True)
class IronClient:
    """Iron Client"""

    fusion_client: FusionClient

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
        endpoint = f'/api/service/{service.name}/case/{case_guid}'
        return await self.fusion_client.post(endpoint, concept_cls=Case)

    async def delete_service_case(
        self, service: Service, case_guid: UUID
    ) -> bool:
        """Delete service case"""
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
        endpoint = f'/api/service/{service.name}/case/{case_guid}/attach/{next_case_guid}'
        return await self.fusion_client.put(endpoint, concept_cls=Case)
