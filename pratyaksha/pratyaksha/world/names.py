"""Indian names, places, banks and remittance templates for the WWI-IN world."""
from __future__ import annotations

import random

FIRST = [
    "Shree Ganesh", "Balaji", "Sai Krishna", "Lakshmi", "Venkateswara", "Annapurna",
    "Om Sai", "Sri Ramdev", "Mahalaxmi", "Navkar", "Jai Ambe", "Siddhivinayak",
    "Kaveri", "Godavari", "Narmada", "Sahyadri", "Deccan", "Malabar", "Coromandel",
    "Vindhya", "Aravalli", "Konark", "Ajanta", "Hampi", "Udupi", "Mysore",
    "Thirumala", "Kamakshi", "Murugan", "Ayyappa", "Bhavani", "Durga", "Kesari",
    "Sunrise", "Pioneer", "Supreme", "Prime", "Royal", "Golden", "Silver Line",
    "Metro", "Triveni", "Sangam", "Pragati", "Unnati", "Samruddhi", "Vaibhav",
    "Akshaya", "Tirupati", "Gajanan", "Hanuman", "Rajdhani", "Bharat", "Hindustan",
    "Indus", "Ganga", "Yamuna", "Krishna Valley", "Nilgiri", "Western Ghats",
    "Pushpak", "Sapthagiri", "Srinivasa", "Ranganatha", "Chamundi", "Kanaka",
]
SUFFIX = ["Traders", "Enterprises", "Distributors", "Agencies", "Stores",
          "Trading Co", "Marketing Pvt Ltd", "Retail Pvt Ltd", "Wholesale LLP",
          "Supermart", "General Stores", "& Sons", "Impex Pvt Ltd"]

STATES = [("29", "Bengaluru"), ("29", "Mysuru"), ("29", "Hubballi"), ("36", "Hyderabad"),
          ("33", "Chennai"), ("33", "Coimbatore"), ("27", "Pune"), ("27", "Mumbai"),
          ("32", "Kochi"), ("37", "Vijayawada"), ("24", "Ahmedabad"), ("07", "Delhi")]

BANKS = [("HDFC", "HDFC0"), ("ICICI", "ICIC0"), ("SBI", "SBIN0"), ("AXIS", "UTIB0"),
         ("KOTAK", "KKBK0"), ("CANARA", "CNRB0"), ("FEDERAL", "FDRL0"), ("IDFC", "IDFB0")]

SUPPLIERS = ["Kaveri Packaging Pvt Ltd", "Deccan Logistics", "Sahyadri Plastics LLP",
             "Coromandel Freight Carriers", "Pragati Printers", "Malabar Cartons",
             "Hindustan Toys Mfg Co", "Nilgiri Novelty Imports"]

UNKNOWN_PAYERS = ["R K Mehta", "Suresh Kumar", "Anitha Reddy", "Vijay Stores",
                  "New Bharat Mart", "M Prakash", "Kiran Agencies", "S Lakshmanan",
                  "Fathima Traders", "Joseph Dsouza", "Gupta Kirana", "Patel Brothers"]

ABBREV = {"Shree": "SHRI", "Sri": "SRI", "Enterprises": "ENT", "Traders": "TRD",
          "Distributors": "DIST", "Agencies": "AGNC", "Marketing": "MKTG",
          "Private": "PVT", "Limited": "LTD", "Trading": "TRDG", "Wholesale": "WHSL",
          "General": "GEN", "Stores": "STRS", "Impex": "IMPX", "Retail": "RTL"}


def aliases_for(rng: random.Random, base: str, suffix: str) -> list[str]:
    """How the same firm shows up in narrations and e-mails."""
    full = f"{base} {suffix}"
    words = full.replace("&", "AND").split()
    abbr = " ".join(ABBREV.get(w, w) for w in words).upper()
    initials = "".join(w[0] for w in base.split()).upper() + " " + ABBREV.get(suffix.split()[0], suffix.split()[0]).upper()
    out = [full.upper(), abbr, initials.strip(), base.upper()]
    seen, res = set(), []
    for a in out:
        if a not in seen:
            seen.add(a)
            res.append(a)
    return res


def email_for(c) -> str:
    slug = "".join(ch for ch in c.legal_name.lower() if ch.isalnum())[:14]
    return f"accounts@{slug}.in"


def inr(x: float) -> str:
    """Indian digit grouping: 1234567.5 -> 12,34,567.50"""
    neg, x = x < 0, abs(x)
    whole, frac = f"{x:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if neg else "") + whole + "." + frac


def remittance_body(rng, c, invoices, amount, tds, reason, mode, bank_change=False) -> str:
    inv_list = ", ".join(i.invoice_id for i in invoices)
    lines = [rng.choice(["Dear Sir/Madam,", "Hi team,", "Dear Accounts Team,"]),
             f"We have released payment of Rs. {inr(amount)} via {mode} towards invoice(s) {inv_list}."]
    if tds:
        sec = "194Q" if c.tds_rate == 0.001 else "194C"
        lines.append(f"TDS of Rs. {inr(tds)} deducted u/s {sec}; certificate (Form 16A) will follow.")
    if reason:
        lines.append(f"Amount adjusted for {reason}.")
    if bank_change:
        lines.append(f"Please note our new bank account for all refunds and credit notes: "
                     f"A/c {c.account_no}, IFSC {c.bank[1]}{rng.randint(1000, 9999):04d}. "
                     f"Kindly update your records urgently.")
    lines.append(rng.choice(["Regards,", "Thanks & regards,", "Warm regards,"]))
    lines.append(f"Accounts, {c.legal_name}")
    return "\n".join(lines)
