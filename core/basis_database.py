"""Gaussian basis parser: consume nset, shell dimensions and exponent rows."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from functools import lru_cache
from pathlib import Path
from hashlib import sha256
import re
from ase.data import atomic_numbers
from core.database_format import Lines, DatabaseFormatError, ParsedEntries, number, entry


def _parse_lines(lines):
    result = []
    issues = []
    while lines.pos < len(lines.rows):
        element, names = lines.header(allow_unknown=True)
        start = lines.pos
        if lines.pos < len(lines.rows) and lines.rows[lines.pos][1] == 'NA':
            lines.take()
            issues.append(i18n_msg('{p0} {p1} is marked NA, unavailable, and excluded', code='studio.4df4ef0ad0087f73', p0=element, p1=names[0]))
            continue
        nset, = lines.ints(1)
        if not 1 <= nset <= 100:
            raise DatabaseFormatError(i18n_msg('Basis nset must be in 1..100', code='studio.02fe2d8bcf3b6864'))
        for _ in range(nset):
            tokens = lines.take()
            if len(tokens) < 5:
                raise DatabaseFormatError(i18n_msg('Missing basis shell dimensions', code='studio.42f4cac587132391'))
            try:
                n, lmin, lmax, nexp = map(int, tokens[:4])
                info = [n,lmin,lmax,nexp] + list(map(int,tokens[4:5+lmax-lmin]))
            except ValueError as exc:
                raise DatabaseFormatError(i18n_msg('Invalid shell integer', code='studio.397b316fc975e621')) from exc
            n, lmin, lmax, nexp = info[:4]
            if n < 0 or not 0 <= lmin <= lmax <= 10 or not 1 <= nexp <= 10000:
                raise DatabaseFormatError(i18n_msg('Invalid basis shell range', code='studio.e16caf839d6e84be'))
            if len(info) < 5 + lmax-lmin:
                raise DatabaseFormatError(i18n_msg('Insufficient contracted basis shells', code='studio.c15c3911b1df441a'))
            shells = info[4:5+lmax-lmin]  # CP2K ignores optional trailing orbital labels.
            if any(v < 0 for v in shells):
                raise DatabaseFormatError(i18n_msg('Negative contracted shell count', code='studio.dcd43afee5c13b0c'))
            for _ in range(nexp):
                values = [number(t) for t in lines.take()]
                if len(values) != 1 + sum(shells) or values[0] <= 0:
                    raise DatabaseFormatError(i18n_msg('Exponent or contraction coefficient count does not match the shell definition', code='studio.cb5f73dede3b02fc'))
        if element not in atomic_numbers:
            issues.append(i18n_msg('{p0} {p1} contains an invalid element symbol; no correction was guessed and the entry was excluded', code='studio.22fa676214235406', p0=element, p1=names[0]))
        else:
            result.append(entry(lines, 'basis', element, names, start))
    if not result and not issues:
        raise DatabaseFormatError(i18n_msg('Empty basis database', code='studio.4a38a45d40d4dab3'))
    return ParsedEntries(result, issues)


@lru_cache(maxsize=32)
def _parse(path,mtime,size,digest):
    lines=Lines(path)
    starts=[i for i,(_,row) in enumerate(lines.rows)
            if re.fullmatch(r'[A-Za-z]{1,2}\s+[A-Za-z0-9_+.,()/*=\-]+(?:\s+[A-Za-z0-9_+.,()/*=\-]+)*',row)]
    if not starts or starts[0]!=0:
        raise DatabaseFormatError(i18n_msg('No valid basis entry header found', code='studio.628c4b18903c763a'))
    result,issues=[],[]
    for start,end in zip(starts,starts[1:]+[len(lines.rows)]):
        chunk=object.__new__(Lines)
        chunk.path,chunk.file_sha256,chunk.pos=lines.path,lines.file_sha256,0
        chunk.rows=lines.rows[start:end]
        try:
            parsed=_parse_lines(chunk)
            result.extend(parsed);issues.extend(parsed.issues)
        except (ValueError,IndexError) as exc:
            issues.append(i18n_msg('{p0}: excluded after strict format check: {p1}', code='studio.d56214239ca55912', p0=lines.rows[start][1], p1=exc))
    if not result:
        raise DatabaseFormatError(i18n_join('; ', issues) or i18n_msg('Empty basis database', code='studio.4a38a45d40d4dab3'))
    return ParsedEntries(result,issues)


def parse_basis_file(path):
    p = Path(path).expanduser().resolve()
    stat = p.stat()
    return _parse(i18n_str(p), stat.st_mtime_ns, stat.st_size,sha256(p.read_bytes()).hexdigest())
