"""Generate nerc_holidays.csv.

NERC off-peak holidays: New Year's Day, Memorial Day, Independence Day,
Labor Day, Thanksgiving Day, Christmas Day. A fixed-date holiday that falls
on Sunday is observed the following Monday; one that falls on Saturday is
not moved.

Each holiday is a full local day: [start_local, end_local), end exclusive.

Usage: python3 generate.py
"""

import csv
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

FIRST_YEAR, LAST_YEAR = 2010, 2046

# Market time zone of each region. MISO runs on Eastern Standard Time year-round.
REGIONS = {
    "CAISO": "America/Los_Angeles",
    "ERCOT": "America/Chicago",
    "SPP": "America/Chicago",
    "MISO": "EST",
    "PJM": "America/New_York",
    "NYISO": "America/New_York",
    "ISONE": "America/New_York",
}


def nth_weekday(year, month, weekday, n):
    """n-th weekday (Mon=0) of the month; n=-1 for the last one."""
    if n > 0:
        d = date(year, month, 1)
        d += timedelta(days=(weekday - d.weekday()) % 7)
        return d + timedelta(weeks=n - 1)
    d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def observed(d):
    return d + timedelta(days=1) if d.weekday() == 6 else d


def holidays(year):
    return [
        ("New Year's Day", observed(date(year, 1, 1))),
        ("Memorial Day", nth_weekday(year, 5, 0, -1)),
        ("Independence Day", observed(date(year, 7, 4))),
        ("Labor Day", nth_weekday(year, 9, 0, 1)),
        ("Thanksgiving Day", nth_weekday(year, 11, 3, 4)),
        ("Christmas Day", observed(date(year, 12, 25))),
    ]


def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def main():
    with open("nerc_holidays.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["region", "timezone", "holiday", "start_local", "end_local", "start_utc", "end_utc"])
        for region, tz_name in REGIONS.items():
            tz = ZoneInfo(tz_name)
            for year in range(FIRST_YEAR, LAST_YEAR + 1):
                for name, d in holidays(year):
                    start = datetime.combine(d, time(), tz)
                    end = datetime.combine(d + timedelta(days=1), time(), tz)
                    w.writerow([
                        region, tz_name, name, fmt(start), fmt(end),
                        fmt(start.astimezone(timezone.utc)), fmt(end.astimezone(timezone.utc)),
                    ])


if __name__ == "__main__":
    main()
