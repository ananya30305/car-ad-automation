import csv
import logging
from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR


LOG_FILE = OUTPUT_DIR / "posting_log.csv"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


HEADERS = [
    "timestamp",
    "ad_number",
    "vehicle_id",
    "source_url",
    "year",
    "make",
    "model",
    "variant",
    "status",
    "reason",
]


def create_log_file():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if LOG_FILE.exists():
        return

    with open(
        LOG_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=HEADERS
        )

        writer.writeheader()


def log_result(
    ad,
    status,
    reason=""
):

    create_log_file()

    vehicle_id = (
        ad.get("source_url")
        or ad.get("source_id")
        or ""
    )

    row = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),

        "ad_number": ad.get(
            "ad_number",
            ""
        ),

        "vehicle_id": vehicle_id,

        "source_url": ad.get(
            "source_url",
            ""
        ),

        "year": ad.get(
            "year",
            ""
        ),

        "make": ad.get(
            "make",
            ""
        ),

        "model": ad.get(
            "model",
            ""
        ),

        "variant": ad.get(
            "variant",
            ""
        ),

        "status": status,

        "reason": reason,
    }

    with open(
        LOG_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=HEADERS
        )

        writer.writerow(row)

    logger.info(
        "Recorded: %s | %s %s %s",
        status,
        ad.get("year", ""),
        ad.get("make", ""),
        ad.get("model", "")
    )


def show_summary():

    create_log_file()

    rows = []

    with open(
        LOG_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        rows = list(reader)

    total = len(rows)

    posted = sum(
        1
        for row in rows
        if row["status"].upper() == "POSTED"
    )

    skipped = sum(
        1
        for row in rows
        if row["status"].upper() == "SKIPPED"
    )

    rejected = sum(
        1
        for row in rows
        if row["status"].upper() == "REJECTED"
    )

    failed = sum(
        1
        for row in rows
        if row["status"].upper() == "FAILED"
    )

    print()
    print("=" * 60)
    print("POSTING SUMMARY")
    print("=" * 60)
    print(f"Total records : {total}")
    print(f"Posted        : {posted}")
    print(f"Skipped       : {skipped}")
    print(f"Rejected      : {rejected}")
    print(f"Failed        : {failed}")
    print("=" * 60)
    print(f"Log file: {LOG_FILE}")


if __name__ == "__main__":

    show_summary()