import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
import math
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim


def fetch_citibike_data():
    url = 'https://account.citibikenyc.com/bikesharefe-gql'
    headers = {
        'authority': 'account.citibikenyc.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,es;q=0.8',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'cookie': 'sessId=bbb48a25-e5ab-421d-9c2e-9fd2499ce3ffL1696534807; bfe-fpval=0; _ga=GA1.1.207701956.1696534808; OptanonConsent=isIABGlobal=false&datestamp=Fri+Oct+06+2023+08%3A37%3A33+GMT-0400+(Eastern+Daylight+Time)&version=6.13.0&landingPath=NotLandingPage&groups=1%3A1%2C2%3A0%2C3%3A0%2C4%3A0%2C0_251435%3A0%2C0_251434%3A0%2C0_251436%3A0%2C0_251431%3A0%2C0_251430%3A0%2C0_251433%3A0%2C0_251432%3A0&AwaitingReconsent=false; _ga_6HC3Z0YHLF=GS1.1.1696595709.2.1.1696595857.0.0.0',
        'dnt': '1',
        'origin': 'https://account.citibikenyc.com',
        'pragma': 'no-cache',
        'referer': 'https://account.citibikenyc.com/map',
        'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    }
    data = {
    "operationName": "GetSystemSupply",
    "variables": {
        "input": {
            "regionCode": "NYC",
            "rideablePageLimit": 10000
        }
    },
    "query": """
    query GetSystemSupply($input: SupplyInput) {
        supply(input: $input) {
            stations {
                stationId
                stationName
                location {
                    lat
                    lng
                    __typename
                }
                bikesAvailable
                bikeDocksAvailable
                ebikesAvailable
                scootersAvailable
                totalBikesAvailable
                totalRideablesAvailable
                isValet
                isOffline
                isLightweight
                notices {
                    ...NoticeFields
                    __typename
                }
                siteId
                ebikes {
                    batteryStatus {
                        distanceRemaining {
                            value
                            unit
                            __typename
                        }
                        percent
                        __typename
                    }
                    __typename
                }
                scooters {
                    batteryStatus {
                        distanceRemaining {
                            value
                            unit
                            __typename
                        }
                        percent
                        __typename
                    }
                    __typename
                }
                lastUpdatedMs
                __typename
            }
            rideables {
                rideableId
                location {
                    lat
                    lng
                    __typename
                }
                rideableType
                batteryStatus {
                    distanceRemaining {
                        value
                        unit
                        __typename
                    }
                    percent
                    __typename
                }
                __typename
            }
            notices {
                ...NoticeFields
                __typename
            }
            requestErrors {
                ...NoticeFields
                __typename
            }
            __typename
        }
    }
    
    fragment NoticeFields on Notice {
        localizedTitle
        localizedDescription
        url
        __typename
    }
    """
}
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def filter_stations_with_ebikes(response_data):
    stations = response_data['data']['supply']['stations']
    valid_stations = []

    for station in stations:
        valid_ebikes = [ebike for ebike in station['ebikes'] if ebike['batteryStatus']['distanceRemaining']['value'] >= 3]
        if valid_ebikes:
            station['valid_ebikes'] = valid_ebikes
            valid_stations.append(station)
            
    return valid_stations

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c

    return distance * 0.621371  # Convert km to miles



def main():
    st.title("E-bike Finder")
    
    # Default location (can be any default you want, or even the center of the city)
    lat, lng = 40.72834119151125, -73.94044153113401
    address = st.text_input("Enter an address:")
    if address:
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.geocode(address)
        if location:
            lat, lng = location.latitude, location.longitude
            st.write(f"Latitude: {lat}, Longitude: {lng}")
        else:
            st.write("Could not get the coordinates for this address. Please try a different address.")
    
    # User input for distance
    distance = st.select_slider("Select distance from current location (in miles)", options=[0.1,0.3,0.5,0.7,1.0])

    data = fetch_citibike_data()
    filtered_stations = filter_stations_with_ebikes(data)

    m = folium.Map(location=[lat, lng], zoom_start=14)
    
    # Add a marker for the user's location
    folium.Marker([lat, lng], tooltip="You are here", icon=folium.Icon(color="blue", icon="cloud")).add_to(m)

    for station in filtered_stations:
        station_lat = station['location']['lat']
        station_lon = station['location']['lng']
        distance_to_station = haversine_distance(lat, lng, station_lat, station_lon)

        if distance_to_station <= distance:
            ebike_info = ', '.join([f"{ebike['batteryStatus']['distanceRemaining']['value']} miles ({ebike['batteryStatus']['percent']}% battery)" for ebike in station['valid_ebikes']])
            folium.Marker([station_lat, station_lon], tooltip=f"Station: {station['stationName']}<br>E-Bike Ranges: {ebike_info}").add_to(m)

    folium_static(m)

if __name__ == "__main__":
    main()
