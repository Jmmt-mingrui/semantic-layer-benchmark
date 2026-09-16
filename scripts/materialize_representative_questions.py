"""Reviewable public question definitions and deterministic instance rendering.

Run --check to detect drift, or --patch to print an apply_patch-compatible update.
No Gold results are read and no repository file is written by this script.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from runner.core.question_contracts import render_output_requirements
from scripts.validate_repository import ROOT


INSTANCES = Path("benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl")
QUALIFICATION = Path("benchmark/tpcds/questions/instances/sf1-qualification-q01.jsonl")


def _contract(columns: str, order: str, max_rows: int | None = 100) -> dict[str, Any]:
    keys = []
    for item in order.split(","):
        tokens = item.split()
        keys.append({"column": tokens[0], "direction": tokens[1] if len(tokens) > 1 else "ASC", "nulls": "LAST"})
    return {"columns": columns.split(","), "order_sensitive": True, "max_rows": max_rows,
            "comparison": "exact_normalized", "order_by": keys}


Q01_QUESTION = (
    "For stores in Tennessee (state code TN) during calendar year 2000, return up to 100 customer IDs, "
    "sorted in ascending order, whose total store return amount is more than 20% above the average total "
    "return amount for customers of that same store. Use the return date's calendar year and sum return "
    "amounts per customer and store before computing the store's customer average. Return one row per "
    "qualifying customer-store pair; do not deduplicate customers who qualify at multiple stores."
)

# These definitions describe the attributed SQL's business semantics, including
# its non-obvious duplicate/date/rank behavior. They are not model answer hints.
SPECS: dict[str, dict[str, Any]] = {
    "q01": {
        "question": Q01_QUESTION,
        "parameters": [("YEAR", "integer", 2000), ("STATE", "string", "TN"), ("AGG_FIELD", "identifier", "SR_RETURN_AMT")],
        "contracts": [_contract("c_customer_id", "c_customer_id")],
    },
    "q02": {
        "question": "Combine web and catalog extended sales prices without deduplicating transactions. "
                    "Aggregate sales by absolute calendar week and day name over all available dates, including "
                    "cross-year weeks. Pair each week represented by calendar dates in 2001 with the week exactly "
                    "53 week-sequence units later represented by dates in 2002. For Sunday through Saturday, "
                    "calculate the 2001-week total divided by the 2002-week total, rounded to two decimal places "
                    "(not a percentage increase or the inverse ratio). Missing weekday totals remain NULL. "
                    "Return the 2001 week sequence and the seven ratios. Preserve one copy for every pair of "
                    "qualifying 2001 and 2002 calendar dates in the matched weeks, not just one row per week.",
        "parameters": [("YEAR", "integer", 2001)],
        "contracts": [_contract("d_week_seq1,sun_sales_ratio,mon_sales_ratio,tue_sales_ratio,wed_sales_ratio,thu_sales_ratio,fri_sales_ratio,sat_sales_ratio", "d_week_seq1", None)],
    },
    "q03": {
        "question": "For manufacturer 128 in calendar month 11 of every available year, report the sum of "
                    "extended store-sales price grouped by calendar year, item brand ID, and item brand name. "
                    "Use d_year for the year, brand_id for the brand ID, brand for its name, and sum_agg for the total.",
        "parameters": [("MONTH", "integer", 11), ("SALES_MEASURE", "identifier", "SS_EXT_SALES_PRICE"), ("MANUFACTURER_ID", "integer", 128)],
        "contracts": [_contract("d_year,brand_id,brand,sum_agg", "d_year,sum_agg DESC,brand_id")],
    },
    "q05": {
        "question": "From 2000-08-23 through 2000-09-06 inclusive (start date through start date plus 14 days), "
                    "combine store, catalog, and web sales and returns. Filter sales by sold date and returns "
                    "independently by returned date. Sum extended sales price as sales, return amount as returns, "
                    "and sales net profit minus return net loss as profit. Attribute store rows to store ID, catalog "
                    "rows to catalog-page ID, and web rows to web-site ID; obtain each web return's site from its "
                    "matching sale by order number and item, excluding returns with no matched site. Preserve "
                    "matching-row multiplicity. Use channel labels 'store channel', 'catalog channel', 'web channel' "
                    "and location IDs prefixed respectively with 'store', 'catalog_page', 'web_site'. Roll up channel "
                    "then location ID, including channel subtotals and a grand total with NULL grouping fields.",
        "parameters": [("START_DATE", "date", "2000-08-23")],
        "contracts": [_contract("channel,id,sales,returns,profit", "channel,id")],
    },
    "q12": {
        "question": "For web sales from 1999-02-22 through 1999-03-24 inclusive (start date through start date "
                    "plus 30 days), in the Sports, Books, and Home categories, group by item ID, description, "
                    "category, class, and current price. Sum extended web-sales price as itemrevenue and calculate "
                    "revenueratio as 100 times that revenue divided by total revenue for the same class across "
                    "these filtered item groups. Return the item fields and this percentage, not a fractional share.",
        "parameters": [("START_DATE", "date", "1999-02-22"), ("CATEGORIES", "list", ["Sports", "Books", "Home"])],
        "contracts": [_contract("i_item_id,i_item_desc,i_category,i_class,i_current_price,itemrevenue,revenueratio", "i_category,i_class,i_item_id,i_item_desc,revenueratio")],
    },
    "q14": {
        "question": "Identify brand-ID/class-ID/category-ID combinations with sales in each of store, catalog, "
                    "and web during 1999 through 2001 inclusive; all items in a qualifying combination are eligible. "
                    "Compute a common threshold as the average of quantity times list price per sale row across "
                    "all three channels in those years, without deduplicating sale rows. Submit two outputs. "
                    "First, for November 2001, sum quantity times list price and count sale rows separately by "
                    "channel and qualifying combination; keep channel/group totals strictly above the common "
                    "threshold, then roll up channel, brand ID, class ID, and category ID, including all subtotals "
                    "and the grand total. Label channels 'store', 'catalog', 'web'. Second, for store sales, compare "
                    "the entire calendar week containing December 11, 2000 (ty) against the entire week containing "
                    "December 11, 1999 (ly). In each week keep eligible groups whose quantity-times-list-price "
                    "total is above the same threshold; include only combinations present in both qualifying "
                    "weekly sets. Return channel, hierarchy IDs, total sales, and sale-row count for ty then ly.",
        "parameters": [("YEAR", "integer", 1999), ("DAY", "integer", 11)],
        "contracts": [
            _contract("channel,i_brand_id,i_class_id,i_category_id,sales,number_sales", "channel,i_brand_id,i_class_id,i_category_id"),
            _contract("ty_channel,ty_brand,ty_class,ty_category,ty_sales,ty_number_sales,ly_channel,ly_brand,ly_class,ly_category,ly_sales,ly_number_sales", "ty_channel,ty_brand,ty_class,ty_category"),
        ],
    },
    "q21": {
        "question": "For items with current price from 0.99 to 1.49 inclusive, sum inventory quantity on hand "
                    "by warehouse name and item ID from 2000-02-10 through 2000-04-10 inclusive (30 days before "
                    "through 30 days after 2000-03-11). inv_before sums dates strictly before 2000-03-11 and "
                    "inv_after sums dates on or after it. Keep positive inv_before groups whose inv_after divided "
                    "by inv_before is between two-thirds and three-halves inclusive.",
        "parameters": [("PRICE_CHANGE_DATE", "date", "2000-03-11")],
        "contracts": [_contract("w_warehouse_name,i_item_id,inv_before,inv_after", "w_warehouse_name,i_item_id")],
    },
    "q36": {
        "question": "For Tennessee stores (TN) in calendar year 2001, compute gross_margin as total store-sales "
                    "net profit divided by total extended sales price, grouped by item category and class with "
                    "category subtotals and a grand total. lochierarchy is 0 for category/class detail, 1 for category "
                    "subtotal, and 2 for grand total (use grouping levels, not whether a data value is NULL). Rank "
                    "gross margin in ascending order using RANK with ties and gaps, partitioned by hierarchy "
                    "level and, for detail only, the parent category. Category subtotals rank together. Use category "
                    "and class as deterministic tie-breaks only for final row presentation, not for ranking.",
        "parameters": [("YEAR", "integer", 2001), ("STATES", "list", ["TN"])],
        "contracts": [_contract("gross_margin,i_category,i_class,lochierarchy,rank_within_parent", "lochierarchy DESC,i_category,rank_within_parent,i_category,i_class")],
    },
    "q39": {
        "question": "For inventory in calendar year 2001, group quantity on hand by warehouse name and key, "
                    "item key, and calendar month. Compute mean inventory and sample standard deviation; the "
                    "coefficient of variation is sample standard deviation divided by mean, not a percentage. "
                    "Exclude zero means and require coefficient of variation greater than 1 in both January and "
                    "February. Pair those months on warehouse key and item key. Submit two outputs: all such "
                    "pairs, then the subset with January coefficient of variation strictly greater than 1.5. Each "
                    "output contains January warehouse key, item key, month, mean, coefficient, followed by the "
                    "corresponding February fields; month1/month2 denote the calendar month numbers.",
        "parameters": [("YEAR", "integer", 2001), ("MONTH", "integer", 1), ("COEFFICIENT_THRESHOLD", "number", 1.5)],
        "contracts": [
            _contract("month1_warehouse_sk,month1_item_sk,month1,month1_mean,month1_cov,month2_warehouse_sk,month2_item_sk,month2,month2_mean,month2_cov", "month1_warehouse_sk,month1_item_sk,month1,month1_mean,month1_cov,month2,month2_mean,month2_cov", None),
            _contract("month1_warehouse_sk,month1_item_sk,month1,month1_mean,month1_cov,month2_warehouse_sk,month2_item_sk,month2,month2_mean,month2_cov", "month1_warehouse_sk,month1_item_sk,month1,month1_mean,month1_cov,month2,month2_mean,month2_cov", None),
        ],
    },
    "q49": {
        "question": "For sales in December 2001, separately for web, catalog, and store, match returns to sales "
                    "by order/ticket number and item. Keep matched rows with return amount strictly greater than "
                    "10000, sale net profit greater than 1, sale net paid greater than 0, and sale quantity greater "
                    "than 0. Preserve join multiplicity and aggregate by item key. Calculate return_ratio as total "
                    "return quantity divided by total sale quantity, and currency_ratio as total return amount "
                    "divided by total sale net paid, casting each numerator and denominator to DECIMAL(15,4) "
                    "before division. Rank both ratios ascending independently within each channel using RANK "
                    "with ties and gaps. Return items whose return_rank or currency_rank is at most 10 (the lowest "
                    "ratios, not the highest/worst). Output channel ('web', 'catalog', 'store'), item key, return_ratio "
                    "and both ranks; do not output currency_ratio itself.",
        "parameters": [("YEAR", "integer", 2001), ("MONTH", "integer", 12)],
        "contracts": [_contract("channel,item,return_ratio,return_rank,currency_rank", "channel,return_rank,currency_rank,item")],
    },
    "q75": {
        "question": "For Books sales across catalog, store, and web, match each return by order/ticket and "
                    "item, treating missing return quantity and amount as zero. Net quantity is sale quantity "
                    "minus return quantity; net amount is extended sales price minus return amount. Deduplicate "
                    "identical detail tuples (calendar year, brand ID, class ID, category ID, manufacturer ID, net "
                    "quantity, net amount), including duplicates within or across channels, before summing by "
                    "year and those hierarchy IDs. Compare only groups present in both 2001 and 2002. Keep groups "
                    "where the 2002 count divided by 2001 count, with both counts cast to DECIMAL(17,2), is below "
                    "0.9. Return prev_year=2001, year=2002, the hierarchy IDs, both net counts, and current minus "
                    "previous count and amount differences. Use hierarchy IDs to break final presentation ties.",
        "parameters": [("YEAR", "integer", 2002), ("CATEGORIES", "list", ["Books"])],
        "contracts": [_contract("prev_year,year,i_brand_id,i_class_id,i_category_id,i_manufact_id,prev_yr_cnt,curr_yr_cnt,sales_cnt_diff,sales_amt_diff", "sales_cnt_diff,sales_amt_diff,i_brand_id,i_class_id,i_category_id,i_manufact_id")],
    },
    "q84": {
        "question": "List customers at their current address in Edgewood whose current household income "
                    "band has lower bound at least 38128 and upper bound at most 88128, with valid current "
                    "customer-demographic and household-demographic records. Associate store returns using "
                    "the customer's current demographic profile, not customer ID: produce one row for each "
                    "return with that same customer-demographic key, preserving duplicates even if the return "
                    "belongs to another customer sharing the profile. Return customer_id and customername; "
                    "format the name as last name, comma and space, first name, replacing NULL name parts "
                    "with empty strings.",
        "parameters": [("CITY", "string", "Edgewood"), ("INCOME_RANGE", "list", [38128, 88128])],
        "contracts": [_contract("customer_id,customername", "customer_id")],
    },
}
SPECS["q36"]["contracts"][0]["order_by"][1]["when"] = {"column": "lochierarchy", "equals": 0}


def representative_instances() -> list[dict[str, Any]]:
    rows = []
    for question_id, spec in SPECS.items():
        references = [f"benchmark/tpcds/sql/reference/duckdb/query{question_id[1:]}.sql"]
        if question_id in {"q14", "q39"}:
            references = [f"benchmark/tpcds/sql/reference/duckdb/query{question_id[1:]}_{part}.sql" for part in (1, 2)]
        contracts = spec["contracts"]
        rows.append({
            "schema_version": "0.3.0", "suite": "representative-v1", "benchmark": "TPC-DS-derived", "scale_factor": 1,
            "question_id": question_id, "instance_id": f"{question_id}-sf1-representative-v1-output-v1",
            "source_template": f"query{int(question_id[1:])}.tpl",
            "target_input": {"question": spec["question"] + " " + render_output_requirements(contracts)},
            "orchestrator_only": {"parameters": [{"name": name, "type": kind, "value": value} for name, kind, value in spec["parameters"]]},
            "evaluator_only": {
                "reference_sql": references, "expected_statement_count": len(contracts),
                "result_contract": contracts[0] if len(contracts) == 1 else {"statements": contracts},
                "provenance": {"canonical_question": "benchmark/tpcds/questions/canonical/questions.jsonl",
                               "reference_source": "benchmark/tpcds/sql/reference/duckdb/SOURCE.md",
                               "materialization_revision": "public-output-contract-v1"},
            },
        })
    return rows


def rendered_files(root: Path) -> dict[Path, str]:
    rows = representative_instances()
    qualification = json.loads((root / QUALIFICATION).read_text().strip())
    qualification["target_input"] = rows[0]["target_input"]
    encode = lambda row: json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    return {INSTANCES: "".join(map(encode, rows)), QUALIFICATION: encode(qualification)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--patch", action="store_true", help="Print a patch; never write files")
    args = parser.parse_args(argv)
    changed = {path: text for path, text in rendered_files(args.root).items() if (args.root / path).read_text() != text}
    if args.patch:
        if changed:
            print("*** Begin Patch")
            for path, text in changed.items():
                print(f"*** Update File: {args.root / path}")
                print("@@")
                for line in (args.root / path).read_text().splitlines():
                    print("-" + line)
                for line in text.splitlines():
                    print("+" + line)
            print("*** End Patch")
        return 0
    if changed:
        print("Public question definitions drifted: " + ", ".join(map(str, changed)))
        return 1
    print("PASS: 12 representative questions and the shared q01 qualification wording")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
