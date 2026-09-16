import streamlit as st
import pickle
import pandas as pd
import requests
import base64
import os
from pathlib import Path


# ============================================================
# STREAMLIT PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Movie Recommendation System",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# HUGGING FACE SETTINGS
# ============================================================

# CHANGE THIS:
# Put your actual Hugging Face username here.
HF_USERNAME = "Faizan-Haider"

# CHANGE THIS:
# Put your actual Hugging Face dataset/repository name here.
HF_REPO = "Movie-Recommendation"

HF_BASE_URL = (
    f"https://huggingface.co/datasets/"
    f"{HF_USERNAME}/{HF_REPO}/resolve/main"
)


# ============================================================
# DOWNLOAD PICKLE FILES FROM HUGGING FACE
# ============================================================

@st.cache_resource
def download_file_from_huggingface(filename):

    file_path = Path(filename)

    # If the file already exists, don't download it again.
    if file_path.exists():
        return str(file_path)

    url = f"{HF_BASE_URL}/{filename}"

    try:

        response = requests.get(
            url,
            stream=True,
            timeout=60
        )

        response.raise_for_status()

        total_size = int(
            response.headers.get("content-length", 0)
        )

        progress_bar = st.progress(0)
        downloaded = 0

        with open(file_path, "wb") as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:

                    file.write(chunk)

                    downloaded += len(chunk)

                    if total_size > 0:

                        progress = min(
                            downloaded / total_size,
                            1.0
                        )

                        progress_bar.progress(progress)

        progress_bar.empty()

        return str(file_path)

    except requests.RequestException as e:

        st.error(
            f"Could not download {filename} from Hugging Face."
        )

        st.error(str(e))

        st.stop()


# ============================================================
# LOAD YOUR ORIGINAL PICKLE FILES
# ============================================================

@st.cache_resource
def load_movie_data():

    movies_file = download_file_from_huggingface(
        "movies_dict.pkl"
    )

    similarity_file = download_file_from_huggingface(
        "similarity.pkl"
    )

    with open(
        movies_file,
        "rb"
    ) as file:

        movies_dict = pickle.load(file)

    with open(
        similarity_file,
        "rb"
    ) as file:

        similarity = pickle.load(file)

    movies = pd.DataFrame(movies_dict)

    return movies, similarity


# ============================================================
# LOAD DATA
# ============================================================

try:

    movies, similarity = load_movie_data()

except Exception as e:

    st.error(
        "There was a problem loading the movie data."
    )

    st.exception(e)

    st.stop()


# ============================================================
# BACKGROUND IMAGE
# ============================================================

def set_background(image_path):

    if not os.path.exists(image_path):
        return

    with open(
        image_path,
        "rb"
    ) as file:

        img_data = file.read()

    b64_encoded = base64.b64encode(
        img_data
    ).decode()

    style = f"""

    <style>

    .stApp {{

        background-image:
        url(data:image/png;base64,{b64_encoded});

        background-size: cover;

        background-position: center;

        background-repeat: no-repeat;

        background-attachment: fixed;

    }}

    </style>

    """

    st.markdown(
        style,
        unsafe_allow_html=True
    )


set_background("Background5.jpg")


# ============================================================
# TMDB API
# ============================================================

def get_tmdb_api_key():

    # Streamlit Cloud secret
    try:

        key = st.secrets.get(
            "TMDB_API_KEY",
            ""
        )

        if key:
            return key

    except Exception:
        pass

    # Local environment variable
    return os.getenv(
        "TMDB_API_KEY",
        ""
    )


TMDB_API_KEY = get_tmdb_api_key()


# ============================================================
# FETCH MOVIE POSTER
# ============================================================

def fetch_poster(movie_id):

    if not TMDB_API_KEY:

        return None

    url = (
        "https://api.themoviedb.org/3/movie/"
        f"{movie_id}"
    )

    params = {

        "api_key": TMDB_API_KEY,

        "language": "en-US"

    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        poster_path = data.get(
            "poster_path"
        )

        if poster_path:

            return (
                "https://image.tmdb.org/t/p/w500/"
                + poster_path
            )

    except requests.RequestException:

        return None

    return None


# ============================================================
# RECOMMENDATION FUNCTION
# ============================================================

def recommend(movie):

    movie_index = movies[
        movies["title"] == movie
    ].index[0]

    distances = similarity[
        movie_index
    ]

    movies_list = sorted(
        list(
            enumerate(distances)
        ),
        reverse=True,
        key=lambda x: x[1]
    )[1:6]

    recommended_movie = []

    posters = []

    for item in movies_list:

        movie_id = movies.iloc[
            item[0]
        ].movie_id

        movie_title = movies.iloc[
            item[0]
        ].title

        recommended_movie.append(
            movie_title
        )

        posters.append(
            fetch_poster(movie_id)
        )

    return recommended_movie, posters


# ============================================================
# STREAMLIT FRONTEND
# ============================================================

st.title(
    "🎬 MOVIE RECOMMENDER SYSTEM"
)

st.write(
    "Select a movie and get 5 similar movie recommendations."
)


select_movie_name = st.selectbox(

    "Select The Movie",

    movies["title"].values

)


if st.button(
    "🎥 Recommend"
):

    recommendations, posters = recommend(
        select_movie_name
    )

    cols = st.columns(5)

    for i, col in enumerate(cols):

        with col:

            st.markdown(

                f"""

                <p style="
                    color: yellow;
                    font-weight: bold;
                    text-align: center;
                    min-height: 50px;
                ">

                    {recommendations[i]}

                </p>

                """,

                unsafe_allow_html=True

            )

            if posters[i]:

                st.image(
                    posters[i],
                    use_container_width=True
                )

            else:

                st.warning(
                    "Poster unavailable."
                )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Movie Recommendation System | "
    "Powered by your original similarity matrix"
)