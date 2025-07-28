Of course\! Here is the content converted to Markdown.

# Places API (New) Client Library Examples 🔖

This page has examples of how to use the Places API (New) client libraries to call the following services:

  * Place Details (New)
  * Nearby Search (New)
  * Text Search (New)
  * Autocomplete (New)
  * Place Photos (New)

-----

## Install the client libraries

See [Places API (New) client libraries](https://developers.google.com/maps/documentation/places/web-service/client-library) for installation instructions.

-----

## Authentication

When you use client libraries, you use **Application Default Credentials (ADC)** to authenticate. For information about setting up ADC, see [Provide credentials for Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).

You can also use **API keys** to authenticate to the client libraries. For example:

```python
client = places_v1.PlacesAsyncClient(
  # Instantiates the Places client, passing the API key
  client_options={"api_key": "API_KEY"})
```

When you use API keys in your applications, ensure that they are kept secure during both storage and transmission. Publicly exposing your API keys can lead to unexpected charges on your account. For more information, see [Use API Keys with Places API](https://www.google.com/search?q=https://developers.google.com/maps/documentation/places/web-service/api-key).

For the examples on this page, you use Application Default Credentials.

-----

## Examples

### Place Details (New)

The following is an example of how to call **Place Details** using the client library.

```python
from google.maps import places_v1

async def place_details():
  client = places_v1.PlacesAsyncClient()
  # Build the request
  request = places_v1.GetPlaceRequest(
      name="places/ChIJaXQRs6lZwokRY6EFpJnhNNE",
  )
  # Set the field mask
  fieldMask = "formattedAddress,displayName"
  # Make the request
  response = await client.get_place(request=request, metadata=[("x-goog-fieldmask",fieldMask)])
  return response

print(await place_details())
```

Pass the **Place ID** using the `name` parameter. The **FieldMask** is passed when making the request.

### Nearby Search (New)

The following is an example of how to call **Nearby Search** using the client library.

```python
from google.maps import places_v1
from google.type import latlng_pb2

async def nearby_search():
  # Define the coordinates and radius
  lat = 51.516177
  lng = -0.127245
  radius_meters = 1000.0
  # Create the LatLng object for the center
  center_point = latlng_pb2.LatLng(latitude=lat, longitude=lng)
  # Create the circle
  circle_area = places_v1.types.Circle(
      center=center_point,
      radius=radius_meters
  )
  # Add the circle to the location restriction
  location_restriction = places_v1.SearchNearbyRequest.LocationRestriction(
      circle=circle_area
  )
  client = places_v1.PlacesAsyncClient()
  # Build the request
  request = places_v1.SearchNearbyRequest(
      location_restriction=location_restriction,
      included_types=["restaurant"]
  )
  # Set the field mask
  fieldMask = "places.formattedAddress,places.displayName"
  # Make the request
  response = await client.search_nearby(request=request, metadata=[("x-goog-fieldmask",fieldMask)])
  return response

print(await nearby_search())
```

Define a **Circle Location Restriction** by using latitude and longitude coordinates and radius. When building the example request, use the Location Restriction, alongside an **Included Types** filter of "restaurant". The **FieldMask** is passed when making the request.

### Text Search (New)

The following is an example of how to call **Text Search** using the client library.

```python
from google.maps import places_v1
from google.type import latlng_pb2

async def text_search():
  # Coordinates and radius for the location bias
  lat = 51.516177
  lng = -0.127245
  radius_meters = 1000.0
  # Create the LatLng object for the center
  center_point = latlng_pb2.LatLng(latitude=lat, longitude=lng)
  # Create the Circle object
  circle_area = places_v1.types.Circle(
      center=center_point,
      radius=radius_meters
  )
  # Create the location bias circle
  location_bias = places_v1.SearchTextRequest.LocationBias(
      circle=circle_area
  )
  # Define the search query and other parameters
  search_query = "restaurants with outdoor seating"
  min_place_rating = 4.0
  client = places_v1.PlacesAsyncClient()
  # Build the request
  request = places_v1.SearchTextRequest(
      text_query=search_query,
      location_bias=location_bias,
      min_rating=min_place_rating,
      open_now=True,
      price_levels=[
          places_v1.types.PriceLevel.PRICE_LEVEL_MODERATE,
          places_v1.types.PriceLevel.PRICE_LEVEL_EXPENSIVE
      ]
  )
  # Set the field mask
  fieldMask = "places.formattedAddress,places.displayName"
  # Make the request
  response = await client.search_text(request=request, metadata=[("x-goog-fieldmask",fieldMask)])
  return response

print(await text_search())
```

Define a **Location Bias** by building a Circle object using latitude and longitude coordinates and a radius. Pass the Circle object to the request object, alongside other API parameters:

  * **Text Query**
  * **Minimum Rating**
  * **Open Now**
  * **Price Levels**

The **FieldMask** is passed when making the request.

### Autocomplete

The following is an example of how to call **Autocomplete** using the client library.

```python
import uuid # For generating session tokens
from google.maps import places_v1
from google.type import latlng_pb2

async def autocomplete():
  bias_lat = 51.516177
  bias_lng = -0.127245
  bias_radius_meters = 5000.0
  # Create the LatLng object for the bias center
  bias_center_point = latlng_pb2.LatLng(latitude=bias_lat, longitude=bias_lng)
  # Create the Circle object using a dictionary
  bias_circle_dict = {
      "center": bias_center_point,
      "radius": bias_radius_meters
  }
  bias_circle_area = places_v1.types.Circle(bias_circle_dict)
  # Create the LocationBias object using a dictionary
  location_bias_dict = {
      "circle": bias_circle_area
  }
  location_bias = places_v1.types.AutocompletePlacesRequest.LocationBias(location_bias_dict)
  # The autocomplete text
  user_input = "Google Central St Giles"
  # Language and region
  language = "en-GB"
  region = "GB"
  # Generate a unique session token for this autocomplete session
  session_token = str(uuid.uuid4())
  client = places_v1.PlacesAsyncClient()
  # Build the request
  request = places_v1.AutocompletePlacesRequest(
      input=user_input,
      language_code=language,
      region_code=region,
      location_bias=location_bias,
      session_token=session_token,
  )
  response = await client.autocomplete_places(request=request)
  return response

print(await autocomplete())
```

Define a circle **Location Bias** using a dictionary. A UUID is generated to be used as a **Session Token**. These are passed to the request object, alongside other API parameters:

  * **Input**
  * **Language Code**
  * **Region Code**

**FieldMask** is not a required parameter for Autocomplete, so it has been omitted from this request.

### Place Photos (New)

The following is an example of how to call **Place Photo** using the client library.

```python
from google.maps import places_v1

async def place_photo():
  client = places_v1.PlacesAsyncClient()
  # Build the request
  request = places_v1.GetPlaceRequest(
      name="places/ChIJaXQRs6lZwokRY6EFpJnhNNE",
  )
  # Set the field mask
  fieldMask = "photos"
  # Make the request
  response = await client.get_place(request=request, metadata=[("x-goog-fieldmask",fieldMask)])
  if response.photos:  # Check if the photos list contains photos
      # Get the first photo name from the response
      first_photo_name = response.photos[0].name + "/media"
      # Build the request
      photo_request = places_v1.GetPhotoMediaRequest(
        name=first_photo_name,
        max_width_px=800,
      )
      photo_response = await client.get_photo_media(request=photo_request)
      return photo_response
  else:
      return("No photos were returned in the response.")

print(await place_photo())
```

First, call Place Details (New) to request the photos for a place. Place Details (New) responds with photo names. The first returned **photo name** from Place Details (New) is then used to call Place Photos (New). We also set a **maximum width** for the returned photo.