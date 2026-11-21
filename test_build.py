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

def domain(kind, value):
    return (b'\x08' + varint(kind) if kind else b'') + field(2, value.encode())

def fixture(tags, suffix=''):
    # Synthetic valid protobuf records for tests; never published as real data.
    records = []
    for tag in tags:
        rules = domain(2, tag + suffix + '.example')
        if tag == 'category-ru':

            rules = b''.join(field(2, domain(kind,value)) for kind,value in [
                (0,'plain-marker'), (1,r'^regex-marker\.example$'),
                (2,'root-marker.example'), (3,'exact-marker.example')]) + field(2,rules)
        else:
            rules = field(2,rules)
        records.append(field(1, field(1,tag.upper().encode()) + rules))
    return b''.join(records)

def builder():
    spec = importlib.util.spec_from_file_location('builder', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class PublicationContracts(unittest.TestCase):
    def test_inline_rules_preserve_match_types_and_auto_update(self):
        m = builder()
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            site = fixture(m.SITE_TAGS + ['unused'])
            def publish(blob, now):
                files = {'geosite.dat':blob}
                sums = {'geosite.dat':hashlib.sha256(blob).hexdigest()+'  geosite.dat'}
                return m.publish(output,'https://example.org/public',files,sums,now)
            first = publish(site,100)
            self.assertEqual(first['Geositeurl'],'','Client must not resolve geosite categories from a local DAT')
            self.assertEqual(first['Geoipurl'],'')
            for key in ['DirectSites','ProxySites','BlockSites','DirectIp','ProxyIp','BlockIp']:
                self.assertFalse(any(v.startswith(('geosite:','geoip:','ext:')) for v in first[key]))
            self.assertTrue({'keyword:plain-marker',r'regexp:^regex-marker\.example$',
                             'domain:root-marker.example','full:exact-marker.example'} <= set(first['DirectSites']))
            for cidr in first['DirectIp']:
                ipaddress.ip_network(cidr)
            self.assertFalse(list(output.rglob('*.dat')))
            before = {str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()}
            self.assertEqual(first,publish(site,200))
            self.assertEqual(before,{str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()})
            self.assertEqual(first,publish(site+fixture(['ignored']),250))
            second = publish(fixture(m.SITE_TAGS,suffix='-changed'),300)
            self.assertNotEqual(first['DirectSites'],second['DirectSites'])
            self.assertEqual(second['LastUpdated'],'300')
            self.assertEqual(second['Name'],first['Name'])
            self.assertEqual(first['GlobalProxy'],'true')
            self.assertFalse(first['BlockSites'])

    def test_bad_data_cannot_replace_last_good_inline_profile(self):
        m = builder()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            site = fixture(m.SITE_TAGS)
            def publish(blob, checksum=None):
                return m.publish(out,'https://example.org/public',{'geosite.dat':blob},
                                 {'geosite.dat':checksum or hashlib.sha256(blob).hexdigest()},100)
            publish(site)
            before = {str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}

            bad_domain = b''.join(field(1,field(1,t.upper().encode()) + field(2,domain(99,'invalid.example'))) for t in m.SITE_TAGS)
            for blob,checksum in [(b'corrupt',hashlib.sha256(site).hexdigest()),
                                  (fixture(['private']),None),(bad_domain,None)]:
                with self.assertRaises(ValueError):
                    publish(blob,checksum)
                self.assertEqual(before,{str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()})

if __name__=='__main__':
    unittest.main(verbosity=2)
