"""DFIR IRIS Async Client"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any
from uuid import UUID

from aiohttp import ClientResponse, ClientResponseError, ClientSession
from aiohttp.web import Application, Request
from edf_fusion.helper.logging import get_logger
from edf_fusion.server.storage import get_fusion_storage

from .concept import Case
from .config import IRISClientConfig, get_proxy_config
from .storage import Storage

_LOGGER = get_logger('client', root='iron_x_iris')
_IRIS_CLIENT = '__iris_client'
_DENY_ALL = 1
_FULL_ACCESS = 4


@dataclass(kw_only=True)
class IRISClient:
    """DFIR IRIS Client"""

    config: IRISClientConfig
    session: ClientSession
    storage: Storage

    def _request_kwargs(self, **kwargs):
        req_kwargs = {
            'ssl': self.config.api_ssl,
        }
        req_kwargs.update(kwargs)
        return req_kwargs

    async def _handle_json_response(self, resp: ClientResponse) -> Any:
        try:
            body = await resp.json()
        except (JSONDecodeError, ClientResponseError):
            body = None
        if body is None or resp.status != 200 or body['status'] != 'success':
            _LOGGER.error(
                "iris api error: status=%d, body=%s", resp.status, body
            )
            return None
        return body.get('data')

    async def _case_summary_update(self, iris_cid: int, summary: str) -> bool:
        kwargs = self._request_kwargs()
        kwargs['json'] = {'case_description': summary}
        kwargs['params'] = {'cid': str(iris_cid)}
        endpoint = '/case/summary/update'
        async with self.session.post(endpoint, **kwargs) as resp:
            data = await self._handle_json_response(resp)
            return bool(data)

    async def _manage_cases_add(self, case: Case) -> dict | None:
        kwargs = self._request_kwargs()
        dct = {
            'case_soc_id': case.tsid,
            'case_customer': self.config.case_customer_id,
            'case_name': case.name,
            'case_description': case.description,
        }
        if self.config.case_template_id is not None:
            # https://github.com/dfir-iris/iris-web/issues/482
            dct['case_template_id'] = str(self.config.case_template_id)
        if self.config.case_classification_id is not None:
            dct['classification_id'] = self.config.case_classification_id
        if self.config.append_case_custom_attributes:
            dct['custom_attributes'] = {'Iron': {'GUID': str(case.guid)}}
        kwargs['json'] = dct
        endpoint = '/manage/cases/add'
        async with self.session.post(endpoint, **kwargs) as resp:
            return await self._handle_json_response(resp)

    async def _manage_cases_list(self) -> AsyncIterator[dict]:
        kwargs = self._request_kwargs()
        kwargs['params'] = {'page': 1}
        endpoint = '/manage/cases/filter'
        while True:
            async with self.session.get(endpoint, **kwargs) as resp:
                data = await self._handle_json_response(resp)
                for iris_case in data['cases']:
                    yield iris_case
                if not data['next_page']:
                    break
                kwargs['params'] = {'page': data['next_page']}

    async def _manage_cases_filter(self, iris_cids: set[int]) -> dict | None:
        if not iris_cids:
            return None
        kwargs = self._request_kwargs()
        kwargs['params'] = {'case_ids': ','.join(map(str, iris_cids))}
        endpoint = '/manage/cases/filter'
        async with self.session.get(endpoint, **kwargs) as resp:
            return await self._handle_json_response(resp)

    async def _manage_cases_close(self, iris_cid: int) -> dict | None:
        kwargs = self._request_kwargs()
        endpoint = f'/manage/cases/close/{iris_cid}'
        async with self.session.post(endpoint, **kwargs) as resp:
            return await self._handle_json_response(resp)

    async def _manage_cases_reopen(self, iris_cid: int) -> dict | None:
        kwargs = self._request_kwargs()
        endpoint = f'/manage/cases/reopen/{iris_cid}'
        async with self.session.post(endpoint, **kwargs) as resp:
            return await self._handle_json_response(resp)

    async def _manage_cases_update(self, iris_cid: int, dct) -> dict | None:
        kwargs = self._request_kwargs()
        kwargs['json'] = dct
        endpoint = f'/manage/cases/update/{iris_cid}'
        async with self.session.post(endpoint, **kwargs) as resp:
            return await self._handle_json_response(resp)

    async def _manage_cases_delete(self, iris_cid: int) -> bool:
        kwargs = self._request_kwargs()
        endpoint = f'/manage/cases/delete/{iris_cid}'
        async with self.session.post(endpoint, **kwargs) as resp:
            data = await self._handle_json_response(resp)
            return isinstance(data, list)

    async def _manage_users(self, iris_uid: int) -> dict | None:
        kwargs = self._request_kwargs()
        endpoint = f'/manage/users/{iris_uid}'
        async with self.session.get(endpoint, **kwargs) as resp:
            return await self._handle_json_response(resp)

    async def _manage_users_list(self) -> list | None:
        kwargs = self._request_kwargs()
        endpoint = '/manage/users/list'
        async with self.session.get(endpoint, **kwargs) as resp:
            return await self._handle_json_response(resp)

    async def _manage_users_case_access_update(
        self, iris_cid: int, iris_uid: int, access_level: int
    ) -> bool:
        kwargs = self._request_kwargs()
        kwargs['json'] = {
            'cases_list': [iris_cid],
            'access_level': access_level,
        }
        endpoint = f'/manage/users/{iris_uid}/cases-access/update'
        async with self.session.post(endpoint, **kwargs) as resp:
            data = await self._handle_json_response(resp)
            return data is not None

    async def attach_case(
        self, case_guid: UUID, next_case_guid: UUID
    ) -> Case | None:
        """Attach case"""
        case = None
        async for iris_case in self._manage_cases_list():
            iron_guid = (
                iris_case.get('custom_attributes', {})
                .get('Iron', {})
                .get('GUID', {})
                .get('value')
            )
            if not iron_guid:
                continue
            iron_guid = UUID(iron_guid)
            if case_guid != iron_guid:
                continue
            case = Case(
                guid=next_case_guid,
                managed=True,
                tsid=iris_case['soc_id'],
                name=iris_case['name'],
                description=iris_case['description'],
                iris_id=iris_case['case_id'],
            )
            case = await self.storage.create_case(True, case.to_dict())
        return case

    async def create_case(self, managed: bool, dct) -> Case | None:
        """Create case"""
        if not managed:
            _LOGGER.error("managed cases only!")
            return None
        case = Case.from_dict(dct)
        iris_case = await self._manage_cases_add(case)
        if not iris_case:
            _LOGGER.error("failed to create iris case!")
            return None
        case.iris_id = iris_case['case_id']
        return await self.storage.create_case(managed, case.to_dict())

    async def _case_user_access_retrieve(
        self, iris_cid: int
    ) -> tuple[dict[str, int], set[str]]:
        l_id_map = {}
        l_can_access = set()
        everyone = await self._manage_users_list()
        for someone in everyone:
            iris_uid = someone['user_id']
            if iris_uid in self.config.unmanaged_uids:
                continue
            u_info = await self._manage_users(iris_uid)
            u_login = u_info['user_login'].lower()
            l_id_map[u_login] = iris_uid
            for c_info in u_info['user_cases_access']:
                if c_info['case_id'] != iris_cid:
                    continue
                if c_info['access_level'] != _FULL_ACCESS:
                    continue
                l_can_access.add(u_login)
                break
        return l_id_map, l_can_access

    async def _case_user_set_access(
        self, iris_cid: int, iris_ids: list[tuple[str, int]], access_level: int
    ) -> bool:
        success = True
        for iris_login, iris_uid in iris_ids:
            access_set = await self._manage_users_case_access_update(
                iris_cid, iris_uid, access_level
            )
            logger_func = _LOGGER.info if access_set else _LOGGER.warning
            result = "set" if access_set else "cannot set"
            logger_func(
                "%s (cid=%d, uid=%d, login=%s, access_level=%d)",
                result,
                iris_cid,
                iris_uid,
                iris_login,
                access_level,
            )
            success = success and access_set
        return success

    async def _case_user_access_update(
        self, iris_cid: int, acs: set[str]
    ) -> bool:
        l_id_map, l_can_access = await self._case_user_access_retrieve(
            iris_cid
        )
        # case acs is empty, grant access to every iris users
        if not acs:
            return await self._case_user_set_access(
                iris_cid, list(l_id_map.items()), _FULL_ACCESS
            )
        # case acs does not contain known iris users
        if not acs.intersection(l_id_map.keys()):
            _LOGGER.warning("case acs does not contain known iris users")
            return False
        # case acs contains users, deny user access if needed
        iris_ids = [
            (u_login, l_id_map[u_login])
            for u_login in l_can_access.difference(acs)
        ]
        denied = await self._case_user_set_access(
            iris_cid, iris_ids, _DENY_ALL
        )
        # case acs contains users, grant user access if needed
        iris_ids = [
            (u_login, l_id_map[u_login])
            for u_login in acs.difference(l_can_access)
            if u_login in l_id_map
        ]
        granted = await self._case_user_set_access(
            iris_cid, iris_ids, _FULL_ACCESS
        )
        return denied and granted

    async def update_case(self, case_guid: UUID, dct) -> Case | None:
        """Update case"""
        case = await self.storage.retrieve_case(case_guid)
        if not case:
            return None
        closed = dct.get('closed', case.closed)
        # cannot update closed case
        if case.closed and closed:
            _LOGGER.error("cannot update closed case!")
            return None
        # reopen case if needed
        if case.closed and not closed:
            iris_case = await self._manage_cases_reopen(case.iris_id)
            if not iris_case:
                _LOGGER.error("failed to reopen iris case!")
                return None
        # close case if needed
        if closed and not case.closed:
            iris_case = await self._manage_cases_close(case.iris_id)
            if not iris_case:
                _LOGGER.error("failed to close iris case!")
                return None
        # update case description
        if self.config.update_case_summary and 'description' in dct:
            updated = await self._case_summary_update(
                case.iris_id, dct['description']
            )
            if not updated:
                _LOGGER.error("failed to update case description!")
                return None
        # update case acs
        access_set = False
        if (
            self.config.api_as_admin
            and self.config.update_case_acs
            and 'acs' in dct
        ):
            access_set = await self._case_user_access_update(
                case.iris_id, set(dct['acs'])
            )
        if not access_set:
            _LOGGER.warning("cannot or failed to set access!")
        # update iris case
        iris_dct = {}
        if 'name' in dct:
            iris_dct['case_name'] = dct['name']
        if 'tsid' in dct:
            iris_dct['case_soc_id'] = dct['tsid']
        if iris_dct:
            iris_case = await self._manage_cases_update(case.iris_id, iris_dct)
            if not iris_case:
                _LOGGER.error("failed to update iris case!")
                return None
        # update stored case
        return await self.storage.update_case(case.guid, dct)

    async def delete_case(self, case_guid: UUID) -> bool:
        """Delete case"""
        case = await self.storage.retrieve_case(case_guid)
        if not case:
            return None
        deleted = await self._manage_cases_delete(case.iris_id)
        if not deleted:
            return False
        await self.storage.delete_case(case_guid)
        return True

    async def retrieve_case(self, case_guid: UUID) -> Case | None:
        """Retrieve case"""
        case = await self.storage.retrieve_case(case_guid)
        if not case:
            return None
        message = await self._manage_cases_filter({case.iris_id})
        if not message:
            return None
        if not message['cases']:
            _LOGGER.warning(
                "failed to retrieve case %d from iris", case.iris_id
            )
            await self.storage.delete_case(case.guid)
            return None
        return case

    async def enumerate_cases(self) -> AsyncIterator[Case]:
        """Enumerate cases"""
        async for case in self.storage.enumerate_cases():
            message = await self._manage_cases_filter({case.iris_id})
            if not message:
                continue
            if not message['cases']:
                _LOGGER.warning(
                    "failed to retrieve case %d from iris", case.iris_id
                )
                await self.storage.delete_case(case.guid)
                continue
            yield case


async def _iris_client_context(webapp: Application):
    _LOGGER.info("iris client startup")
    config = get_proxy_config(webapp)
    storage = get_fusion_storage(webapp)
    headers = {'Authorization': f'Bearer {config.iris_client.api_key}'}
    async with ClientSession(
        base_url=config.iris_client.api_url, headers=headers
    ) as session:
        webapp[_IRIS_CLIENT] = IRISClient(
            config=config.iris_client, session=session, storage=storage
        )
        yield
        _LOGGER.info("iris client startup")


def setup_iris_client(webapp: Application):
    """DFIR IRIS client context"""
    _LOGGER.info("setup iris client")
    webapp.cleanup_ctx.append(_iris_client_context)


def get_iris_client(request: Request) -> IRISClient:
    """Retrieve DFIR IRIS client from request context"""
    return request.app[_IRIS_CLIENT]
