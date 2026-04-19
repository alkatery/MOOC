"""SCORM package import and runtime bridge.

This is a pragmatic implementation that:

* Accepts a SCORM .zip upload
* Extracts the manifest (imsmanifest.xml) to find the launch entry point
* Stores the package under ``<data_dir>/scorm/<pkg_id>/``
* Exposes a simple JSON API that a SCORM 1.2 wrapper JS can call
  to persist ``cmi.core.lesson_status``, ``cmi.core.score.raw``, etc.

It is not a full-blown SCORM LMS — rather the minimum viable runtime
that lets NELC-compliant SCORM content packages run inside the platform
while emitting xAPI statements for audit.
"""

from __future__ import annotations

import re
import shutil
import uuid
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import get_settings


@dataclass
class ScormPackage:
    package_id: str
    title: str
    launch_url: str
    version: str
    root: Path


NAMESPACES = {
    "ims": "http://www.imsproject.org/xsd/imscp_rootv1p1p2",
    "adl": "http://www.adlnet.org/xsd/adlcp_rootv1p2",
    "imsss": "http://www.imsglobal.org/xsd/imsss",
}


def _find_text(elem: ET.Element, paths) -> str:
    for p in paths:
        node = elem.find(p, NAMESPACES)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def import_package(zip_path: Path) -> ScormPackage:
    """Extract a SCORM zip and return a :class:`ScormPackage`."""
    settings = get_settings()
    pkg_id = uuid.uuid4().hex
    dest = settings.data_dir / "scorm" / pkg_id
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            # Protect against zip-slip
            target = dest / member
            try:
                target.resolve().relative_to(dest.resolve())
            except ValueError:
                raise ValueError(f"Unsafe path in SCORM package: {member}")
        zf.extractall(dest)

    manifest = dest / "imsmanifest.xml"
    if not manifest.exists():
        raise ValueError("SCORM package is missing imsmanifest.xml")

    tree = ET.parse(manifest)
    root = tree.getroot()

    version = ""
    schemaversion = _find_text(root, ["./{*}metadata/{*}schemaversion"])
    if schemaversion:
        version = schemaversion
    else:
        version = root.attrib.get("version", "unknown")

    title = _find_text(
        root,
        [
            "./{*}organizations/{*}organization/{*}title",
            "./{*}organizations/{*}organization/{*}item/{*}title",
        ],
    ) or "SCORM Package"

    resources = root.findall("./{*}resources/{*}resource")
    launch_href = ""
    for res in resources:
        scorm_type = res.attrib.get(
            "{http://www.adlnet.org/xsd/adlcp_rootv1p2}scormtype"
        ) or res.attrib.get("adlcp:scormtype", "")
        href = res.attrib.get("href", "")
        if href and (scorm_type.lower() == "sco" or not scorm_type):
            launch_href = href
            break
    if not launch_href:
        # Fallback: first HTML file
        for p in dest.rglob("*.html"):
            launch_href = str(p.relative_to(dest))
            break

    launch_url = f"/scorm/{pkg_id}/{launch_href}"
    return ScormPackage(
        package_id=pkg_id,
        title=title,
        launch_url=launch_url,
        version=version,
        root=dest,
    )


def delete_package(package_id: str) -> bool:
    settings = get_settings()
    pkg_dir = settings.data_dir / "scorm" / package_id
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
        return True
    return False


def package_root(package_id: str) -> Optional[Path]:
    settings = get_settings()
    candidate = settings.data_dir / "scorm" / package_id
    return candidate if candidate.exists() else None


# SCORM 1.2 <-> xAPI mapping helpers -----------------------------------------


_SCORM_STATUS_MAP = {
    "passed": "passed",
    "failed": "failed",
    "completed": "completed",
    "incomplete": "experienced",
    "browsed": "experienced",
    "not attempted": "launched",
}


def scorm_status_to_xapi_verb(status: str) -> str:
    return _SCORM_STATUS_MAP.get((status or "").strip().lower(), "experienced")


_CMI_KEY = re.compile(r"^cmi\.[a-z0-9_.]+$")


def is_valid_cmi_key(key: str) -> bool:
    return bool(_CMI_KEY.match(key or ""))
