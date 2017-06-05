from flask import Flask, render_template, request, redirect, jsonify
from flask import url_for, flash
from flask import session as login_session
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Category, Item, User
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
import random
import string
import logging
app = Flask(__name__)
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


# login route
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for
                    x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s " % login_session['state']
    return render_template('login.html', STATE=state)


# gconnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    login_session['email'] = data['email']
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['access_token'] = credentials.access_token
    login_session['logged_in'] = True
    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: ' \
              '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# logout user
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('User not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % \
          login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        login_session['logged_in'] = False
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash('You are now logged out!')
        return redirect(url_for('showCategories'))
        # return response
    else:

        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# get name of category
@app.context_processor
def utility_processor():
    def getCategoryName(category_id):
        category = session.query(Category).filter_by(id=category_id).one()
        return category.name

    return dict(getCategoryName=getCategoryName)


# JSON API to view all items in a category
@app.route('/catalog/category/<int:category_id>/item/JSON')
# @app.route('/catalog/category/<int:category_id/item/JSON')
def categoryItemJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(CategoryItems=[i.serialize for i in items])


# JSON API to view all categories
@app.route('/catalog/category/JSON')
def categoriesJSON():
    category = session.query(Category).all()
    return jsonify(Categories=[c.serialize for c in category])


# JSON API to view all items
@app.route('/catalog/category/item/JSON')
def itemCatagoryJSON():
    items = session.query(Item).order_by(desc(Item.id)).all()
    return jsonify(Items=[i.serialize for i in items])


# JSON API to view top 10 recent items
@app.route('/catalog/recentitems/JSON')
def recentItemsJSON():
    items = session.query(Item).order_by(desc(Item.id)).limit(10)
    return jsonify(Items=[i.serialize for i in items])


# JSON API to view one item given item_id
@app.route('/catalog/category/<int:item_id>/item/JSON')
def itemJSON(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=[item.serialize])


# JSON API to view one category given category_id
@app.route('/catalog/category/<int:category_id>/JSON')
def categoryJSON(category_id):
    item = session.query(Item).filter_by(id=category_id).one()
    return jsonify(Category=[item.serialize])


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
        'email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Create a new category
@app.route('/catalog/category/add', methods=['GET', 'POST'])
def addCategory():
    # To do: check if a registered user is accessing the page, set cookies
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        try:
            category = session.query(Category).filter_by(name=request.form[
                'name']).one()
            if category:
                flash('Name already exists! Choose a different name')
                return redirect(url_for('showCategories'))
        except:
            newCategory = Category(name=request.form['name'],
                                   description=request.form['description'],
                                   user_id=login_session['user_id'])
            session.add(newCategory)
            flash('New category %s Successfully created')
            session.commit()
            return redirect(url_for('showCategories'))
    else:
        return render_template('addCategory.html', login_session=login_session)


# Edit a categoryshowcategoriesshowCategories
@app.route('/catalog/category/<int:category_id>/edit', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedCategory = session.query(Category).filter_by(id=category_id).one()
    if 'username' in login_session and login_session['user_id'] != \
            editedCategory.user_id:
        flash('Category is not owned by you and hence can not be edited')
        return redirect(url_for('showCategories'))
    if request.method == 'POST':
        if request.form['name']:
            try:
                category = session.query(Category).filter_by(name=request.form[
                    'name']).one()
                if category:
                    flash('Name already exists! Choose a different name')
                    return redirect(url_for('showCategories'))
            except:
                editedCategory.name = request.form['name']
        if request.form['description']:
            editedCategory.description = request.form['description']
        session.add(editedCategory)
        session.commit()
        flash('Category successfully edited %s' % editedCategory.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('editCategory.html', category=editedCategory,
                               login_session=login_session)


# Delete a category
@app.route('/catalog/category/<int:category_id>/delete',
           methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    if 'username' in login_session and login_session['user_id'] != \
            category.user_id:
        flash('Category is not owned by you and hence can not be deleted')
        return redirect(url_for('showCategories'))
    if request.method == 'POST':
        session.delete(category)
        flash('%s Successfully deleted' % category.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteCategory.html', category=deleteCategory,
                               login_session=login_session)


# Show all categories
@app.route('/')
@app.route('/catalog/category')
def showCategories():
    categories = session.query(Category).order_by(asc(Category.id))
    items = session.query(Item).order_by(desc(Item.id)).limit(10)
    return render_template('category.html', categories=categories,
                           items=items, login_session=login_session)


# Show details of a selected category
@app.route('/catalog/category/<int:category_id>')
def showSelectedCategory(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    return render_template('selectedCategory.html', category=category,
                           login_session=login_session)


# Create an item
@app.route('/catalog/category/item/add',
           methods=['GET', 'POST'])
def addItem():
    if 'username' not in login_session:
        return redirect('/login')

    categories = session.query(Category).order_by(asc(Category.id))
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       category_id=request.form['category'],
                       user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash('New item %s is successfully created' % newItem.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('addItem.html', category_options=categories,
                               login_session=login_session)


# Edit an item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    item = session.query(Item).filter_by(id=item_id).one()
    if 'username' in login_session and login_session['user_id'] != \
            item.user_id:
        flash('Item is not owned by you and hence can not be edited')
        return redirect(url_for('showCategories'))
    categories = session.query(Category).order_by(asc(Category.id))
    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
        if request.form['description']:
            item.name = request.form['description']
        if request.form['category']:
            item.category_id = request.form['category']
        session.add(item)
        session.commit()
        flash("%s item is successfully edited" % item.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('editItem.html', category_id=category_id,
                               item=item, category_options=categories,
                               login_session=login_session)


# Delete an item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    item = session.query(Item).filter_by(id=item_id).one()
    if 'username' in login_session and login_session['user_id'] != \
            item.user_id:
        flash('Item is not owned by you and hence can not be deleted')
        return redirect(url_for('showCategories'))
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash('Item %s successfully deleted' % item.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteItem.html', item=item,
                               login_session=login_session)


# Show all items in a category
@app.route('/catalog/category/<int:category_id>/', methods=['GET', 'POST'])
def showItemsCategory(category_id):
    items = session.query(Item).filter_by(category_id=category_id).all()
    category = session.query(Category).filter_by(id=category_id).one()
    if not items:
        return redirect(url_for('showCategories'))
    return render_template('itemCategory.html', items=items,
                           category=category, login_session=login_session)


# Show details of an item
@app.route('/catalog/category/item/<int:item_id>/', methods=['GET', 'POST'])
def showItem(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    if not item:
        return redirect(url_for('showCategories'))
    return render_template('item.html', item=item, login_session=login_session)


# Show all recent items
@app.route('/catalog/recentitems/', methods=['GET', 'POST'])
def recentItems():
    items = session.query(Item).order_by(desc(Item.id)).limit(10)
    return render_template('recentItems.html', items=items,
                           login_session=login_session)


if __name__ == '__main__':
    app.secret_key = 'test_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
