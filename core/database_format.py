"""Strict readers for CP2K's count-delimited Gaussian/GTH data formats."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
import re
from ase.data import atomic_numbers


class DatabaseFormatError(ValueError):
    pass


class ParsedEntries(tuple):
    def __new__(cls, entries, issues=()):
        result = super().__new__(cls, entries)
        result.issues = tuple(issues)
        return result


def number(token):
    try:
        value = Decimal(token.replace('D', 'E').replace('d', 'e'))
        if not value.is_finite():
            raise ValueError('non-finite')
        return value
    except (InvalidOperation, ValueError) as exc:
        raise DatabaseFormatError(i18n_msg('Invalid numeric value: {p0}', code='studio.7af3fb33081efbc3', p0=token)) from exc


class Lines:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        content = self.path.read_bytes()
        if len(content) > 50 * 1024 * 1024:
            raise DatabaseFormatError(i18n_msg('Database file exceeds 50 MB', code='studio.1c8a891c965af62d'))
        self.file_sha256 = sha256(content).hexdigest()
        self.rows = []
        for i, line in enumerate(content.decode('utf-8-sig').splitlines(), 1):
            clean = re.split('[#!]', line, maxsplit=1)[0].strip()
            if clean:
                self.rows.append((i, clean))
        self.pos = 0

    def take(self):
        if self.pos >= len(self.rows):
            raise DatabaseFormatError(i18n_msg('{p0}: data block ended early', code='studio.cc8cfb858d5ad3de', p0=self.path.name))
        line, value = self.rows[self.pos]
        self.pos += 1
        return value.split()

    def ints(self, count=None):
        values = self.take()
        if count is not None and len(values) != count:
            raise DatabaseFormatError(i18n_msg('Expected {p0} integers; got {p1}', code='studio.38220f73ff20225b', p0=count, p1=values))
        try:
            return [int(v) for v in values]
        except ValueError as exc:
            raise DatabaseFormatError(i18n_msg('Expected an integer; got {p0}', code='studio.1f3e3ebf433c601b', p0=values)) from exc

    def header(self, allow_unknown=False):
        values = self.take()
        if values:
            values[0] = values[0].capitalize()
        if len(values) < 2 or (not allow_unknown and values[0] not in atomic_numbers) or not re.fullmatch(r'[A-Z][a-z]?', values[0]) or values[0] == 'X':
            raise DatabaseFormatError(i18n_msg('{p0}: invalid entry header {p1}', code='studio.45be267617669551', p0=self.path.name, p1=values))
        if any(not re.fullmatch(r'[A-Za-z0-9_+.,()/*=\-]+', n) for n in values[1:]):
            raise DatabaseFormatError(i18n_msg('Invalid database name: {p0}', code='studio.4cb29e23744e7efd', p0=values[1:]))
        return values[0], tuple(dict.fromkeys(values[1:]))


@dataclass(frozen=True)
class DatabaseEntry:
    category: str
    element: str
    name: str
    aliases: tuple[str, ...]
    path: str
    file_sha256: str
    content_sha256: str
    payload: tuple[str, ...]
    version: str = ''
    source: str = ''
    quality: str = ''
    tags: tuple[str, ...] = ()
    q: int | None = None
    xc: str | None = None
    family: str = 'general'
    description: str = ''

    @property
    def names(self):
        return (self.name, *self.aliases)

    @property
    def key(self):
        return (self.element, self.name, self.path, self.content_sha256)

    def reference(self):
        return dict(path=self.path, sha256=self.file_sha256, entry_sha256=self.content_sha256,
                    version=self.version, source=self.source, pack=True)

    def render(self, names=None):
        return f'{self.element} {i18n_join(" ", names or self.names)}\n' + i18n_join('\n', self.payload) + '\n'


def entry(lines, category, element, names, start, *, q=None):
    payload = tuple(v for _, v in lines.rows[start:lines.pos])
    normalized = []
    for row in payload:
        tokens = []
        for token in row.split():
            try:
                tokens.append(i18n_str(number(token).normalize()))
            except DatabaseFormatError:
                tokens.append(token)  # NLCC and optional orbital labels on shell headers.
        normalized.append(i18n_join(' ', tokens))
    digest = sha256((i18n_join('\n', normalized)).encode()).hexdigest()
    q_values = {int(m.group(1)) for n in names for m in [re.search(r'-q(\d+)(?:$|[_-])', n, re.I)] if m}
    if len(q_values) > 1 or (q is not None and q_values and q not in q_values):
        raise DatabaseFormatError(i18n_msg('{p0} {p1}: name q value conflicts with the data', code='studio.5abfd053fae4e2db', p0=element, p1=names[0]))
    q = next(iter(q_values)) if q_values else q
    all_names = i18n_join(' ', names).upper()
    quality = next((tag for tag in ['QZVPP','QZV3P','QZV2P','QZVP','TZV2PX','TZV2P','TZVPP','TZVP','DZVP','SZV'] if tag in all_names), '')
    tags = tuple(t for t in ['MOLOPT', 'SR', 'GTH', 'ALL', 'UZH'] if re.search(rf'(?:^|[ _-]){t}(?:$|[ _-])', all_names))
    xc = next((x for x in ['PBE0','BLYP','PBE','PADE','LDA','SCAN'] if re.search(rf'(?:^|[-_ ]){x}(?:$|[-_ ])', all_names)), None)
    return DatabaseEntry(category, element, names[0], names[1:], i18n_str(lines.path), lines.file_sha256,
                         digest, payload, quality=quality, tags=tags, q=q, xc=xc,
                         family='UZH' if 'UZH' in lines.path.name.upper() else 'general',
                         description=f'{element} · {quality or category.upper()} · q={q if q is not None else i18n_msg('Cannot confirm automatically', code='studio.76835fdb33c70096')}' + (f' · {xc}' if xc else ''))
