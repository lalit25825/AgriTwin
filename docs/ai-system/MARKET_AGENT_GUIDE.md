# AgriTwin Market Agent Guide

## What the Market Agent does

1. Fetches the current published mandi-price snapshot from the Government of India OGD / AGMARKNET API when `DATA_GOV_API_KEY` is configured.
2. Resolves a region to a state and district, then filters the online state snapshot to the requested crop and region.
3. If the requested district has no fresh quote for the crop, checks the configured neighbouring districts and compares all matching markets found there.
4. Records successful observations in `data/market/processed/market_live_history.csv` so newly published daily prices accumulate for forecasting.
5. Shows the observation date, API fetch time, quote age, min/max/modal prices, source, market comparison, quality/variety spread and forecast validation status.
6. Forecasts from a single selected mandi history. With sufficient history it compares Random Forest, naive and moving-average models using chronological validation. With less history it clearly labels the baseline as lower confidence.

## Configure the live mandi source

Add your own key to the private `.env` file in the project root:

```env
DATA_GOV_API_KEY=your_data_gov_api_key
MARKET_CACHE_TTL_SECONDS=300
MARKET_HISTORY_BACKFILL_DAYS=365
```

Restart AgriTwin after editing `.env`. Never paste the key into chat, screenshots, source files or a committed file. The API key is used on the backend, not exposed to the browser.

## Open the Market command centre

Open the AgriTwin home page and select **Market command centre** in the left navigation. Enter a crop name and region/district/mandi. The preset crop suggestions are only shortcuts; the commodity field accepts custom text, but a quote is returned only when the configured data source contains matching commodity records.

The dashboard refreshes its data check every five minutes while the tab is visible. Use **Refresh feed** to bypass the short cache and force a source request.

## Understand the data cadence

The OGD / AGMARKNET resource is a daily dataset. A five-minute UI refresh only checks whether the source has published a newer observation. It does not create a stream of trade executions. The official e-NAM dashboard is linked from the Market command centre for its public live trade, arrival and price dashboard. This release does not scrape or claim an unsupported e-NAM transaction API.

Prices are official *published modal wholesale quotes* in INR per quintal. The row for a mandi can contain different variety/grade observations. The dashboard uses the median of the latest reported variety/grade modal quotes for a mandi and shows the spread so unlike grades are not silently presented as identical. Check the precise variety and grade with the APMC before a sale.

## How the forecast works

- The forecast is calculated for the selected best-available mandi's daily price history, not averaged across unrelated mandis.
- With at least 70 distinct dates, the existing ML pipeline trains and compares Random Forest with naive and moving-average baselines using chronological validation.
- With fewer dates, AgriTwin chooses from simple walk-forward baselines and labels its confidence. With one or two observations it only shows a carry-forward reference and explicitly says it is not a reliable ML forecast.
- MAE and MAPE are validation errors, not promises that future errors will stay inside those values. Unexpected weather, policy, export, demand, arrivals and quality shocks are not fully modelled.

The bundled CSV is only a snapshot dated 2026-09-09. The first useful multi-day forecast requires historical records to be returned by the configured source or enough daily observations to accumulate in the local history store.

## Important pricing limitation

The highest gross modal price is not automatically the farmer's most profitable choice. A true net realization comparison needs quantity, transport, loading, commission, grading, storage, wastage and distance/time cost. The Market Agent labels its price comparison as gross and avoids claiming net profit when those costs are unknown.
