"""Conservative suggestions from actual entries; never constructs a name."""
from i18n.messages import i18n_msg
from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    basis: object
    potential: object
    note: str


def recommend(catalog, element, xc):
    if not xc:
        return []
    candidates = []
    for basis in catalog.query('basis',element):
        # UZH is selectable and validated, but no independently verified
        # protocol table is shipped. Do not claim a protocol recommendation.
        if basis.family == 'UZH' or basis.xc is not None or 'GTH' not in basis.tags or basis.q is None:
            continue
        for potential in catalog.query('potential',element,xc=xc):
            if potential.family == 'UZH' or potential.q != basis.q or not potential.name.upper().startswith('GTH-'):
                continue
            note = {'SZV':i18n_msg('Relatively small basis', code='studio.c54b857416db6fc3'),'DZVP':i18n_msg('Conventional calculation candidate', code='studio.1b4eda0ff06a0337'),'TZVP':i18n_msg('Higher-quality candidate', code='studio.f65e68836452626e'),
                    'TZV2P':i18n_msg('Higher-quality candidate', code='studio.f65e68836452626e')}.get(basis.quality,i18n_msg('Available basis candidate', code='studio.50ad4c65aeb99ac1'))
            if 'SR' in basis.tags:
                note += i18n_msg(' · Short-range SR form', code='studio.3e5521b4f03bc04f')
            candidates.append(Recommendation(basis,potential,note+i18n_msg('; matching q and XC names', code='studio.1d688d06aa785a69')))
    order = {'DZVP':0,'TZVP':1,'TZV2P':2,'SZV':3}
    return sorted(candidates,key=lambda r:(order.get(r.basis.quality,4),r.basis.name,r.potential.name))
