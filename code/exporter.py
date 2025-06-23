import os
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from prometheus_client import generate_latest, REGISTRY
from prometheus_client.core import GaugeMetricFamily
from threading import Lock
from io import BytesIO
from freeipaserver import FreeIPAServer

CACHE_TTL = int(os.getenv("CACHE_TTL", 60))
EXPORTER_PORT = int(os.getenv("EXPORTER_PORT", "9189"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FreeIPACollector:
    def __init__(self, hosts, domain, binddn, bindpw):
        self.hosts = hosts
        self.domain = domain
        self.binddn = binddn
        self.bindpw = bindpw
        self.cache = None
        self.cache_time = 0
        self.lock = Lock()

    def collect(self):
        with self.lock:
            now = time.time()
            if self.cache and (now - self.cache_time < CACHE_TTL):
                for metric in self.cache:
                    yield metric
                return

            start_time = time.time()
            metrics = []

            checks = {
                'users': 'Active Users',
                'susers': 'Stage Users',
                'pusers': 'Preserved Users',
                'hosts': 'Hosts',
                'services': 'Services',
                'ugroups': 'User Groups',
                'hgroups': 'Host Groups',
                'ngroups': 'Netgroups',
                'hbac': 'HBAC Rules',
                'sudo': 'SUDO Rules',
                'zones': 'DNS Zones',
                'certs': 'Certificates',
                'conflicts': 'LDAP Conflicts',
                'ghosts': 'Ghost Replicas',
                'bind': 'Anonymous BIND (1=ON, 0=OFF)',
                'msdcs': 'Microsoft ADTrust (1=True, 0=False)',
            }

            status_metrics = {
                k: GaugeMetricFamily(f"ipa_{k}", desc, labels=["host"])
                for k, desc in checks.items()
            }

            replica_metric = GaugeMetricFamily("ipa_replication_status", "Replication status (0=OK, 1=Error)", labels=["source", "target"])
            up_metric = GaugeMetricFamily("ipa_up", "Was the last scrape of this FreeIPA instance successful", labels=["host"])
            duration_metric = GaugeMetricFamily("ipa_scrape_duration_seconds", "Time taken to scrape metrics from FreeIPA", labels=["host"])

            for host in self.hosts:
                logger.info(f"Scraping FreeIPA host: {host}")
                host_start = time.time()
                server = FreeIPAServer(host, self.domain, self.binddn, self.bindpw)
                scrape_ok = 0

                if not server._conn:
                    logger.warning(f"Could not connect to {host}")
                    up_metric.add_metric([host], 0.0)
                    duration_metric.add_metric([host], 0.0)
                    continue

                try:
                    for key in checks:
                        val = getattr(server, key)
                        if val is None:
                            continue
                        if isinstance(val, str):
                            if val.upper() in ("ON", "TRUE"):
                                val = 1
                            elif val.upper() in ("OFF", "FALSE"):
                                val = 0
                            else:
                                val = int(float(val))
                        else:
                            val = int(val)
                        status_metrics[key].add_metric([server.hostname_short], val)

                    if server.replicas:
                        for line in server.replicas.splitlines():
                            parts = line.split()
                            if len(parts) == 2:
                                target, status = parts
                                val = 0 if status in ["0", "18"] else 1
                                replica_metric.add_metric([server.hostname_short, target], val)

                    scrape_ok = 1

                except Exception as e:
                    logger.warning(f"Failed to scrape metrics from {host}: {e}")

                up_metric.add_metric([server.hostname_short], scrape_ok)
                duration_metric.add_metric([server.hostname_short], time.time() - host_start)

            metrics.extend(status_metrics.values())
            metrics.append(replica_metric)
            metrics.append(up_metric)
            metrics.append(duration_metric)

            self.cache = metrics
            self.cache_time = now

            for metric in metrics:
                yield metric


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            output = generate_latest(REGISTRY)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)

        elif self.path == "/":
            html = """<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>FreeIPA Exporter</title>
        </head>
        <body>
            <h1>FreeIPA Exporter</h1>
            <p>This exporter provides metrics for FreeIPA monitoring.</p>
            <ul>
                <li><a href="/metrics">/metrics</a> — Prometheus metrics</li>
                <li><a href="/health">/health</a> — Health check endpoint</li>
            </ul>
        </body>
        </html>
        """
            encoded = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    domain = os.getenv("FREEIPA_DOMAIN")
    binddn = os.getenv("FREEIPA_BIND_DN", "cn=Directory Manager")
    bindpw = os.getenv("FREEIPA_BIND_PW")
    hosts = [h.strip() for h in os.getenv("FREEIPA_HOSTS", "").split(',') if h.strip()]

    if not all([domain, bindpw, hosts]):
        raise SystemExit("Missing one of FREEIPA_DOMAIN, FREEIPA_BIND_PW, or FREEIPA_HOSTS env vars")

    collector = FreeIPACollector(hosts, domain, binddn, bindpw)
    REGISTRY.register(collector)

    server = ThreadedHTTPServer(("0.0.0.0", EXPORTER_PORT), MetricsHandler)
    logger.info(f"FreeIPA exporter listening on port {EXPORTER_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down exporter.")
