"""Pure conservative statement-sample extraction; no I/O or submitted execution.

The caller must authenticate HTML/request provenance before using this result.
Availability means syntactic extraction only, not testcase-feedback availability.
There is deliberately no production CLI, hidden-test loader or network fallback.
"""
from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
import re


VERSION = 'generator_visible_statement_samples_v1'
_HEADING = re.compile(r'Sample\s+(Input|Output)(?:\s+([1-9][0-9]*))?', re.I)
_HEADINGS = frozenset(('h1', 'h2', 'h3', 'h4', 'h5', 'h6'))
_RAW_IGNORE = frozenset(('script', 'style', 'title', 'textarea', 'xmp', 'iframe', 'noembed', 'noframes'))
_INERT_IGNORE = frozenset(('template', 'noscript'))


class _Unavailable(ValueError):
    pass


@dataclass(frozen=True)
class StatementSample:
    index: int
    input_bytes: bytes
    output_bytes: bytes

    @property
    def input_sha256(self):
        return hashlib.sha256(self.input_bytes).hexdigest()

    @property
    def output_sha256(self):
        return hashlib.sha256(self.output_bytes).hexdigest()


@dataclass(frozen=True)
class Extraction:
    available: bool
    reason: str
    samples: tuple[StatementSample, ...]
    html_sha256: str
    version: str = VERSION


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = None
        self.heading_parts = []
        self.heading_markup = False
        self.pending = None
        self.active = None
        self.parts = []
        self.blocks = {}
        self.pre_open = False
        self.ignored = None
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        del attrs
        if self.ignored is not None:
            if self.ignored in _INERT_IGNORE:
                if tag == self.ignored:
                    self.ignored_depth += 1
                elif tag in _RAW_IGNORE | _INERT_IGNORE or tag == 'plaintext':
                    raise _Unavailable('mixed_rawtext_in_inert_subtree')
            return
        if self.active is not None:
            raise _Unavailable('nested_tag_in_sample')
        if tag == 'plaintext':
            raise _Unavailable('unsupported_plaintext_document')
        if tag in _RAW_IGNORE | _INERT_IGNORE:
            if self.heading is not None:
                raise _Unavailable('nested_ignored_content_in_heading')
            self.ignored = tag
            self.ignored_depth = 1
            return
        if tag in _HEADINGS:
            if self.heading is not None or self.pre_open:
                raise _Unavailable('nested_heading_or_pre')
            if self.pending is not None:
                raise _Unavailable('sample_heading_without_block')
            self.heading = tag
            self.heading_parts = []
            self.heading_markup = False
        elif tag == 'pre':
            if self.heading is not None or self.pre_open:
                raise _Unavailable('nested_heading_or_pre')
            self.pre_open = True
            if self.pending is not None:
                self.active = self.pending
                self.pending = None
                self.parts = []
        elif self.heading is not None:
            self.heading_markup = True

    def handle_startendtag(self, tag, attrs):
        if self.active is not None:
            raise _Unavailable('nested_tag_in_sample')
        if tag == 'pre' or tag in _HEADINGS | _RAW_IGNORE | _INERT_IGNORE:
            raise _Unavailable('self_closing_nonvoid_structure')
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.ignored is not None:
            if tag == self.ignored:
                self.ignored_depth -= 1
                if self.ignored_depth == 0:
                    self.ignored = None
            return
        if self.active is not None:
            if tag != 'pre':
                raise _Unavailable('nested_tag_in_sample')
            if self.active in self.blocks:
                raise _Unavailable('duplicate_sample_index')
            self.blocks[self.active] = ''.join(self.parts)
            self.active = None
            self.parts = []
            self.pre_open = False
            return
        if tag in _HEADINGS:
            if self.heading != tag:
                raise _Unavailable('unmatched_heading')
            if tag == 'h3':
                heading = ' '.join(''.join(self.heading_parts).split())
                match = _HEADING.fullmatch(heading)
                if match:
                    if self.heading_markup:
                        raise _Unavailable('markup_in_sample_heading')
                    try:
                        index = int(match.group(2) or '1')
                    except ValueError:
                        raise _Unavailable('invalid_sample_index') from None
                    self.pending = (match.group(1).lower(), index)
            self.heading = None
            self.heading_parts = []
        elif tag == 'pre':
            if not self.pre_open:
                raise _Unavailable('unmatched_pre')
            self.pre_open = False
        elif self.heading is not None:
            self.heading_markup = True

    def handle_data(self, data):
        if self.ignored is not None:
            return
        if self.active is not None:
            self.parts.append(data)
        elif self.heading is not None:
            self.heading_parts.append(data)

    def _nondata(self):
        if self.active is not None:
            raise _Unavailable('nondata_markup_in_sample')
        if self.heading is not None:
            self.heading_markup = True

    def handle_comment(self, data):
        del data
        self._nondata()

    def handle_decl(self, decl):
        del decl
        self._nondata()

    def unknown_decl(self, data):
        del data
        self._nondata()

    def handle_pi(self, data):
        del data
        self._nondata()

    def finish(self):
        self.close()
        if self.active is not None or self.pre_open or self.heading is not None or self.ignored is not None:
            raise _Unavailable('unclosed_structure')
        if self.pending is not None:
            raise _Unavailable('sample_heading_without_block')
        inputs = {index for kind, index in self.blocks if kind == 'input'}
        outputs = {index for kind, index in self.blocks if kind == 'output'}
        if not inputs and not outputs:
            raise _Unavailable('no_recognized_samples')
        if inputs != outputs:
            raise _Unavailable('unpaired_sample_indexes')
        return tuple(StatementSample(i, self.blocks['input', i].encode('utf-8'),
                                     self.blocks['output', i].encode('utf-8'))
                     for i in sorted(inputs))


def extract_samples(html_bytes):
    """Return all declared pairs or one whole-problem unavailable result.

    Provenance failure is not a parser fallback: the caller must separately
    verify the external SHA and the exact frozen statement-text projection.
    Never infer missing content or silently retain only valid-looking pairs.
    """
    if type(html_bytes) is not bytes:
        raise ValueError('immutable exact HTML bytes required')
    digest = hashlib.sha256(html_bytes).hexdigest()
    try:
        text = html_bytes.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        return Extraction(False, 'invalid_utf8', (), digest)
    parser = _Parser()
    try:
        parser.feed(text)
        samples = parser.finish()
    except _Unavailable as exc:
        return Extraction(False, str(exc), (), digest)
    except AssertionError:
        # HTMLParser raises this for unsupported malformed marked declarations.
        return Extraction(False, 'malformed_html_declaration', (), digest)
    return Extraction(True, 'explicit_complete_pairs', samples, digest)


if __name__ == '__main__':
    raise SystemExit('No production CLI: authenticated source-only preparation requires a separate release.')
