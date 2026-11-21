# INCY: Russian services direct, other traffic through VPN

Standalone, auto-updating INCY routing profile. No VPN credentials, server addresses or subscription identifiers are stored here.

## Import

Raw profile URL (available after the first successful workflow):

https://raw.githubusercontent.com/dobryiBRO/incy-routing/main/public/profile.json

Add without forcing activation:

`incy://autorouting/add/https://raw.githubusercontent.com/dobryiBRO/incy-routing/main/public/profile.json`

Keep the existing VPN subscription and selected server. Add this URL as an **Autorouting** source, wait for geodata downloads, select the profile, enable routing and reconnect. Update interval: 24 hours. Restore the previous routing profile or disable routing and reconnect to roll back.

## Policy

- Default: existing VPN.
- Direct: `category-ru`, `ru-available-only-inside`, private domains/IPs.
- Explicit proxy categories: YouTube, Google, Meta, OpenAI.
- GeoSite-only service classification. Local networks use explicit IPv4/IPv6 CIDRs; no `geoip:` rules or custom GeoIP download (`Geoipurl` is empty). An INCY version may still manage its own built-in geodata independently.
- No broad country-IP bypass; no ad or tracker blocking.
- Direct DNS: Yandex 77.88.8.8 (UDP); proxied DNS: Cloudflare DoH.

`category-ru` includes the entire `.ru` zone. Direct requests use the access network, exposing destination/DNS metadata to that network while preserving normal site HTTPS. Client-generated precedence and application behavior must be checked on the actual INCY version.

## Updates and integrity

GitHub Actions checks Runet Freedom twice daily. Each build downloads geodata and checksums from one immutable upstream commit and verifies SHA-256. Only referenced records are retained, verbatim. The published subset has its own checksum.

Changed data gets a content-addressed URL, a bare-hex `.sha256` companion and a newer profile `LastUpdated`. Unchanged selected data leaves the profile unchanged. Previous URLs remain available. Invalid upstream data is rejected before publication.

INCY periodically fetches the source according to its update interval. Sleep, a closed client, network/CDN failures and GitHub scheduler delays can postpone checks. GitHub can disable public-repository schedules after 60 days of inactivity; check Actions if updates stop.

## Validation

`python3 test_build.py`

Publisher tests and Xray parser acceptance do not prove installed-client routing or client auto-refresh. Test Russian-service login/video and foreign workloads, inspect actual direct/proxy decisions, then verify a profile/geodata version transition on the target device. A public-IP checker establishes only its own route.

## Sources and licenses

Data comes from [Runet Freedom](https://github.com/runetfreedom/russia-v2ray-rules-dat), which incorporates [Domain List Community](https://github.com/v2fly/domain-list-community) categories and additional Russia-specific lists. Original category records are copied unchanged; the container is reduced to the categories used by this profile.

- Publisher code and tests: MIT, see `LICENSE`.
- Runet Freedom upstream license: GPL-3.0, full notice in `LICENSE-RUNET-FREEDOM`.
- Domain List Community upstream license: MIT, full notice in `LICENSE-DLC`.
- Corresponding upstream release revision and checksums are recorded in the Actions build log. Original compiled files and source/build infrastructure are available in the linked upstream repositories and their release branches. This repository does not claim ownership of upstream data or remove upstream licensing requirements.

No existing VPN server or client is changed by publishing this repository.
