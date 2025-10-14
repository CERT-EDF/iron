"""Service concept"""

from dataclasses import dataclass, field

from edf_fusion.concept import Concept
from yarl import URL


@dataclass(kw_only=True)
class Service(Concept):
    """Service"""

    name: str
    xref: str | None = None
    api_url: URL
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, dct):
        return cls(
            name=dct['name'],
            xref=dct.get('xref'),
            api_url=URL(dct['api_url']),
            metadata=dct.get('metadata', {}),
        )

    def to_dict(self):
        return {
            'name': self.name,
            'xref': self.xref,
            'api_url': str(self.api_url),
            'metadata': self.metadata,
        }

    def update(self, dct):
        raise RuntimeError("Service.update shall not be called")
