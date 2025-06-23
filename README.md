# FreeIPA Prometheus Exporter

A Prometheus exporter for FreeIPA that collects various metrics about your FreeIPA infrastructure including user accounts, hosts, services, groups, and replication status.

## Overview

This exporter is based on the work from [peterpakos/checkipaconsistency](https://github.com/peterpakos/checkipaconsistency/tree/master), extending its functionality to provide Prometheus-compatible metrics. The original repository provided a comprehensive FreeIPA consistency checker, which we've adapted to serve as a metrics exporter for long-term monitoring.

## Features

- Scrapes metrics from one or more FreeIPA servers
- Provides comprehensive metrics about FreeIPA infrastructure
- Supports caching to reduce load on FreeIPA servers
- Threaded HTTP server for concurrent requests
- Simple health check endpoint

## Metrics Collected

The exporter provides the following metrics:

### Status Metrics (all labeled with `host` - short hostname of the FreeIPA server)

| Metric Name | Description |
|-------------|-------------|
| `ipa_users` | Number of active users |
| `ipa_susers` | Number of stage users |
| `ipa_pusers` | Number of preserved users |
| `ipa_hosts` | Number of hosts |
| `ipa_services` | Number of services |
| `ipa_ugroups` | Number of user groups |
| `ipa_hgroups` | Number of host groups |
| `ipa_ngroups` | Number of netgroups |
| `ipa_hbac` | Number of HBAC rules |
| `ipa_sudo` | Number of SUDO rules |
| `ipa_zones` | Number of DNS zones |
| `ipa_certs` | Number of certificates |
| `ipa_conflicts` | Number of LDAP conflicts |
| `ipa_ghosts` | Number of ghost replicas |
| `ipa_bind` | Anonymous BIND status (1=ON, 0=OFF) |
| `ipa_msdcs` | Microsoft ADTrust status (1=True, 0=False) |

### Other Metrics

| Metric Name | Description | Labels |
|-------------|-------------|--------|
| `ipa_replication_status` | Replication status (0=OK, 1=Error) | `source`, `target` |
| `ipa_up` | Was the last scrape successful (1=yes, 0=no) | `host` |
| `ipa_scrape_duration_seconds` | Time taken to scrape metrics | `host` |

## Installation

### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t freeipa-exporter .
   ```

2. Run the container:
   ```bash
   docker run -d \
     -p 9189:9189 \
     -e FREEIPA_DOMAIN=your.ipa.domain \
     -e FREEIPA_BIND_DN="cn=Directory Manager" \
     -e FREEIPA_BIND_PW=your_password \
     -e FREEIPA_HOSTS="ipa1.your.domain,ipa2.your.domain" \
     -e CACHE_TTL=60 \
     freeipa-exporter
   ```

### Direct Python Execution

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the exporter:
   ```bash
   FREEIPA_DOMAIN=your.ipa.domain \
   FREEIPA_BIND_DN="cn=Directory Manager" \
   FREEIPA_BIND_PW=your_password \
   FREEIPA_HOSTS="ipa1.your.domain,ipa2.your.domain" \
   python exporter.py
   ```

## Configuration

The exporter is configured through environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FREEIPA_DOMAIN` | Yes | - | Your FreeIPA domain (e.g., example.com) |
| `FREEIPA_BIND_DN` | No | "cn=Directory Manager" | Bind DN for LDAP connection |
| `FREEIPA_BIND_PW` | Yes | - | Password for the Bind DN |
| `FREEIPA_HOSTS` | Yes | - | Comma-separated list of FreeIPA servers to scrape |
| `CACHE_TTL` | No | 60 | Cache time-to-live in seconds |
| `EXPORTER_PORT` | No | 9189 | Port the exporter listens on |

## Endpoints

- `/metrics`: Prometheus metrics endpoint
- `/health`: Health check endpoint (returns 200 OK)
- `/`: Basic HTML page with exporter information

## Prometheus Configuration

Add the following to your Prometheus configuration to scrape this exporter:

```yaml
scrape_configs:
  - job_name: 'freeipa'
    static_configs:
      - targets: ['your-exporter-host:9189']
    scrape_interval: 60s
```

## Development

### Requirements

- Python 3.8+
- libsasl2-dev, libldap2-dev, libssl-dev (for python-ldap)

### Testing

To test the exporter locally:

```bash
python exporter.py
```

Then visit `http://localhost:9189/metrics` to see the metrics.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0), in compliance with the license of the original work it derives from. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
