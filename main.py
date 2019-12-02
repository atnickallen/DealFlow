import time
from typing import Any, Dict, List, Union

import requests
import sentry_sdk

import functions
import settings

sentry_sdk.init("https://2e9daba5b3a74ee29c0411292e9f3767@sentry.io/1829847")

#
#   Set last_timestamp
#
try:
    with open("last_timestamp.txt") as file:
        last_timestamp = int(file.read())
except FileNotFoundError:
    # Defaults to 10 days ago
    last_timestamp = int(time.time()) - 10 * 24 * 60 * 60

with open("last_timestamp.txt", "w+") as file:
    file.write(str(int(time.time())))

#
#   Fetch funding rounds from Crunchbase
#
next_page_url = settings.crunchbase_url

params: Dict[str, Any] = {
    "updated_since": last_timestamp,
    "user_key": settings.crunchbase_key,
}

crunchbase_funding_rounds: List[Dict] = []

while next_page_url:
    print("Fetching page of funding rounds from Crunchbase")
    r = requests.get(next_page_url, params=params)
    r.raise_for_status()

    data = r.json()["data"]
    # When we reach the last page, this will be None and thus the loop will exit.
    next_page_url = data["paging"]["next_page_url"]

    # We need this as the next_page_url returned already contains this parameter
    if "updated_since" in params.keys():
        del params["updated_since"]

    filtered_items = [
        item
        for item in data["items"]
        if item["properties"]["funding_type"] in settings.funding_types
    ]

    crunchbase_funding_rounds.extend(filtered_items)

crunchbase_funding_round_ids = [fr["uuid"] for fr in crunchbase_funding_rounds]

#
#   Build mappings between Crunchbase IDs and Airtable record IDs
#
print("Fetching ID maps from Airtable")
funding_round_id_map = functions.get_id_map(
    settings.airtable_urls.investment_rounds,
    extra_params={
        "filterByFormula": 'SEARCH({ID}, "'
        + ",".join(crunchbase_funding_round_ids)
        + '")'
    },
)

company_id_map = functions.get_id_map(settings.airtable_urls.companies)

fund_id_map = functions.get_id_map(settings.airtable_urls.funds)

person_id_map = functions.get_id_map(settings.airtable_urls.people)


#
#   Fetch extra data for each funding round
#
crunchbase_companies: List[dict] = []
airtable_companies_to_insert: List[dict] = []
airtable_companies_to_update: List[dict] = []

airtable_funds_to_insert: List[dict] = []
airtable_funds_to_update: List[dict] = []

airtable_people_to_insert: List[dict] = []
airtable_people_to_update: List[dict] = []

N = len(crunchbase_funding_rounds)
for i, crunchbase_funding_round in enumerate(crunchbase_funding_rounds):
    print(f"Fetching funding round details ({i+1} of {N})")
    r = requests.get(
        crunchbase_funding_round["properties"]["api_url"],
        params={"user_key": settings.crunchbase_key,},
    )
    r.raise_for_status()

    crunchbase_funding_round_data = r.json()["data"]

    #
    #   Handle Funds
    #
    investments = crunchbase_funding_round_data["relationships"]["investments"]["items"]
    airtable_funds_to_insert.extend(
        {"fields": functions.transform_fund_structure(investment)}
        for investment in investments
        if investment["relationships"]["investors"]["uuid"] not in fund_id_map.keys()
    )
    airtable_funds_to_update.extend(
        {
            "fields": functions.transform_fund_structure(investment),
            "id": fund_id_map[investment["relationships"]["investors"]["uuid"]],
        }
        for investment in investments
        if investment["relationships"]["investors"]["uuid"] in fund_id_map.keys()
    )
    crunchbase_funding_round["fund_crunchbase_ids"] = [
        i["relationships"]["investors"]["uuid"] for i in investments
    ]
    crunchbase_funding_round["lead_fund_crunchbase_id"] = next(
        (
            i["relationships"]["investors"]["uuid"]
            for i in investments
            if i["properties"]["is_lead_investor"]
        ),
        None,
    )

    #
    #   Handle Company
    #
    print("Fetching company details")
    company_api_url = crunchbase_funding_round_data["relationships"][
        "funded_organization"
    ]["item"]["properties"]["api_url"]

    r = requests.get(company_api_url, params={"user_key": settings.crunchbase_key,},)
    r.raise_for_status()

    crunchbase_company_data = r.json()["data"]
    crunchbase_company_data["founder_crunchbase_ids"] = []

    # Sort out Founders
    crunchbase_people = crunchbase_company_data["relationships"]["founders"]["items"]
    for crunchbase_person in crunchbase_people:
        print("Fetching person details")

        person_api_url = crunchbase_person["properties"]["api_url"]
        r = requests.get(person_api_url, params={"user_key": settings.crunchbase_key,},)
        r.raise_for_status()

        crunchbase_person_data = r.json()["data"]

        airtable_person_data = functions.transform_person_structure(crunchbase_person_data)

        person_airtable_id = person_id_map.get(airtable_person_data["ID"])
        if person_airtable_id:
            airtable_people_to_update.append(
                {"id": person_airtable_id, "fields": airtable_person_data}
            )
        else:
            airtable_people_to_insert.append({"fields": airtable_person_data})

        crunchbase_company_data["founder_crunchbase_ids"].append(
            airtable_person_data["ID"]
        )

    crunchbase_funding_round["company_crunchbase_id"] = crunchbase_company_data["uuid"]
    crunchbase_companies.append(crunchbase_company_data)


#
#   Add new people to Airtable
#
print("Pushing people to Airtable")
functions.push_to_airtable(settings.airtable_urls.people, airtable_people_to_update)
functions.push_to_airtable(
    settings.airtable_urls.people,
    airtable_people_to_insert,
    update=False,
    id_map=person_id_map,
)

#
#   Add new funds to Airtable
#
print("Pushing funds to Airtable")
functions.push_to_airtable(settings.airtable_urls.funds, airtable_funds_to_update)
functions.push_to_airtable(
    settings.airtable_urls.funds,
    airtable_funds_to_insert,
    update=False,
    id_map=fund_id_map,
)

#
#   Add new companies to Airtable
#
for crunchbase_company_data in crunchbase_companies:
    crunchbase_company_data["founder_airtable_ids"] = [
        person_id_map[id] for id in crunchbase_company_data["founder_crunchbase_ids"]
    ]
    airtable_company_data = functions.transform_company_structure(
        crunchbase_company_data
    )

    company_airtable_id = company_id_map.get(airtable_company_data["ID"])
    if company_airtable_id:
        airtable_companies_to_update.append(
            {"id": company_airtable_id, "fields": airtable_company_data}
        )
    else:
        airtable_companies_to_insert.append({"fields": airtable_company_data})

print("Pushing companies to Airtable")
functions.push_to_airtable(
    settings.airtable_urls.companies, airtable_companies_to_update
)
functions.push_to_airtable(
    settings.airtable_urls.companies,
    airtable_companies_to_insert,
    update=False,
    id_map=company_id_map,
)

#
#   Resolve funding round references with id maps
#
for crunchbase_funding_round in crunchbase_funding_rounds:
    crunchbase_funding_round["company_airtable_id"] = company_id_map[
        crunchbase_funding_round["company_crunchbase_id"]
    ]
    crunchbase_funding_round["fund_airtable_ids"] = [
        fund_id_map[id] for id in crunchbase_funding_round["fund_crunchbase_ids"]
    ]
    crunchbase_funding_round["lead_fund_airtable_id"] = fund_id_map.get(
        crunchbase_funding_round["lead_fund_crunchbase_id"]
    )

#
#   Add new funding rounds to Airtable
#
print("Pushing funding rounds to Airtable")
airtable_funding_rounds = [
    functions.transform_funding_round_structure(fr) for fr in crunchbase_funding_rounds
]

airtable_funding_rounds_to_insert = [
    {"fields": ft}
    for ft in airtable_funding_rounds
    if ft["ID"] not in funding_round_id_map.keys()
]
airtable_funding_rounds_to_update = [
    {"fields": ft, "id": funding_round_id_map[ft["ID"]]}
    for ft in airtable_funding_rounds
    if ft["ID"] in funding_round_id_map.keys()
]


functions.push_to_airtable(
    settings.airtable_urls.investment_rounds, airtable_funding_rounds_to_update
)
functions.push_to_airtable(
    settings.airtable_urls.investment_rounds,
    airtable_funding_rounds_to_insert,
    update=False,
)
