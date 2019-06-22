import json, os, pafy, sqlite3
from peewee import *
from flask import flash, Flask, g, render_template, request, redirect, session, url_for
from datetime import datetime

# sablon a kodban demo
from jinja2 import Template

app = Flask(__name__)
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'forum.db'),
    DEBUG=True,
    SECRET_KEY='development key'))

database = SqliteDatabase(app.config['DATABASE'])

# Az adatbazis alap osztalya a Peewee ORM-bol szarmaztatjuk
# ORM Objektum-relacios lekepzes / Object-Relational Mapping
# Az adatbazis elerese SQL queryk helyett osztalyok es fuggvenyek segitsegevel.  
class BaseModel(Model):
    class Meta:
        database = SqliteDatabase(app.config['DATABASE'])

# Mivel 1 kulcsot sem definialtunk primary_key=True -val, automatikusan letrejon
# egy AutoField tipusu magatol novekvo 'id' nevu mezo amely elsodleges kulcs lesz.
class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    email = CharField()
    join_date = DateTimeField()

class Forum(BaseModel):
    title = CharField(unique=True)
    created_by = ForeignKeyField(User)
    created_on = DateTimeField(default=datetime.now)

class Post(BaseModel):
    text = TextField()
    created_by = ForeignKeyField(User, backref='created_by')
    forum = ForeignKeyField(Forum, backref='posts')
    created_on = DateTimeField(default=datetime.now)
     

# A funkcio letrehozza az adatbazis tablakat az osztalyok alapjan, csak egyszer
# kell futtatni.
def create_tables():
    with database:
        database.create_tables([User, Forum, Post])

@app.before_request
def before_request():
  if not hasattr(g, 'database'):
        g.database = database.connect()

@app.errorhandler(404)
def page_not_found(e):
    """404 hibauzenet ha hibas URL-t ut be a felhasznalo."""
    template = Template('''
      Error {{ code }} : The requested page does not exist.
    ''')
    return template.render(code=404)

@app.teardown_appcontext
def close_db(error):
    """Lezarjuk az adatbazis kapcsolatot a request vegen vagy hiba eseten."""
    if hasattr(g, 'database'):
        database.close()

# uj felhasznalo kodja
@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if request.method == 'GET':
    return render_template('signup.html')
  else:
    if request.form['username'] == '' or request.form['password'] == '' or request.form['email'] == '':
      flash('Please complete all the fields.')
      return render_template('signup.html')
    try:
      with database.atomic():
        # Megprobaljuk a felhasznalot letrehozni. Ha a felhasznalo mar letezik,
        # egy IntegrityError hibat dob mert a usename egyedi kell legyen. 
        user = User.create(
            username=request.form['username'],
            password=request.form['password'],
            email=request.form['email'],
            join_date=datetime.now())
      # beallitjuk a session valtozokat, a felhasznalo beleptetve feliratkozaskor
      session['logged_in'] = True
      session['username'] = request.form['username']
      return redirect(url_for('main'))
    except IntegrityError:
      flash('That username is already taken.')
      return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    query = User.select()
    if request.method == 'POST':
        if request.form['username'] == '' :
            flash('Username is mandatory.') 
            return render_template('login.html')
        if request.form['username'] not in [user.username for user in query]:
            flash('Error: Invalid username')
        elif request.form['password'] not in [user.password for user in query if user.username == request.form['username']]:
            flash('Error: Invalid password')
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('%s user logged in' % session['username'])
            return redirect(url_for('forum'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('%s user was logged out' % session['username'])
    session.pop('username', None)
    return redirect(url_for('main'))

@app.route('/forum', methods=['GET', 'POST'])
def forum():
    query = Forum.select()
    if request.method == 'GET':
      return render_template('forum.html', topics = query)
    else:
      print ('title:',request.form['title'])
      if request.form['title'] == '':
        flash('Topic title is mandatory.') 
      else:
        try:
          topic = Forum(title=request.form['title'],created_by=User.get(User.username == session['username']))
          topic.save()
        except IntegrityError:
          flash('That topic already exists.')
    return render_template('forum.html', topics = query)

@app.route('/forum/<int:id>', methods=['GET', 'POST'])
def topic(id):
    query = Forum.select()
    title = [forum.title for forum in query if forum.id == id][0]
    posts = [ post for post in Post.select() if post.forum_id == id]
    print 'posts:',posts
    if request.method == 'POST':
      post = Post(text=request.form['comment'], forum=id, created_by=User.get(User.username == session['username']))
      post.save()
      posts.append(post)
    users = []
    for user in User.select():
      users.append(user.username) 
    print users
    return render_template('posts.html', title=title, posts=posts, id=id, users=users)

@app.route("/")
def main():
    return render_template('header.html')

if __name__ == "__main__":
    app.run(debug=True, host='localhost', port='5001')
