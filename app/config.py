# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import ipaddress
import socket
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Sicherheitsgehärtete Anwendungskonfiguration basierend auf Pydantic v2.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Datenbank
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/podcast_researcher",
        description="Async SQLAlchemy Datenbank-Verbindungs-URL (PostgreSQL oder SQLite)"
    )

    # Gemini AI
    GEMINI_API_KEY: str | None = Field(
        default=None,
        description="Google Gemini API-Key für KI-Analysen"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Standard-Modell für Analysen (z.B. gemini-2.5-flash, gemini-1.5-pro)"
    )

    # Allgemein & Sicherheit
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    MAX_EPISODES_PER_IMPORT: int = Field(default=100, ge=1, le=500)
    REQUEST_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:8000", "http://127.0.0.1:8000"]
    )

    # Webspaces & Publishing (Gemini & Gopher)
    PUBLIC_DIR: str = Field(default="public", description="Basis-Ausgabeverzeichnis für statische Gemini- & Gopher-Dateien")
    GOPHER_HOST: str = Field(default="localhost", description="Standard Hostname für RFC 1436 Gophermap-Menüeinträge")
    GOPHER_PORT: int = Field(default=70, ge=1, le=65535, description="Standard Port für Gopherspace")
    GEMINI_BASE_URL: str = Field(default="gemini://localhost", description="Basis-URL für Geminispace-Verweise")

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        # Falls postgres:// übergeben wird (z.B. von manchen Cloud-Providern), auf postgresql+asyncpg:// umschreiben
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    def is_gemini_available(self) -> bool:
        """Prüft, ob ein gültiger Gemini API-Key konfiguriert ist."""
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip() and self.GEMINI_API_KEY != "your_gemini_api_key_here")

    def get_masked_gemini_key(self) -> str:
        """Gibt den maskierten API-Key zurück, um Secrets in Logs/UIs niemals zu exponieren."""
        if not self.GEMINI_API_KEY or not self.is_gemini_available():
            return "NICHT KONFIGURIERT"
        key = self.GEMINI_API_KEY.strip()
        if len(key) <= 8:
            return "******"
        return f"{key[:4]}...{key[-4:]}"


# Globales Settings-Objekt
settings = Settings()


# ==============================================================================
# SSRF- & URL-Sicherheitsvalidierung (ADR-0001)
# ==============================================================================
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # 'This' Network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (CGNAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local (inkl. AWS Metadata 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    ipaddress.ip_network("::1/128"),            # IPv6 Loopback
    ipaddress.ip_network("::/128"),             # IPv6 Unspecified
    ipaddress.ip_network("fc00::/7"),           # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),          # IPv6 Link-Local
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
]


def _is_ip_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Prüft, ob eine IP-Adresse in einem geblockten / privaten / Loopback-Bereich liegt."""
    if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified:
        return True
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped and _is_ip_blocked(ip_obj.ipv4_mapped):
        return True
    return any(ip_obj in net for net in BLOCKED_IP_NETWORKS)


def _parse_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """
    Parst IP-Literale in Standard-, Dezimal- (DWORD), Hex- oder Oktalnotation.
    Verhindert typische SSRF-Bypass-Tricks wie http://2130706433/ oder http://0x7f000001.
    """
    # Standard IPv4 / IPv6 Notation
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass

    # C-Socket / inet_aton Notation (z.B. 0177.0.0.1, 2130706433, 0x7f000001)
    try:
        packed = socket.inet_aton(host)
        if len(packed) == 4 and (host.count(".") > 0 or host.isdigit() or host.lower().startswith("0x")):
            return ipaddress.IPv4Address(packed)
    except (OSError, OverflowError, ValueError):
        pass

    # Direkte Integer- oder Hex-Repräsentation
    try:
        val = int(host, 0)
        if 0 <= val <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(val)
    except (ValueError, TypeError):
        pass

    return None


def is_safe_external_url(url: str) -> tuple[bool, str]:
    """
    Validiert eine externe URL strikt gegen SSRF, bösartige Schemes und private IP-Bereiche.
    Gibt (is_safe, error_reason) zurück.
    """
    if not url or not isinstance(url, str):
        return False, "Ungültige oder leere URL."

    cleaned_url = url.strip()
    if len(cleaned_url) > 2048:
        return False, "URL überschreitet die maximale Länge von 2048 Zeichen."

    try:
        parsed = urlparse(cleaned_url)
    except Exception as e:
        return False, f"URL-Parsing fehlgeschlagen: {str(e)}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unzulässiges URL-Scheme '{parsed.scheme}'. Erlaubt sind nur http:// und https://."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL enthält keinen gültigen Hostnamen."

    hostname_lower = hostname.lower().strip()

    # Statische Prüfung auf bekannte interne Hostnamen
    if (
        hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal")  # nosec B104
        or hostname_lower.endswith(".local")
        or hostname_lower.endswith(".internal")
        or hostname_lower.endswith(".localhost")
    ):
        return False, f"Zugriff auf internen Host '{hostname}' ist aus Sicherheitsgründen untersagt (SSRF-Schutz)."

    # IP-Prüfung bei direkter IP-Eingabe (inklusive DWORD/Hex/Oktal Evasion)
    ip_obj = _parse_ip_literal(hostname_lower)
    if ip_obj:
        if _is_ip_blocked(ip_obj):
            return False, f"IP-Adresse '{ip_obj}' liegt in einem gesperrten Adressbereich (SSRF-Schutz)."
    else:
        # Domain-Name: DNS-Auflösung zur Überprüfung, ob Domain auf private IP zeigt (DNS-Rebinding Schutz)
        try:
            addr_info = socket.getaddrinfo(hostname_lower, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for item in addr_info:
                resolved_ip = ipaddress.ip_address(item[4][0])
                if _is_ip_blocked(resolved_ip):
                    return False, f"Domain '{hostname}' löst auf gesperrte IP '{resolved_ip}' auf (SSRF-Schutz)."
        except (socket.gaierror, Exception):
            pass

    return True, ""
