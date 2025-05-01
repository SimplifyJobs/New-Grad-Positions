import json
import re
from datetime import date, datetime, timezone, timedelta
import random
import os

# SIMPLIFY_BUTTON = "https://i.imgur.com/kvraaHg.png"
SIMPLIFY_BUTTON = "https://i.imgur.com/MXdpmi0.png" # says apply
SHORT_APPLY_BUTTON = "https://i.imgur.com/fbjwDvo.png"
SQUARE_SIMPLIFY_BUTTON = "https://i.imgur.com/aVnQdox.png"
LONG_APPLY_BUTTON = "https://i.imgur.com/G5Bzlx3.png"

# Define categories with their correct anchor formats and emojis
CATEGORIES = {
    "Software": {
        "name": "Software Engineering",
        "emoji": "💻"
    },
    "AI/ML/Data": {
        "name": "Data Science, AI & Machine Learning",
        "emoji": "🤖"
    },
    "Quant": {
        "name": "Quantitative Finance",
        "emoji": "📈"
    },
    "Hardware": {
        "name": "Hardware Engineering",
        "emoji": "🔧"
    }
}

def setOutput(key, value):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f'{key}={value}', file=fh)

def fail(why):
    setOutput("error_message", why)
    exit(1)

def getLocations(listing):
    locations = "</br>".join(listing["locations"])
    if len(listing["locations"]) <= 3:
        return locations
    num = str(len(listing["locations"])) + " locations"
    return f'<details><summary>**{num}**</summary>{locations}</details>'

def getSponsorship(listing):
    if listing["sponsorship"] == "Does Not Offer Sponsorship":
        return " 🛂"
    elif listing["sponsorship"] == "U.S. Citizenship is Required":
        return " 🇺🇸"
    return ""

def getLink(listing):
    if not listing["active"]:
        return "🔒"
    link = listing["url"]
    if "?" not in link:
        link += "?utm_source=Simplify&ref=Simplify"
    else:
        link += "&utm_source=Simplify&ref=Simplify"
    # return f'<a href="{link}" style="display: inline-block;"><img src="{SHORT_APPLY_BUTTON}" width="160" alt="Apply"></a>'

    if listing["source"] != "Simplify":
        return f'<a href="{link}"><img src="{LONG_APPLY_BUTTON}" width="100" alt="Apply"></a>'
    
    simplifyLink = f"https://simplify.jobs/p/{listing['id']}?utm_source=GHList"
    return f'<a href="{link}"><img src="{SHORT_APPLY_BUTTON}" width="49" alt="Apply"></a> <a href="{simplifyLink}"><img src="{SQUARE_SIMPLIFY_BUTTON}" width="26" alt="Simplify"></a>'

def filter_active(listings):
    return [listing for listing in listings if listing.get("active", False)]

def create_md_table(listings):
    table = ""
    table = "| Company | Role | Location | Application | Age |\n"
    table += "| ------- | ---- | -------- | ---------- | --- |\n"
    prev_company = None
    prev_days_active = None

    for listing in listings:
        raw_url = listing.get("company_url", "").strip()
        company_url = raw_url + '?utm_source=GHList&utm_medium=company' if raw_url.startswith("http") else ""
        company = f"**[{listing['company_name']}]({company_url})**" if company_url else listing["company_name"]
        location = getLocations(listing)
        position = listing["title"] + getSponsorship(listing)
        link = getLink(listing)

        # Days active calculation
        days_active = (datetime.now() - datetime.fromtimestamp(listing["date_posted"])).days
        days_active = max(days_active, 0)

        days_display = (
            "0d" if days_active == 0 else
            f"{(days_active // 30)}mo" if days_active >= 30 else
            f"{days_active}d"
        )

        if prev_company == listing['company_name'] and prev_days_active == days_active:
            company = "↳"
        else:
            prev_company = listing['company_name']
            prev_days_active = days_active

        table += f"| {company} | {position} | {location} | {link} | {days_display} |\n"

    return table
    
def filterListings(listings, earliest_date):
    final_listings = []
    inclusion_terms = ["software eng", "software dev", "data scientist", "data engineer", "founding eng", "research eng", "product manage", "apm", "frontend", "front end", "front-end", "backend", "back end", "full-stack", "full stack", "full-stack", "devops", "android", "ios", "mobile dev", "sre", "site reliability eng", "quantitative trad", "quantitative research", "quantitative trad", "quantitative dev", "security eng", "compiler eng", "machine learning eng", "hardware eng", "firmware eng", "infrastructure eng"]
    new_grad_terms = ["new grad", "early career", "college grad", "entry level", "founding", "early in career", "university grad", "fresh grad", "2024 grad", "2025 grad", "engineer 0", "engineer 1", "engineer i ", "junior", "sde 1", "sde i"]
    for listing in listings:
        if listing["is_visible"] and listing["date_posted"] > earliest_date:
            if listing['source'] != "Simplify" or (any(term in listing["title"].lower() for term in inclusion_terms) and (any(term in listing["title"].lower() for term in new_grad_terms) or (listing["title"].lower().endswith("engineer i")))):
                final_listings.append(listing)

    return final_listings

def getListingsFromJSON(filename=".github/scripts/listings.json"):
    with open(filename) as f:
        listings = json.load(f)
        print("Recieved " + str(len(listings)) +
              " listings from listings.json")
        return listings

def create_category_table(listings, category_name):
    category_listings = [listing for listing in listings if listing["category"] == category_name]
    if not category_listings:
        return ""
    
    # Find the emoji for this category
    emoji = next((cat["emoji"] for cat in CATEGORIES.values() if cat["name"] == category_name), "")
    
    table = f"\n## {emoji} {category_name} New Grad Roles\n\n"
    table += "[Back to top](#2025-new-grad-positions-by-coder-quad-and-simplify)\n\n"
    table += create_md_table(category_listings)
    return table

def classifyJobCategory(job):
    # First check if there's an existing category
    if "category" in job and job["category"]:
        # Map the existing category to our standardized categories
        category = job["category"].lower()
        if category in ["hardware", "hardware engineering", "embedded engineering"]:
            return "Hardware Engineering"
        elif category in ["quant", "quantitative finance"]:
            return "Quantitative Finance"
        elif category in ["ai/ml/data", "data & analytics", "ai & machine learning", "data science"]:
            return "Data Science, AI & Machine Learning"
        elif category in ["software", "software engineering"]:
            return "Software Engineering"
    
    # If no category exists or it's not recognized, classify by title
    title = job.get("title", "").lower()
    if any(term in title for term in ["hardware", "embedded", "fpga", "circuit", "chip", "silicon", "asic"]):
        return "Hardware Engineering"
    elif any(term in title for term in ["quant", "quantitative", "trading", "finance", "investment"]):
        return "Quantitative Finance"
    elif any(term in title for term in ["data science", "data scientist", "data science", "ai &", "machine learning", "ml", "analytics", "analyst" ]):
        return "Data Science, AI & Machine Learning"
    return "Software Engineering"

def ensureCategories(listings):
    for listing in listings:
        if "category" not in listing:
            listing["category"] = classifyJobCategory(listing)
    return listings

def embedTable(listings):    
    listings = ensureCategories(listings)    
    active_listings = filter_active(listings)    
    category_counts = {}
    for category_info in CATEGORIES.values():
        count = len([l for l in active_listings if l["category"] == category_info["name"]])
        category_counts[category_info["name"]] = count
    
    total_active = len(active_listings)    
    # Create category links with counts using correct anchor formats and emojis
    category_links = []
    for category_info in CATEGORIES.values():
        count = category_counts[category_info["name"]]
        anchor = category_info["name"].lower().replace(" ", "-").replace(",", "").replace("&", "")
        category_links.append(f"{category_info['emoji']} **[{category_info['name']}](#-{anchor}-new-grad-roles)** ({count})")
    category_counts_str = "\n\n".join(category_links)

    filepath = "README.md"
    newText = ""
    in_browse_section = False
    browse_section_replaced = False
    in_table_section = False
    
    with open(filepath, "r") as f:
        for line in f.readlines():
            if not browse_section_replaced and line.startswith("### Browse"):
                # Start of Browse section
                in_browse_section = True
                newText += f"### Browse {total_active} New Grad Roles by Category\n\n{category_counts_str}\n\n---\n"
                browse_section_replaced = True
                continue
            
            if in_browse_section:
                if line.startswith("---"):
                    in_browse_section = False
                continue
            
            if not in_table_section and "TABLE_START" in line:
                in_table_section = True
                newText += line
                # Add page break before first category
                newText += "\n---\n\n"
                # Add tables for each category
                for category_info in CATEGORIES.values():
                    if category_info["name"] == "Software Engineering":
                        newText += create_category_table(listings, category_info["name"])
                        # Add the blockquote after Software Engineering section
                        newText += '\n> 🎓 Here\'s the [resume template](https://example.com) that Pitt CSC and Stanford CS share with software new grads.\n>\n> 🧠 Want to know what keywords your resume is missing for a job? Use the blue Simplify application link to instantly compare your resume to any job description.\n\n'
                    else:
                        newText += create_category_table(listings, category_info["name"])
                newText += "\n"
                table_section_replaced = True
                continue
            
            if in_table_section:
                if "TABLE_END" in line:
                    in_table_section = False
                    newText += line
                continue
            
            if not in_browse_section and not in_table_section:
                newText += line

    with open(filepath, "w") as f:
        f.write(newText)

def sortListings(listings):
    oldestListingFromCompany = {}
    linkForCompany = {}

    for listing in listings:
        date_posted = listing["date_posted"]
        if listing["company_name"].lower() not in oldestListingFromCompany or oldestListingFromCompany[listing["company_name"].lower()] > date_posted:
            oldestListingFromCompany[listing["company_name"].lower()] = date_posted
        if listing["company_name"] not in linkForCompany or len(listing["company_url"]) > 0:
            linkForCompany[listing["company_name"]] = listing["company_url"]

    listings.sort(
        key=lambda x: (
            x["active"],  # Active listings first
            x['date_posted'],
            x['company_name'].lower(),
            x['date_updated']
        ),
        reverse=True
    )

    for listing in listings:
        listing["company_url"] = linkForCompany[listing["company_name"]]

    return listings


def checkSchema(listings):
    props = ["source", "company_name",
             "id", "title", "active", "date_updated", "is_visible",
             "date_posted", "url", "locations", "company_url",
             "sponsorship"]
    for listing in listings:
        for prop in props:
            if prop not in listing:
                fail("ERROR: Schema check FAILED - object with id " +
                      listing["id"] + " does not contain prop '" + prop + "'")
