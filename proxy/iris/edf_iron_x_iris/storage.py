"""Helium Storage"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from edf_fusion.helper.filesystem import iter_guid_items
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.config import FusionStorageConfig
from edf_fusion.server.storage import ConceptStorage, FusionStorage

from .concept import Case

_LOGGER = get_logger('storage', root='iron_x_iris')


@dataclass(kw_only=True)
class CaseStorage(ConceptStorage):
    """Case Storage"""


@dataclass(kw_only=True)
class Storage(FusionStorage):
    """File System Storage"""

    config: FusionStorageConfig

    def case_storage(self, case_guid: UUID) -> CaseStorage:
        """Retrieve case storage"""
        directory = self.config.directory / str(case_guid)
        return CaseStorage(directory=directory)

    async def attach_case(
        self, case_guid: UUID, next_case_guid: UUID
    ) -> Case | None:
        raise NotImplementedError("operation not supported!")

    async def create_case(self, managed: bool, dct) -> Case | None:
        if not managed:
            _LOGGER.error("managed cases only!")
            return None
        case = Case.from_dict(dct)
        case_storage = self.case_storage(case.guid)
        case_storage.create()
        case.to_filepath(case_storage.metadata)
        return case

    async def update_case(self, case_guid: UUID, dct) -> Case | None:
        case_storage = self.case_storage(case_guid)
        metadata = case_storage.metadata
        if not metadata.is_file():
            _LOGGER.error("case metadata not found: %s", metadata)
            return None
        case = Case.from_filepath(metadata)
        case.update(dct)
        case.to_filepath(metadata)
        return case

    async def delete_case(self, case_guid: UUID):
        """Remove case from storage"""
        case_storage = self.case_storage(case_guid)
        case_storage.remove()

    async def retrieve_case(self, case_guid: UUID) -> Case | None:
        case_storage = self.case_storage(case_guid)
        metadata = case_storage.metadata
        if not metadata.is_file():
            _LOGGER.error("case metadata not found: %s", metadata)
            return None
        return Case.from_filepath(metadata)

    async def enumerate_cases(self) -> AsyncIterator[Case]:
        for directory in iter_guid_items(self.config.directory):
            if not directory.is_dir():
                continue
            metadata = CaseStorage(directory=directory).metadata
            if not metadata.is_file():
                continue
            yield Case.from_filepath(metadata)
