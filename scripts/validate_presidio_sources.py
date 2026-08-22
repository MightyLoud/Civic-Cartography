#!/usr/bin/env python3
"""Validate Presidio County roster and mixed optional-office contracts."""
from __future__ import annotations
import csv, json, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(path):return list(csv.DictReader((ROOT/path).open(encoding="utf-8")))
def main():
 roster=rows("data/raw/presidio-county/current-elected-offices.csv")
 assert len(roster)==10 and len({r["officeholder_name"] for r in roster})==10
 assert sum(r["office_name"]=="Sheriff" for r in roster)==1
 assert sum(r["office_name"]=="Tax Assessor-Collector" for r in roster)==1
 assert not any("Sheriff/Tax" in r["office_name"] for r in roster)
 assert sum(r["office_name"]=="District Clerk and County Clerk" for r in roster)==1
 structure=rows("data/raw/presidio-county/mixed-office-structure.csv")
 assert {r["contract"] for r in structure}=={"separate_sheriff_tax","combined_clerk"}
 contract=json.loads((ROOT/"data/raw/presidio-county/gis-source-contract.json").read_text())
 assert contract["commissioner_assignments"]=={"1":"1","2":"1","3":"2","4":"2","5":"3","6":"3","7":"4"}
 urls=sorted({r["source_url"] for r in roster})
 for url in urls:
  req=urllib.request.Request(url,headers={"User-Agent":"Civic-Cartography/0.1"})
  with urllib.request.urlopen(req,timeout=60) as response:
   if response.status!=200:raise AssertionError(url)
 print(f"Validated {len(urls)} live Presidio County page contract(s).")
 print("Presidio County roster, mixed offices, scope, and source contracts are valid.")
if __name__=="__main__":main()
