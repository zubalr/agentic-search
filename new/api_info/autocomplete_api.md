Here is the provided text converted into Markdown format.

-----

# Autocomplete (New)

**Release Notes**

Select platform: Android | iOS | JavaScript | Web Service
European Economic Area (EEA) developers

## Introduction

**Autocomplete (New)** is a web service that returns place predictions and query predictions in response to an HTTP request. In the request, specify a text search string and geographic bounds that control the search area.

Autocomplete (New) can match on full words and substrings of the input, resolving place names, addresses, and plus codes. Applications can therefore send queries as the user types, to provide on-the-fly place and query predictions.

The response from Autocomplete (New) can contain two types of predictions:

  * **Place predictions:** Places, such as businesses, addresses, and points of interest, based on the specified input text string and search area. Place predictions are returned by default.
  * **Query predictions:** Query strings matching the input text string and search area. Query predictions are not returned by default. Use the `includeQueryPredictions` request parameter to add query predictions to the response.

For example, you call Autocomplete (New) using as input a string that contains a partial user input, "Sicilian piz," with the search area limited to San Francisco, CA. The response then contains a list of **place predictions** that match the search string and search area, such as the restaurant named "Sicilian Pizza Kitchen," along with details about the place.

The returned **place predictions** are designed to be presented to the user to aid them in selecting the intended place. You can make a **Place Details (New)** request to get more information about any of the returned place predictions.

The response can also contain a list of **query predictions** that match the search string and search area, such as "Sicilian Pizza & Pasta." Each query prediction in the response includes the `text` field containing a recommended text search string. Use that string as an input to **Text Search (New)** to perform a more detailed search.

The APIs Explorer lets you make live requests so that you can get familiar with the API and the API options:

Try it\!

-----

## Autocomplete (New) requests

An Autocomplete (New) request is an HTTP POST request to a URL in the form:

```
https://places.googleapis.com/v1/places:autocomplete
```

Pass all parameters in the JSON request body or in headers as part of the POST request. For example:

```
curl -X POST -d '{
  "input": "pizza",
  "locationBias": {
    "circle": {
      "center": {
        "latitude": 37.7937,
        "longitude": -122.3965
      },
      "radius": 500.0
    }
  }
}' \
-H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
https://places.googleapis.com/v1/places:autocomplete
```

### Supported parameters

| Parameter | Description |
| :--- | :--- |
| **`input`**\* | Text string to search on (full words, substrings, place names, addresses, plus codes). |
| `FieldMask` (HTTP Header) | Comma-separated list specifying which fields to return in the response. |
| `includedPrimaryTypes` | Restricts results to places matching one of up to five specified primary types. |
| `includePureServiceAreaBusinesses` | If true, includes businesses without a physical location (service area businesses). Defaults to false. |
| `includeQueryPredictions` | If true, includes both place and query predictions in the response. Defaults to false. |
| `includedRegionCodes` | Array of up to 15 two-character country codes to restrict results to. |
| `inputOffset` | Zero-based Unicode char offset of cursor position within input string, influencing predictions. Defaults to input length. |
| `languageCode` | Preferred language (IETF BCP-47 code) for results. Defaults to Accept-Language header or 'en'. |
| `locationBias` | Specifies an area (circle or rectangle) to bias search results towards, allowing results outside the area. Cannot be used with locationRestriction. |
| `locationRestriction` | Specifies an area (circle or rectangle) to restrict search results within. Results outside this area are excluded. Cannot be used with locationBias. |
| `origin` | Origin point (lat, long) used to calculate straight-line distance (distanceMeters) to predicted destinations. |
| `regionCode` | Region code used to format the response and bias suggestions (e.g., 'uk', 'fr'). |
| `sessionToken` | User-generated string to group Autocomplete calls into a session for billing purposes. |

\* Denotes required field.

-----

## About the response

Autocomplete (New) returns a JSON object as a response. In the response:

  * The `suggestions` array contains all of the predicted places and queries in order based on their perceived relevance. Each place is represented by a `placePrediction` field and each query is represented by a `queryPrediction` field.
  * A `placePrediction` field contains detailed information about a single place prediction, including the place ID, and text description.
  * A `queryPrediction` field contains detailed information about a single query prediction.

**Note:** Autocomplete (New) returns five total predictions, either as `placePredictions`, `queryPredictions`, or a combination, depending on the request. If the request does not set `includeQueryPredictions`, the response includes up to five `placePredictions`. If the request sets `includeQueryPredictions`, the response includes up to five predictions in a combination of `placePredictions` and `queryPredictions`.

The complete JSON object is in the form:

```json
{
  "suggestions": [
    {
      "placePrediction": {
        "place": "places/ChIJ5YQQf1GHhYARPKG7WLIaOko",
        "placeId": "ChIJ5YQQf1GHhYARPKG7WLIaOko",
        "text": {
          "text": "Amoeba Music, Haight Street, San Francisco, CA, USA",
          "matches": [
            {
              "endOffset": 6
            }]
        },
      ...
    },
    {
      "queryPrediction": {
        "text": {
          "text": "Amoeba Music",
          "matches": [
            {
              "endOffset": 6
            }]
        },
        ...
    }
  ...]
}
```

-----

## Required parameters

### `input`

The text string on which to search. Specify full words and substrings, place names, addresses, and plus codes. The Autocomplete (New) service returns candidate matches based on this string and orders results based on their perceived relevance.

-----

## Optional parameters

### `FieldMask`

Specify the list of fields to return in the response by creating a **response field mask**. Pass the response field mask to the method by using the HTTP header `X-Goog-FieldMask`.

Specify a comma-separated list of suggestion fields to return. For example, to retrieve the `suggestions.placePrediction.text.text` and `suggestions.queryPrediction.text.text` of the suggestion.

```
X-Goog-FieldMask: suggestions.placePrediction.text.text,suggestions.queryPrediction.text.text
```

**Note:** Spaces are not allowed anywhere in the field list.

Use `*` to retrieve all fields.

```
X-Goog-FieldMask: *
```

### `includedPrimaryTypes`

A place can only have a **single primary type** from types listed in **Table A** or **Table B**. For example, the primary type might be "mexican\_restaurant" or "steak\_house."

By default, the API returns all places based on the `input` parameter, regardless of the primary type value associated with the place. Restrict results to be of a certain primary type or primary types by passing the `includedPrimaryTypes` parameter.

Use this parameter to specify up to five type values from **Table A** or **Table B**. A place must match one of the specified primary type values to be included in the response.

This parameter may also include, instead, one of `(regions)` or `(cities)`. The `(regions)` type collection filters for areas or divisions, such as neighborhoods and postal codes. The `(cities)` type collection filters for places that Google identifies as a city.

The request is rejected with an `INVALID_REQUEST` error if:

  * More than five types are specified.
  * Any type is specified in addition to `(cities)` or `(regions)`.
  * Any unrecognized types are specified.

**Note:** The `includedPrimaryTypes` parameter only works on the primary type of the place, not all types associated with the place. Although every place has a primary type, not every primary type is supported by Places API (New). Supported types include those listed in **Table A** or **Table B**.

### `includePureServiceAreaBusinesses`

If set to `true`, the response includes businesses that visit or deliver to customers directly, but don't have a physical business location. If set to `false`, the API returns only businesses with a physical business location.

### `includeQueryPredictions`

If `true`, the response includes both place and query predictions. The default value is `false`, meaning the response only includes place predictions.

### `includedRegionCodes`

Only include results from the list of specified regions, specified as an array of up to 15 **ccTLD ("top-level domain")** two-character values. If omitted, no restrictions are applied to the response. For example, to limit the regions to Germany and France:

```json
"includedRegionCodes": ["de", "fr"]
```

If you specify both `locationRestriction` and `includedRegionCodes`, the results are located in the area of intersection of the two settings.

**Note:** If you receive unexpected results with a country code, verify that you are using a code which includes the countries, dependent territories, and special areas of geographical interest you intend. You can find code information at Wikipedia: List of ISO 3166 country codes or the ISO Online Browse Platform.

### `inputOffset`

The zero-based Unicode character offset indicating the cursor position in `input`. The cursor position can influence what predictions are returned. If empty, it defaults to the length of `input`.

**Note:** In the initial Restricted Preview release, this property was called `predictionTermOffset`.

### `languageCode`

The preferred language in which to return results. The results might be in mixed languages if the language used in `input` is different from the value specified by `languageCode`, or if the returned place does not have a translation from the local language to `languageCode`.

You must use **IETF BCP-47 language codes** to specify the preferred language.

If `languageCode` is not supplied, the API uses the value specified in the `Accept-Language` header. If neither is specified, the default is `en`. If you specify an invalid language code, the API returns an `INVALID_ARGUMENT` error.

The preferred language has a small influence on the set of results that the API chooses to return, and the order in which they are returned. This also affects the API's ability to correct spelling errors.

The API attempts to provide a street address that is readable for both the user and local population, while at the same time reflecting the user input. Place predictions are formatted differently depending on the user input in each request.Matching terms in the `input` parameter are chosen first, using names aligned with the language preference indicated by the `languageCode` parameter when available, while otherwise using names that best match the user input.

Street addresses are formatted in the local language, in a script readable by the user when possible, only after matching terms have been picked to match the terms in the `input` parameter.

All other addresses are returned in the preferred language, after matching terms have been chosen to match the terms in the `input` parameter. If a name is not available in the preferred language, the API uses the closest match.

### `locationBias` or `locationRestriction`

You can specify `locationBias` or `locationRestriction`, but not both, to define the search area. Think of `locationRestriction` as specifying the region which the results must be within, and `locationBias` as specifying the region that the results must be near but can be outside of the area.

**Note:** If you omit both `locationBias` and `locationRestriction`, Autocomplete (New) uses IP biasing by default. With IP biasing, Autocomplete (New) uses the IP address of the device to bias the results.

#### `locationBias`

Specifies an area to search. This location serves as a bias which means results around the specified location can be returned, including results outside the specified area.

#### `locationRestriction`

Specifies an area to search. Results outside the specified area are not returned.

Specify the `locationBias` or `locationRestriction` region as a **rectangular Viewport** or as a **circle**.

A circle is defined by center point and radius in meters. The radius must be between 0.0 and 50000.0, inclusive. The default value is 0.0. For `locationRestriction`, you must set the radius to a value greater than 0.0. Otherwise, the request returns no results.

For example:

```json
"locationBias": {  "circle": {    "center": {      "latitude": 37.7937,      "longitude": -122.3965    },    "radius": 500.0  }}
```

A rectangle is a latitude-longitude viewport, represented as two diagonally opposite `low` and high points. A viewport is considered a closed region, meaning it includes its boundary. The latitude bounds must range between -90 to 90 degrees inclusive, and the longitude bounds must range between -180 to 180 degrees inclusive:

  * If `low` = `high`, the viewport consists of that single point.
  * If `low.longitude` \> `high.longitude`, the longitude range is inverted (the viewport crosses the 180 degree longitude line).
  * If `low.longitude` = -180 degrees and `high.longitude` = 180 degrees, the viewport includes all longitudes.
  * If `low.longitude` = 180 degrees and `high.longitude` = -180 degrees, the longitude range is empty.

Both `low` and `high` must be populated, and the represented box cannot be empty. An empty viewport results in an error.

For example, this viewport fully encloses New York City:

```json
"locationBias": {  "rectangle": {    "low": {      "latitude": 40.477398,      "longitude": -74.259087    },    "high": {      "latitude": 40.91618,      "longitude": -73.70018    }  }}
```

### `origin`

The origin point from which to calculate straight-line distance to the destination (returned as `distanceMeters`). If this value is omitted, straight-line distance will not be returned. Must be specified as latitude and longitude coordinates:

```json
"origin": {    "latitude": 40.477398,    "longitude": -74.259087}
```

### `regionCode`

The region code used to format the response, specified as a **ccTLD ("top-level domain")** two-character value. Most ccTLD codes are identical to ISO 3166-1 codes, with some notable exceptions. For example, the United Kingdom's ccTLD is "uk" (.co.uk) while its ISO 3166-1 code is "gb" (technically for the entity of "The United Kingdom of Great Britain and Northern Ireland").

Suggestions are also biased based on region codes. Google recommends setting the `regionCode` according to the user's regional preference.

If you specify an invalid region code, the API returns an `INVALID_ARGUMENT` error. The parameter can affect results based on applicable law.

### `sessionToken`

Session tokens are user-generated strings that track Autocomplete (New) calls as "sessions." Autocomplete (New) uses session tokens to group the query and selection phases of a user autocomplete search into a discrete session for billing purposes. For more information, see [Session tokens](https://developers.google.com/maps/documentation/places/web-service/session-tokens).

-----

## Choose parameters to bias results

Autocomplete (New) parameters can influence search results differently. The following table provides recommendations for parameter usage based on the intended outcome.

| Parameter | Usage recommendation |
| :--- | :--- |
| **`regionCode`** | Set according to user's regional preference. |
| **`includedRegionCodes`** | Set to limit results to the list of specified regions. |
| **`locationBias`** | Use when results are preferred **in or around a region.** If applicable, define the region as the viewport of the map the user is looking at. |
| **`locationRestriction`** | Use **only** when results outside of a region **shouldn't** be returned. |
| **`origin`** | Use when a **straight-line distance** to each prediction is intended. |

**Note:** The distance won't be available for every prediction. See **Distance missing from response**.

-----

## Autocomplete (New) examples

### Restrict search to an area using `locationRestriction`

**Note:** Autocomplete (New) uses IP biasing by default to control the search area. With IP biasing, Autocomplete (New) uses the IP address of the device to bias the results. You can optionally use `locationRestriction` or `locationBias`, but not both, to specify an area to search.

`locationRestriction` specifies the area to search. Results outside the specified area are not returned. In the following example, you use `locationRestriction` to limit the request to a **circle** 5000 meters in radius centered on San Francisco:

```
curl -X POST -d '{
  "input": "Art museum",
  "locationRestriction": {
    "circle": {
      "center": {
        "latitude": 37.7749,
        "longitude": -122.4194
      },
      "radius": 5000.0
    }
  }
}' \
-H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
https://places.googleapis.com/v1/places:autocomplete
```

All results from within the specified areas are contained in the `suggestions` array:

```json
{    "suggestions": [      {        "placePrediction": {          "place": "places/ChIJkQQVTZqAhYARHxPt2iJkm1Q",          "placeId": "ChIJkQQVTZqAhYARHxPt2iJkm1Q",          "text": {            "text": "Asian Art Museum, Larkin Street, San Francisco, CA, USA",            "matches": [              {                "startOffset": 6,                "endOffset": 16              }            ]          },          "structuredFormat": {            "mainText": {              "text": "Asian Art Museum",              "matches": [                {                  "startOffset": 6,                  "endOffset": 16                }              ]            },            "secondaryText": {              "text": "Larkin Street, San Francisco, CA, USA"            }          },          "types": [            "establishment",            "museum",            "point_of_interest"          ]        }      },      {        "placePrediction": {          "place": "places/ChIJI7NivpmAhYARSuRPlbbn_2w",          "placeId": "ChIJI7NivpmAhYARSuRPlbbn_2w",          "text": {            "text": "de Young Museum, Hagiwara Tea Garden Drive, San Francisco, CA, USA",            "matches": [              {                "endOffset": 15              }            ]          },          "structuredFormat": {            "mainText": {              "text": "de Young Museum",              "matches": [                {                  "endOffset": 15                }              ]            },            "secondaryText": {              "text": "Hagiwara Tea Garden Drive, San Francisco, CA, USA"            }          },          "types": [            "establishment",            "point_of_interest",            "tourist_attraction",            "museum"          ]        }      },      /.../    ]  }
```

You can also use `locationRestriction` to restrict searches to a **rectangular Viewport**. The following example limits the request to downtown San Francisco:

```
  curl -X POST -d '{
    "input": "Art museum",
    "locationRestriction": {
      "rectangle": {
        "low": {
          "latitude": 37.7751,
          "longitude": -122.4219
        },
        "high": {
          "latitude": 37.7955,
          "longitude": -122.3937
        }
      }
    }
  }' \
  -H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
  https://places.googleapis.com/v1/places:autocomplete
```

Results are contained in the `suggestions` array:

```json
  {    "suggestions": [      {        "placePrediction": {          "place": "places/ChIJkQQVTZqAhYARHxPt2iJkm1Q",          "placeId": "ChIJkQQVTZqAhYARHxPt2iJkm1Q",          "text": {            "text": "Asian Art Museum, Larkin Street, San Francisco, CA, USA",            "matches": [              {                "startOffset": 6,                "endOffset": 16              }            ]          },          "structuredFormat": {            "mainText": {              "text": "Asian Art Museum",              "matches": [                {                  "startOffset": 6,                  "endOffset": 16                }              ]            },            "secondaryText": {              "text": "Larkin Street, San Francisco, CA, USA"            }          },          "types": [            "point_of_interest",            "museum",            "establishment"          ]        }      },      {        "placePrediction": {          "place": "places/ChIJyQNK-4SAhYARO2DZaJleWRc",          "placeId": "ChIJyQNK-4SAhYARO2DZaJleWRc",          "text": {            "text": "International Art Museum of America, Market Street, San Francisco, CA, USA",            "matches": [              {                "startOffset": 14,                "endOffset": 24              }            ]          },          "structuredFormat": {            "mainText": {              "text": "International Art Museum of America",              "matches": [                {                  "startOffset": 14,                  "endOffset": 24                }              ]            },            "secondaryText": {              "text": "Market Street, San Francisco, CA, USA"            }          },          "types": [            "museum",            "point_of_interest",            "tourist_attraction",            "art_gallery",            "establishment"          ]        }      }    ]  }
```

### Bias search to an area using `locationBias`

With `locationBias`, the location serves as a bias which means results around the specified location can be returned, including results outside the specified area. In the following example, you bias the request to downtown San Francisco:

```
curl -X POST -d '{
  "input": "Amoeba",
  "locationBias": {
    "circle": {
      "center": {
        "latitude": 37.7749,
        "longitude": -122.4194
      },
      "radius": 5000.0
    }
  }
}' \
-H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
https://places.googleapis.com/v1/places:autocomplete
```

The results now contain many more items, including results outside of the 5000 meter radius:

```json
{  "suggestions": [    {      "placePrediction": {        "place": "places/ChIJ5YQQf1GHhYARPKG7WLIaOko",        "placeId": "ChIJ5YQQf1GHhYARPKG7WLIaOko",        "text": {          "text": "Amoeba Music, Haight Street, San Francisco, CA, USA",          "matches": [            {              "endOffset": 6            }          ]        },        "structuredFormat": {          "mainText": {            "text": "Amoeba Music",            "matches": [              {                "endOffset": 6              }            ]          },          "secondaryText": {            "text": "Haight Street, San Francisco, CA, USA"          }        },        "types": [          "electronics_store",          "point_of_interest",          "store",          "establishment",          "home_goods_store"        ]      }    },    {      "placePrediction": {        "place": "places/ChIJr7uwwy58hYARBY-e7-QVwqw",        "placeId": "ChIJr7uwwy58hYARBY-e7-QVwqw",        "text": {          "text": "Amoeba Music, Telegraph Avenue, Berkeley, CA, USA",          "matches": [            {              "endOffset": 6            }          ]        },        "structuredFormat": {          "mainText": {            "text": "Amoeba Music",            "matches": [              {                "endOffset": 6              }            ]          },          "secondaryText": {            "text": "Telegraph Avenue, Berkeley, CA, USA"          }        },        "types": [          "electronics_store",          "point_of_interest",          "establishment",          "home_goods_store",          "store"        ]      }    },    ...  ]}
```

You can also use `locationBias` to restrict searches to a **rectangular Viewport**. The following example limits the request to downtown San Francisco:

```
  curl -X POST -d '{
    "input": "Amoeba",
    "locationBias": {
      "rectangle": {
        "low": {
          "latitude": 37.7751,
          "longitude": -122.4219
        },
        "high": {
          "latitude": 37.7955,
          "longitude": -122.3937
        }
      }
    }
  }' \
  -H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
  https://places.googleapis.com/v1/places:autocomplete
```

Although search results within the rectangular viewport appear in the response, some results are outside of the defined boundaries, due to biasing. Results are also contained within the `suggestions` array:

```json
  {    "suggestions": [      {        "placePrediction": {          "place": "places/ChIJ5YQQf1GHhYARPKG7WLIaOko",          "placeId": "ChIJ5YQQf1GHhYARPKG7WLIaOko",          "text": {            "text": "Amoeba Music, Haight Street, San Francisco, CA, USA",            "matches": [              {                "endOffset": 6              }            ]          },          "structuredFormat": {            "mainText": {              "text": "Amoeba Music",              "matches": [                {                  "endOffset": 6                }              ]            },            "secondaryText": {              "text": "Haight Street, San Francisco, CA, USA"            }          },          "types": [            "point_of_interest",            "store",            "establishment"          ]        }      },      {        "placePrediction": {          "place": "places/ChIJr7uwwy58hYARBY-e7-QVwqw",          "placeId": "ChIJr7uwwy58hYARBY-e7-QVwqw",          "text": {            "text": "Amoeba Music, Telegraph Avenue, Berkeley, CA, USA",            "matches": [              {                "endOffset": 6              }            ]          },          "structuredFormat": {            "mainText": {              "text": "Amoeba Music",              "matches": [                {                  "endOffset": 6                }              ]            },            "secondaryText": {              "text": "Telegraph Avenue, Berkeley, CA, USA"            }          },          "types": [            "point_of_interest",            "store",            "establishment"          ]        }      },      {        "placePrediction": {          "place": "places/ChIJRdmfADq_woARYaVhnfQSUTI",          "placeId": "ChIJRdmfADq_woARYaVhnfQSUTI",          "text": {            "text": "Amoeba Music, Hollywood Boulevard, Los Angeles, CA, USA",            "matches": [              {                "endOffset": 6              }            ]          },          "structuredFormat": {            "mainText": {              "text": "Amoeba Music",              "matches": [                {                  "endOffset": 6                }              ]            },            "secondaryText": {              "text": "Hollywood Boulevard, Los Angeles, CA, USA"            }          },          "types": [            "point_of_interest",            "store",            "establishment"          ]        }      },    /.../    ]  }
```

### Use `includedPrimaryTypes`

Use the `includedPrimaryTypes` parameter to specify up to five type values from **Table A**, **Table B**, or only `(regions)`, or only `(cities)`. A place must match one of the specified primary type values to be included in the response.

In the following example, you specify an `input` string of "Soccer" and use the `includedPrimaryTypes` parameter to restrict results to establishments of type `"sporting_goods_store"`:

```
curl -X POST -d '{
  "input": "Soccer",
  "includedPrimaryTypes": ["sporting_goods_store"],
  "locationBias": {
    "circle": {
      "center": {
        "latitude": 37.7749,
        "longitude": -122.4194
      },
      "radius": 500.0
    }
  }
}' \
-H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
https://places.googleapis.com/v1/places:autocomplete
```

If you omit the `includedPrimaryTypes` parameter, then the results can include establishments of a type that you do not want, such as `"athletic_field"`.

### Request query predictions

Query predictions are not returned by default. Use the `includeQueryPredictions` request parameter to add query predictions to the response. For example:

```
curl -X POST -d '{
  "input": "Amoeba",
  "includeQueryPredictions": true,
  "locationBias": {
    "circle": {
      "center": {
        "latitude": 37.7749,
        "longitude": -122.4194
      },
      "radius": 5000.0
    }
  }
}' \
-H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
https://places.googleapis.com/v1/places:autocomplete
```

The `suggestions` array now contains both place predictions and query predictions as shown above in **About the response**. Each query prediction includes the `text` field containing a recommended text search string. You can make a **Text Search (New)** request to get more information about any of the returned query predictions.

**Note:** Query predictions are not returned when the `includedRegionCodes` parameter is set.

### Use `origin`

In this example, include `origin` in the request as latitude and longitude coordinates. When you include `origin`, Autocomplete (New) includes the `distanceMeters` field in the response which contains the straight-line distance from the `origin` to the destination. This example sets the origin to the center of San Francisco:

```
curl -X POST -d '{
  "input": "Amoeba",
  "origin": {
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "locationRestriction": {
    "circle": {
      "center": {
        "latitude": 37.7749,
        "longitude": -122.4194
      },
      "radius": 5000.0
    }
  }
}' \
-H 'Content-Type: application/json' -H "X-Goog-Api-Key: API_KEY" \
https://places.googleapis.com/v1/places:autocomplete
```

The response now includes `distanceMeters`:

```json
{  "suggestions": [    {      "placePrediction": {        "place": "places/ChIJ5YQQf1GHhYARPKG7WLIaOko",        "placeId": "ChIJ5YQQf1GHhYARPKG7WLIaOko",        "text": {          "text": "Amoeba Music, Haight Street, San Francisco, CA, USA",          "matches": [            {              "endOffset": 6            }          ]        },        "structuredFormat": {          "mainText": {            "text": "Amoeba Music",            "matches": [              {                "endOffset": 6                }              ]            },            "secondaryText": {              "text": "Haight Street, San Francisco, CA, USA"            }          },        "types": [          "home_goods_store",          "establishment",          "point_of_interest",          "store",          "electronics_store"        ],        "distanceMeters": 3012      }    }  ]}
```

### Distance missing from response

In certain cases, `distanceMeters` is missing from the response body, even when `origin` is included in the request. This may happen in the following scenarios:

  * `distanceMeters` is not included for **route** predictions.
  * `distanceMeters` is not included when its value is **0**, which is the case for predictions that are less than 1 meter away from the provided `origin` location.

Client libraries attempting to read the `distanceMeters` field out of a parsed object will return a field with value `0`. To avoid misleading users, **don't** display a zero distance to users.