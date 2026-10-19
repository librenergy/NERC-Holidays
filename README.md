# NERC Holidays

NERC off-peak holidays as a CSV, one row per region per holiday, 2010–2046.

```
https://raw.githubusercontent.com/librenergy/NERC-Holidays/main/nerc_holidays.csv
```

## Rules

Six holidays: New Year's Day, Memorial Day, Independence Day, Labor Day,
Thanksgiving Day, Christmas Day. When a fixed-date holiday falls on a Sunday,
it moves to the following Monday. When it falls on a Saturday, it stays on Saturday.

## Columns

| column        | example                  | notes                                    |
|---------------|--------------------------|------------------------------------------|
| `region`      | `CAISO`                  | CAISO, ERCOT, SPP, MISO, PJM, NYISO, ISONE |
| `timezone`    | `America/Los_Angeles`    | IANA name of the market's time zone (MISO uses `EST` year-round) |
| `holiday`     | `Christmas Day`          |                                          |
| `start_local` | `2026-12-25 00:00:00`    | inclusive, market local time             |
| `end_local`   | `2026-12-26 00:00:00`    | exclusive, market local time             |
| `start_utc`   | `2026-12-25 08:00:00`    | inclusive, UTC                           |
| `end_utc`     | `2026-12-26 08:00:00`    | exclusive, UTC                           |

The intervals are half-open (`start <= ts < end`), so hour-beginning data lines up
without double-counting midnight. Join on the `_utc` columns if your timestamps are
UTC, or on the `_local` columns if they're in market local time.

## DuckDB

```sql
CREATE TABLE nerc_holidays AS
SELECT * FROM 'https://raw.githubusercontent.com/librenergy/NERC-Holidays/main/nerc_holidays.csv';

-- Drop holiday hours from a UTC time series
SELECT p.*
FROM prices p
ANTI JOIN nerc_holidays h
  ON h.region = 'CAISO'
 AND p.ts_utc >= h.start_utc AND p.ts_utc < h.end_utc;
```

## ClickHouse / chDB

Pass the schema explicitly. Otherwise ClickHouse parses `start_utc`/`end_utc` in the
session time zone instead of UTC.

```sql
CREATE TABLE nerc_holidays ENGINE = Memory AS
SELECT * FROM url(
    'https://raw.githubusercontent.com/librenergy/NERC-Holidays/main/nerc_holidays.csv',
    CSVWithNames,
    'region String, timezone String, holiday String, start_local DateTime, end_local DateTime, start_utc DateTime(\'UTC\'), end_utc DateTime(\'UTC\')'
);

-- Drop holiday hours from a UTC time series
SELECT p.*
FROM prices p
WHERE NOT EXISTS (
  SELECT 1 FROM nerc_holidays h
  WHERE h.region = 'CAISO'
    AND p.ts_utc >= h.start_utc AND p.ts_utc < h.end_utc
);
```

## Time spine with a holiday flag

Builds a row per interval (5 min, 10 min, hourly, ...) with `is_holiday`. Build the spine
in UTC and convert to local time for display: a local-time spine has a missing hour in
spring and a repeated one in fall. Holidays start and end on the hour, so any interval
that divides an hour falls entirely inside or outside a holiday.

DuckDB:

```sql
WITH spine AS (
    SELECT 'CAISO' AS region, ts AS ts_utc
    FROM range(TIMESTAMP '2026-01-01', TIMESTAMP '2027-01-01', INTERVAL 5 MINUTE) t(ts)
)
SELECT s.region, s.ts_utc,
       timezone('America/Los_Angeles', timezone('UTC', s.ts_utc)) AS ts_local,
       h.holiday IS NOT NULL AS is_holiday,
       h.holiday
FROM spine s
LEFT JOIN nerc_holidays h
  ON h.region = s.region AND s.ts_utc >= h.start_utc AND s.ts_utc < h.end_utc;
```

ClickHouse uses an `ASOF` join, which finds the latest holiday starting at or before
`ts_utc` and then checks whether `ts_utc` falls before its end:

```sql
WITH
    toDateTime('2026-01-01 00:00:00', 'UTC') AS t0,
    toDateTime('2027-01-01 00:00:00', 'UTC') AS t1,
    300 AS step,  -- seconds: 300 = 5 min, 600 = 10 min, 3600 = hourly
    spine AS (
        SELECT 'CAISO' AS region, t0 + toIntervalSecond(number * step) AS ts_utc
        FROM numbers(intDiv(dateDiff('second', t0, t1), step))
    )
SELECT s.region, s.ts_utc,
       toTimeZone(s.ts_utc, 'America/Los_Angeles') AS ts_local,
       s.ts_utc < h.end_utc AS is_holiday,
       if(is_holiday, h.holiday, '') AS holiday
FROM spine s
ASOF LEFT JOIN nerc_holidays h ON s.region = h.region AND s.ts_utc >= h.start_utc;
```

## Regenerating

```sh
python3 generate.py   # stdlib only, rewrites nerc_holidays.csv
```

To add a region or extend the year range, edit `REGIONS` or `FIRST_YEAR`/`LAST_YEAR`
in `generate.py` and rerun.
