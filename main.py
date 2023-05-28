from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from sqlalchemy.exc import NoResultFound
from functools import wraps


###### I left the database with the mock products and one user created for testing purposes. ######
###### User email: test@test.com; Password: 12345 #########

##### This is for testing purposes only. Should use environment variable instead.
SECRET_KEY = 'top_secret'

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
Bootstrap(app)

###### Connect to DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

###### Configure DB tables


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def find_user_by_email(self, user_email):
        with app.app_context():
            # Had to catch a NoResultFound exception in order to flash the message in main.py
            # sqlalchemy kept returning a exc.NoResultFound error, regardless of where the IF statement was located
            try:
                user = db.session.execute(db.select(User).filter_by(email=user_email)).scalar_one()
                return user
            except NoResultFound:
                return "Email not found"


class Products(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(150), nullable=False)
    sub_cat = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.String(100), nullable=False)
    img_url = db.Column(db.String, nullable=False)
    cart = db.relationship('Cart', back_populates='products')


class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    products = db.relationship('Products', back_populates='cart')
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(100), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    quantity = db.Column(db.Integer)


class Wishlist(db.Model):
    __tablename__ = 'wishlist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='wishlist')
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product = db.relationship('Products', backref='wishlist')
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(100), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    def __init__(self, user_id, product_id, name, price, img_url):
        self.user_id = user_id
        self.product_id = product_id
        self.name = name
        self.price = price
        self.img_url = img_url


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        else:
            return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def home():
    all_products = Products.query.all()
    supplements = Products.query.filter_by(category='Supplements').all()
    accessories = Products.query.filter_by(category="Accessories").all()
    towels = Products.query.filter_by(sub_cat='Towels').all()
    bags = Products.query.filter_by(sub_cat='Bags').all()
    shirts = Products.query.filter_by(sub_cat='T-shirt').all()
    hoodies = Products.query.filter_by(sub_cat='Hoodies').all()
    return render_template('index.html', products=all_products, supplements=supplements, accessories=accessories,
                           towels=towels, bags=bags, shirts=shirts, hoodies=hoodies)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        user = User().find_user_by_email(email)
        if user == "Email not found":
            flash("This email doesn't exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("Password incorrect, please try again.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home', user_email=current_user.email))
    return render_template('login.html', logged_in=current_user.is_authenticated)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(email=request.form['email']).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        hash_salted_password = generate_password_hash(
            request.form['password'],
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=request.form['email'],
            password=hash_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home', user_email=current_user.email))
    return render_template('register.html')


##### This route has to be manually typed in the address bar. Only works if your user_id is 1.#####
##### Check top comment in main.py for admin credentials. #########
@app.route('/add', methods=["GET", "POST"])
@admin_only
def add_new_product():
    if request.method == "POST":
        new_product = Products(
        category=request.form.get('category'),
        sub_cat=request.form.get('sub_cat'),
        name=request.form.get('name'),
        price=request.form.get('price'),
        img_url=request.form.get('img_url'),
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add2.html')


@app.route('/products', methods=["GET"])
def all_products():
    all_products = Products.query.all()
    supplements = Products.query.filter_by(category='Supplements').all()
    accessories = Products.query.filter_by(category="Accessories").all()
    towels = Products.query.filter_by(sub_cat='Towels').all()
    bags = Products.query.filter_by(sub_cat='Bags').all()
    shirts = Products.query.filter_by(sub_cat='T-shirt').all()
    hoodies = Products.query.filter_by(sub_cat='Hoodies').all()
    return render_template('product.html', products=all_products, supplements=supplements, accessories=accessories,
                           towels=towels, bags=bags, shirts=shirts, hoodies=hoodies)


@app.route('/product_page/<int:product_id>', methods=["GET"])
def product_page(product_id):
    requested_product = Products.query.get(product_id)
    return render_template('product_page.html', product=requested_product)


@app.route('/shopping-cart/', methods=["GET", "POST"])
def cart():
    products_in_cart = Cart.query.all()
    products = []
    grand_total = 0
    index = 0
    for item in products_in_cart:
        product = item.products
        quantity = item.quantity
        total = item.quantity * int(item.price.lstrip('$'))
        grand_total += int(total)
        products.append({'id': product.id, 'name': product.name, 'price': product.price, 'img_url': product.img_url, 'quantity': quantity, 'total': total, 'user_id': item.user_id, 'index': index})
        index += 1
    grand_total_plus_shipping = grand_total + 20
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    return render_template('shopping-cart.html', prod_id=products_in_cart, products=products, grand_total=grand_total, grand_total_plus_shipping=grand_total_plus_shipping)


@app.route('/add-to-cart/<int:prod_id>', methods=["GET", "POST"])
def add_to_cart(prod_id):
    product = Products.query.get(prod_id)
    default_quantity = 1
    if not current_user.is_authenticated:
        flash("You need to be logged in to add products to cart.")
        return redirect(url_for('login'))

    cart_item = Cart.query.filter_by(product_id=prod_id,user_id=current_user.id).first()
    if cart_item:
        cart_item.quantity += 1
        db.session.commit()
        return redirect(url_for('cart'))

    prod = Cart(
        product_id=prod_id,
        user_id=current_user.id,
        name=product.name,
        price=product.price,
        img_url=product.img_url,
        quantity=default_quantity,
    )
    db.session.add(prod)
    db.session.commit()
    return redirect(url_for('home'))


############## There is a bug that I couldn't fix. The first product that is added to the cart can't be removed. ######
############## The route works perfectly fine for the products that are added afterwards ###################
@app.route('/remove-from-cart/<int:product_id>', methods=["GET", "POST"])
def remove_from_cart(product_id):
    if request.method != 'POST':
        return abort(405)  # Method Not Allowed
    # print("Remove from cart route triggered")
    # print("Current user ID:", current_user.id)
    # print("Product ID:", product_id)
    if not current_user.is_authenticated:
        flash("You need to be logged in to remove products from the cart.")
        return redirect(url_for('login'))
    #
    # cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    # print("Cart items:")
    # for item in cart_items:
    #     print("Cart item ID:", item.id)
    #     print("Cart item product ID:", item.product_id)

    item_to_remove = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    # print("item to remove:", item_to_remove)
    if item_to_remove:
        # print("Item found, deleting...")
        db.session.delete(item_to_remove)
        db.session.commit()
        flash('Product removed from cart successfully.')
    else:
        flash('Product not found in the cart.')
    #
    # cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    # print("Cart items after removal:")
    # for item in cart_items:
    #     print("Cart item ID:", item.id)
    #     print("Cart item product ID:", item.product_id)

    return redirect(url_for('cart'))


@app.route('/whishlist/add/<int:product_id>', methods=["GET", "POST"])
def add_to_wishlist(product_id):
    if current_user.is_authenticated:
        product = Products.query.get(product_id)
        if product:
            wishlist_item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
            if not wishlist_item:
                wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id, name=product.name,
                                         price=product.price, img_url=product.img_url)
                db.session.add(wishlist_item)
                db.session.commit()
                return redirect(url_for('wishlist'))
            else:
                flash('Product already exists in wishlist.', 'info')
        else:
            flash('Product not found.', 'error')
    else:
        flash('Please log in to add products to your wishlist.', 'error')
    return redirect(url_for('wishlist'))


@app.route('/wishlist')
def wishlist():
    if current_user.is_authenticated:
        wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
        return render_template('wishlist.html', wishlist_items=wishlist_items)
    else:
        flash('Please log in to view your wishlist.', 'error')
        return redirect(url_for('login'))


@app.route('/wishlist/remove/<int:wishlist_id>', methods=['GET', 'POST'])
def remove_from_wishlist(wishlist_id):
    if current_user.is_authenticated:
        wishlist_item = Wishlist.query.filter_by(id=wishlist_id, user_id=current_user.id).first()
        if wishlist_item:
            db.session.delete(wishlist_item)
            db.session.commit()
            flash('Product removed from wishlist successfully.', 'success')
        else:
            flash('Product not found in wishlist.', 'error')
    else:
        flash('Please log in to remove products from your wishlist.', 'error')
    return redirect(url_for('wishlist'))


@app.route('/about', methods=["GET"])
def about():
    return render_template('about.html')


@app.route('/contact', methods=["GET", "POST"])
def contact():
    return render_template('contact.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)