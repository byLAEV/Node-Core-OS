#!/usr/bin/env python3
"""Dependency-free structural and referential-integrity validator for global mapping CSVs."""
import csv
import re
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
URL_RE = re.compile(r"^https?://[^\\s]+$", re.IGNORECASE)

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path.name}: missing header")
        rows = list(reader)
        for line, row in enumerate(rows, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path.name}:{line}: inconsistent CSV field count")
        return reader.fieldnames, rows

def validate_mapping(directory=BASE):
    errors = []
    _, jurisdictions = read_csv(directory / "COUNTRY-AND-JURISDICTION-REGISTER.csv")
    ih, institutions = read_csv(directory / "INSTITUTION-AND-PATHWAY-REGISTER.csv")
    eh, issuers = read_csv(directory / "ISSUER-AND-API-REGISTER.csv")
    ph, pathways = read_csv(directory / "LAWFUL-IDENTITY-PATHWAY-REGISTER.csv")
    for header, required, name in [
        (ih, ["institution_record_id","m49_country_or_area_code","iso3166_alpha2","evidence_source_urls","last_checked_utc","node_core_os_connector_status"], "institution"),
        (eh, ["issuer_record_id","institution_record_id","country_or_area_code"], "issuer"),
        (ph, ["procedure_record_id","m49_country_or_area_code","competent_institution_record_ids","procedure_status","source_urls","last_checked_utc"], "pathway")]:
        for field in required:
            if field not in header:
                errors.append(f"{name}: missing column {field}")
    if errors:
        return errors
    geo = {row["m49_country_or_area_code"]: row for row in jurisdictions}
    by_id = {}
    for line, row in enumerate(institutions, start=2):
        rid = row["institution_record_id"]
        if not rid or rid in by_id:
            errors.append(f"institution:{line}: empty or duplicate ID {rid}")
        by_id[rid] = row
        g = geo.get(row["m49_country_or_area_code"])
        if not g:
            errors.append(f"institution:{line}: unknown M49 {row['m49_country_or_area_code']}")
        elif g.get("iso3166_alpha2") != row["iso3166_alpha2"]:
            errors.append(f"institution:{line}: ISO/M49 mismatch for {rid}")
        try:
            date.fromisoformat(row["last_checked_utc"])
        except ValueError:
            errors.append(f"institution:{line}: invalid date for {rid}")
        sources = [v.strip() for v in row["evidence_source_urls"].split(";") if v.strip()]
        if not sources:
            errors.append(f"institution:{line}: missing evidence for {rid}")
        for url in sources:
            if not URL_RE.match(url):
                errors.append(f"institution:{line}: invalid source URL for {rid}")
    seen_issuers = set()
    for line, row in enumerate(issuers, start=2):
        rid = row["issuer_record_id"]
        if rid in seen_issuers:
            errors.append(f"issuer:{line}: duplicate ID {rid}")
        seen_issuers.add(rid)
        if row["institution_record_id"] not in by_id:
            errors.append(f"issuer:{line}: unresolved institution link {row['institution_record_id']}")
    seen_procedures = set()
    for line, row in enumerate(pathways, start=2):
        rid = row["procedure_record_id"]
        if rid in seen_procedures:
            errors.append(f"pathway:{line}: duplicate ID {rid}")
        seen_procedures.add(rid)
        if row["m49_country_or_area_code"] not in geo:
            errors.append(f"pathway:{line}: unknown M49 for {rid}")
        linked = [v.strip() for v in row["competent_institution_record_ids"].split(";") if v.strip()]
        if not linked:
            errors.append(f"pathway:{line}: no linked institution for {rid}")
        for institution_id in linked:
            if institution_id not in by_id:
                errors.append(f"pathway:{line}: unresolved institution {institution_id}")
        sources = [v.strip() for v in row["source_urls"].split(";") if v.strip()]
        if not sources:
            errors.append(f"pathway:{line}: missing source for {rid}")
        for url in sources:
            if not URL_RE.match(url):
                errors.append(f"pathway:{line}: invalid source URL for {rid}")
        try:
            date.fromisoformat(row["last_checked_utc"])
        except ValueError:
            errors.append(f"pathway:{line}: invalid date for {rid}")
    return errors

def main():
    errors = validate_mapping()
    if errors:
        for item in errors:
            print("ERROR:", item)
        print(f"Validation failed: {len(errors)} error(s).")
        return 1
    print("Validation passed.")
    for filename, label in [
        ("COUNTRY-AND-JURISDICTION-REGISTER.csv","Jurisdictions"),
        ("INSTITUTION-AND-PATHWAY-REGISTER.csv","Institutions"),
        ("ISSUER-AND-API-REGISTER.csv","Issuer records"),
        ("LAWFUL-IDENTITY-PATHWAY-REGISTER.csv","Procedure records")]:
        print(f"{label}: {len(read_csv(BASE / filename)[1])}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
