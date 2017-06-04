from flask import Flask, render_template, request, redirect, jsonify, url_for, \
    flash
from os import environ
app = Flask(__name__)
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Category, Item

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

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

# Create a new category
@app.route('/catalog/category/add', methods=['GET', 'POST'])
def addCategory():
    #To do: check if a registered user is accessing the page, set cookies
    if request.method == 'POST':
        try:
            category = session.query(Category).filter_by(name=request.form[
                'name']).one()
            if category:
                flash('Name already exists! Choose a different name')
                return redirect(url_for('showCategories'))
        except:
            newCategory = Category(name=request.form['name'],
                               description = request.form['description'])
            session.add(newCategory)
            flash('New category %s Successfully created')
            session.commit()
            return redirect(url_for('showCategories'))
    else:
        return render_template('addCategory.html')


# Edit a categoryshowcategoriesshowCategories
@app.route('/catalog/category/<int:category_id>/edit', methods=['GET', 'POST'])
def editCategory(category_id):
    #To do: check if user is logged in or not, set cookies
    editedCategory = session.query(Category).filter_by(id=category_id).one()
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
        return render_template('editCategory.html', category=editedCategory)


# Delete a category
@app.route('/catalog/category/<int:category_id>/delete',
           methods=['GET', 'POST'])
def deleteCategory(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        session.delete(category)
        flash('%s Successfully deleted' % category.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteCategory.html', category=deleteCategory)


# Show all categories
@app.route('/')
@app.route('/catalog/category')
def showCategories():
    categories = session.query(Category).order_by(asc(Category.id))
    items = session.query(Item).order_by(desc(Item.id)).limit(10)
    return render_template('category.html', categories= categories, items=items)


# Show details of a selected category
@app.route('/catalog/category/<int:category_id>')
def showSelectedCategory(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    return render_template('selectedCategory.html', category=category)


# Create an item
@app.route('/catalog/category/item/add',
           methods=['GET', 'POST'])
def addItem():
    categories = session.query(Category).order_by(asc(Category.id))
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       category_id=request.form['category'])
        session.add(newItem)
        session.commit()
        flash('New item %s is successfully created' % newItem.name)
        return redirect(url_for('showCategories'))
        #return redirect(url_for('showItemsCategory', category_id=category_id))
    else:
        return render_template('addItem.html', category_options=categories)


# Edit an item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
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
                               item=item, category_options=categories)


# Delete an item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash('Item %s successfully deleted' % item.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteItem.html', item=item)


# Show all items in a category
@app.route('/catalog/category/<int:category_id>/', methods=['GET', 'POST'])
def showItemsCategory(category_id):
    items = session.query(Item).filter_by(category_id=category_id).all()
    category = session.query(Category).filter_by(id=category_id).one()
    if not items:
        return redirect(url_for('showCategories'))
    return render_template('itemCategory.html', items=items, category=category)


# Show details of an item
@app.route('/catalog/category/item/<int:item_id>/', methods=['GET', 'POST'])
def showItem(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    if not item:
        return redirect(url_for('showCategories'))
    return render_template('item.html', item=item)


# Show all recent items
@app.route('/catalog/recentitems/', methods=['GET', 'POST'])
def recentItems():
    items = session.query(Item).order_by(desc(Item.id)).limit(10)
    return render_template('recentItems.html', items=items)



if __name__ == '__main__':
    app.secret_key = 'test_secret_key'
    app.debug = True
    app.run(debug=False, port=environ.get("PORT", 5000), processes=2)
    #app.run(host='0.0.0.0', port=5000)
