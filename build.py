"""Publish small INCY geodata subsets from checksum-verified Runet Freedom data.

No third-party packages, VPN credentials, client changes or server access.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.request

SITE_TAGS = ['category-ru', 'ru-available-only-inside', 'private', 'youtube', 'google', 'meta', 'openai']
IP_TAGS = ['private']


def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    return bytes(result) + bytes([value])


def read_varint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        if pos >= len(data):
            raise ValueError('Truncated protobuf integer')
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise ValueError('Oversized protobuf integer')


def fields(data):
    pos = 0
    while pos < len(data):
        key, pos = read_varint(data, pos)
        number, wire = key >> 3, key & 7
        if number == 0:
            raise ValueError('Invalid protobuf field')
        if wire == 2:
            size, pos = read_varint(data, pos)
            end = pos + size
            if end > len(data):
                raise ValueError('Truncated protobuf field')
            yield number, wire, data[pos:end]
            pos = end
        elif wire == 0:
            _, pos = read_varint(data, pos)
        elif wire in (1, 5):
            pos += 8 if wire == 1 else 4
            if pos > len(data):
                raise ValueError('Truncated fixed protobuf field')
        else:
            raise ValueError('Unsupported protobuf wire type')


def entries(data):
    result = {}
    for number, wire, payload in fields(data):
        if number != 1 or wire != 2:
            raise ValueError('Unexpected geodata container field')
        tags = [v.decode('ascii').lower() for n, w, v in fields(payload) if n == 1 and w == 2]
        if len(tags) != 1 or tags[0] in result:
            raise ValueError('Missing or duplicate geodata tag')
        result[tags[0]] = payload
    return result


def subset(data, tags):
    source = entries(data)
    missing = set(tags) - source.keys()
    if missing:
        raise ValueError('Missing upstream categories: ' + ', '.join(sorted(missing)))
    return b''.join(b'\x0a' + varint(len(source[t])) + source[t] for t in sorted(tags))


def publish(output, base, files, checksums, now):
    if not base.startswith('https://'):
        raise ValueError('HTTPS publication URL required')
    selected = {}
    for name, tags in [('geosite.dat', SITE_TAGS), ('geoip.dat', IP_TAGS)]:
        digest = hashlib.sha256(files[name]).hexdigest()
        advertised = checksums[name].split()[0]
        if not re.fullmatch('[0-9a-fA-F]{64}', advertised) or digest != advertised.lower():
            raise ValueError('Upstream checksum mismatch: ' + name)
        selected[name] = subset(files[name], tags)
    # Validate all inputs before modifying any last-known-good output.
    paths = {name: f'data/{hashlib.sha256(blob).hexdigest()}/{name}' for name, blob in selected.items()}
    profile = {
        'Name': 'Aleksey RU Direct Pilot',
        'GlobalProxy': 'true',
        'RemoteDNSType': 'DoH',
        'RemoteDNSDomain': 'https://cloudflare-dns.com/dns-query',
        'RemoteDNSIP': '1.1.1.1',
        'DomesticDNSType': 'DoU',
        'DomesticDNSDomain': '',
        'DomesticDNSIP': '77.88.8.8',
        'DnsHosts': {'cloudflare-dns.com': '1.1.1.1'},
        'Geositeurl': base.rstrip('/') + '/' + paths['geosite.dat'],
        'Geoipurl': base.rstrip('/') + '/' + paths['geoip.dat'],
        'DirectSites': ['geosite:category-ru', 'geosite:ru-available-only-inside', 'geosite:private'],
        'DirectIp': ['geoip:private'],
        'ProxySites': ['geosite:youtube', 'geosite:google', 'geosite:meta', 'geosite:openai'],
        'ProxyIp': [],
        'BlockSites': [],
        'BlockIp': [],
        'DomainStrategy': 'IPIfNonMatch',
        'FakeDNS': 'false',
        'useChunkFiles': False,
    }
    profile_path = output / 'profile.json'
    old = json.loads(profile_path.read_text()) if profile_path.exists() else {}
    old_policy = {k: v for k, v in old.items() if k != 'LastUpdated'}
    if old_policy == profile:
        return old
    profile['LastUpdated'] = str(max(int(now), int(old.get('LastUpdated', '0')) + 1))
    for name, blob in selected.items():
        target = output / paths[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        target.with_name(target.name + '.sha256').write_text(hashlib.sha256(blob).hexdigest() + '\n')
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / '.profile.json.new'
    temporary.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(profile_path)
    return profile


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'incy-ru-direct-pilot'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True, help='Public HTTPS URL of output directory')
    parser.add_argument('--out', type=Path, default=Path('public'))
    args = parser.parse_args()
    commit = json.loads(download('https://api.github.com/repos/runetfreedom/russia-v2ray-rules-dat/commits/release'))['sha']
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Invalid upstream revision')
    root = f'https://raw.githubusercontent.com/runetfreedom/russia-v2ray-rules-dat/{commit}/'
    names = ['geosite.dat', 'geoip.dat']
    requested = names + [n + '.sha256sum' for n in names]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        blobs = dict(zip(requested, pool.map(lambda n: download(root + n), requested)))
    files = {n: blobs[n] for n in names}
    sums = {n: blobs[n + '.sha256sum'].decode('ascii') for n in names}
    profile = publish(args.out, args.base, files, sums, time.time())
    print(json.dumps({'upstream_commit': commit, 'profile': str(args.out/'profile.json'),
                      'last_updated': profile['LastUpdated'],
                      'input_bytes': {n: len(files[n]) for n in names},
                      'output_bytes': {n: (args.out / profile[k].removeprefix(args.base.rstrip('/')+'/')).stat().st_size
                                       for n,k in [('geosite.dat','Geositeurl'),('geoip.dat','Geoipurl')]},
                      'categories': SITE_TAGS, 'checksum_verified': True}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
