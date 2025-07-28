
---

# Google Maps Platform – Places API – Text Search (New)

**Release Date:** Last updated **2025‑07‑23 UTC**
**Platform:** Web Services (HTTP/REST)
**Scope:** European Economic Area (EEA) noted

---

## 🔎 Overview

`Text Search (New)` lets you search for places using a free-text query (e.g., `"pizza in New York"`, `"shoe stores near Ottawa"`, `"123 Main Street"`). Results are returned in a list of places matching the query and any specified location bias.

You can fine-tune results using **required** and **optional parameters**.
The **APIs Explorer** enables live testing of requests.

---

## ⚙️ Endpoint & Request Format

### Endpoint

```
POST https://places.googleapis.com/v1/places:searchText
```

You can pass all parameters either in:

* **Request body** (JSON)
* **Headers** (for things like API key and FieldMask)

---

### Example `curl`

```bash
curl -X POST -d '{
  "textQuery": "Spicy Vegetarian Food in Sydney, Australia"
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.displayName,places.formattedAddress,places.priceLevel' \
'https://places.googleapis.com/v1/places:searchText'
```

Replace `API_KEY` with your API key.

---

## 📥 Response Structure

```json
{
  "places": [
    { /* Place object according to requested FieldMask */ }
  ]
}
```

* `places` is an array of `Place` objects.
* You must include a `FieldMask`; otherwise, the API returns an error.
* **Max results per query:** 60 (across all pages).

---

## 🎯 Required Parameter: FieldMask

* **Purpose:** Specify which `Place` fields to return.
* Passed via `X-Goog-FieldMask` header (or `fields` URL param).
* No default; omission → **error**.
* Format: comma-separated list (no spaces).

```http
X-Goog-FieldMask: places.displayName,places.formattedAddress
```

* To return **all fields**, use:

```http
X-Goog-FieldMask: *
```

*(Wildcard use discouraged in production due to data volume.)*

### Field Categories and Pricing Tiers

| Tier                        | Fields                                                                                                                        |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Essentials** (ID)         | `places.attributions`, `places.id`, `places.name*`, `nextPageToken`                                                           |
| **Pro**                     | `places.accessibilityOptions`, `.addressComponents`, `.addressDescriptor*`, `.formattedAddress`, `.location`, `.photos`, etc. |
| **Enterprise**              | `.currentOpeningHours`, `.internationalPhoneNumber`, `.rating`, `.websiteUri`, `.userRatingCount`, etc.                       |
| **Enterprise + Atmosphere** | Adds rich access: `.reviews`, `.menuForChildren`, `.parkingOptions`, `.outdoorSeating`, `.servesWine`, etc.                   |

\* Note: `.addressDescriptor` experimental outside India; `.googleMapsLinks` is pre-GA and free during preview.

---

## ✏️ Request Body Structure

### Basic

```json
{
  "textQuery": "your search text"
}
```

### Full JSON Schema

```json
{
  "textQuery":        "string",              // e.g., "pizza in New York"
  "includedType":     "string",              // e.g., "bar", "pharmacy"
  "includePureServiceAreaBusinesses": true,  // include non-physical businesses
  "languageCode":     "string",              // e.g., "en", "fr" (CLDR code)
  "locationBias": {
    "circle": {
      "center": {"latitude": 0, "longitude": 0},
      "radius": 0.0
    },
    "rectangle": {
      "low": {"latitude": 0, "longitude": 0},
      "high": {"latitude": 0, "longitude": 0}
    }
  },
  "locationRestriction": { /* same schema as rectangle above */ },
  "maxResultCount":   "integer (1–20)",     // deprecated, use pageSize
  "evOptions": {
    "connectorTypes":        ["type1", ...],
    "minimumChargingRateKw": "number"
  },
  "minRating":         "0.0–5.0 (step 0.5)",
  "openNow":           true|false,
  "pageSize":          "integer (1–20)",
  "pageToken":         "string",
  "priceLevels":       ["PRICE_LEVEL_INEXPENSIVE", "..."],
  "rankPreference":    "RELEVANCE"|"DISTANCE",
  "regionCode":        "string (CLDR)",
  "strictTypeFiltering": true|false
}
```

---

## 📌 Optional Parameters

* **includedType**: filter results by place type (single allowed)
* **includePureServiceAreaBusinesses**: include non-physical service businesses
* **languageCode**: CLDR code; default is `en`
* **locationBias**: bias results towards a circle or rectangle region
* **locationRestriction**: restrict results strictly within a rectangle
* **pageSize**: results per page (1–20)
* **pageToken**: token from previous response for pagination
* **priceLevels**: filter by pricing tier (food/drink/services/shopping)
* **evOptions**: filter EV charging station results by connector type & capacity
* **minRating**: filter by average user rating (0.0–5.0)
* **openNow**: show only currently open places
* **rankPreference**: choose `RELEVANCE` or `DISTANCE`
* **regionCode**: for formatting and result bias
* **strictTypeFiltering**: mandate `includedType` vs. soft filter

> Deprecated: `maxResultCount` — use `pageSize`

---

## 🧭 Common Use Cases: Examples

### 1. Basic Search

```bash
curl -X POST -d '{
  "textQuery":"Spicy Vegetarian Food in Sydney, Australia"
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.displayName,places.formattedAddress' \
'https://places.googleapis.com/v1/places:searchText'
```

### 2. Add `types` & `websiteUri`

Add to FieldMask:

```text
places.types,places.websiteUri
```

Response includes type list & website.

---

### 3. Filter by Price Level

```bash
curl -X POST -d '{
  "textQuery": "Spicy Vegetarian Food in Sydney, Australia",
  "priceLevels": ["PRICE_LEVEL_INEXPENSIVE","PRICE_LEVEL_MODERATE"]
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.displayName,places.formattedAddress,places.priceLevel' \
'https://places.googleapis.com/v1/places:searchText'
```

---

### 4. Location Restriction

```bash
curl -X POST -d '{
  "textQuery": "vegetarian food",
  "pageSize": 10,
  "locationRestriction": {
    "rectangle": {
      "low": {"latitude":40.477398,"longitude":-74.259087},
      "high":{"latitude":40.91618,"longitude":-73.70018}
    }
  }
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.id,places.formattedAddress' \
'https://places.googleapis.com/v1/places:searchText'
```

### 5. Location Bias

```bash
curl -X POST -d '{
  "textQuery": "vegetarian food",
  "openNow": true,
  "pageSize": 10,
  "locationBias": {
    "circle": {
      "center":{"latitude":37.7937,"longitude":-122.3965},
      "radius":500.0
    }
  }
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.displayName,places.formattedAddress' \
'https://places.googleapis.com/v1/places:searchText'
```

---

### 6. EV Chargers Filter

```bash
curl -X POST -d '{
  "textQuery": "EV Charging Station Mountain View",
  "pageSize": 4,
  "evOptions": {
    "minimumChargingRateKw": 10,
    "connectorTypes": ["EV_CONNECTOR_TYPE_J1772","EV_CONNECTOR_TYPE_TESLA"]
  }
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.displayName,places.evChargeOptions' \
'https://places.googleapis.com/v1/places:searchText'
```

---

### 7. Pure Service-Area Businesses

```bash
curl -X POST -d '{
  "textQuery": "plumber San Francisco",
  "includePureServiceAreaBusinesses": true
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.displayName,places.formattedAddress' \
'https://places.googleapis.com/v1/places:searchText'
```

---

### 8. Pagination (Next Page)

```bash
curl -X POST -d '{
  "textQuery":"pizza in New York",
  "pageSize":5,
  "pageToken":"NEXT_PAGE_TOKEN"
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.id,nextPageToken' \
'https://places.googleapis.com/v1/places:searchText'
```

*Note: Other parameters must match exactly to avoid `INVALID_ARGUMENT`.*

---

### 9. Address Descriptors (Relational Info)

```bash
curl -X POST -d '{
  "textQuery":"clothes",
  "maxResultCount":5,
  "locationBias":{
    "circle":{"center":{"latitude":37.321328,"longitude":-121.946275}}
  },
  "rankPreference":"RANK_PREFERENCE_UNSPECIFIED"
}' \
-H 'Content-Type: application/json' \
-H 'X-Goog-Api-Key: API_KEY' \
-H 'X-Goog-FieldMask: places.displayName,places.addressDescriptor' \
https://places.googleapis.com/v1/places:searchText
```

**Response** includes `landmarks` and `areas`, with names, distances, and containment data.

---

## 🔧 Getting Started (APIs Explorer)

1. Click the API icon on the right to open the explorer.
2. Edit request parameters if needed.
3. Click **Execute** and authorize.
4. (Optional) Expand to fullscreen.

---

## 📝 Licensing & Support

* **Content license:** Creative Commons Attribution 4.0
* **Code samples:** Apache 2.0 License
* **Support channels:** Stack Overflow (`google-maps`), GitHub, Discord, Issue Tracker

---

## 🌐 Related Pages

* FAQ
* API Picker
* Place ID Finder

## 📚 Documentation Links

* Android / iOS / Web / Web Services
* Pricing & Plans
* Sales & Support
* Terms & Privacy

---

