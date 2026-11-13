#!/usr/bin/env python3
"""Populate data/assets.json from official museum APIs. Run locally with network access.
Only records that an API actually returns are written. CC0/public-domain images are downloaded
(untouched originals kept in images/original). V&A and anything else is flagged needs-review.
Optional: pip install rembg pillow  ->  --cutout writes PNG cut-outs to images/cutouts (originals untouched)."""
import json, os, sys, time, datetime, urllib.parse as up, urllib.request as ur
OUT, MS, IMG = "data/assets.json", "data/milestones.json", "images"
def get(u):
    with ur.urlopen(ur.Request(u, headers={"User-Agent": "fashion-archive/0.1"}), timeout=40) as r: return json.load(r)
def met(q, n):
    ids = get("https://collectionapi.metmuseum.org/public/collection/v1/search?hasImages=true&isPublicDomain=true&q=" + up.quote(q)).get("objectIDs") or []
    k = 0
    for i in ids[:n * 4]:
        o = get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{i}")
        if o.get("isPublicDomain") and o.get("primaryImage"):
            yield dict(id=f"met-{i}", title=o["title"], maker=o.get("artistDisplayName") or o.get("culture") or "", date=o.get("objectDate", ""), region=o.get("culture") or o.get("country") or "", museum="The Metropolitan Museum of Art", page=o["objectURL"], url=o["primaryImage"], licence="CC0", rights_status="cc0")
            k += 1
            if k >= n: return
        time.sleep(.15)
def cma(q, n):
    for o in get("https://openaccess-api.clevelandart.org/api/artworks/?cc0=1&has_image=1&limit=%d&q=%s" % (n, up.quote(q)))["data"]:
        im = (o.get("images") or {}).get("web") or {}
        if im.get("url"):
            yield dict(id=f"cma-{o['id']}", title=o["title"], maker=", ".join(c["description"] for c in o.get("creators", [])), date=o.get("creation_date", ""), region=o.get("culture", [""])[0] if o.get("culture") else "", museum="Cleveland Museum of Art", page=o["url"], url=im["url"], w=im.get("width"), h=im.get("height"), licence="CC0", rights_status="cc0")
def vam(q, n):
    for o in get("https://api.vam.ac.uk/v2/objects/search?images_exist=1&page_size=%d&q=%s" % (n, up.quote(q)))["records"]:
        im = o.get("_primaryImageId")
        if im:
            yield dict(id=f"vam-{o['systemNumber']}", title=o.get("_primaryTitle") or o.get("objectType", ""), maker=(o.get("_primaryMaker") or {}).get("name", ""), date=o.get("_primaryDate", ""), region=o.get("_primaryPlace", ""), museum="Victoria and Albert Museum", page=f"https://collections.vam.ac.uk/item/{o['systemNumber']}/", url=f"https://framemark.vam.ac.uk/collections/{im}/full/!1200,1200/0/default.jpg", licence="V&A terms: check this item", rights_status="needs-review")
SRC = {"met": met, "cma": cma, "vam": vam}
# (source, query, category, milestone ids, max). Edit freely; judge every result by eye before use.
T = [
("met","Mughal painting court","paintings",["mughal-court"],6),("cma","Mughal miniature","paintings",["mughal-court"],6),("met","Mughal textile","textiles",["mughal-muslin"],4),("met","Mughal jewelry","jewellery",["mughal-court"],4),("vam","jamdani muslin","textiles",["mughal-muslin"],3),
("met","robe a la francaise","garments",["rococo-francaise"],5),("met","fashion plate 1780","illustrations",["rococo-bertin"],4),("vam","robe a la francaise","garments",["rococo-francaise"],5),("met","Rococo portrait silk gown","portraits",["rococo-francaise"],4),
("met","kosode","garments",["edo-kosode"],5),("met","ukiyo-e beauty kimono","paintings",["edo-kosode"],6),("cma","kosode","garments",["edo-kosode"],4),("met","kimono pattern book","illustrations",["edo-yuzen"],3),("vam","kosode","garments",["edo-kosode"],3),
("met","Egyptian pleated linen","textiles",["tarkhan-dress","egypt-new-kingdom"],4),("met","Egyptian tomb painting dress","paintings",["egypt-new-kingdom"],5),("met","Egyptian statue wig","sculptures",["egypt-new-kingdom"],5),("met","Egyptian collar necklace","jewellery",["egypt-new-kingdom"],4),("cma","Egyptian relief","sculptures",["egypt-new-kingdom"],4),
("met","1920s evening dress","garments",["twenties-silhouette"],6),("met","1920s fashion illustration","illustrations",["twenties-silhouette"],5),("vam","1920s dress beaded","garments",["twenties-silhouette"],4),("met","cloche hat","jewellery",["twenties-silhouette"],3),("met","Chanel dress","garments",["chanel-lbd"],3),
("vam","Alexander McQueen","garments",["mcqueen-1995-1999"],3),("vam","Margiela","garments",["deconstruction-late-80s"],3),("met","Comme des Garcons","garments",["kawakubo-1997"],3),
]
def main():
    cutout = "--cutout" in sys.argv
    A = {a["id"]: a for a in json.load(open(OUT))["assets"]}
    for src, q, cat, ms, n in T:
        try:
            for r in SRC[src](q, n):
                a = A.setdefault(r["id"], r)
                a.update(category=cat, verified_at=datetime.date.today().isoformat())
                a["milestones"] = sorted(set(a.get("milestones", []) + ms))
                if a["rights_status"] in ("cc0", "public-domain") and not a.get("original_local"):
                    os.makedirs(f"{IMG}/original", exist_ok=True)
                    p = f"{IMG}/original/{a['id']}.jpg"
                    ur.urlretrieve(a["url"], p)
                    a["original_local"] = a["local"] = p
                    try:
                        from PIL import Image
                        with Image.open(p) as im: a["w"], a["h"] = im.size
                    except Exception: pass
                    if cutout:
                        try:
                            from rembg import remove
                            os.makedirs(f"{IMG}/cutouts", exist_ok=True)
                            c = f"{IMG}/cutouts/{a['id']}.png"; open(c, "wb").write(remove(open(p, "rb").read())); a["cutout_local"] = c
                        except Exception as e: print("cutout skipped", a["id"], e)
        except Exception as e: print("target failed", src, q, e)
    doc = json.load(open(OUT)); doc["assets"] = list(A.values()); doc["status"] = f"{len(A)} records (review each by eye before use)"
    json.dump(doc, open(OUT, "w"), indent=1)
    m = json.load(open(MS))
    for e in m["milestones"]: e["assets"] = [i for i, a in A.items() if e["id"] in a.get("milestones", [])]
    json.dump(m, open(MS, "w"), indent=1)
    print(len(A), "assets")
if __name__ == "__main__": main()
