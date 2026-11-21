# INCY: Russian services direct, other traffic through VPN

Standalone, auto-updating INCY routing profile. No VPN credentials, server addresses or subscription identifiers are stored here.

## Import or refresh

Autorouting source:

https://raw.githubusercontent.com/dobryiBRO/incy-routing/main/public/profile.json

Add without forcing activation:

`incy://autorouting/add/https://raw.githubusercontent.com/dobryiBRO/incy-routing/main/public/profile.json`

Keep the existing VPN subscription and selected server. Refresh this **Autorouting source**, select `Aleksey RU Direct Pilot`, enable routing and reconnect. Use a 24-hour source update interval. Updating geodata alone does not replace stale profile rules. Restore the previous routing profile or disable routing and reconnect to roll back.

## Policy and compatibility

- Default: existing VPN.
- Direct categories: `category-ru`, `ru-available-only-inside`, private domains.
- Explicit proxy categories: YouTube, Google, Meta, OpenAI.
- Source: GeoSite data from Runet Freedom, including DLC categories. The publisher expands categories into ordinary `domain:`, `full:`, `regexp:` and `keyword:` rules while preserving match types.
- The client receives the domain rules inside the profile JSON. No client-side `geosite:`, `geoip:` or `ext:` lookup is needed. Both custom geodata URLs are empty; a client may still maintain its own unrelated built-in files.
- Local networks use explicit IPv4/IPv6 CIDRs. No broad country-IP bypass, ad blocking or tracker blocking.
- Direct DNS: Yandex 77.88.8.8 (UDP); proxied DNS: Cloudflare DoH.

This removes the runtime dependency on whether INCY/Ferrum loaded the custom GeoSite category directory. It does not change the data source to a hand-maintained list.

`category-ru` includes the entire `.ru` zone. Direct requests use the access network, exposing destination/DNS metadata to that network while preserving normal site HTTPS. Client-generated rule precedence and application behavior must be checked on the actual INCY version.

## Updates and integrity

GitHub Actions checks Runet Freedom twice daily. Each build downloads GeoSite and its checksum from one immutable upstream release commit and verifies SHA-256 before decoding selected categories. Match types are preserved; category attributes are not filters in this policy.

Changed domain rules or policy produce a newer profile `LastUpdated`. Unchanged effective rules leave the profile unchanged, including when only unused upstream categories change. Malformed records, unknown match types, missing categories or bad checksums abort before replacing the last good profile. Older immutable DAT assets remain available for previously imported profiles but are not referenced by the current one.

INCY periodically fetches the **Autorouting JSON source** according to its source update interval. There is no custom DAT/checksum download step on the client in this version. Sleep, a closed client, network/CDN failures and GitHub scheduler delays can postpone checks. GitHub can disable public-repository schedules after 60 days of inactivity; check Actions if updates stop.

## Validation

`python3 test_build.py`

The publisher contracts cover match types, idempotence, updates and rejection without overwriting the last good publication. Real upstream rules were checked using Xray `run -test` with an empty geodata directory. This does not prove installed-client import, generated rule order, DNS decisions or source auto-refresh. Verify those on the target device, including actual domestic login/video and foreign-service workloads. A public-IP checker establishes only its own route.

## Sources and licenses

Data comes from [Runet Freedom](https://github.com/runetfreedom/russia-v2ray-rules-dat), which incorporates [Domain List Community](https://github.com/v2fly/domain-list-community) categories and additional Russia-specific lists. Selected compiled domain records are decoded into equivalent textual matching rules.

- Publisher code and tests: MIT, see `LICENSE`.
- Runet Freedom upstream license: GPL-3.0, full notice in `LICENSE-RUNET-FREEDOM`.
- Domain List Community upstream license: MIT, full notice in `LICENSE-DLC`.
- Corresponding upstream revision is recorded in the Actions build log. Original compiled files, source lists and build infrastructure are available in the linked upstream repositories and release branches. Upstream licensing requirements remain applicable.

Publishing this repository does not change VPN servers, shared subscriptions or any installed client.
