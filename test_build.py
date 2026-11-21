import hashlib
import importlib.util
import ipaddress
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
    # Minimal protobuf test fixtures; never published as real geodata.
    return b''.join(field(1, field(1, tag.upper().encode())) for tag in tags)

def builder():
    spec = importlib.util.spec_from_file_location('builder', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class PublicationContracts(unittest.TestCase):
    def test_geosite_only_refresh_preserves_old_versions(self):
        m = builder()
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            site = fixture(m.SITE_TAGS + ['unused'])
            # Include the old GeoIP fixture to reproduce the rejected 436-byte
            # publication class. It must never be referenced by the new profile.
            ip = fixture(['private'])
            def publish(site_bytes, now):
                files = {'geosite.dat': site_bytes, 'geoip.dat': ip}
                sums = {name: hashlib.sha256(data).hexdigest()+'  '+name for name,data in files.items()}
                return m.publish(output, 'https://example.org/public', files, sums, now)
            first = publish(site, 100)
            self.assertEqual(first.get('Geoipurl'), '', 'GeoSite-only profile must not request a GeoIP download')
            self.assertFalse(any(v.startswith('geoip:') for key in ['DirectIp','ProxyIp','BlockIp'] for v in first[key]))
            for cidr in first['DirectIp']:
                ipaddress.ip_network(cidr)
            self.assertFalse(list(output.rglob('geoip.dat')))
            before = {str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()}
            self.assertEqual(first, publish(site, 200))
            self.assertEqual(before, {str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()})
            changed = site + field(1, field(1, b'IGNORED'))
            self.assertEqual(first, publish(changed, 250))
            changed = b''.join(field(1, field(1, tag.upper().encode()) + (field(2,b'new-domain-fixture') if tag=='category-ru' else b'')) for tag in m.SITE_TAGS)
            second = publish(changed, 300)
            self.assertNotEqual(first['Geositeurl'], second['Geositeurl'])
            self.assertEqual(second['LastUpdated'], '300')
            self.assertEqual(second['Geoipurl'], '')
            for profile in (first, second):
                relative = profile['Geositeurl'].removeprefix('https://example.org/public/')
                blob = (output/relative).read_bytes()
                self.assertEqual((output/(relative+'.sha256')).read_text().strip(), hashlib.sha256(blob).hexdigest())
                self.assertEqual(set(m.entries(blob)), set(m.SITE_TAGS))
            self.assertEqual(first['GlobalProxy'], 'true')
            self.assertFalse(first['BlockSites'])

    def test_bad_geosite_cannot_replace_last_good_publication(self):
        m = builder()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            # No GeoIP input exists: the publisher must work with GeoSite alone.
            files = {'geosite.dat': fixture(m.SITE_TAGS)}
            sums = {n:hashlib.sha256(b).hexdigest()+'  '+n for n,b in files.items()}
            m.publish(out, 'https://example.org/public', files, sums, 100)
            before = {str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
            missing = fixture(['private'])
            for bad,bad_sums in [({'geosite.dat':b'corrupt'},sums),
                                  ({'geosite.dat':missing},{'geosite.dat':hashlib.sha256(missing).hexdigest()})]:
                with self.assertRaises(ValueError):
                    m.publish(out, 'https://example.org/public', bad, bad_sums, 200)
                self.assertEqual(before, {str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()})

if __name__ == '__main__':
    unittest.main(verbosity=2)
