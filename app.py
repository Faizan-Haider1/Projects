import os
import json
from datetime import date

import streamlit as st
from groq import Groq


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="TravelGenie",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background:
            linear-gradient(rgba(4, 18, 38, 0.88), rgba(4, 18, 38, 0.94)),
            url("https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=2200&q=80");
        background-size: cover;
        background-attachment: fixed;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 2rem;
        border-radius: 24px;
        background: rgba(7, 30, 55, 0.80);
        border: 1px solid rgba(255,255,255,0.14);
        box-shadow: 0 10px 40px rgba(0,0,0,0.25);
        margin-bottom: 1.5rem;
    }

    .hero h1 {
        font-size: 3.2rem;
        margin-bottom: 0.2rem;
    }

    .hero p {
        font-size: 1.15rem;
        color: #dbeafe;
    }

    .card {
        background: rgba(8, 28, 50, 0.88);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 18px;
        padding: 1.1rem;
        margin-bottom: 0.9rem;
    }

    .price {
        font-size: 1.35rem;
        font-weight: 700;
    }

    .muted {
        color: #b9c8d9;
    }

    .badge {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.18);
        color: #bfdbfe;
        font-size: 0.8rem;
        margin-right: 0.35rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Demo inventory
# IMPORTANT:
# This is sample inventory for the hackathon.
# It is NOT live booking data.
# -----------------------------
FLIGHTS = [
    {
        "id": "F001",
        "airline": "PIA",
        "price": 25000,
        "departure_time": "08:00",
        "arrival_time": "10:30",
        "from": "Karachi",
        "to": "Islamabad",
        "duration": "2h 30m",
        "stops": 0,
    },
    {
        "id": "F002",
        "airline": "Airblue",
        "price": 22000,
        "departure_time": "11:00",
        "arrival_time": "13:15",
        "from": "Karachi",
        "to": "Islamabad",
        "duration": "2h 15m",
        "stops": 0,
    },
    {
        "id": "F003",
        "airline": "AirSial",
        "price": 28000,
        "departure_time": "18:30",
        "arrival_time": "20:50",
        "from": "Karachi",
        "to": "Islamabad",
        "duration": "2h 20m",
        "stops": 0,
    },
    {
        "id": "F004",
        "airline": "PIA",
        "price": 18000,
        "departure_time": "09:00",
        "arrival_time": "10:05",
        "from": "Lahore",
        "to": "Islamabad",
        "duration": "1h 05m",
        "stops": 0,
    },
    {
        "id": "F005",
        "airline": "Airblue",
        "price": 20000,
        "departure_time": "15:00",
        "arrival_time": "16:10",
        "from": "Lahore",
        "to": "Islamabad",
        "duration": "1h 10m",
        "stops": 0,
    },
    {
        "id": "F006",
        "airline": "Fly Jinnah",
        "price": 19000,
        "departure_time": "19:30",
        "arrival_time": "20:35",
        "from": "Lahore",
        "to": "Islamabad",
        "duration": "1h 05m",
        "stops": 0,
    },
    {
        "id": "F007",
        "airline": "PIA",
        "price": 17000,
        "departure_time": "07:30",
        "arrival_time": "09:30",
        "from": "Islamabad",
        "to": "Lahore",
        "duration": "2h 00m",
        "stops": 0,
    },
    {
        "id": "F008",
        "airline": "Airblue",
        "price": 16000,
        "departure_time": "13:00",
        "arrival_time": "14:05",
        "from": "Islamabad",
        "to": "Lahore",
        "duration": "1h 05m",
        "stops": 0,
    },
    {
        "id": "F009",
        "airline": "AirSial",
        "price": 17500,
        "departure_time": "20:00",
        "arrival_time": "21:05",
        "from": "Islamabad",
        "to": "Lahore",
        "duration": "1h 05m",
        "stops": 0,
    },
    {
        "id": "F010",
        "airline": "PIA",
        "price": 23000,
        "departure_time": "10:00",
        "arrival_time": "12:00",
        "from": "Islamabad",
        "to": "Karachi",
        "duration": "2h 00m",
        "stops": 0,
    },
    {
        "id": "F011",
        "airline": "Airblue",
        "price": 21000,
        "departure_time": "14:30",
        "arrival_time": "16:35",
        "from": "Islamabad",
        "to": "Karachi",
        "duration": "2h 05m",
        "stops": 0,
    },
    {
        "id": "F012",
        "airline": "Fly Jinnah",
        "price": 24000,
        "departure_time": "19:00",
        "arrival_time": "21:00",
        "from": "Islamabad",
        "to": "Karachi",
        "duration": "2h 00m",
        "stops": 0,
    },
    {
        "id": "F013",
        "airline": "Fly Jinnah",
        "price": 42000,
        "departure_time": "09:00",
        "arrival_time": "11:15",
        "from": "Karachi",
        "to": "Dubai",
        "duration": "3h 15m",
        "stops": 0,
    },
    {
        "id": "F014",
        "airline": "PIA",
        "price": 46000,
        "departure_time": "15:00",
        "arrival_time": "17:20",
        "from": "Karachi",
        "to": "Dubai",
        "duration": "3h 20m",
        "stops": 0,
    },
    {
        "id": "F015",
        "airline": "Emirates",
        "price": 65000,
        "departure_time": "20:30",
        "arrival_time": "22:50",
        "from": "Karachi",
        "to": "Dubai",
        "duration": "3h 20m",
        "stops": 0,
    },
    {
        "id": "F016",
        "airline": "PIA",
        "price": 44000,
        "departure_time": "08:30",
        "arrival_time": "10:40",
        "from": "Islamabad",
        "to": "Dubai",
        "duration": "3h 10m",
        "stops": 0,
    },
    {
        "id": "F017",
        "airline": "Flydubai",
        "price": 52000,
        "departure_time": "14:00",
        "arrival_time": "16:15",
        "from": "Islamabad",
        "to": "Dubai",
        "duration": "3h 15m",
        "stops": 0,
    },
    {
        "id": "F018",
        "airline": "Emirates",
        "price": 68000,
        "departure_time": "21:00",
        "arrival_time": "23:10",
        "from": "Islamabad",
        "to": "Dubai",
        "duration": "3h 10m",
        "stops": 0,
    },
]

HOTELS = {
    "Islamabad": [
        {
            "id": "H001",
            "name": "Hotel Sunrise",
            "price_per_night": 8000,
            "rating": 4.2,
            "location": "City Center",
            "amenities": ["WiFi", "Breakfast included", "Parking"],
        },
        {
            "id": "H002",
            "name": "Capital View Hotel",
            "price_per_night": 11000,
            "rating": 4.6,
            "location": "Blue Area",
            "amenities": ["WiFi", "Breakfast included", "Gym"],
        },
        {
            "id": "H003",
            "name": "Margalla Inn",
            "price_per_night": 6500,
            "rating": 4.0,
            "location": "F-8",
            "amenities": ["WiFi", "Parking"],
        },
        {
            "id": "H004",
            "name": "Royal Islamabad",
            "price_per_night": 14500,
            "rating": 4.8,
            "location": "F-6",
            "amenities": ["WiFi", "Breakfast included", "Pool", "Gym"],
        },
    ],
    "Lahore": [
        {
            "id": "H005",
            "name": "Lahore Grand Hotel",
            "price_per_night": 8500,
            "rating": 4.3,
            "location": "Gulberg",
            "amenities": ["WiFi", "Breakfast included", "Parking"],
        },
        {
            "id": "H006",
            "name": "Pearl City Inn",
            "price_per_night": 12000,
            "rating": 4.7,
            "location": "DHA",
            "amenities": ["WiFi", "Breakfast included", "Gym"],
        },
        {
            "id": "H007",
            "name": "Fort View Hotel",
            "price_per_night": 7000,
            "rating": 4.1,
            "location": "Mall Road",
            "amenities": ["WiFi", "Parking"],
        },
    ],
    "Karachi": [
        {
            "id": "H008",
            "name": "Karachi Pearl Hotel",
            "price_per_night": 9000,
            "rating": 4.3,
            "location": "Clifton",
            "amenities": ["WiFi", "Breakfast included", "Parking"],
        },
        {
            "id": "H009",
            "name": "Sea View Residency",
            "price_per_night": 13000,
            "rating": 4.6,
            "location": "DHA",
            "amenities": ["WiFi", "Breakfast included", "Pool"],
        },
        {
            "id": "H010",
            "name": "City Comfort Inn",
            "price_per_night": 6000,
            "rating": 4.0,
            "location": "PECHS",
            "amenities": ["WiFi", "Parking"],
        },
    ],
    "Dubai": [
        {
            "id": "H011",
            "name": "Dubai Central Hotel",
            "price_per_night": 28000,
            "rating": 4.4,
            "location": "Deira",
            "amenities": ["WiFi", "Breakfast included", "Pool"],
        },
        {
            "id": "H012",
            "name": "Marina Comfort Hotel",
            "price_per_night": 42000,
            "rating": 4.7,
            "location": "Dubai Marina",
            "amenities": ["WiFi", "Breakfast included", "Gym", "Pool"],
        },
        {
            "id": "H013",
            "name": "Budget Stay Dubai",
            "price_per_night": 22000,
            "rating": 4.0,
            "location": "Bur Dubai",
            "amenities": ["WiFi", "Parking"],
        },
    ],
}

CITIES = ["Karachi", "Lahore", "Islamabad", "Dubai", "Multan", "Peshawar"]

# -----------------------------
# Helper functions
# -----------------------------
def get_route_flights(origin, destination):
    return [
        flight.copy()
        for flight in FLIGHTS
        if flight["from"] == origin and flight["to"] == destination
    ]


def get_hotels(destination):
    return [hotel.copy() for hotel in HOTELS.get(destination, [])]


def rank_with_groq(flights, hotels, priority):
    """
    Groq is used only to rank the inventory already supplied by this app.
    It is NOT used as a live flight/hotel database.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or (not flights and not hotels):
        return flights, hotels, False, None

    try:
        client = Groq(api_key=api_key)

        payload = {
            "priority": priority,
            "flights": flights,
            "hotels": hotels,
        }

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the TravelGenie ranking assistant. "
                        "Rank ONLY the supplied flight and hotel objects. "
                        "Never invent, delete, edit, or change any object, price, "
                        "airline, hotel name, rating, time, city, or amenity. "
                        "Return valid JSON with exactly two arrays: "
                        "flights and hotels. The arrays must contain the same "
                        "objects supplied by the user, only reordered."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload),
                },
            ],
        )

        data = json.loads(response.choices[0].message.content)

        flight_ids = [item.get("id") for item in data.get("flights", [])]
        hotel_ids = [item.get("id") for item in data.get("hotels", [])]

        flight_map = {item["id"]: item for item in flights}
        hotel_map = {item["id"]: item for item in hotels}

        ranked_flights = [
            flight_map[item_id]
            for item_id in flight_ids
            if item_id in flight_map
        ]
        ranked_hotels = [
            hotel_map[item_id]
            for item_id in hotel_ids
            if item_id in hotel_map
        ]

        # Safety check: if the model returns an incomplete list, keep
        # the original complete inventory instead of losing options.
        if len(ranked_flights) != len(flights):
            ranked_flights = flights

        if len(ranked_hotels) != len(hotels):
            ranked_hotels = hotels

        return ranked_flights, ranked_hotels, True, None

    except Exception as exc:
        return flights, hotels, False, str(exc)


def format_pkr(value):
    return f"PKR {value:,.0f}"


# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <h1>✈️ TravelGenie</h1>
        <p>
            Find multiple flight and hotel options for your destination,
            compare prices, and let AI rank the best choices for you.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Hackathon demo: flight and hotel prices below are sample inventory, "
    "not live booking prices or live availability."
)

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("🧳 Trip Planner")

    origin = st.selectbox("From", CITIES, index=0)

    destination_options = [city for city in CITIES if city != origin]
    destination = st.selectbox("To", destination_options)

    travel_date = st.date_input(
        "Travel date",
        value=date.today(),
        min_value=date.today(),
    )

    hotel_nights = st.number_input(
        "Hotel nights",
        min_value=1,
        max_value=30,
        value=2,
        step=1,
    )

    max_flight_price = st.number_input(
        "Maximum flight price (PKR)",
        min_value=0,
        max_value=500000,
        value=100000,
        step=5000,
    )

    priority = st.selectbox(
        "AI ranking priority",
        [
            "Lowest price",
            "Best rating",
            "Balanced price + quality",
        ],
    )

    find_options = st.button(
        "🔎 Find Travel Options",
        type="primary",
        use_container_width=True,
    )

# -----------------------------
# Main logic
# -----------------------------
if find_options:
    st.session_state["search_done"] = True
    st.session_state["origin"] = origin
    st.session_state["destination"] = destination
    st.session_state["travel_date"] = travel_date
    st.session_state["hotel_nights"] = hotel_nights
    st.session_state["max_flight_price"] = max_flight_price
    st.session_state["priority"] = priority

if st.session_state.get("search_done"):
    origin = st.session_state["origin"]
    destination = st.session_state["destination"]
    travel_date = st.session_state["travel_date"]
    hotel_nights = st.session_state["hotel_nights"]
    max_flight_price = st.session_state["max_flight_price"]
    priority = st.session_state["priority"]

    flights = get_route_flights(origin, destination)
    flights = [
        flight
        for flight in flights
        if flight["price"] <= max_flight_price
    ]

    hotels = get_hotels(destination)

    ranked_flights, ranked_hotels, ai_used, ai_error = rank_with_groq(
        flights,
        hotels,
        priority,
    )

    st.subheader(
        f"✈️ {origin} → {destination}  |  📅 {travel_date.strftime('%d %b %Y')}"
    )

    if ai_used:
        st.success("🤖 Groq AI ranking applied to the available demo options.")
    else:
        st.warning(
            "Showing the available demo options in their default order. "
            "Add GROQ_API_KEY in Streamlit Secrets to enable AI ranking."
        )

    if ai_error:
        with st.expander("Technical information"):
            st.code(ai_error)

    # -----------------------------
    # Flights
    # -----------------------------
    st.markdown("## ✈️ Flight Options")

    if not ranked_flights:
        st.error(
            "No sample flights match this route and maximum price. "
            "Try another route or increase the maximum flight price."
        )
    else:
        for flight in ranked_flights:
            st.markdown(
                f"""
                <div class="card">
                    <span class="badge">{flight["airline"]}</span>
                    <span class="badge">{flight["duration"]}</span>
                    <span class="badge">
                        {"Direct" if flight["stops"] == 0 else str(flight["stops"]) + " stop(s)"}
                    </span>

                    <h3>{flight["departure_time"]} → {flight["arrival_time"]}</h3>

                    <p class="muted">
                        {flight["from"]} → {flight["to"]}
                    </p>

                    <p class="price">{format_pkr(flight["price"])}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -----------------------------
    # Hotels
    # -----------------------------
    st.markdown("## 🏨 Hotel Options")

    if not ranked_hotels:
        st.error("No sample hotel inventory is available for this destination.")
    else:
        for hotel in ranked_hotels:
            total = hotel["price_per_night"] * hotel_nights
            amenities = " • ".join(hotel["amenities"])

            st.markdown(
                f"""
                <div class="card">
                    <h3>{hotel["name"]}</h3>

                    <span class="badge">⭐ {hotel["rating"]}</span>
                    <span class="badge">{hotel["location"]}</span>

                    <p class="muted">{amenities}</p>

                    <p>
                        <strong>{format_pkr(hotel["price_per_night"])}</strong>
                        per night
                    </p>

                    <p class="price">
                        Estimated {hotel_nights}-night total:
                        {format_pkr(total)}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -----------------------------
    # JSON output for hackathon/demo
    # -----------------------------
    st.markdown("## 📦 Agent Output")

    st.caption(
        "This JSON structure can be passed to another TravelGenie agent "
        "or displayed as the flight/hotel recommendation result."
    )

    st.json(
        {
            "flights": ranked_flights,
            "hotels": ranked_hotels,
        }
    )

else:
    st.markdown(
        """
        <div class="card">
            <h2>🌍 Plan your next trip</h2>
            <p class="muted">
                Select your origin, destination, date, budget, hotel nights,
                and AI ranking preference from the sidebar, then click
                <strong>Find Travel Options</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
