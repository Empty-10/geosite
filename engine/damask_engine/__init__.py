"""damask scan engine — URL in, scored GEO/SEO report out."""

from .scanner import scan, scan_html
from .models import Report, Finding, Confidence, Severity, Status, Pillar

__all__ = ["scan", "scan_html", "Report", "Finding", "Confidence", "Severity", "Status", "Pillar"]
__version__ = "0.0.1"
