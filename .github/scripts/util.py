import json

from datetime import date, datetime, timezone, timedelta
import random
import os

# SIMPLIFY_BUTTON = "https://i.imgur.com/kvraaHg.png"
SIMPLIFY_BUTTON = "https://i.imgur.com/MXdpmi0.png" # says apply
SHORT_APPLY_BUTTON = "https://i.imgur.com/w6lyvuC.png"
SQUARE_SIMPLIFY_BUTTON = "https://i.imgur.com/aVnQdox.png"
LONG_APPLY_BUTTON = "https://i.imgur.com/u1KNU8z.png"


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
        return f'<a href="{link}" target="_blank"><img src="{LONG_APPLY_BUTTON}" width="118" alt="Apply"></a>'
    
    simplifyLink = "https://simplify.jobs/p/" + listing["id"] + "?utm_source=GHList"
    return f'<a href="{link}" target="_blank"><img src="{SHORT_APPLY_BUTTON}" width="84" alt="Apply"></a> <a href="{simplifyLink}"><img src="{SQUARE_SIMPLIFY_BUTTON}" width="30" alt="Simplify"></a>'
 

def create_md_table(listings):
    table = ""
    table += "| Company | Role | Location | Application/Link | Date Posted |\n"
    table += "| --- | --- | --- | :---: | :---: |\n"
    for listing in listings:
        company_url = listing["company_url"]
        company = listing["company_name"]
        company = f"[{company}]({company_url})" if len(
            company_url) > 0 and listing["active"] else company
        location = getLocations(listing)
        position = listing["title"] + getSponsorship(listing)
        link = getLink(listing)
        month = datetime.fromtimestamp(listing["date_posted"]).strftime('%b')
        dayMonth = datetime.fromtimestamp(listing["date_posted"]).strftime('%b %d')
        isBeforeJuly18 = datetime.fromtimestamp(listing["date_posted"]) < datetime(2023, 7, 18, 0, 0, 0)
        datePosted = month if isBeforeJuly18 else dayMonth
        table += f"| **{company}** | {position} | {location} | {link} | {datePosted} |\n"
        # table += f"| **{company}** | {location} | {position} | {link} | {status} | {datePosted} |\n"
    return table

def filterListings(listings, earliest_date):
    final_listings = []
    inclusion_terms = ["software eng", "software dev", "data scientist", "data engineer", "product manage", "apm", "frontend", "front end", "front-end", "backend", "back end", "full-stack", "full stack", "full-stack", "devops", "android", "ios", "mobile dev", "sre", "site reliability eng", "quantitative trad", "quantitative research", "quantitative trad", "quantitative dev", "security eng", "compiler eng", "machine learning eng", "infrastructure eng"]
    new_grad_terms = ["new grad", "early career", "college grad", "entry level", "early in career", "university grad", "fresh grad", "2024 grad", "2025 grad", "engineer 0", "engineer 1", "engineer i ", "junior"]
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


def embedTable(listings):
    filepath = "README.md"
    newText = ""
    readingTable = False
    with open(filepath, "r") as f:
        for line in f.readlines():
            if readingTable:
                if "|" not in line and "TABLE_END" in line:
                    newText += line
                    readingTable = False
                continue
            else:
                newText += line
                if "TABLE_START" in line:
                    readingTable = True
                    newText += "\n" + \
                        create_md_table(listings) + "\n"
    with open(filepath, "w") as f:
        f.write(newText)

def sortListings(listings):

    linkForCompany = {}
    for listing in listings:
        if listing["company_name"] not in linkForCompany or len(listing["company_url"]) > 0:
            linkForCompany[listing["company_name"]] = listing["company_url"]

    def getKey(listing):
        date_posted = listing["date_posted"]
        date_updated = listing["date_updated"]
        return str(date_posted) + listing["company_name"].lower() + str(date_updated)

    listings.sort(key=getKey, reverse=True)

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
