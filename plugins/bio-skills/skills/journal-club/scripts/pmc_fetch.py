#!/usr/bin/env python3
"""
pmc_fetch.py — Fetch PMC / bioRxiv papers and parse JATS XML, stdlib only.

Author: Samuel Ahuno (ekwame001@gmail.com)
Date: 2026-04-30

Replaces the previously-external `pmc_utils.py`. Designed to be self-contained
(uses only Python stdlib: urllib, xml.etree, zipfile, json) so the journal-club
skill works outside the user's main project.

Capabilities
------------
- Resolve a PMID to a PMCID via NCBI eutils (`pmid2pmcid`).
- Resolve a bioRxiv DOI to a PMC record via NCBI eutils, when the preprint is
  also indexed in PMC (most are within ~weeks of posting).
- Download JATS XML for a given PMCID via eutils efetch.
- Parse a JATS XML into a structured dict: title, authors, abstract, sections,
  references, figure catalogue (with verbatim captions), data-availability,
  funding, supplementary-material entries.
- Pull supplementary files via the Europe PMC `supplementaryFiles` ZIP endpoint
  (not Cloudflare-protected; works for PMC-indexed papers including bioRxiv
  preprints once they have a PMC ID).

Limitations
-----------
- Does NOT handle Cloudflare-protected bioRxiv full-text or PDF directly. For
  preprints not yet indexed in PMC, fall back to playwright/cloudscraper-based
  fetch_preprint() (not vendored here; install separately).
- Does NOT extract images from PDFs — see `extract_pdf_images.py` for that.

CLI usage
---------
  # Fetch a PMC paper, save XML and parse
  python pmc_fetch.py PMC12918801 --out-dir ~/journalClub/PMC12918801/

  # Fetch a bioRxiv preprint by DOI (will look up PMC via eutils)
  python pmc_fetch.py --doi 10.64898/2026.02.12.705658 --out-dir ~/journalClub/<id>/

  # Fetch supplementary files (zip) from Europe PMC
  python pmc_fetch.py PMC12918801 --supplement --out-dir ~/journalClub/PMC12918801/

Programmatic usage
------------------
    from pmc_fetch import download_pmc_xml, parse_pmc_xml, fetch_supplement_zip

    xml_path = download_pmc_xml('PMC12918801', out_dir='xml/')
    paper = parse_pmc_xml(xml_path, pmcid='PMC12918801')
    fetch_supplement_zip('PMC12918801', out_dir='pdf/')
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

XLINK = "{http://www.w3.org/1999/xlink}href"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EPMC_REST = "https://www.ebi.ac.uk/europepmc/webservices/rest"
PMC_BIN = "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{href}"

USER_AGENT = "journal-club-skill/1.0 (mailto:ekwame001@gmail.com)"


# ---------- HTTP helpers -------------------------------------------------------


def _get(url: str, timeout: int = 30) -> bytes:
    """Stdlib HTTP GET with a custom User-Agent."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------- ID resolution ------------------------------------------------------


def pmid_to_pmcid(pmid: str) -> str | None:
    """Map a PMID to a PMCID via eutils elink. Returns 'PMC<digits>' or None."""
    url = f"{EUTILS}/elink.fcgi?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json"
    data = json.loads(_get(url).decode())
    try:
        links = data["linksets"][0]["linksetdbs"]
        for ldb in links:
            if ldb.get("linkname") == "pubmed_pmc":
                return f"PMC{ldb['links'][0]}"
    except (KeyError, IndexError):
        pass
    return None


def doi_to_pmcid(doi: str) -> str | None:
    """Resolve a DOI (preprint or journal) to a PMCID via eutils esearch+elink.

    Returns 'PMC<digits>' if the DOI is indexed in PubMed and has a PMC link.
    """
    # Step 1: DOI -> PMID via esearch
    q = urllib.parse.quote(f'"{doi}"[doi]')
    url = f"{EUTILS}/esearch.fcgi?db=pubmed&term={q}&retmode=json"
    data = json.loads(_get(url).decode())
    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None
    pmid = ids[0]
    # Step 2: PMID -> PMCID via elink
    return pmid_to_pmcid(pmid)


# ---------- XML download -------------------------------------------------------


def download_pmc_xml(pmcid: str, out_dir: str | Path) -> Path:
    """Download JATS XML for a PMCID via eutils efetch.

    Args
    ----
    pmcid : str  e.g. 'PMC12918801' or '12918801'
    out_dir : path  directory where the XML will be saved (created if absent)

    Returns
    -------
    Path to the saved XML file: <out_dir>/<pmcid>.xml
    """
    pmcid_num = pmcid.replace("PMC", "")
    pmcid_full = f"PMC{pmcid_num}"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{pmcid_full}.xml"
    url = f"{EUTILS}/efetch.fcgi?db=pmc&id={pmcid_num}&retmode=xml"
    out_path.write_bytes(_get(url, timeout=60))
    return out_path


# ---------- JATS parsing -------------------------------------------------------


def _text_of(el: ET.Element | None) -> str:
    """Concatenate all itertext() under an element with whitespace normalized."""
    if el is None:
        return ""
    return " ".join(t.strip() for t in el.itertext()).strip()


def parse_pmc_xml(xml_path: str | Path, pmcid: str | None = None) -> dict:
    """Parse a JATS XML into a structured dict for journal-club downstream stages.

    Args
    ----
    xml_path : path to a JATS XML file
    pmcid : str, optional. Used for constructing figure URLs. If None, attempts
        to derive from the XML or filename.

    Returns
    -------
    dict with keys:
        title, authors, journal, year, doi, pmid, pmcid,
        abstract, sections, figures, supplements, data_availability,
        funding, references
    """
    xml_path = Path(xml_path)
    root = ET.parse(xml_path).getroot()

    # ----- IDs (title, journal, year, DOI, PMID, PMCID) -----
    title_el = root.find(".//article-title")
    title = _text_of(title_el)

    journal_el = root.find(".//journal-title")
    journal = _text_of(journal_el)

    year_el = root.find(".//pub-date/year")
    year = year_el.text.strip() if (year_el is not None and year_el.text) else ""

    ids = {}
    for aid in root.iter("article-id"):
        kind = aid.get("pub-id-type", "")
        if aid.text:
            ids[kind] = aid.text.strip()
    doi = ids.get("doi", "")
    pmid = ids.get("pmid", "")
    pmcid_xml = ids.get("pmcaid", "") or ids.get("pmcid", "")
    if not pmcid:
        pmcid = pmcid_xml or xml_path.stem  # fall back to filename stem

    # ----- Authors -----
    authors = []
    for contrib in root.iter("contrib"):
        if contrib.get("contrib-type", "") != "author":
            continue
        surname = contrib.findtext(".//surname", default="").strip()
        given = contrib.findtext(".//given-names", default="").strip()
        if surname:
            authors.append({"surname": surname, "given": given})

    # ----- Abstract -----
    abstract_el = root.find(".//abstract")
    abstract = _text_of(abstract_el)

    # ----- Body sections -----
    sections = []
    for sec in root.findall(".//body//sec"):
        sec_title = sec.find("title")
        sections.append({
            "id": sec.get("id", ""),
            "title": (sec_title.text.strip() if (sec_title is not None and sec_title.text) else ""),
            "text": _text_of(sec)[:5000],  # cap to avoid bloat
        })

    # ----- Figures with verbatim captions -----
    figures = []
    for fig in root.iter("fig"):
        label_el = fig.find("label")
        cap_el = fig.find("caption")
        gfx_el = fig.find("graphic")
        caption_full = _text_of(cap_el)
        href = gfx_el.attrib.get(XLINK, "") if gfx_el is not None else ""
        url = PMC_BIN.format(pmcid=pmcid, href=href) if (href and pmcid) else ""
        headline = caption_full.split(". ", 1)[0] + "." if caption_full else ""
        figures.append({
            "id": fig.get("id", ""),
            "label": label_el.text.strip() if (label_el is not None and label_el.text) else "",
            "headline": headline,
            "caption_full": caption_full,
            "graphic_href": href,
            "url": url,
        })

    # ----- Supplementary material -----
    supplements = []
    for sm in root.iter("supplementary-material"):
        media_el = sm.find("media")
        media_href = media_el.attrib.get(XLINK, "") if media_el is not None else ""
        label = sm.find("label")
        cap = sm.find("caption")
        supplements.append({
            "id": sm.get("id", ""),
            "label": _text_of(label) if label is not None else "",
            "caption": _text_of(cap) if cap is not None else "",
            "media_href": media_href,
            "pmc_url": PMC_BIN.format(pmcid=pmcid, href=media_href) if (media_href and pmcid) else "",
        })

    # ----- Data availability + Funding (named-section convention) -----
    data_availability = ""
    funding = ""
    for sec in root.iter("sec"):
        sec_title = sec.find("title")
        sec_title_txt = (sec_title.text or "") if sec_title is not None else ""
        if re.search(r"data\s*availability", sec_title_txt, re.IGNORECASE):
            data_availability = _text_of(sec)
        elif re.search(r"funding", sec_title_txt, re.IGNORECASE):
            funding = _text_of(sec)

    # ----- References -----
    references = []
    for ref in root.iter("ref"):
        ref_id = ref.get("id", "")
        cit = ref.find(".//mixed-citation")
        if cit is None:
            cit = ref.find(".//element-citation")
        if cit is not None:
            references.append({"id": ref_id, "text": _text_of(cit)})

    return {
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "doi": doi,
        "pmid": pmid,
        "pmcid": pmcid,
        "abstract": abstract,
        "sections": sections,
        "figures": figures,
        "supplements": supplements,
        "data_availability": data_availability,
        "funding": funding,
        "references": references,
    }


# ---------- Supplementary files via Europe PMC ---------------------------------


def fetch_supplement_zip(pmcid: str, out_dir: str | Path) -> Path | None:
    """Fetch the EuropePMC supplementaryFiles ZIP for a PMCID.

    Not Cloudflare-protected — this is the preferred PMC supplement path.
    Typical ZIP contents: media-1.pdf (the supplement), plus per-figure
    JPGs and GIFs. Caller is responsible for unpacking and routing.

    Args
    ----
    pmcid : str  e.g. 'PMC12918801' or '12918801'
    out_dir : path  where to save the ZIP and unpack contents

    Returns
    -------
    Path to the saved ZIP, or None if EuropePMC has no supplement for this PMCID.
    """
    pmcid_full = f"PMC{pmcid.replace('PMC', '')}"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"{EPMC_REST}/{pmcid_full}/supplementaryFiles"
    try:
        data = _get(url, timeout=120)
    except Exception as e:
        print(f"[pmc_fetch] EuropePMC supplementaryFiles failed for {pmcid_full}: {e}",
              file=sys.stderr)
        return None
    # EuropePMC returns 200 with HTML when no supplement exists; ZIP magic is PK\x03\x04
    if not data.startswith(b"PK\x03\x04"):
        print(f"[pmc_fetch] EuropePMC returned non-ZIP response for {pmcid_full} "
              "(no supplement available)", file=sys.stderr)
        return None
    zip_path = out_dir / "supplementary.zip"
    zip_path.write_bytes(data)
    return zip_path


def unpack_supplement_zip(
    zip_path: str | Path,
    pdf_dir: str | Path,
    images_dir: str | Path,
) -> dict:
    """Unpack a EuropePMC supplement ZIP, routing files by extension.

    PDFs go to pdf_dir; image files (.jpg, .gif, .png, .tif) go to images_dir.

    Returns
    -------
    dict {'pdfs': [Path, ...], 'images': [Path, ...]}
    """
    zip_path = Path(zip_path)
    pdf_dir = Path(pdf_dir); pdf_dir.mkdir(parents=True, exist_ok=True)
    images_dir = Path(images_dir); images_dir.mkdir(parents=True, exist_ok=True)
    out = {"pdfs": [], "images": []}
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".bmp"}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            ext = Path(name).suffix.lower()
            if ext == ".pdf":
                target = pdf_dir / Path(name).name
                target.write_bytes(zf.read(name))
                out["pdfs"].append(target)
            elif ext in image_exts:
                target = images_dir / Path(name).name
                target.write_bytes(zf.read(name))
                out["images"].append(target)
    return out


# ---------- bioRxiv preprint metadata (no Cloudflare needed) -------------------


def fetch_biorxiv_metadata(doi: str) -> dict:
    """Fetch metadata + abstract for a bioRxiv preprint by DOI.

    The bioRxiv API endpoint is not Cloudflare-protected and returns title,
    authors, abstract, posting date(s), license, category — useful for Stage 1
    metadata even when full text isn't accessible.
    """
    url = f"https://api.biorxiv.org/details/biorxiv/{doi}"
    return json.loads(_get(url, timeout=30).decode())


# ---------- Convenience driver -------------------------------------------------


def fetch_paper(
    *,
    pmcid: str | None = None,
    pmid: str | None = None,
    doi: str | None = None,
    out_dir: str | Path,
    fetch_supplement: bool = True,
) -> dict:
    """One-call driver: resolve identifier → download XML → optionally fetch
    supplement ZIP → parse and return structured paper dict.

    Provide exactly one of pmcid / pmid / doi.

    Returns the parsed `paper` dict from `parse_pmc_xml`, plus extra keys:
        'xml_path', 'supplement_zip_path' (None if not requested or not available),
        'unpacked' (None if no zip).
    """
    out_dir = Path(out_dir)
    if pmcid is None and pmid is not None:
        pmcid = pmid_to_pmcid(pmid)
    if pmcid is None and doi is not None:
        pmcid = doi_to_pmcid(doi)
    if pmcid is None:
        raise ValueError("Could not resolve a PMCID from the provided identifier")

    xml_path = download_pmc_xml(pmcid, out_dir / "xml")
    paper = parse_pmc_xml(xml_path, pmcid=pmcid)
    paper["xml_path"] = str(xml_path)

    paper["supplement_zip_path"] = None
    paper["unpacked"] = None
    if fetch_supplement:
        zip_path = fetch_supplement_zip(pmcid, out_dir / "pdf")
        if zip_path is not None:
            paper["supplement_zip_path"] = str(zip_path)
            unpacked = unpack_supplement_zip(
                zip_path, pdf_dir=out_dir / "pdf", images_dir=out_dir / "images",
            )
            paper["unpacked"] = {
                "pdfs": [str(p) for p in unpacked["pdfs"]],
                "images": [str(p) for p in unpacked["images"]],
            }

    return paper


# ---------- CLI ----------------------------------------------------------------


def _cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("identifier", nargs="?", help="PMCID (e.g. PMC12918801)")
    ap.add_argument("--pmid", help="Resolve via PMID instead")
    ap.add_argument("--doi", help="Resolve via DOI (works for many bioRxiv preprints once PMC-indexed)")
    ap.add_argument("--out-dir", required=True, help="Where to save artifacts")
    ap.add_argument("--no-supplement", action="store_true",
                    help="Skip the EuropePMC supplementaryFiles ZIP fetch")
    ap.add_argument("--summary-only", action="store_true",
                    help="Print summary, do not write summary.json")
    args = ap.parse_args()

    pmcid = args.identifier
    paper = fetch_paper(
        pmcid=pmcid,
        pmid=args.pmid,
        doi=args.doi,
        out_dir=args.out_dir,
        fetch_supplement=not args.no_supplement,
    )

    print(f"Title:    {paper['title']}")
    print(f"Authors:  {len(paper['authors'])} listed (first: "
          f"{paper['authors'][0]['surname'] if paper['authors'] else '?'})")
    print(f"Journal:  {paper['journal']} ({paper['year']})")
    print(f"DOI:      {paper['doi']}")
    print(f"PMCID:    {paper['pmcid']}")
    print(f"Sections: {len(paper['sections'])}")
    print(f"Figures:  {len(paper['figures'])}")
    print(f"Refs:     {len(paper['references'])}")
    print(f"XML:      {paper['xml_path']}")
    if paper["supplement_zip_path"]:
        print(f"Suppl.:   {paper['supplement_zip_path']}")
        print(f"  PDFs:   {len(paper['unpacked']['pdfs'])}")
        print(f"  Images: {len(paper['unpacked']['images'])}")
    else:
        print("Suppl.:   not available / skipped")

    if not args.summary_only:
        out_dir = Path(args.out_dir)
        summary_path = out_dir / "fetch_summary.json"
        # Strip section bodies for the summary file; keep figures/captions intact
        compact = {**paper}
        compact["sections"] = [{"id": s["id"], "title": s["title"]} for s in paper["sections"]]
        compact["references"] = compact["references"][:20]  # cap
        summary_path.write_text(json.dumps(compact, indent=2))
        print(f"Summary:  {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
