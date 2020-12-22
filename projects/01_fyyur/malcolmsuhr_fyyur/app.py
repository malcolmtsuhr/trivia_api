# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import sys
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect
from flask import url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form, FlaskForm
from forms import *
from flask_migrate import Migrate
from datetime import datetime
from sqlalchemy import func

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    genres = db.Column(db.String())
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean(), nullable=False, default=False)
    seeking_description = db.Column(db.String())
    creation_date = db.Column(db.DateTime, nullable=False)
    shows = db.relationship(
        'Show', backref='venue', cascade='all, delete-orphan', lazy='joined')


class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    genres = db.Column(db.String())
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String())
    creation_date = db.Column(db.DateTime, nullable=False)
    shows = db.relationship(
        'Show', backref='artist', cascade='all, delete-orphan', lazy='joined')


class Show(db.Model):
    __tablename__ = 'show'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'))
    start_time = db.Column(db.DateTime, nullable=False)


class Area(db.Model):
    __tablename__ = 'area'

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    venues = db.relationship(
        'Venue', backref='area', cascade='all, delete-orphan', lazy='joined')
    artists = db.relationship(
        'Artist', backref='area', cascade='all, delete-orphan', lazy='joined')

    # city and state are input normalized as lowercase city, enum code state
    # city is rendered with title() function in UI html

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


# Format Date time
def format_datetime(value, format='medium'):
    if isinstance(value, str):
        date = dateutil.parser.parse(value)
    else:
        date = value
        if format == 'full':
            format = "EEEE MMMM, d, y 'at' h:mma"
        elif format == 'medium':
            format = "EE MM, dd, y h:mma"
        return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Functions.
# ----------------------------------------------------------------------------#

# Recieve multi part phone data from form & format to xxx-xxx-xxxx
def recieve_phone(form):
    area_code = str(form.area_code.data)
    exchange_code = str(form.exchange_code.data)
    line_number = str(form.line_number.data)
    format_phone = '-'.join([area_code, exchange_code, line_number])
    return format_phone


# Reformat phone string into parsed integers for edit-form prefill
def reformat_phone(form, object):
    phone_str = object.phone
    form.area_code.data = phone_str[:3]
    form.exchange_code.data = phone_str[4:7]
    form.line_number.data = phone_str[8:12]
    return form


# Query|Create Area: takes form city|state data, Object of venue|artist
def query_create_area(form, newObject):
    if form.city.data:
        if Area.query.filter_by(
                city=form.city.data.lower(),
                state=form.state.data).count() > 0:
            # if city + state match form input then:
            this_area = Area.query.filter_by(
                city=form.city.data.lower(),
                state=form.state.data).first()
            newObject.area_id = this_area.id
            objects = [newObject]
        elif db.session.query(db.func.max(Area.id)).scalar():
            # else populate new Area with city + state combo & generate uuid
            area_uuid = db.session.query(db.func.max(Area.id)).scalar() + 1
            newArea = Area(
                id=area_uuid,
                city=form.city.data.lower(),
                state=form.state.data)
            newObject.area_id = newArea.id
            objects = [newObject, newArea]
        else:
            # else populate first Area with city + state combo & generate id 1
            area_uuid = 1
            newArea = Area(
                id=area_uuid,
                city=form.city.data.lower(),
                state=form.state.data)
            newObject.area_id = newArea.id
            objects = [newObject, newArea]
    return objects


# Format Genres: takes venue|artist object as self returns UI normalized genres
def format_genres(self):
    tmp_genres = (self.genres).replace(
        '{', '').replace('}', '').replace('"', '')
    tmp_genres = tmp_genres.split(',')
    genre_array = {}
    for genre in tmp_genres:
        genre_array[genre] = genre
    return genre_array


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

# populate home page with 10 recent venue|artist listings
@app.route('/')
def index():
    recent_venues = Venue.query.order_by(
                    db.desc(Venue.creation_date)).limit(10).all()
    recent_artists = Artist.query.order_by(
                    db.desc(Artist.creation_date)).limit(10).all()
    return render_template(
        'pages/home.html', venues=recent_venues, artists=recent_artists)


#  ----------------------------------------------------------------
#  VENUES Controllers Section
#  ----------------------------------------------------------------

#  LIST Venues
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():
    areas = Area.query.join(Area.venues).order_by('state', 'city')

    def comp_data(area):
        venues = Venue.query.filter_by(area_id=area.id).all()

        def comp_venues(venue):
            shows = venue.shows
            upcoming_shows = [show for show in shows
                              if show.start_time >= datetime.today()]
            return {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(upcoming_shows)
                }
        return {
            "city": area.city,
            "state": area.state,
            "venues": list(map(lambda venue: comp_venues(venue=venue), venues))
            }
    area_data = list(map(lambda area: comp_data(area=area), areas))
    return render_template('pages/venues.html', areas=area_data)


#  SEARCH Venues
#  ----------------------------------------------------------------
@app.route('/venues/search', methods=['POST', 'GET'])
def search_venues():
    search_term = request.form.get('search_term', '')
    venues = Venue.query.all()
    search_venues = [venue for venue in venues
                     if search_term.lower() in venue.name.lower()
                     or search_term.lower() in
                     Area.query.get(venue.area_id).city.lower() + ", " +
                     Area.query.get(venue.area_id).state.lower()]

    def comp_venues(venue):
        shows = venue.shows
        upcoming_shows = [show for show in shows
                          if show.start_time >= datetime.today()]
        return {
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": len(upcoming_shows)
            }
# Search on venues with partial string search; Case-insensitive.
    response = {
      "count": len(search_venues),
      "data": list(map(lambda venue: comp_venues(venue=venue), search_venues))
    }
    return render_template(
        'pages/search_venues.html', results=response, search_term=search_term)


#  SHOW Venue Details
#  ----------------------------------------------------------------
@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    this_venue = Venue.query.get(venue_id)
    ref_area = Area.query.get(this_venue.area_id)
    shows = this_venue.shows
    upcoming_shows = [show for show in shows
                      if show.start_time >= datetime.today()]
    past_shows = [show for show in shows if show.start_time < datetime.today()]
    genre_array = format_genres(this_venue)

    def comp_shows(show):
        this_artist = Artist.query.get(show.artist_id)
        return {
            "artist_id": this_artist.id,
            "artist_name": this_artist.name,
            "artist_image_link": this_artist.image_link,
            "start_time": show.start_time
            }
    data = {
      "id": this_venue.id,
      "name": this_venue.name,
      "address": this_venue.address,
      "genres": genre_array,
      "city": ref_area.city,
      "state": ref_area.state,
      "phone": this_venue.phone,
      "website": this_venue.website,
      "facebook_link": this_venue.facebook_link,
      "seeking_talent": this_venue.seeking_talent,
      "seeking_description": this_venue.seeking_description,
      "image_link": this_venue.image_link,
      "past_shows": [comp_shows(show=show) for show in past_shows],
      "upcoming_shows": [comp_shows(show=show) for show in upcoming_shows],
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows),
    }
    return render_template('pages/show_venue.html', venue=data)


#  CREATE Venue GET|POST
#  ----------------------------------------------------------------
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form, meta={"csrf": False})
    format_phone = recieve_phone(form)
    error = False
    try:
        newVenue = Venue(
            name=form.name.data,
            genres=form.genres.data,
            address=form.address.data,
            phone=format_phone,
            website=form.website.data,
            image_link=form.image_link.data,
            facebook_link=form.facebook_link.data,
            seeking_description=form.seeking_description.data,
            creation_date=form.creation_date.data)
        if form.seeking_description.data:
            newVenue.seeking_talent = True
# function querys existing areas compared to form input; else generate new area
        objects = query_create_area(form, newVenue)

        db.session.add_all(objects)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        error = True
        flash('An error occurred. Venue ' + request.form['name'] +
              ' could not be listed.')
        print(sys.exc_info())
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  EDIT Venue GET|POST
#  ----------------------------------------------------------------
@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    this_venue = Venue.query.get(venue_id)
    ref_area = Area.query.get(this_venue.area_id)
    phone = reformat_phone(form, this_venue)
    venue = {
        "id": this_venue.id,
        "name": this_venue.name,
        "genres": this_venue.genres,
        "address": this_venue.address,
        "city": ref_area.city,
        "state": ref_area.state,
        "phone": phone,
        "website": this_venue.website,
        "facebook_link": this_venue.facebook_link,
        "seeking_talent": this_venue.seeking_talent,
        "seeking_description": this_venue.seeking_description,
        "image_link": this_venue.image_link
        }
    form.state.data = ref_area.state
    form.genres.data = this_venue.genres
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = VenueForm(request.form, meta={"csrf": False})
    editVenue = Venue.query.get(venue_id)
    format_phone = recieve_phone(form)
    error = False
    try:
        editVenue.id = venue_id
        editVenue.name = form.name.data
        editVenue.genres = form.genres.data
        editVenue.address = form.address.data
        editVenue.phone = format_phone
        editVenue.website = form.website.data
        editVenue.image_link = form.image_link.data
        editVenue.facebook_link = form.facebook_link.data
        editVenue.seeking_description = form.seeking_description.data
        if form.seeking_description.data:
            editVenue.seeking_talent = True
# function querys existing areas compared to form input; else generate new area
        objects = query_create_area(form, editVenue)

        db.session.add_all(objects)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully edited!')
    except:
        db.session.rollback()
        error = True
        flash('An error occurred. Venue ' + request.form['name'] +
              ' could not be edited.')
        print(sys.exc_info())
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))


#  DELETE Venue
#  ----------------------------------------------------------------
@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    error = False
    try:
        this_venue = Venue.query.get(venue_id)
        db.session.delete(this_venue)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    return redirect(url_for('index'))


#  ----------------------------------------------------------------
#  ARTISTS Controllers Section
#  ----------------------------------------------------------------

#  LIST Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    artists = Artist.query.order_by('name')
    return render_template('pages/artists.html', artists=artists)


#  SEARCH Artists
#  ----------------------------------------------------------------
@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    artists = Artist.query.all()
    search_artists = [artist for artist in artists
                      if search_term.lower() in artist.name.lower()
                      or search_term.lower() in
                      Area.query.get(artist.area_id).city.lower() + ", " +
                      Area.query.get(artist.area_id).state.lower()]

    def comp_artists(artist):
        shows = artist.shows
        upcoming_shows = [show for show in shows
                          if show.start_time >= datetime.today()]
        return {
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": len(upcoming_shows)
            }
    response = {
      "count": len(search_artists),
      "data": [comp_artists(artist=artist) for artist in search_artists]
    }
    return render_template(
        'pages/search_artists.html', results=response, search_term=search_term)


#  SHOW Artist Details
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>', methods=['GET'])
def show_artist(artist_id):
    this_artist = Artist.query.get(artist_id)
    ref_area = Area.query.get(this_artist.area_id)
    shows = this_artist.shows
    upcoming_shows = [show for show in shows
                      if show.start_time >= datetime.today()]
    past_shows = [show for show in shows if show.start_time < datetime.today()]
    genre_array = format_genres(this_artist)

    def comp_shows(show):
        this_venue = Venue.query.get(show.venue_id)
        return {
            "venue_id": this_venue.id,
            "venue_name": this_venue.name,
            "venue_image_link": this_venue.image_link,
            "start_time": show.start_time
            }
    data = {
      "id": this_artist.id,
      "name": this_artist.name,
      "genres": genre_array,
      "city": ref_area.city,
      "state": ref_area.state,
      "phone": this_artist.phone,
      "website": this_artist.website,
      "facebook_link": this_artist.facebook_link,
      "seeking_venue": this_artist.seeking_venue,
      "seeking_description": this_artist.seeking_description,
      "image_link": this_artist.image_link,
      "past_shows": [comp_shows(show=show) for show in past_shows],
      "upcoming_shows": [comp_shows(show=show) for show in upcoming_shows],
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows),
    }
    return render_template('pages/show_artist.html', artist=data)


#  EDIT Artist GET|POST
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    this_artist = Artist.query.get(artist_id)
    ref_area = Area.query.get(this_artist.area_id)
    phone = reformat_phone(form, this_artist)
    artist = {
        "id": this_artist.id,
        "name": this_artist.name,
        "genres": this_artist.genres,
        "city": ref_area.city,
        "state": ref_area.state,
        "phone": phone,
        "website": this_artist.website,
        "facebook_link": this_artist.facebook_link,
        "seeking_venue": this_artist.seeking_venue,
        "seeking_description": this_artist.seeking_description,
        "image_link": this_artist.image_link
        }
    form.state.data = ref_area.state
    form.genres.data = this_artist.genres
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm(request.form, meta={"csrf": False})
    editArtist = Artist.query.get(artist_id)
    format_phone = recieve_phone(form)
    error = False
    try:
        editArtist.id = artist_id
        editArtist.name = form.name.data
        editArtist.genres = form.genres.data
        editArtist.phone = format_phone
        editArtist.website = form.website.data
        editArtist.image_link = form.image_link.data
        editArtist.facebook_link = form.facebook_link.data
        editArtist.seeking_description = form.seeking_description.data
        if form.seeking_description.data:
            editArtist.seeking_venue = True
# function querys existing areas compared to form input; else generate new area
        objects = query_create_area(form, editArtist)

        db.session.add_all(objects)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully edited!')
    except:
        db.session.rollback()
        error = True
        flash('An error occurred. Venue ' + request.form['name'] +
              ' could not be edited.')
        print(sys.exc_info())
    finally:
        db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))


#  Create Artist GET|POST
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form, meta={"csrf": False})
    error = False
    format_phone = recieve_phone(form)
    try:
        newArtist = Artist(
            name=form.name.data,
            genres=form.genres.data,
            phone=format_phone,
            website=form.website.data,
            image_link=form.image_link.data,
            facebook_link=form.facebook_link.data,
            seeking_description=form.seeking_description.data,
            creation_date=form.creation_date.data)
        if form.seeking_description.data:
            newArtist.seeking_venue = True
# function querys existing areas compared to form input; else generate new area
        objects = query_create_area(form, newArtist)

        db.session.add_all(objects)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        error = True
        flash('An error occurred. Artist ' + request.form['name'] +
              ' could not be listed.')
        print(sys.exc_info())
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  DELETE Artist
#  ----------------------------------------------------------------
@app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    error = False
    try:
        this_artist = Artist.query.get(artist_id)
        db.session.delete(this_artist)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    return redirect(url_for('index'))


#  ----------------------------------------------------------------
#  Shows Controllers Section
#  ----------------------------------------------------------------

#  LIST Shows
#  ----------------------------------------------------------------
@app.route('/shows')
def shows():
    shows = Show.query.order_by('start_time')
    upcoming_shows = [show for show in shows
                      if show.start_time >= datetime.today()]
    past_shows = [show for show in shows if show.start_time < datetime.today()]

    # compile upcoming show data & reference venue|artist data by id
    def comp_data(show):
        venue_id = show.venue_id
        artist_id = show.artist_id
        return {
            "venue_id": venue_id,
            "venue_name": Venue.query.get(venue_id).name,
            "artist_id": artist_id,
            "artist_name": Artist.query.get(artist_id).name,
            "artist_image_link": Artist.query.get(artist_id).image_link,
            "start_time": show.start_time
            }
    show_data = [comp_data(show=show) for show in upcoming_shows]

    # compile past show data & reference venue|artist data by id
    def comp_data(show):
        venue_id = show.venue_id
        artist_id = show.artist_id
        return {
            "venue_id": venue_id,
            "venue_name": Venue.query.get(venue_id).name,
            "artist_id": artist_id,
            "artist_name": Artist.query.get(artist_id).name,
            "artist_image_link": Artist.query.get(artist_id).image_link,
            "start_time": show.start_time
            }
    past_show_data = [comp_data(show=show) for show in past_shows]
    return render_template(
        'pages/shows.html', shows=show_data, past_shows=past_show_data)


#  SEARCH Shows
#  ----------------------------------------------------------------
@app.route('/shows/search', methods=['POST', 'GET'])
def search_shows():
    search_term = request.form.get('search_term', '')
    shows = Show.query.order_by('start_time')

    # compile searched show data & reference venue|artist data by id
    def comp_data(show):
        venue_id = show.venue_id
        artist_id = show.artist_id
        return {
            "venue_id": venue_id,
            "venue_name": Venue.query.get(venue_id).name,
            "artist_id": artist_id,
            "artist_name": Artist.query.get(artist_id).name,
            "artist_image_link": Artist.query.get(artist_id).image_link,
            "start_time": show.start_time
            }
    # Search query by case insensitive venue|artist name or show date
    search_shows = [comp_data(show=show) for show in shows
                    if search_term.lower() in
                    Venue.query.get(show.venue_id).name.lower()
                    or search_term.lower() in
                    Artist.query.get(show.artist_id).name.lower()
                    or search_term in show.start_time.strftime("%A %B %d %Y")]
    response = {
      "count": len(search_shows),
      "data": search_shows
    }
    return render_template(
        'pages/search_shows.html', results=response, search_term=search_term)


#  CREATE Shows GET|POST
#  ----------------------------------------------------------------
@app.route('/shows/create', methods=['GET'])
def create_shows():
    # renders create show form.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form, meta={"csrf": False})
    error = False
    try:
        newShow = Show(
            artist_id=form.artist_id.data,
            venue_id=form.venue_id.data,
            start_time=form.start_time.data)
        db.session.add(newShow)
        db.session.commit()
        flash('Show was successfully listed!')
    except:
        db.session.rollback()
        error = True
        flash('An error occurred. Show could not be listed.')
        print(sys.exc_info())
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  ----------------------------------------------------------------
#  Route Handler Controllers Section.
#  ----------------------------------------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s:' +
                  ' %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.debug = True
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
