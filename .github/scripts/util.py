import json
import re
from datetime import date, datetime, timezone, timedelta
import random
import os
import time
import urllib.request
import urllib.error

# SIMPLIFY_BUTTON = "https://i.imgur.com/kvraaHg.png"
SIMPLIFY_BUTTON = "https://i.imgur.com/MXdpmi0.png" # says apply
SHORT_APPLY_BUTTON = "https://i.imgur.com/fbjwDvo.png"
SQUARE_SIMPLIFY_BUTTON = "https://i.imgur.com/aVnQdox.png"
LONG_APPLY_BUTTON = "https://i.imgur.com/G5Bzlx3.png"
INACTIVE_THRESHOLD_MONTHS = 4

# Wayback Machine "Archived" button
WAYBACK_LOGO = "https://archive.org/favicon.ico"
WAYBACK_SAVE_URL = "https://web.archive.org/save/"
WAYBACK_USER_AGENT = "New-Grad-Positions-Bot/1.0 (+https://github.com/SimplifyJobs/New-Grad-Positions)"
WAYBACK_MAX_PER_RUN = 6
WAYBACK_DELAY_SECONDS = 20

# Set of Simplify company URLs to block from appearing in the README
# Add Simplify company URLs to block them (e.g., "https://simplify.jobs/c/Jerry")
BLOCKED_COMPANIES = {
    "https://simplify.jobs/c/Jerry",
}

# Define categories with their correct anchor formats and emojis
CATEGORIES = {
    "Software": {
        "name": "Software Engineering",
        "emoji": "💻"
    },
    "Product": {
        "name": "Product Management",
        "emoji": "📱"
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
    },
    "Other": {
        "name": "Other",
        "emoji": "💼"
    }
}

# FAANG+ companies - will be marked with fire emoji
FAANG_PLUS = {
    "airbnb", "adobe", "amazon", "amd", "anthropic", "apple", "asana", "atlassian", "bytedance", "cloudflare","coinbase", "crowdstrike","databricks", "datadog",
    "doordash", "dropbox", "duolingo", "figma", "google", "ibm", "instacart", "intel", "linkedin", "lyft", "meta", "microsoft",
    "netflix", "notion", "nvidia", "openai", "oracle", "palantir", "paypal", "perplexity", "pinterest", "ramp", "reddit","rippling", "robinhood", "roblox",
    "salesforce", "samsara", "servicenow", "shopify", "slack", "snap", "snapchat", "spacex", "splunk","snowflake", "stripe", "square", "tesla", "tinder","tiktok", "uber",
    "visa","waymo", "x"
}

def setOutput(key, value):
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            # Handle multiline values using heredoc format
            if isinstance(value, str) and ('\n' in value or '\r' in value or value.startswith('#') or value.startswith('*')):
                # Use heredoc format for multiline or markdown content
                delimiter = f"EOF_{key}_{hash(value) % 10000}"
                print(f'{key}<<{delimiter}', file=fh)
                print(value, file=fh)
                print(delimiter, file=fh)
            else:
                # Use simple format for single-line values
                print(f'{key}={value}', file=fh)
    else:
        # Safe fallback for local/dev use
        print(f'[set-output] {key}={value}')
        
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

def getArchiveButton(listing):
    wayback_url = listing.get("wayback_url")
    if not wayback_url:
        return ""
    return f' <a href="{wayback_url}"><img src="{WAYBACK_LOGO}" width="16" height="16" alt="Archived" title="View on the Wayback Machine"></a>'

def getLink(listing):
    archive_button = getArchiveButton(listing)
    if not listing["active"]:
        return "🔒" + archive_button
    link = listing["url"]
    if "?" not in link:
        link += "?utm_source=Simplify&ref=Simplify"
    else:
        link += "&utm_source=Simplify&ref=Simplify"
    # return f'<a href="{link}" style="display: inline-block;"><img src="{SHORT_APPLY_BUTTON}" width="160" alt="Apply"></a>'

    if listing["source"] != "Simplify":
        return f'<a href="{link}"><img src="{LONG_APPLY_BUTTON}" width="100" alt="Apply"></a>{archive_button}'

    simplifyLink = f"https://simplify.jobs/p/{listing['id']}?utm_source=GHList"
    return (
        f'<div align="center">'
        f'<a href="{link}"><img src="{SHORT_APPLY_BUTTON}" width="52" alt="Apply"></a> '
        f'<a href="{simplifyLink}"><img src="{SQUARE_SIMPLIFY_BUTTON}" width="28" alt="Simplify"></a>'
        f'{archive_button}'
        f'</div>'
    )
    
def mark_stale_listings(listings):
    now = datetime.now()
    for listing in listings:
        if listing["source"] != "Simplify":
            age_in_months = (now - datetime.fromtimestamp(listing["date_posted"])).days / 30
            if age_in_months > INACTIVE_THRESHOLD_MONTHS:
                listing["active"] = False
    return listings    

def filter_active(listings):
    return [listing for listing in listings if listing.get("active", False)]

def convert_markdown_to_html(text):
    """Convert basic markdown formatting to HTML for use in HTML tables"""
    if not text:
        return text
    
    # Convert **bold** to <strong>bold</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Convert [link text](url) to <a href="url">link text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    return text

def create_md_table(listings):
    table = ""
    # Use HTML table with CSS for better width control and spacing
    # This provides much better column width control than markdown tables
    table = '<table style="width: 100%; border-collapse: collapse;">\n'
    table += '<thead>\n'
    table += '<tr>\n'
    table += '<th style="width: 25%; min-width: 200px; padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Company</th>\n'
    table += '<th style="width: 30%; min-width: 250px; padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Role</th>\n'
    table += '<th style="width: 20%; min-width: 150px; padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Location</th>\n'
    table += '<th style="width: 15%; min-width: 120px; padding: 8px; text-align: center; border-bottom: 2px solid #ddd;">Application</th>\n'
    table += '<th style="width: 10%; min-width: 80px; padding: 8px; text-align: center; border-bottom: 2px solid #ddd;">Age</th>\n'
    table += '</tr>\n'
    table += '</thead>\n'
    table += '<tbody>\n'
    prev_company = None
    prev_days_active = None

    for listing in listings:
        # Add fire emoji for FAANG+ companies
        company_name = listing["company_name"]
        if company_name.lower() in FAANG_PLUS:
            company_name = f"🔥 {company_name}"
            listing["company_name"] = company_name  # Update the listing as well
        
        raw_url = listing.get("company_url", "").strip()
        company_url = raw_url + '?utm_source=GHList&utm_medium=company' if raw_url.startswith("http") else ""
        company = f"**[{company_name}]({company_url})**" if company_url else f"**{company_name}**"
        
        location = getLocations(listing)
        
        # Check for advanced degree requirements and add graduation cap emoji
        title_with_degree_emoji = listing["title"]
        
        # Check degrees field for advanced degree requirements
        degrees = listing.get("degrees", [])
        if degrees:
            # Check if only advanced degrees are required (no Bachelor's or Associate's)
            has_bachelors_or_associates = any(
                degree.lower() in ["bachelor's", "associate's"]
                for degree in degrees
            )
            has_advanced_degrees = any(
                degree.lower() in ["master's", "phd", "mba"]
                for degree in degrees
            )
            
            if has_advanced_degrees and not has_bachelors_or_associates:
                title_with_degree_emoji += " 🎓"
        
        # Also check title text for degree mentions
        title_lower = listing["title"].lower()
        if any(term in title_lower for term in ["master's", "masters", "master", "mba", "phd", "ph.d", "doctorate", "doctoral"]):
            if "🎓" not in title_with_degree_emoji:
                title_with_degree_emoji += " 🎓"
        
        position = title_with_degree_emoji + getSponsorship(listing)
        link = getLink(listing)

        # Days active calculation
        days_active = (datetime.now() - datetime.fromtimestamp(listing["date_posted"])).days
        days_active = max(days_active, 0)

        days_display = (
            "0d" if days_active == 0 else
            f"{(days_active // 30)}mo" if days_active >= 30 else
            f"{days_active}d"
        )

        if prev_company == company_name and prev_days_active == days_active:
            company = "↳"
        else:
            prev_company = company_name
            prev_days_active = days_active

        # Convert markdown formatting to HTML for proper rendering in HTML tables
        company_html = convert_markdown_to_html(company)
        position_html = convert_markdown_to_html(position)
        location_html = convert_markdown_to_html(location)
        
        table += '<tr>\n'
        table += f'<td>{company_html}</td>\n'
        table += f'<td>{position_html}</td>\n'
        table += f'<td>{location_html}</td>\n'
        table += f'<td>{link}</td>\n'
        table += f'<td>{days_display}</td>\n'
        table += '</tr>\n'

    table += '</tbody>\n'
    table += '</table>\n'
    return table
    

def filterListings(listings, earliest_date):
    final_listings = []
    inclusion_terms = ["software eng", "software dev", "product engineer", "fullstack engineer", "frontend", "front end", "front-end", "backend", "back end", "full-stack", "full stack", "founding engineer", "mobile dev", "mobile engineer", "data scientist", "data engineer", "research eng", "product manag", "apm", "product", "devops", "android", "ios", "sre", "site reliability eng", "quantitative trad", "quantitative research", "quantitative dev", "security eng", "compiler eng", "machine learning eng", "hardware eng", "firmware eng", "infrastructure eng", "embedded", "fpga", "circuit", "chip", "silicon", "asic", "quant", "quantitative", "trading", "finance", "investment", "ai &", "machine learning", "ml", "analytics", "analyst", "research sci"]
    new_grad_terms = ["new grad", "early career", "college grad", "entry level", "founding", "early in career", "university grad", "fresh grad", "2024 grad", "2025 grad", "engineer 0", "engineer 1", "engineer i ", "junior", "sde 1", "sde i"]
    
    # Convert blocked URLs to lowercase for case-insensitive comparison
    blocked_urls_lower = {url.lower() for url in BLOCKED_COMPANIES}
    
    for listing in listings:
        if listing["is_visible"] and listing["date_posted"] > earliest_date:
            # Check if listing is from a blocked company
            company_url = listing.get("company_url", "").lower()
            if any(blocked_url in company_url for blocked_url in blocked_urls_lower):
                continue  # Skip blocked companies
            
            if listing['source'] != "Simplify" or (any(term in listing["title"].lower() for term in inclusion_terms) and (any(term in listing["title"].lower() for term in new_grad_terms) or (listing["title"].lower().endswith("engineer i")))):
                final_listings.append(listing)

    return final_listings

def getListingsFromJSON(filename=".github/scripts/listings.json"):
    with open(filename) as f:
        listings = json.load(f)
        print("Recieved " + str(len(listings)) +
              " listings from listings.json")
        return listings

def saveListingsToJSON(listings, filename=".github/scripts/listings.json"):
    # Write to a temp file first so a failure mid-dump can't leave listings.json truncated
    temp_filename = filename + ".tmp"
    try:
        with open(temp_filename, "w") as f:
            json.dump(listings, f, indent=4)
        os.replace(temp_filename, filename)
    except Exception:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise

class WaybackRateLimited(Exception):
    pass

def save_to_wayback(url, timeout=15):
    """Best-effort request asking the Wayback Machine to capture url now.
    Returns the archived URL, or None if the capture couldn't be confirmed."""
    # urllib drops any #fragment before sending, and Wayback hands back a
    # fragment-less snapshot URL, so keep it aside and re-attach it to the result.
    target, _, fragment = url.partition("#")
    suffix = "#" + fragment if fragment else ""
    request = urllib.request.Request(WAYBACK_SAVE_URL + target, headers={"User-Agent": WAYBACK_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_location = response.headers.get("Content-Location")
            if content_location:
                return "https://web.archive.org" + content_location + suffix
            if response.geturl().startswith("https://web.archive.org/web/"):
                return response.geturl() + suffix
            return None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise WaybackRateLimited()
        print(f"Wayback: could not archive {url} (HTTP {e.code})")
        return None
    except Exception as e:
        print(f"Wayback: could not archive {url} ({type(e).__name__}: {e})")
        return None

def archiveNewListings(listings, max_attempts=WAYBACK_MAX_PER_RUN, delay_seconds=WAYBACK_DELAY_SECONDS):
    """Archive active listings that don't have a wayback_url yet until rate-limited.
    Mutates listings in place. Stops early if the Wayback Machine rate-limits us."""
    candidates = [l for l in listings if l.get("active") and not l.get("wayback_url")]
    candidates.sort(key=lambda l: l["date_posted"], reverse=True)

    archived_count = 0
    for i, listing in enumerate(candidates[:max_attempts]):
        if i > 0:
            time.sleep(delay_seconds)
        try:
            wayback_url = save_to_wayback(listing["url"])
        except WaybackRateLimited:
            print("Wayback Machine rate-limited us, stopping archive attempts for this run")
            break
        if wayback_url:
            listing["wayback_url"] = wayback_url
            archived_count += 1

    print(f"Archived {archived_count} listing(s) to the Wayback Machine this run")
    return listings

def create_category_table(listings, category_name):
    category_listings = [listing for listing in listings if listing["category"] == category_name]
    if not category_listings:
        return ""

    emoji = next((cat["emoji"] for cat in CATEGORIES.values() if cat["name"] == category_name), "")
    header = f"\n\n## {emoji} {category_name} New Grad Roles\n\n"
    header += "[Back to top](#2026-new-grad-positions-by-coder-quad-and-simplify)\n\n"

    # Optional callout under Data Science section
    if category_name == "Data Science, AI & Machine Learning":
        header += (
            "> 📄 Here's the [resume template](https://docs.google.com/document/d/1azvJt51U2CbpvyO0ZkICqYFDhzdfGxU_lsPQTGhsn94/edit?usp=sharing) that Pitt CSC and Stanford CS share with software new grads.\n"
            ">\n"
            "> 🧠 Want to know what keywords your resume is missing for a job? Use the blue Simplify application link to instantly compare your resume to any job description.\n\n"
        )
        
    if category_name == 'Product Management':
        header += (
            "> 📅 Curious when Big Tech APM roles typically open? Simplify put together an [openings tracker](https://simplify.jobs/top-list/Associate-Product-Manager?utm_source=GHList&utm_medium=ot) based on historical data for those companies.\n"
            "\n"
        )

    # Sort and split
    active = sorted([l for l in category_listings if l["active"]], key=lambda l: l["date_posted"], reverse=True)
    inactive = sorted([l for l in category_listings if not l["active"]], key=lambda l: l["date_posted"], reverse=True)

    result = header
    if active:
        result += create_md_table(active) + "\n\n"

    if inactive:
        result += (
            "<details>\n"
            f"<summary>🗃️ Inactive roles ({len(inactive)})</summary>\n\n"
            + create_md_table(inactive) +
            "\n\n</details>\n\n"
        )

    return result

def classifyJobCategory(job):
    # First check if there's an existing category
    if "category" in job and job["category"]:
        # Map the existing category to our standardized categories
        category = job["category"].lower().strip()
        
        # Hardware variations
        if category in ["hardware", "hardware engineering", "embedded engineering", "embedded", "firmware", "fpga", "circuit", "chip", "silicon", "asic"]:
            return "Hardware Engineering"
        
        # Quantitative Finance variations
        elif category in ["quant", "quantitative finance", "quantitative", "finance", "trading", "investment", "financial"]:
            return "Quantitative Finance"
        
        # Data Science, AI & ML variations
        elif category in ["ai/ml/data", "data & analytics", "ai & machine learning", "data science", "data science, ai & machine learning", 
                         "ai", "ml", "machine learning", "data", "analytics", "research", "ai/ml", "data science & analytics"]:
            return "Data Science, AI & Machine Learning"
        
        # Product Management variations
        elif category in ["product", "product management", "pm", "apm", "product manager"]:
            return "Product Management"
        
        # Software Engineering variations (most common)
        elif category in ["software", "software engineering", "software engineer", "engineering", "swe", "dev", "developer", 
                         "backend", "frontend", "fullstack", "full-stack", "mobile", "web", "infrastructure", "devops", "sre"]:
            return "Software Engineering"
        
        # Other
        elif category in ["other", "misc", "miscellaneous"]:
            return "Other"
        
        # If category is already in the correct format, return it as-is
        if job["category"] in ["Hardware Engineering", "Quantitative Finance", "Data Science, AI & Machine Learning", "Product Management", "Software Engineering", "Other"]:
            return job["category"]
    
    # If no category exists or it's not recognized, classify by title
    # Order of filtering based on title: hardware -> quant -> data science -> software eng -> product -> other
    title = job.get("title", "").lower()
    
    # Hardware (first priority)
    if any(term in title for term in ["hardware", "embedded", "fpga", "circuit", "chip", "silicon", "asic", "robotics"]):
        return "Hardware Engineering"
    
    # Quant (second priority)
    elif any(term in title for term in ["quant", "quantitative", "trading", "finance", "investment"]):
        return "Quantitative Finance"
    
    # Data Science (third priority)
    elif any(term in title for term in ["data science", "data scientist", "ai &", "machine learning", "ml", "data analytics", "data analyst", "research eng", "research sci"]):
        return "Data Science, AI & Machine Learning"
    
    # Software Engineering (fourth priority)
    elif any(term in title for term in ["forward deployed", "forward-deployed","software", "software eng", "software dev", "product engineer", "fullstack engineer", "frontend", "backend", "founding engineer", "mobile dev", "mobile engineer"]):
        return "Software Engineering"
    
    # Product (fifth priority)
    elif any(term in title for term in ["product manag", "product analyst", "apm"]) or ("product" in title and "analyst" in title):
        return "Product Management"
    
    # Other (everything else)
    else:
        return "Other"

def ensureCategories(listings):
    for listing in listings:
        # Always classify to ensure proper category mapping
        # This handles missing categories AND maps existing categories to standard format
        listing["category"] = classifyJobCategory(listing)
    return listings

def embedTable(listings):    
    listings = ensureCategories(listings)    
    listings = mark_stale_listings(listings)

    active_listings = filter_active(listings)    
    category_counts = {}
    for category_info in CATEGORIES.values():
        count = len([l for l in active_listings if l["category"] == category_info["name"]])
        category_counts[category_info["name"]] = count
    
    total_active = len(active_listings)    
    # Create category links with counts using correct anchor formats and emojis
    # Order: Software, Product, Data, Quant, Hardware, Other
    category_order = ["Software", "Product", "AI/ML/Data", "Quant", "Hardware", "Other"]
    category_links = []
    for category_key in category_order:
        if category_key in CATEGORIES:
            category_info = CATEGORIES[category_key]
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
                for category_key in category_order:
                    if category_key in CATEGORIES:
                        category_info = CATEGORIES[category_key]
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