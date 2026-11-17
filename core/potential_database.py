"""GTH parser including triangular nonlocal matrices and optional NLCC."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from functools import lru_cache
from pathlib import Path
from hashlib import sha256
import re
from core.database_format import Lines, DatabaseFormatError, ParsedEntries, number, entry


def _parse_lines(lines):
    result = []
    issues = []
    while lines.pos < len(lines.rows):
        element, names = lines.header()
        start = lines.pos
        if lines.pos < len(lines.rows) and lines.rows[lines.pos][1] == 'NA':
            lines.take()
            issues.append(i18n_msg('{p0} {p1} is marked NA, unavailable, and excluded', code='studio.4df4ef0ad0087f73', p0=element, p1=names[0]))
            continue
        electrons = lines.ints()
        if not electrons or any(v < 0 for v in electrons):
            raise DatabaseFormatError(i18n_msg('Invalid pseudopotential electron configuration', code='studio.c1c2e57b68dba56c'))
        local = lines.take()
        if len(local) < 2:
            raise DatabaseFormatError(i18n_msg('Missing pseudopotential local term', code='studio.8cf1509d71824172'))
        radius = number(local[0])
        try:
            ncoeff = int(local[1])
        except ValueError as exc:
            raise DatabaseFormatError(i18n_msg('Invalid local coefficient count', code='studio.7100309caf64f3c6')) from exc
        if ncoeff < 0 or len(local) != ncoeff + 2 or radius < 0:
            raise DatabaseFormatError(i18n_msg('Local coefficient count mismatch', code='studio.43c2379e522c3233'))
        for token in local[2:]:
            number(token)
        if lines.pos < len(lines.rows) and lines.rows[lines.pos][1].startswith('NLCC '):
            tokens = lines.take()
            if len(tokens) != 2:
                raise DatabaseFormatError(i18n_msg('Invalid NLCC header', code='studio.82c59442534eca99'))
            try:
                nnlcc = int(tokens[1])
            except ValueError as exc:
                raise DatabaseFormatError(i18n_msg('Invalid NLCC count', code='studio.02d12ac7c5d99dfb')) from exc
            if not 0 <= nnlcc <= 100:
                raise DatabaseFormatError(i18n_msg('Invalid NLCC count', code='studio.02d12ac7c5d99dfb'))
            for _ in range(nnlcc):
                row = lines.take()
                if len(row) != 3:
                    raise DatabaseFormatError(i18n_msg('Invalid NLCC data', code='studio.18242596dab6d48d'))
                for token in row:
                    number(token)
        all_electron = any(n.upper() in {'ALL','ALLELECTRON'} for n in names)
        # ALL records have only electron configuration and a zero local line.
        nprojectors = 0
        if not all_electron or (lines.pos < len(lines.rows) and lines.rows[lines.pos][1] == '0'):
            nprojectors, = lines.ints(1)
        if not 0 <= nprojectors <= 20:
            raise DatabaseFormatError(i18n_msg('Invalid nonlocal channel count', code='studio.dc52ede281f9a5b8'))
        for _ in range(nprojectors):
            row = lines.take()
            if len(row) < 2:
                raise DatabaseFormatError(i18n_msg('Missing nonlocal term', code='studio.df6de87b16e8fdba'))
            if number(row[0]) < 0:
                raise DatabaseFormatError(i18n_msg('Negative nonlocal radius', code='studio.7d5697d7e1c282c3'))
            try:
                n = int(row[1])
            except ValueError as exc:
                raise DatabaseFormatError(i18n_msg('Invalid projector count', code='studio.431548aa8316845d')) from exc
            if not 0 <= n <= 20:
                raise DatabaseFormatError(i18n_msg('Invalid projector count', code='studio.431548aa8316845d'))
            coefficients = row[2:]
            required = n*(n+1)//2
            while len(coefficients) < required:
                coefficients += lines.take()
            if len(coefficients) != required:
                raise DatabaseFormatError(i18n_msg('Nonlocal triangular-matrix coefficient count mismatch', code='studio.cc7dba22c44eea41'))
            for token in coefficients:
                number(token)
        result.append(entry(lines, 'potential', element, names, start, q=sum(electrons)))
    if not result and not issues:
        raise DatabaseFormatError(i18n_msg('Empty pseudopotential database', code='studio.3953f8adfa99e27a'))
    return ParsedEntries(result, issues)


@lru_cache(maxsize=32)
def _parse(path, mtime, size, digest):
    lines = Lines(path)
    # Full header grammar separates records for bounded validation/recovery.
    # Numeric coefficient rows cannot match this grammar.
    starts = [i for i,(_,row) in enumerate(lines.rows)
              if re.fullmatch(r'[A-Za-z]{1,2}\s+[A-Za-z][A-Za-z0-9_+.,()=\-]*(?:\s+[A-Za-z][A-Za-z0-9_+.,()=\-]*)*',row)]
    if not starts or starts[0] != 0:
        raise DatabaseFormatError(i18n_msg('No valid pseudopotential entry header found', code='studio.b07ddd79efca277a'))
    result, issues = [], []
    for start,end in zip(starts,starts[1:]+[len(lines.rows)]):
        chunk = object.__new__(Lines)
        chunk.path,chunk.file_sha256,chunk.pos = lines.path,lines.file_sha256,0
        chunk.rows = lines.rows[start:end]
        try:
            parsed = _parse_lines(chunk)
            result.extend(parsed)
            issues.extend(parsed.issues)
        except (ValueError, IndexError) as exc:
            issues.append(i18n_msg('{p0}: corrupt entry excluded: {p1}', code='studio.6bf80154d34da2de', p0=lines.rows[start][1], p1=exc))
    if not result:
        raise DatabaseFormatError(i18n_join('; ', issues) or i18n_msg('Empty pseudopotential database', code='studio.3953f8adfa99e27a'))
    return ParsedEntries(result,issues)


def parse_potential_file(path):
    p = Path(path).expanduser().resolve()
    stat = p.stat()
    return _parse(i18n_str(p), stat.st_mtime_ns, stat.st_size,sha256(p.read_bytes()).hexdigest())
