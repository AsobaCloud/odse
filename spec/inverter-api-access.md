# Inverter API Access Setup

This document captures API onboarding requirements for inverter OEMs used by ODS-E transforms, including OEMs with newly added transform specifications.

Last reviewed: 2026-02-09

## Transform Specs

- Huawei: `transforms/huawei-fusionsolar.yaml`
- SolarEdge: `transforms/solaredge-monitoring.yaml`
- Enphase: `transforms/enphase-envoy.yaml`
- Fronius: `transforms/fronius-solar-api.yaml`
- Switch: `transforms/switch-meter.yaml`
- SMA: `transforms/sma-monitoring-api.yaml`
- FIMER: `transforms/fimer-auroravision-api.yaml`
- Solis: `transforms/soliscloud-api.yaml`
- SolaX: `transforms/solaxcloud-api-v2.yaml`

## Runtime Support (Python `ods_e.transform`)

| Source Key | Runtime Status |
|------------|----------------|
| `huawei` | Implemented |
| `switch` | Implemented |
| `solaxcloud`, `solax` | Implemented |
| `fimer`, `auroravision` | Implemented |
| `enphase` | Placeholder (returns empty list) |
| `solarman` | Placeholder (returns empty list) |

## Status Key

- Included: OEM has an existing transform in this repository.
- Included (Spec): OEM has a transform specification in this repository; production connector/runtime may still be pending.

## OEM API Access Summary

| OEM | Status | API Type | Setup Prerequisites | Auth Model |
|-----|--------|----------|---------------------|------------|
| Huawei FusionSolar | Included | Cloud (Northbound) | Enable Northbound management in FusionSolar company admin and assign API capability | API account or OAuth2 (depends on access mode) |
| SolarEdge | Included | Cloud Monitoring API | Generate site/account API key in SolarEdge monitoring portal | API key in query parameter |
| Enphase Envoy / Enlighten | Included | Cloud + local gateway | Register app in Enphase developer platform and authorize system access | OAuth2 (token-based) |
| Fronius | Included | Local inverter API | Inverter reachable on LAN; Solar API enabled on device/network | Typically none (local endpoint access) |
| SMA | Included (Spec) | Cloud API | Create developer app in SMA developer portal and complete consent for target system owner | OAuth2 (authorization code flow) |
| FIMER Aurora Vision | Included (Spec) | Cloud API | Aurora Vision account with required role; request API enablement via FIMER support | Vendor-issued credentials per Aurora Vision API docs |
| SolisCloud | Included (Spec) | Cloud API | Complete Solis cooperation/application process and receive API activation materials | OAuth2 with AppKey/AppSecret |
| SolaX Cloud | Included (Spec) | Cloud API | Generate API token in Solax Cloud third-party ecosystem settings | API token |

## Setup Instructions By OEM

### Huawei FusionSolar (Included)

1. Sign in as company administrator in FusionSolar.
2. Open `System > Company Management > Northbound Management`.
3. Create or enable a Northbound application and grant required API capabilities.
4. Choose an access mode:
   - API account access (northbound account created in FusionSolar), or
   - OAuth Connect (OAuth2 client setup for third-party app).
5. Confirm plant/site visibility for the account/client before ingestion.

Official references:
- Huawei FusionSolar Northbound API setup and authentication:
  - https://support.huawei.com/enterprise/en/doc/EDOC1100440661/d5d876c7/creating-api-account-company-administrator
  - https://support.huawei.com/enterprise/en/doc/EDOC1100427895/95c18db0/oauth-connect

### SolarEdge (Included)

1. In Monitoring Portal, open API access for account or specific site.
2. Create/copy API key.
3. Use key on Monitoring API endpoints (`monitoringapi.solaredge.com`).

Official references:
- https://knowledge-center.solaredge.com/sites/kc/files/se_monitoring_api.pdf

### Enphase Envoy / Enlighten (Included)

1. Register an app in the Enphase developer platform.
2. Configure OAuth redirect/callback.
3. Have the system owner authorize the app.
4. Exchange authorization code for access token.
5. Use token for system/telemetry API calls.

Official references:
- https://developer-v4.enphase.com/docs/quickstart.html
- https://developer-v4.enphase.com/docs/authentication.html

### Fronius Local Solar API (Included)

1. Ensure the inverter is on the same network as the integration service.
2. Resolve inverter IP/hostname.
3. Query local endpoints under `/solar_api/v1`.
4. Validate required endpoints respond (`GetPowerFlowRealtimeData.fcgi`, `GetInverterRealtimeData.cgi`, etc.).

Official references:
- https://www.fronius.com/~/downloads/Solar%20Energy/Operating%20Instructions/42,0410,2012.pdf

### SMA (Included (Spec))

1. Create a developer app in SMA developer portal.
2. Configure OAuth client details and redirect URI.
3. Ask system owner to consent to API scopes.
4. Exchange authorization code for access/refresh tokens.
5. Use SMA APIs for plant and inverter telemetry.

Official references:
- https://developer.sma.de/

### FIMER Aurora Vision (Included (Spec))

1. Ensure Aurora Vision account is active and validated.
2. Ensure account role/permissions are sufficient for portfolio access.
3. Open a FIMER support ticket to enable required Aurora Vision API capabilities.
4. Use credentials and authentication flow exactly as provided in Aurora Vision documentation.

Official references:
- https://www.fimer.com/faq/where-can-i-find-documentation-such-release-notes-and-guides-dedicated-aurora-vision-products
- https://www.fimer.com/faq/how-can-i-access-plant-portfolio-manager

### SolisCloud (Included (Spec))

1. Reach a cooperation agreement with Solis and submit API activation materials.
2. Receive OAuth2 access documentation plus `AppKey` and `AppSecret` from Solis.
3. Implement OAuth2 authorization flow for user-consented data access.
4. Call SolisCloud APIs within the authorized scope.

Official references:
- https://doc.soliscloud.com/en/20.API%20documentation/01.SolisCloud%20Platform%20API%20Document.html

### SolaX Cloud (Included (Spec))

1. Sign in to Solax Cloud.
2. Open `Service > API` (third-party ecosystem section).
3. Generate or copy `tokenId`.
4. Use token in SolaX API v2 requests.

Official references:
- https://global.solaxcloud.com/blue/4/user_api/2024/SolaXCloud_User_API_V2.pdf
- https://doc.solaxcloud.com/en/inst-w/service/

## Implementation Notes For ODS-E

- Treat cloud APIs as rate-limited and implement retries with backoff.
- Store API credentials in a secret manager; do not commit into repository files.
- Transform specs for SMA, FIMER Aurora Vision, SolisCloud, and SolaX Cloud are now present in `transforms/`.
- Runtime ingestion connectors should bind to vendor OpenAPI/docs and validate with sample payload captures before production use.
