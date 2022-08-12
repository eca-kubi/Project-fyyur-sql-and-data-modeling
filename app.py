# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

from logging import Formatter, FileHandler

import babel
import dateutil.parser
import logging
from flask import Flask, render_template, request, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app, session_options={
    'expire_on_commit': False
})

from models import Venue, Show, Artist


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    if isinstance(value, datetime):
        date = value
    else:
        date = dateutil.parser.parse(value)

    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Helper functions.
# ----------------------------------------------------------------------------#
# Transform comma-delimited string of genres to list
def to_genres_list(genres):
    return genres.split(",")


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    areas_list = []
    try:

        venues_list = db.session.execute(f"""
            SELECT "Venue".id AS "id", "Venue".name AS name, "Venue".city AS city,
            "Venue".state AS state, count("Show".id) AS num_upcoming_shows FROM "Venue"
            LEFT JOIN "Show" ON "Venue".id = "Show".venue_id
            AND "Show".start_time > now() 
            GROUP BY "Venue".id
        """)\
            .mappings()\
            .all()

        query = Venue.query \
            .with_entities(Venue.city.label('city'), Venue.state.label('state')) \
            .group_by(Venue.state, Venue.city) \
            .all()

        areas_list = list(map(lambda q: q._asdict(), query))
        for a in areas_list:
            a['venues'] = []
            for v in venues_list:
                if a['city'] == v['city']:
                    a['venues'].append(v)
    except Exception as err:
        flash('An error occurred!')
    finally:
        db.session.close()
    return render_template('pages/venues.html', areas=areas_list)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # implement search on artists with partial string search. Ensure it is case-insensitive.
    # search for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    search_term = request.form['search_term']
    error = False
    response = {}
    try:
        # search for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
        # search for "band" should return "The Wild Sax Band".
        data = db.session.execute("""
                 SELECT  "Venue".id, "Venue".name, COUNT("Show".id) as num_upcoming_shows
                 FROM "Venue" 
                 LEFT OUTER JOIN "Show" ON "Venue".id = "Show".venue_id
                 AND "Show".start_time > now() 
                 WHERE "Venue".name ILIKE :val
                 GROUP BY "Venue".id

                """, {'val': '%' + search_term + '%'}) \
            .mappings() \
            .all()
        response = {
            "count": len(data),
            "data": data
        }
    except Exception as err:
        error = True
    finally:
        db.session.close()
        if error:
            flash('An error occurred!')
            abort(500)
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    # replace with real venue data from the venues table, using venue_id
    error = False
    venue = {}
    try:
        # shows the artist page with the given artist_id
        venue = Venue.query.filter_by(id=venue_id).one()
        venue.genres = to_genres_list(venue.genres)

        past_shows = db.session.query(Show.start_time, Show.artist_id, Show.id, Show.venue_id, Venue.id, Venue.name,
                                      Venue.image_link) \
            .filter(Show.venue_id == venue_id, Show.start_time < func.now()) \
            .join(Venue, Artist)

        upcoming_shows = db.session.query(Show.start_time, Show.artist_id, Show.id, Show.venue_id, Venue.id, Venue.name,
                                          Venue.image_link) \
            .filter(Show.venue_id == venue_id, Show.start_time > func.now()) \
            .join(Venue, Artist)
        venue.website = venue.website_link
        venue.past_shows = past_shows.all()
        venue.upcoming_shows = upcoming_shows.all()
        venue.upcoming_shows_count = upcoming_shows.count()
        venue.past_shows_count = past_shows.count()
    except Exception as err:
        error = True
        flash('An error occurred!')
        abort(500)
    finally:
        db.session.close()
    return render_template('pages/show_venue.html', venue=venue)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    error = False
    if form.validate():
        venue = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            address=form.address.data,
            phone=form.phone.data,
            genres=', '.join(form.genres.data),
            image_link=form.image_link.data,
            facebook_link=form.facebook_link.data,
            website_link=form.website_link.data,
            seeking_talent=form.seeking_talent.data,
            seeking_description=form.seeking_description.data
        )
        try:
            db.session.add(venue)
            db.session.commit()
        except Exception as err:
            error = True
            db.session.rollback()
        finally:
            db.session.close()
        if error:
            flash('An error occurred. Venue ' + venue.name + ' could not be listed.')
        else:
            flash('Venue ' + request.form['name'] + ' was successfully listed!')
    else:
        flash(form.errors)
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # Complete this endpoint for taking a venue_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
        flash('Venue deleted successfully!')
    except Exception as err:
        db.session.rollback()
        flash(str(err))
        flash('Venue deletion failed!')
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = Artist.query.with_entities(Artist.id, Artist.name).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form['search_term']
    error = False
    response = {}
    try:
        # search for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
        # search for "band" should return "The Wild Sax Band".
        data = db.session.execute("""
             SELECT  "Artist".id, "Artist".name, COUNT("Show".artist_id) as num_upcoming_shows
             FROM "Artist" 
             LEFT OUTER JOIN "Show" ON "Artist".id = "Show".artist_id 
             WHERE "Artist".name ILIKE :val
             GROUP BY "Artist".id
    
            """, {'val': '%' + search_term + '%'}) \
            .mappings() \
            .all()
        response = {
            "count": len(data),
            "data": data
        }
    except Exception as err:
        error = True
    finally:
        db.session.close()
        if error:
            flash('An error occurred!')
            abort(500)
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    error = False
    artist = []
    try:
        # shows the artist page with the given artist_id
        artist = Artist.query.filter_by(id=artist_id).one()
        artist.genres = to_genres_list(artist.genres)

        past_shows = db.session.query(Show.start_time, Show.artist_id, Show.id, Show.venue_id, Venue.id, Venue.name,
                                      Venue.image_link) \
            .filter(Show.artist_id == artist_id, Show.start_time < func.now()) \
            .join(Venue, Artist)

        upcoming_shows = db.session.query(Show.start_time, Show.artist_id, Show.id, Show.venue_id, Venue.id, Venue.name,
                                          Venue.image_link) \
            .filter(Show.artist_id == artist_id, Show.start_time > func.now()) \
            .join(Venue, Artist)

        artist.past_shows = past_shows.all()
        artist.upcoming_shows = upcoming_shows.all()
        artist.upcoming_shows_count = upcoming_shows.count()
        artist.past_shows_count = past_shows.count()
    except Exception as err:
        error = True
        flash('An error occurred!')
    finally:
        db.session.close()
    return render_template('pages/show_artist.html', artist=artist)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = {}
    try:
        artist = Artist.query.filter_by(id=artist_id).first()
        form.name.data = artist.name
        form.genres.data = to_genres_list(artist.genres)
        form.phone.data = artist.phone
        form.state.data = artist.state
        form.city.data = artist.city
        form.facebook_link.data = artist.facebook_link
        form.website_link.data = artist.website_link
        form.image_link.data = artist.image_link
        form.seeking_venue.data = artist.seeking_venue
        form.seeking_description.data = artist.seeking_description
    except Exception as err:
        db.session.rollback()
        flash('An error occurred!')
    finally:
        db.session.close()
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes
    form = ArtistForm(request.form)
    if form.validate():
        try:
            artist = Artist.query.filter_by(id=artist_id).first()
            artist.name = form.name.data
            artist.city = form.city.data
            artist.state = form.state.data
            artist.phone = form.phone.data
            artist.genres = ', '.join(form.genres.data)
            artist.image_link = form.image_link.data
            artist.facebook_link = form.facebook_link.data
            artist.website_link = form.website_link.data
            artist.seeking_venue = form.seeking_venue.data
            artist.seeking_description = form.seeking_description.data
            db.session.commit()
            flash('Artist info edited successfully!')
        except Exception as err:
            flash('Artist edition failed!')
            db.session.rollback()
        finally:
            db.session.close()
    else:
        flash(form.errors)
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = []
    try:
        venue = Venue.query.filter_by(id=venue_id).first()
        form.phone.data = venue.phone
        form.state.data = venue.state
        form.city.data = venue.city
        form.facebook_link.data = venue.facebook_link
        form.website_link.data = venue.website_link
        form.name.data = venue.name
        form.seeking_description.data = venue.seeking_description
        form.seeking_talent.data = venue.seeking_talent
        form.image_link.data = venue.image_link
        form.address.data = venue.address
        form.genres.data = to_genres_list(venue.genres)
    except Exception as err:
        db.session.rollback()
        flash('An error occurred!')
    finally:
        db.session.close()
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes
    form = VenueForm(request.form)
    if form.validate():
        try:
            venue = Venue.query.filter_by(id=venue_id).first()
            venue.name = form.name.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.phone = form.phone.data
            venue.genres = ', '.join(form.genres.data)
            venue.image_link = form.image_link.data
            venue.facebook_link = form.facebook_link.data
            venue.website_link = form.website_link.data
            venue.seeking_talent = form.seeking_talent.data
            venue.seeking_description = form.seeking_description.data
            venue.address = form.address.data
            db.session.commit()
            flash('Venue info edited successfully!')
        except Exception as err:
            flash('Venue edition failed!')
            db.session.rollback()
        finally:
            db.session.close()
    else:
        flash(form.errors)
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form)
    error = False
    if form.validate():
        artist = Artist(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            phone=form.phone.data,
            genres=', '.join(form.genres.data),
            image_link=form.image_link.data,
            facebook_link=form.facebook_link.data,
            website_link=form.website_link.data,
            seeking_venue=form.seeking_venue.data,
            seeking_description=form.seeking_description.data
        )
        try:
            db.session.add(artist)
            db.session.commit()
        except Exception as err:
            error = True
            db.session.rollback()
        finally:
            db.session.close()
        if error:
            flash('An error occurred. Artist ' + artist.name + ' could not be listed.')
        else:
            flash('Artist ' + request.form['name'] + ' was successfully listed!')
    else:
        flash(form.errors)
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # replace with real venues data.
    data = []
    try:
        data = db.session.execute(f"""
            SELECT "Show".id , "Show".venue_id, "Show".artist_id, "Show".start_time, 
            "Venue".name AS venue_name, "Venue".id AS venue_id, 
            "Artist".id AS artist_id, "Artist".name AS artist_name, "Artist".image_link AS artist_image_link
            FROM "Show" 
            JOIN "Venue" ON "Venue".id = "Show".venue_id 
            JOIN "Artist" ON "Artist".id = "Show".artist_id
        """).mappings() \
            .all()
    except Exception as err:
        flash('An error occurred!')
    finally:
        db.session.close()
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    error = False
    if form.validate():
        artist = db.session.query(Artist).filter_by(id=form.artist_id.data).first()
        venue = db.session.query(Venue).filter_by(id=form.venue_id.data).first()
        if artist is None:
            flash('Unknown artist with id ' + form.artist_id.data)
        if venue is None:
            flash('Unknown venue with id ' + form.venue_id.data)
        show = Show(
            artist_id=form.artist_id.data,
            venue_id=form.venue_id.data,
            start_time=form.start_time.data
        )
        try:
            db.session.add(show)
            db.session.commit()
        except Exception as err:
            error = True
            db.session.rollback()
        finally:
            db.session.close()
        if error:
            flash('Show could not be listed!')
        else:
            flash('Show for ' + artist.name + ' was successfully listed!')
    else:
        flash(form.errors)
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
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
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
