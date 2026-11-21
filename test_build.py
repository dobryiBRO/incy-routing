import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name('build.py')

def varint(n):
    out = bytearray()
    while n > 127:
        out.append((n & 127) | 128)
        n >>= 7
    return bytes(out) + bytes([n])

def field(n, data):
    return varint(n << 3 | 2) + varint(len(data)) + data

def fixture(tags):
    # Deliberately minimal protobuf fixtures, never published as real geodata.
    return b''.join(field(1, field(1, tag.upper().encode())) for tag in tags)

class PublicationContracts(unittest.TestCase):
    def test_refresh_is_versioned_and_unchanged_input_is_stable(self):
        self.assertTrue(MODULE.exists(), 'Missing autorouting publisher implementation')
        spec = importlib.util.spec_from_file_location('builder', MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            site = fixture(m.SITE_TAGS + ['unused'])
            ip = fixture(['private', 'unused'])
            checks = {name: hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                      for name, data in [('geosite.dat', site), ('geoip.dat', ip)]}
            def publish(site_bytes, now):
                files = {'geosite.dat': site_bytes, 'geoip.dat': ip}
                sums = {name: hashlib.sha256(data).hexdigest() + '  ' + name for name, data in files.items()}
                return m.publish(output, 'https://example.org/public', files, sums, now)
            first = publish(site, 100)
            before = {str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()}
            again = publish(site, 200)
            self.assertEqual(first, again)
            self.assertEqual(before, {str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()})
            changed = site.replace(b'CATEGORY-RU', b'CATEGORY-RU', 1) + field(1, field(1, b'IGNORED'))
            self.assertEqual(first, publish(changed, 250), 'Unused upstream changes must not force an update')
            changed = b''.join(field(1, field(1, tag.upper().encode()) + (field(2, b'new-domain-fixture') if tag == 'category-ru' else b'')) for tag in m.SITE_TAGS)
            second = publish(changed, 300)
            self.assertNotEqual(first['Geositeurl'], second['Geositeurl'])
            self.assertEqual(second['LastUpdated'], '300')
            self.assertEqual(first['Geoipurl'], second['Geoipurl'])
            for profile in (first, second):
                for key in ('Geositeurl', 'Geoipurl'):
                    relative = profile[key].removeprefix('https://example.org/public/')
                    blob = (output / relative).read_bytes()
                    self.assertEqual((output / (relative+'.sha256')).read_text().strip(), hashlib.sha256(blob).hexdigest())
            self.assertEqual(set(m.entries((output / first['Geositeurl'].removeprefix('https://example.org/public/')).read_bytes())), set(m.SITE_TAGS))
            self.assertEqual(first['GlobalProxy'], 'true')
            self.assertNotIn('geoip:ru', first['DirectIp'])
            self.assertFalse(first['BlockSites'])

    def test_bad_data_cannot_replace_last_good_publication(self):
        self.assertTrue(MODULE.exists(), 'Missing autorouting publisher implementation')
        spec = importlib.util.spec_from_file_location('builder', MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            files = {'geosite.dat': fixture(m.SITE_TAGS), 'geoip.dat': fixture(['private'])}
            sums = {n: hashlib.sha256(b).hexdigest()+'  '+n for n,b in files.items()}
            m.publish(out, 'https://example.org/public', files, sums, 100)
            before = {str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
            for bad, bad_sums in [(dict(files, **{'geosite.dat':b'corrupt'}), sums),
                                  (dict(files, **{'geosite.dat': fixture(['private'])}), dict(sums, **{'geosite.dat': hashlib.sha256(fixture(['private'])).hexdigest()}))]:
                with self.assertRaises(ValueError):
                    m.publish(out, 'https://example.org/public', bad, bad_sums, 200)
                self.assertEqual(before, {str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()})

if __name__ == '__main__':
    unittest.main(verbosity=2)
