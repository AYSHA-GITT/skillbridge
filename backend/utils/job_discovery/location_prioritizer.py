"""
Location Prioritization Engine for SkillBridge Job Discovery.
Ensures opportunities in India and Asia are strictly prioritized first,
followed by generic remote, and lastly opportunities from other countries.
"""
import re
from typing import Tuple

INDIA_KEYWORDS = [
    "india", "bengaluru", "bangalore", "pune", "mumbai", "hyderabad",
    "chennai", "delhi", "gurgaon", "gurugram", "noida", "kolkata",
    "ahmedabad", "kerala", "kochi", "thiruvananthapuram", "tenkasi",
    "coimbatore", "mysore", "mysuru", "jaipur", "chandigarh", "indore",
    "bhubaneswar", "visakhapatnam", "lucknow", "karnataka", "maharashtra",
    "tamil nadu", "telangana", "uttar pradesh", "west bengal", "gujarat",
    "haryana", "punjab", "rajasthan", "madhya pradesh", "andhra pradesh"
]

ASIA_KEYWORDS = [
    "asia", "singapore", "japan", "tokyo", "korea", "seoul",
    "dubai", "uae", "united arab emirates", "malaysia", "kuala lumpur",
    "indonesia", "jakarta", "thailand", "bangkok", "vietnam", "ho chi minh",
    "taiwan", "taipei", "hong kong", "philippines", "manila", "qatar", "doha",
    "saudi arabia", "riyadh"
]


def get_location_rank(location: str = "", title: str = "", company: str = "") -> int:
    """
    Ranks job opening by geographical preference:
    0: India (Highest Priority)
    1: Other Asia (Second Priority)
    2: Remote (General / Accessible)
    3: Other Countries / Western Europe / US (Lowest Priority)
    """
    combined = f"{location or ''} {title or ''} {company or ''}".lower()

    # 1. Match India keywords
    for kw in INDIA_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', combined):
            return 0

    # 2. Match Asia keywords
    for kw in ASIA_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', combined):
            return 1

    # 3. Match Remote
    if "remote" in combined or "work from home" in combined or "wfh" in combined:
        return 2

    # 4. Other International
    return 3


def get_location_region_label(location: str = "", title: str = "", company: str = "") -> str:
    """
    Returns user-friendly region badge text for frontend rendering.
    """
    rank = get_location_rank(location, title, company)
    if rank == 0:
        return "India"
    elif rank == 1:
        return "Asia"
    elif rank == 2:
        return "Remote"
    return "International"
