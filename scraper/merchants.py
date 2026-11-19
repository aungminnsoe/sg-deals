"""Work out which merchant a deal belongs to, from its title/categories."""
from __future__ import annotations

import re
import unicodedata

# Canonical name -> patterns that identify it (matched case-insensitively,
# on word boundaries). Add your own freely; order does not matter.
BRANDS: dict[str, list[str]] = {
    # Marketplaces / online
    "Amazon": [r"amazon"],
    "Shopee": [r"shopee"],
    "Lazada": [r"lazada"],
    "Qoo10": [r"qoo10"],
    "Taobao": [r"taobao"],
    "AliExpress": [r"aliexpress"],
    "Zalora": [r"zalora"],
    "iHerb": [r"iherb"],
    "Temu": [r"temu"],
    "Klook": [r"klook"],
    # Fast food / F&B
    "KFC": [r"kfc"],
    "McDonald's": [r"mcdonald'?s", r"mcdonalds", r"mcdelivery"],
    "Burger King": [r"burger king"],
    "Popeyes": [r"popeyes"],
    "Subway": [r"subway"],
    "Pizza Hut": [r"pizza hut"],
    "Domino's": [r"domino'?s"],
    "Jollibee": [r"jollibee"],
    "Texas Chicken": [r"texas chicken"],
    "Starbucks": [r"starbucks"],
    "Coffee Bean": [r"coffee bean", r"tcc"],
    "LiHO": [r"liho"],
    "Gong Cha": [r"gong ?cha"],
    "KOI": [r"\bkoi\b"],
    "Sushiro": [r"sushiro"],
    "Genki Sushi": [r"genki"],
    "Swensen's": [r"swensen'?s"],
    "4Fingers": [r"4 ?fingers"],
    "Mr Bean": [r"mr\.? bean"],
    "Old Chang Kee": [r"old chang kee"],
    "bb.q Chicken": [r"bb\.?q chicken"],
    "Haidilao": [r"haidilao"],
    # Delivery
    "GrabFood / Grab": [r"\bgrab\b", r"grabfood", r"grabmart", r"grabrides"],
    "foodpanda": [r"foodpanda", r"pandamart"],
    "Deliveroo": [r"deliveroo"],
    # Groceries & convenience
    "FairPrice": [r"fairprice", r"ntuc"],
    "Sheng Siong": [r"sheng siong"],
    "Giant": [r"\bgiant\b"],
    "Cold Storage": [r"cold storage"],
    "7-Eleven": [r"7-?eleven"],
    "Cheers": [r"\bcheers\b"],
    "RedMart": [r"redmart"],
    "Don Don Donki": [r"don ?don ?donki", r"donki"],
    # Retail / fashion / home
    "UNIQLO": [r"uniqlo"],
    "IKEA": [r"ikea"],
    "Decathlon": [r"decathlon"],
    "Charles & Keith": [r"charles ?& ?keith", r"charles and keith"],
    "H&M": [r"h&m"],
    "Sephora": [r"sephora"],
    "Watsons": [r"watsons"],
    "Guardian": [r"guardian"],
    "Challenger": [r"challenger"],
    "Courts": [r"\bcourts\b"],
    "Harvey Norman": [r"harvey norman"],
    "Best Denki": [r"best denki"],
    "Apple": [r"\bapple\b", r"iphone", r"macbook"],
    "Samsung": [r"samsung"],
    "Xiaomi": [r"xiaomi"],
    "Dyson": [r"dyson"],
    "LEGO": [r"\blego\b"],
    # Travel
    "Singapore Airlines": [r"singapore airlines", r"\bsia\b", r"scoot"],
    "Agoda": [r"agoda", r"agoda\.com"],
    "Booking.com": [r"booking\.com", r"booking com"],
    "Expedia": [r"expedia"],
    "Trip.com": [r"trip\.com", r"trip com", r"ctrip", r"trip\.com group"],
    "Traveloka": [r"traveloka"],
    "Airbnb": [r"airbnb"],
    "Pelago": [r"pelago"],
    "IHG": [r"\bihg\b"],
    "Marriott": [r"marriott"],
    "Accor": [r"accor"],
    # Banks & telco
    "DBS / POSB": [r"\bdbs\b", r"posb"],
    "OCBC": [r"ocbc"],
    "UOB": [r"\buob\b"],
    "Citibank": [r"citibank", r"\bciti\b"],
    "Maybank": [r"maybank"],
    "Trust Bank": [r"trust bank"],
    "Singtel": [r"singtel"],
    "StarHub": [r"starhub"],
    "M1": [r"\bm1\b"],
    "Simba": [r"simba"],
    # Misc
    "Shell": [r"\bshell\b"],
    "Esso": [r"\besso\b"],
    "Caltex": [r"caltex"],
    "SP Group": [r"sp group"],
    "Golden Village": [r"golden village", r"\bgv\b"],
    "Shaw Theatres": [r"shaw theatres"],
    "Cathay Cineplexes": [r"cathay cineplex"],
    "Universal Studios": [r"universal studios", r"\brws\b", r"resorts world"],
}

_COMPILED = {
    name: [re.compile(rf"(?<![a-z0-9]){p}(?![a-z0-9])", re.I) for p in pats]
    for name, pats in BRANDS.items()
}


def detect(title: str, categories: list[str] | None = None) -> list[str]:
    """Return every brand mentioned in the title (categories as a weak fallback)."""
    hits = [name for name, pats in _COMPILED.items()
            if any(p.search(title) for p in pats)]
    if not hits and categories:
        blob = " ".join(categories)
        hits = [name for name, pats in _COMPILED.items()
                if any(p.search(blob) for p in pats)]
    return hits


def fallback_name(title: str) -> str:
    """When no known brand matches, guess the merchant from the leading words."""
    cleaned = re.sub(r"^\(expired\)\s*", "", title, flags=re.I).strip()
    stop = {"s'pore", "singapore", "sg", "spore", "s’pore"}
    # Headline verbs: the brand name has ended by the time one of these appears.
    stop |= {
        "opens", "open", "brings", "bringing", "offers", "offering", "giving",
        "gives", "launches", "launching", "pops", "returns", "now", "is", "has",
        "adds", "drops", "slashes", "cuts", "introduces", "unveils", "to", "at",
        "up", "new", "back", "will",
    }
    joiners = {"of", "and", "&", "the", "de", "la"}

    guess: list[str] = []
    for word in cleaned.split()[:3]:
        low = word.lower().strip(".,")
        if low in stop or not re.match(r"^[A-Za-z0-9&'’.\-]+$", word):
            break
        guess.append(word)
        # A joiner ("Bank of China") carries on; any other lowercase word
        # means the brand name has ended ("Tokyo's cult-favourite ...").
        if not word[0].isupper() and low not in joiners:
            break
    while guess and guess[-1].lower() in joiners:
        guess.pop()

    name = " ".join(guess).strip(" -&")
    return name if len(name) >= 2 else "Other"


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "other"
