"""CP2K 2026.1 file values, separate from Bash quoting and general strings.

Only the file keywords currently emitted by Studio are handled here.
These use CP2K long-character values (whole line), not Shell string literals.
See docs/file-reference-fix.md for the versioned keyword/parser sources.
"""
from i18n.messages import i18n_msg, i18n_join
from dataclasses import dataclass
from pathlib import Path
import re
import sys


FILE_KEYWORDS = {
    ('EXT_RESTART',): {'RESTART_FILE_NAME'},
    ('FORCE_EVAL', 'DFT'): {'BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME'},
    ('FORCE_EVAL', 'SUBSYS', 'TOPOLOGY'): {'COORD_FILE_NAME'},
}


class FileReferenceError(ValueError):
    pass


def serialize_file_reference(value, keyword):
    if keyword not in set.union(*FILE_KEYWORDS.values()):
        raise FileReferenceError(i18n_msg('No file-keyword serialization rule is defined for {p0}', code='studio.6cba4fab0637f991', p0=keyword))
    # Long-character input allows single internal spaces. Reject everything
    # requiring quoting/preprocessing or ambiguous whitespace normalization.
    # Do not strip or expand a value after checking: its literal spelling is
    # also what the final dependency checker must open.
    # Windows user/OneDrive folders may contain Unicode letters and digits.
    # Keep separators/metacharacter restrictions and all POSIX behavior intact.
    path_pattern = r'[\w./: -]+' if sys.platform == 'win32' else r'[A-Za-z0-9_./: -]+'
    if (not isinstance(value, str) or not value or value != value.strip()
            or '  ' in value or not re.fullmatch(path_pattern, value)):
        raise FileReferenceError(i18n_msg('{p0}: path cannot be safely written directly into CP2K INP: {p1!r}. Export a complete package to normalize filenames, or rename the source file first.', code='studio.56ceeae123ffa617', p0=keyword, p1=value))
    return value


def safe_resource_name(name):
    """Portable basename only; callers prefix a unique index for collisions."""
    cleaned = re.sub(r'[^A-Za-z0-9_.-]', '_', name).strip('.')
    return cleaned[:100] or 'resource.dat'


@dataclass(frozen=True)
class FileReference:
    section: tuple[str, ...]
    keyword: str
    value: str


def generated_file_references(text):
    """Inspect final Studio-generated text, retaining literal quote characters.

    This is deliberately limited to our generated Section subset, not an
    alternative general CP2K/preprocessor parser. XML validation stays separate.
    """
    stack = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('!', '#')):
            continue
        parts = line.split(maxsplit=1)
        key = parts[0].upper()
        if key == '&END':
            if stack:
                stack.pop()
        elif key.startswith('&'):
            stack.append(key[1:])
        elif key in FILE_KEYWORDS.get(tuple(stack), set()):
            yield FileReference(tuple(stack), key, parts[1] if len(parts) == 2 else '')


def check_generated_dependencies(text, base_dir, *, require_relative=False):
    """Open the final literal filenames from the exported run directory."""
    base = Path(base_dir).resolve()
    errors = []
    for ref in generated_file_references(text):
        location = i18n_join('/', (*ref.section, ref.keyword))
        try:
            value = serialize_file_reference(ref.value, ref.keyword)
            path = Path(value)
            if require_relative and (path.is_absolute() or '..' in path.parts):
                raise ValueError(i18n_msg('A complete package INP must use paths relative to the package', code='studio.3f502bfeae6d9c1a'))
            path = path if path.is_absolute() else base / path
            if require_relative and not path.resolve().is_relative_to(base):
                raise ValueError(i18n_msg('The reference resolves outside the package', code='studio.2f7bb880fed4faa9'))
            with path.open('rb') as handle:
                handle.read(1)
        except (OSError, ValueError) as exc:
            errors.append(i18n_msg('{p0}: dependency is inaccessible: {p1!r} (working directory {p2}): {p3}', code='studio.5c8624e46e9af3fd', p0=location, p1=ref.value, p2=base, p3=exc))
    return errors
