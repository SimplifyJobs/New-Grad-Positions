import json
from datetime import datetime
import os
import util
import re


def main():

    listings = util.getListingsFromJSON()

    util.checkSchema(listings)
    filtered = util.filterListings(listings)
    
    util.sortListings(filtered)
    util.embedTable(filtered)

    util.setOutput("commit_message", "Updating README at " + datetime.now().strftime("%B %d, %Y %H:%M:%S"))


if __name__ == "__main__":
    main()
