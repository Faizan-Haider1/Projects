import streamlit as st
import pickle
import pandas as pd
import requests
import base64

from streamlit.elements.widgets import color_picker


def set_background(image_path):
    with open(image_path, "rb") as f:
        img_data = f.read()
    b64_encoded = base64.b64encode(img_data).decode()
    style = f"""
        <style>
        .stApp {{
            background-image: url(data:image/png;base64,{b64_encoded});
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
    """
    st.markdown(style, unsafe_allow_html=True)

set_background("Background5.jpg")  # path to your local image



movies_dict = pickle.load(open('movies_dict.pkl','rb'))
movies = pd.DataFrame(movies_dict)
st.title('MOVIE RECOMMENDER SYSTEM')

select_movie_name = st.selectbox(
'Select The Movie',
movies['title'].values)

def fetch_poster(movie_id):
    response = requests.get('https://api.themoviedb.org/3/movie/{}?api_key=bb05adccf1540d04311fe6ef82437a89&language=en-US'.format(movie_id))
    data = response.json()
    return "https://image.tmdb.org/t/p/w500/"+data['poster_path']

def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]
    recommended_movie = []
    poster = []
    for b in movies_list:
        movie_id = movies.iloc[b[0]].movie_id
        recommended_movie.append(movies.iloc[b[0]].title)
        # Fetching posters using API's:
        poster.append(fetch_poster(movie_id))
    return recommended_movie,poster

similarity = pickle.load(open('similarity.pkl','rb'))

if st.button('Recommend'):
    Recommendations, posters = recommend(select_movie_name)
    cols = st.columns(5)
    for i, col in enumerate(cols):
        with col:
            st.markdown(f"<p style='color:yellow; font-weight:bold; text-align:center;'>{Recommendations[i]}</p>", unsafe_allow_html=True)
            st.image(posters[i])

