"""Structured diagnostics independent of the selected display language.

Message is string-compatible for existing validation consumers. Its canonical
string preserves the historical diagnostic spelling, while code/source/params
retain everything needed to render either language without rerunning a check.
User names, paths, CP2K keywords, and numeric values are always parameters.
"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from core.resources import resource_path
import copy
import xml.etree.ElementTree as ET


@lru_cache(maxsize=1)
def _canonical_catalog():
    path = resource_path('i18n', 'cp2kstudio_zh_CN.ts')
    if not path.is_file():
        return {}
    return {(m.findtext('comment') or '', m.findtext('source') or ''): m.findtext('translation') or ''
            for m in ET.parse(path).findall('.//message')}


def _value(value, language):
    if isinstance(value, Message):
        return value.render(language)
    if isinstance(value, BaseException):
        return _value(i18n_str(value), language)
    return value


class Message(str):
    def __new__(cls, source, params=None, code=None):
        # Never retain exception tracebacks (which can retain GUI objects) in
        # a report delivered by a worker thread. Keep only the structured error.
        params = {k: i18n_str(v) if isinstance(v, BaseException) else v for k, v in (params or {}).items()}
        code = code or 'studio.' + sha256(source.encode()).hexdigest()[:16]
        canonical = _canonical_catalog().get((code, source), source)
        text = canonical.format_map({k: _value(v, 'canonical') for k, v in params.items()})
        obj = str.__new__(cls, text)
        obj.source, obj.params, obj.code = source, params, code
        return obj

    def render(self, language=None):
        if language == 'canonical':
            return str.__str__(self)
        from i18n.language_manager import language_manager
        template = language_manager().translate(self.source, self.code, language)
        values = {k: _value(v, language) for k, v in self.params.items()}
        try:
            return template.format_map(values)
        except (KeyError, ValueError, IndexError):
            return self.source.format_map(values)

    def to_dict(self):
        return {'code': self.code, 'source': self.source,
                'parameters': {k: v.to_dict() if isinstance(v, Message) else str(v) for k, v in self.params.items()}}

    def __add__(self, other):
        if not isinstance(other, str):
            return NotImplemented
        return Message('{p0}{p1}', {'p0': self, 'p1': other}, 'composite.concat')

    def __radd__(self, other):
        if not isinstance(other, str):
            return NotImplemented
        return Message('{p0}{p1}', {'p0': other, 'p1': self}, 'composite.concat')

    def __deepcopy__(self, memo):
        return Message(self.source, copy.deepcopy(self.params, memo), self.code)

    def __reduce__(self):
        return Message, (self.source, self.params, self.code)


def i18n_msg(source, *, code=None, **params):
    return Message(source, params, code)


def i18n_str(value=''):
    if isinstance(value, Message):
        return value
    if isinstance(value, BaseException) and len(value.args) == 1 and isinstance(value.args[0], Message):
        return value.args[0]
    # Pydantic retains the originating ValueError in ctx even though msg is text.
    if hasattr(value, 'errors') and callable(value.errors):
        try:
            issues = value.errors(include_url=False)
        except TypeError:
            issues = []
        if issues:
            return i18n_join('\n', [i18n_msg('{p0}: {p1}', p0='.'.join(map(str, e['loc'])),
                p1=i18n_str(e.get('ctx', {}).get('error')) if e.get('ctx', {}).get('error') else e['msg']) for e in issues])
    return str(value)


def i18n_join(separator, values):
    values = list(values)
    if separator == '、':
        separator = i18n_msg(', ')
    if not any(isinstance(v, Message) for v in values) and not isinstance(separator, Message):
        return separator.join(values)
    parts = []
    for index, value in enumerate(values):
        if index:
            parts.append(separator)
        parts.append(value)
    return Message(''.join('{p'+str(i)+'}' for i in range(len(parts))),
                   {'p'+str(i): part for i, part in enumerate(parts)}, 'composite.join')


def i18n_render(value, language=None):
    value = i18n_str(value)
    return value.render(language) if isinstance(value, Message) else value
