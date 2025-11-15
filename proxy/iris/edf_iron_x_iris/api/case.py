"""/api/case* routes implementation"""

from edf_fusion.concept import Case
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.case import (
    AttachContext,
    CreateContext,
    DeleteContext,
    EnumerateContext,
    RetrieveContext,
    UpdateContext,
)

from ..client import get_iris_client

_LOGGER = get_logger('api.case', root='iron_x_iris')


async def attach_case_impl(ctx: AttachContext) -> Case | None:
    """Attach case"""
    iris_client = get_iris_client(ctx.request)
    return await iris_client.attach_case(ctx.case_guid, ctx.next_case_guid)


async def create_case_impl(ctx: CreateContext) -> Case | None:
    """Create case"""
    iris_client = get_iris_client(ctx.request)
    return await iris_client.create_case(ctx.managed, ctx.body)


async def update_case_impl(ctx: UpdateContext) -> Case | None:
    """Update case"""
    iris_client = get_iris_client(ctx.request)
    return await iris_client.update_case(ctx.case_guid, ctx.body)


async def delete_case_impl(ctx: DeleteContext) -> bool:
    """Delete case"""
    iris_client = get_iris_client(ctx.request)
    return await iris_client.delete_case(ctx.case_guid)


async def retrieve_case_impl(ctx: RetrieveContext) -> Case | None:
    """Retrieve case"""
    iris_client = get_iris_client(ctx.request)
    return await iris_client.retrieve_case(ctx.case_guid)


async def enumerate_cases_impl(ctx: EnumerateContext) -> list[Case]:
    """Enumerate cases"""
    iris_client = get_iris_client(ctx.request)
    return [case async for case in iris_client.enumerate_cases()]
