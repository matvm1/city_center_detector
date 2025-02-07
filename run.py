from dotenv import load_dotenv
from app import create_app
from app.services import (init_lsatimg, get_lsatimg, viz_lsat_img,
                          get_lsatimg_url, get_lsatimg_info, get_coords,
                          LANDSAT_8_BAND_COMBINATIONS,
                          IMAGE_COLLECTION_NAME)
import os
from flask import render_template, request, session
from datetime import timedelta
import logging


load_dotenv(override=True)
app = create_app()

app.config['SECRET_KEY'] = os.getenv('SESSION_KEY')
app.config['SESSION_PERMANENT'] = False
# Expire after 30 minutes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)


VALID_HOMEPAGE_REQUEST_ARGS = ['address', 'band_combination_option']


@app.route('/')
def index():
    session.pop('lsatimg', None)

    return render_template('index.html',
                           band_combinations=LANDSAT_8_BAND_COMBINATIONS)


@app.route('/get_landsat_img')
def landsat_image():
    gee_init_status = init_lsatimg()

    if gee_init_status != 0:
        error_message = "Failed to authenticate/initialize Google Earth Engine"
        return render_template("error.html", error_message=error_message)

    address = request.args.get('address')

    # Fetch the coordinates for the address
    lat, lon = None, None
    try:
        lat, lon = get_coords(address)
    except Exception as e:
        logging.exception(e)
        error_message = "Failed to fetch coordinates for the address"
        return render_template("error.html", error_message=error_message)

    # Check if the address was geocoded successfully
    if (lat, lon) == (None, None):
        error_message = f"Could not find coordinates for {address}"
        return render_template("error.html", error_message=error_message)

    lsatimg = get_lsatimg(lat, lon)
    session['lsatimg'] = get_lsatimg_info(lsatimg)

    for arg in request.args.keys():
        if arg not in VALID_HOMEPAGE_REQUEST_ARGS:
            error_message = f"Request argument {arg} not supported"
            return render_template("error.html", error_message=error_message)

    band_combinations_req = request.args.getlist('band_combination_option')

    for user_selection in band_combinations_req:
        if LANDSAT_8_BAND_COMBINATIONS.get(user_selection) is None:
            error_message = f"Band combination {user_selection} is invalid"
            return render_template("error.html", error_message=error_message)

    city_lsatimg_urls = {}
    for combination in band_combinations_req:
        city_lsatimg_urls[combination] = (get_lsatimg_url(
                                            viz_lsat_img(
                                                lsatimg,
                                                combination)))

    return render_template('city_center.html',
                           image_collection_name=IMAGE_COLLECTION_NAME,
                           address=address,
                           city_lsatimg_urls=city_lsatimg_urls)


if __name__ == '__main__':
    app.run(debug=True)
