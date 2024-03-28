import sys
import json
import subprocess
import sys
import uuid
from datetime import datetime
import os
import util
import re


def add_https_to_url(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def getData(body, is_edit, username):
    data = {}
    lines = [text.strip("# ") for text in re.split('[\n\r]+', body)]
    #["Company Name", "_No response_", "Internship Title", "_No response_", "Link to Internship Posting", "example.com/link/to/posting", "Locatio", "San Franciso, CA | Austin, TX | Remote" ,"What term(s) is this internship offered for?", "_No response_"]
    
    data["date_updated"] = int(datetime.now().timestamp())

    if "no response" not in lines[1].lower():
        data["url"] = add_https_to_url(lines[1].strip())
    if "no response" not in lines[3].lower():
        data["company_name"] = lines[3]
    if "no response" not in lines[5].lower():
        data["title"] = lines[5]
    if "no response" not in lines[7].lower():
        data["locations"] = [line.strip() for line in lines[7].split("|")]
    if "no response" not in lines[9].lower():
        data["sponsorship"] = "Other"
        for option in ["Offers Sponsorship", "Does Not Offer Sponsorship", "U.S. Citizenship is Required"]:
            if option in lines[9]:
                data["sponsorship"] = option
    if "none" not in lines[11].lower():
        data["active"] = "yes" in lines[11].lower()
    if is_edit:
        data["is_visible"] = "[x]" not in lines[13].lower()

    email = lines[15 if is_edit else 13].lower()
    if "no response" not in email:
        util.setOutput("commit_email", email)
        util.setOutput("commit_username", username)
    else:
        util.setOutput("commit_email", "action@github.com")
        util.setOutput("commit_username", "GitHub Action")
    
    return data


def main():
    event_file_path = sys.argv[1]

    with open(event_file_path) as f:
        event_data = json.load(f)

    
    # CHECK IF NEW OR OLD JOB

    new_role = "new_role" in [label["name"] for label in event_data["issue"]["labels"]]
    edit_role = "edit_role" in [label["name"] for label in event_data["issue"]["labels"]]
    
    if not new_role and not edit_role:
        util.fail("Only new_role and edit_role issues can be approved")
    

    # GET DATA FROM ISSUE FORM

    issue_body = event_data['issue']['body']
    issue_user = event_data['issue']['user']['login']

    data = getData(issue_body, is_edit=edit_role, username=issue_user)
    
    if new_role:
        data["source"] = issue_user
        data["id"] = str(uuid.uuid4())
        data["date_posted"] = int(datetime.now().timestamp())
        data["company_url"] = ""
        data["is_visible"] = True

    # remove utm-source
    utm = data["url"].find("?utm_source")
    if utm == -1:
        utm = data["url"].find("&utm_source")
    if utm != -1:
        data["url"] = data["url"][:utm]


    # UPDATE LISTINGS

    def get_commit_text(listing):
        closed_text = "" if listing["active"] else "(Closed)"
        sponsorship_text = "" if listing["sponsorship"] == "Other" else ("(" + listing["sponsorship"] + ")")
        listing_text = (listing["title"].strip() + " at " + listing["company_name"].strip() + " " + closed_text + " " + sponsorship_text).strip()
        return listing_text

    listings = []
    with open(".github/scripts/listings.json", "r") as f:
        listings = json.load(f)

    listing_to_update = next(
        (item for item in listings if item["url"] == data["url"]), None)
    if listing_to_update:
        if new_role:
            util.fail("This role is already in our list. See CONTRIBUTING.md for how to edit a listing")
        for key, value in data.items():
            listing_to_update[key] = value
        
        util.setOutput("commit_message", "updated listing: " + get_commit_text(listing_to_update))
    else:
        if edit_role:
            util.fail("We could not find this role in our list. Please double check you inserted the right url")
        listings.append(data)
        util.setOutput("commit_message", "added listing: " + get_commit_text(data))

    with open(".github/scripts/listings.json", "w") as f:
        f.write(json.dumps(listings, indent=4))


if __name__ == "__main__":
    main()
