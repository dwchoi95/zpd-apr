"""Synthetic-only statement parsing; never opens a real problem/testcase."""
import hashlib
import unittest

from scripts.zpd_statement_samples import extract_samples


def block(kind, value, number='1'):
    suffix = '' if number is None else ' ' + number
    return f'<section><h3>Sample {kind}{suffix}</h3><pre>{value}</pre></section>'


def pair(input_text='1\n', output_text='2\n', number='1'):
    return block('Input', input_text, number) + block('Output', output_text, number)


class StatementSamplesTests(unittest.TestCase):
    def test_exact_bytes_and_hashes(self):
        html = pair('  x\t y\r\n\r\nz ', '한글\n').encode()
        result = extract_samples(html)
        self.assertTrue(result.available)
        self.assertEqual(result.samples[0].input_bytes, b'  x\t y\r\n\r\nz ')
        self.assertEqual(result.samples[0].output_bytes, '한글\n'.encode())
        self.assertEqual(result.html_sha256, hashlib.sha256(html).hexdigest())
        self.assertEqual(result.samples[0].input_sha256,
                         hashlib.sha256(result.samples[0].input_bytes).hexdigest())
        self.assertEqual(result.samples[0].output_sha256,
                         hashlib.sha256(result.samples[0].output_bytes).hexdigest())

    def test_numeric_order_and_identical_pairs_retained(self):
        result = extract_samples((pair(number='10') + pair(number='2')).encode())
        self.assertTrue(result.available)
        self.assertEqual([s.index for s in result.samples], [2, 10])
        self.assertEqual(result.samples[0].input_bytes, result.samples[1].input_bytes)

    def test_unnumbered_and_case_insensitive_heading(self):
        html = pair(number=None).replace('Sample Input', 'sAmPlE  INPUT')
        result = extract_samples(html.encode())
        self.assertTrue(result.available)
        self.assertEqual(result.samples[0].index, 1)

    def test_explicit_empty_pairs_not_missing(self):
        result = extract_samples(pair('', '').encode())
        self.assertTrue(result.available)
        self.assertEqual((result.samples[0].input_bytes, result.samples[0].output_bytes), (b'', b''))

    def test_single_entity_decoding(self):
        result = extract_samples(pair('&amp;lt; &#65; &lt;x&gt;', '&amp;amp;').encode())
        self.assertTrue(result.available)
        self.assertEqual(result.samples[0].input_bytes, b'&lt; A <x>')
        self.assertEqual(result.samples[0].output_bytes, b'&amp;')

    def test_duplicate_index_invalidates_whole_problem(self):
        result = extract_samples((pair() + block('Input', '3')).encode())
        self.assertFalse(result.available)
        self.assertEqual(result.reason, 'duplicate_sample_index')
        self.assertEqual(result.samples, ())

    def test_unpaired_invalidates_other_complete_pairs(self):
        result = extract_samples((pair() + block('Input', '3', '2')).encode())
        self.assertEqual(result.reason, 'unpaired_sample_indexes')
        self.assertEqual(result.samples, ())

    def test_no_sample_is_unavailable(self):
        result = extract_samples(b'<h3>Input</h3><pre>example?</pre><p>Output 2</p>')
        self.assertFalse(result.available)
        self.assertEqual(result.reason, 'no_recognized_samples')

    def test_scripts_and_styles_not_sample_sources(self):
        html = '<script>' + pair() + '</script><style>' + pair() + '</style>'
        self.assertFalse(extract_samples(html.encode()).available)
        self.assertTrue(extract_samples((html + pair()).encode()).available)

    def test_nested_sample_markup_rejected(self):
        for content in ('a<br>b', '<span>x</span>', '<!--x-->', '<?data x?>', '<!DOCTYPE html>', '<pre>x</pre>'):
            with self.subTest(content=content):
                result = extract_samples(pair(content, '2').encode())
                self.assertFalse(result.available)
                self.assertEqual(result.samples, ())

    def test_missing_pre_or_intervening_heading(self):
        for html in ('<h3>Sample Input 1</h3>', '<h3>Sample Input 1</h3><h2>Explanation</h2><pre>1</pre>'):
            with self.subTest(html=html):
                self.assertEqual(extract_samples(html.encode()).reason, 'sample_heading_without_block')

    def test_unclosed_structures(self):
        for html in ('<h3>Sample Input', '<h3>Sample Input 1</h3><pre>1', '<script>text', '<pre>other'):
            with self.subTest(html=html):
                self.assertEqual(extract_samples(html.encode()).reason, 'unclosed_structure')

    def test_nested_heading_or_pre_rejected(self):
        for html in ('<h3><h3>Sample Input</h3>', '<pre><h3>Sample Input</h3>', '<h3><pre>Sample Input</pre>'):
            with self.subTest(html=html):
                self.assertEqual(extract_samples(html.encode()).reason, 'nested_heading_or_pre')

    def test_invalid_utf8_and_wrong_input_type(self):
        self.assertEqual(extract_samples(b'\xff').reason, 'invalid_utf8')
        for value in ('text', bytearray(b'text'), None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                extract_samples(value)

    def test_output_first_is_complete_and_no_trailing_newline_added(self):
        result = extract_samples((block('Output', '2') + block('Input', '1')).encode())
        self.assertTrue(result.available)
        self.assertEqual(result.samples[0].input_bytes, b'1')
        self.assertEqual(result.samples[0].output_bytes, b'2')

    def test_self_closing_nonvoid_structure_is_not_empty_block(self):
        for html in ('<h3/>', '<h3>Sample Input</h3><pre/>',
                     '<h3>Sample Input</h3><pre/><h3>Sample Output</h3><pre/>', '<textarea/>'):
            with self.subTest(html=html):
                self.assertEqual(extract_samples(html.encode()).reason, 'self_closing_nonvoid_structure')

    def test_sample_heading_markup_even_balanced_is_unavailable(self):
        for heading in ('<span>Sample Input</span>', '<span>Sample Input', 'Sample <!--x-->Input'):
            html = '<h3>' + heading + '</h3><pre>1</pre>' + block('Output', '2', None)
            with self.subTest(heading=heading):
                self.assertEqual(extract_samples(html.encode()).reason, 'markup_in_sample_heading')

    def test_malformed_marked_declaration_is_unavailable(self):
        result = extract_samples(pair('<![bad[ x ]]>', '2').encode())
        self.assertFalse(result.available)
        self.assertEqual(result.samples, ())

    def test_rawtext_and_inert_subtrees_are_not_samples(self):
        for tag in ('title', 'textarea', 'xmp', 'iframe', 'noembed', 'noframes', 'template', 'noscript'):
            hidden = '<' + tag + '>' + pair() + '</' + tag + '>'
            with self.subTest(tag=tag):
                self.assertFalse(extract_samples(hidden.encode()).available)
                self.assertTrue(extract_samples((hidden + pair()).encode()).available)

    def test_nested_inert_subtree_stays_ignored(self):
        html = '<template><template>' + pair() + '</template>' + pair() + '</template>'
        self.assertFalse(extract_samples(html.encode()).available)
        self.assertTrue(extract_samples((html + pair()).encode()).available)

    def test_rawtext_cannot_escape_inert_parent(self):
        for outer in ('template', 'noscript'):
            for inner in ('script', 'style', 'title', 'textarea', 'xmp', 'iframe', 'noembed', 'noframes',
                          'noscript' if outer == 'template' else 'template', 'plaintext'):
                html = f'<{outer}><{inner}></{outer}>' + pair() + f'</{inner}></{outer}>'
                with self.subTest(outer=outer, inner=inner):
                    self.assertEqual(extract_samples(html.encode()).reason, 'mixed_rawtext_in_inert_subtree')

    def test_plaintext_document_unavailable(self):
        self.assertEqual(extract_samples(('<plaintext>' + pair()).encode()).reason,
                         'unsupported_plaintext_document')


if __name__ == '__main__':
    unittest.main()
