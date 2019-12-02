from datetime import datetime
from typing import Any, Dict, Optional

import requests

import settings

crunchbase_url = "https://www.crunchbase.com/"


def get_id_map(airtable_url: str, extra_params: dict = {}) -> dict:
    """Builds a map from Crunchbase IDs to Airtable IDs
    
    :param airtable_url: URL to Airtable API tab endpoint
    :type airtable_url: str
    :param extra_params: Extra parameters to be sent to the Airtable API call, defaults to {}
    :type extra_params: dict, optional
    :return: Mapping
    :rtype: dict
    """
    offset = 0

    params: Dict[str, Any] = {
        "fields[]": ["ID"],
        "api_key": settings.airtable_key,
    }

    params.update(extra_params)

    id_map: Dict[str, str] = {}

    while offset is not None:
        params["offset"] = offset
        r = requests.get(airtable_url, params=params)
        r.raise_for_status()

        data = r.json()
        offset = data.get("offset")
        id_map.update(
            (record["fields"]["ID"], record["id"])
            for record in data["records"]
            if "ID" in record["fields"].keys()
        )

    return id_map


def humanize_funding_type(type: str) -> str:
    """Converts raw funding type returned by Crunchbase to the humanized version we have
    in Airtable.
    
    For example, humanize_funding_type("post_ipo_equity") returns "Post-IPO Equity"
    
    :param type: Type as returned by Crunchbase
    :type type: str
    :return: Human-friendly version of the type for Airtable
    :rtype: str
    """
    map = {
        "pre_seed": "Pre-Seed",
        "seed": "Seed",
        "angel": "Angel",
        "venture": "Venture",
        "equity_crowdfunding": "Equity Crowdfunding",
        "product_crowdfunding": "Product Crowdfunding",
        "private_equity": "Private Equity",
        "convertible_note": "Convertible Note",
        "debt_financing": "Debt Financing",
        "secondary_market": "Secondary Market",
        "grant": "Grant",
        "post_ipo_equity": "Post-IPO Equity",
        "post_ipo_debt": "Post-IPO Debt",
        "non_equity_assistance": "Non-Equity Assistance",
        "undisclosed": "Undisclosed",
        "corporate_round": "Corporate Round",
        "initial_coin_offering": "Initial Coin Offering",
        "post_ipo_secondary": "Post-IPO Secondary",
        "series_a": "Series A",
        "series_b": "Series B",
        "series_c": "Series C",
        "series_d": "Series D",
        "series_e": "Series E",
        "series_f": "Series F",
        "series_g": "Series G",
        "series_h": "Series H",
        "series_i": "Series I",
        "series_j": "Series J",
        "series_unknown": "Venture - Series Unknown",
    }
    return map[type]


def humanize_investor_type(type: str) -> str:
    """Converts raw investor type returned by Crunchbase to the humanized version we have
    in Airtable.
    
    For example, humanize_investor_type("micro_vc") returns "microVC"
    
    :param type: Type as returned by Crunchbase
    :type type: str
    :return: Human-friendly version of the type for Airtable
    :rtype: str
    """
    map = {
        "micro_vc": "microVC",
        "venture_capital": "VC",
        "incubator": "Incubator Fund",
        "private_equity_firm": "Private Equity Firm",
        "accelerator": "Accelerator",
    }
    return map.get(type, "Other Institution")


def transform_funding_round_structure(crunchbase_funding_round: dict) -> dict:
    """Prepares a Funding Round record Airtable will accept given a Crunchbase record
    
    :param crunchbase_funding_round: Record as returned by CB
    :type crunchbase_funding_round: dict
    :return: Record for Airtable
    :rtype: dict
    """
    properties = crunchbase_funding_round["properties"]
    return {
        "ID": crunchbase_funding_round["uuid"],
        "Round Type": humanize_funding_type(properties["funding_type"]),
        "Round Size": properties["target_money_raised_usd"],
        "Raised So Far": properties["money_raised_usd"],
        "Pre-Money Valuation or Note Cap": properties["pre_money_valuation_usd"],
        "Close Date": properties.get("close_date"),
        "Announcement Date": properties["announced_on"],
        "Company": [crunchbase_funding_round["company_airtable_id"]],
        "Investors": list(set(crunchbase_funding_round["fund_airtable_ids"])),
        "Lead Investor": [crunchbase_funding_round["lead_fund_airtable_id"]]
        if crunchbase_funding_round["lead_fund_airtable_id"] is not None
        else None,
        "Last Updated": datetime.fromtimestamp(properties["updated_at"]).isoformat(),
    }


def transform_company_structure(crunchbase_company: dict) -> dict:
    """Prepares a Company record Airtable will accept given a Crunchbase record
    
    :param crunchbase_funding_round: Record as returned by CB
    :type crunchbase_funding_round: dict
    :return: Record for Airtable
    :rtype: dict
    """
    properties = crunchbase_company["properties"]
    relationships = crunchbase_company["relationships"]
    headquarters = relationships["headquarters"].get("item")
    data = {
        "ID": crunchbase_company["uuid"],
        "Company Name": properties["name"],
        "Company Logo": properties["profile_image_url"],
        "Website": properties["homepage_url"],
        "Description": properties["description"],
        "Categories": [
            item["properties"]["name"] for item in relationships["categories"]["items"]
        ],
        "Email Address": properties["contact_email"],
        "Phone Number": properties["phone_number"],
        "Crunchbase": crunchbase_url + properties["web_path"],
        "LinkedIn": next(
            (
                site["properties"]["url"]
                for site in relationships["websites"]["items"]
                if site["properties"]["website_type"] == "linkedin"
            ),
            None,
        ),
        "Twitter": next(
            (
                site["properties"]["url"]
                for site in relationships["websites"]["items"]
                if site["properties"]["website_type"] == "twitter"
            ),
            None,
        ),
        "Last Updated": datetime.fromtimestamp(properties["updated_at"]).isoformat(),
        "Founders": crunchbase_company["founder_airtable_ids"],
    }
    if headquarters:
        data.update(
            {
                "HQ Name": headquarters["properties"]["name"],
                "HQ Street 1": headquarters["properties"]["street_1"],
                "HQ Street 2": headquarters["properties"]["street_2"],
                "HQ City": headquarters["properties"]["city"],
                "HQ Region": headquarters["properties"]["region"],
                "HQ Country": headquarters["properties"]["country"],
                "HQ Postcode": headquarters["properties"]["postal_code"],
            }
        )

    return data


def transform_fund_structure(crunchbase_investment: dict) -> dict:
    """Prepares a Fund record Airtable will accept given a Crunchbase record
    
    :param crunchbase_investment: Record as returned by CB
    :type crunchbase_investment: dict
    :return: Record for Airtable
    :rtype: dict
    """
    fund = crunchbase_investment["relationships"]["investors"]
    properties = fund["properties"]
    name = None
    if fund["type"] == "Organization":
        name = properties["name"]
        investor_type = (
            humanize_investor_type(properties["investor_type"][0])
            if properties["investor_type"]
            else None
        )
    elif fund["type"] == "Person":
        name = properties["first_name"] + " " + properties["last_name"]
        investor_type = "Individual"

    return {
        "ID": fund["uuid"],
        "Name": name,
        "Website": properties.get("homepage_url"),
        "Email": properties.get("contact_email"),
        "Last Updated": datetime.fromtimestamp(properties["updated_at"]).isoformat(),
        "Type": investor_type,
    }


def transform_person_structure(crunchbase_person: dict) -> dict:
    """Prepares a Person record Airtable will accept given a Crunchbase record
    
    :param crunchbase_person: Record as returned by CB
    :type crunchbase_person: dict
    :return: Record for Airtable
    :rtype: dict
    """
    properties = crunchbase_person["properties"]
    relationships = crunchbase_person["relationships"]
    websites = relationships["websites"]["items"]
    return {
        "ID": crunchbase_person["uuid"],
        "First Name": properties["first_name"],
        "Last Name": properties["last_name"],
        "Bio": properties["bio"],
        "Birthday": properties["born_on"],
        "Twitter": next(
            (
                site["properties"]["url"]
                for site in websites
                if site["properties"]["website_type"] == "twitter"
            ),
            None,
        ),
        "LinkedIn": next(
            (
                site["properties"]["url"]
                for site in websites
                if site["properties"]["website_type"] == "linkedin"
            ),
            None,
        ),
        "Crunchbase": crunchbase_url + properties["web_path"],
        "Last Updated": datetime.fromtimestamp(properties["updated_at"]).isoformat(),
    }


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


def push_to_airtable(
    airtable_url: str,
    records: list,
    update: bool = True,
    id_map: Optional[dict] = None,
) -> None:
    """Inserts or updates records in Airtable, and updates an id map in the case of 
    insertion
    
    :param airtable_url: URL to Airtable API tab endpoint
    :type airtable_url: str
    :param records: Records to be inserted into Airtable
    :type records: list
    :param update: False = Insert, defaults to True = Update
    :type update: bool, optional
    :param id_map: Map of Crunchbase IDs to Airtable IDs to be updated if inserting
    :type id_map: Optional[dict], optional
    :raises ValueError: If updating, id_map cannot be updated
    """
    if update and id_map is not None:
        raise ValueError("The id map cannot be updated if records are being updated")

    # Remove duplicates
    records = [i for n, i in enumerate(records) if i not in records[n + 1 :]]

    method = requests.patch if update else requests.post

    for records_chunk in chunks(records, 10):
        r = method(
            airtable_url,
            params={"api_key": settings.airtable_key},
            json={"records": records_chunk},
        )
        r.raise_for_status()
        if id_map is not None:
            id_map.update(
                {record["fields"]["ID"]: record["id"] for record in r.json()["records"]}
            )
