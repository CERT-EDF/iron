"""Iron x DFIR IRIS Case"""

from dataclasses import dataclass

from edf_fusion.concept import Case as FusionCase


@dataclass(kw_only=True)
class Case(FusionCase):
    """Iron x DFIR IRIS Case"""

    iris_id: int | None = None

    @classmethod
    def from_dict(cls, dct):
        metadata = super().from_dict(dct)
        metadata.iris_id = dct.get('iris_id')
        return metadata

    def to_dict(self):
        dct = super().to_dict()
        dct.update({'iris_id': self.iris_id})
        return dct
