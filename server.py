from flask import Flask, redirect, url_for, send_from_directory, jsonify
from flask_login import LoginManager, current_user
from flask_resources import User
from db import init_db
from security_config import limiter, init_config
import accounts as acc
import resources as res
import posts

app = Flask(__name__, template_folder='public', static_folder='build', static_url_path='')

login_manager = LoginManager(app)
login_manager.session_protection = 'strong'  # Important!

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def config_app():
    routes = [
        ('/', 'serve', serve, ['GET']),
        ('/<string:name>', 'serve', serve, ['GET'])
    ]

    acc.config_app(app)
    posts.config_app(app)

    routes.extend(res.get_routes())
    routes.extend(acc.get_routes())
    routes.extend(posts.get_routes())

    blueprints = [acc.acc_bp, posts.posts_bp, res.res_bp]

    init_config(app, routes, blueprints)
    init_db()

config_app()

# Serve React App
@app.route('/')
@app.route('/<string:name>', methods=['GET'])
@limiter.exempt
def serve(name=None):
    # user = get_db_users().find_one({'username':ADMIN_NAME})

    # if user['creds'] is None:
    # authorize()

    # logout()

    if not current_user.is_authenticated:
        return redirect(url_for("sec.login"))
    else:
        return send_from_directory(app.static_folder, 'index.html')
    # return ''

# Example API endpoint
@app.route('/api/hello')
def hello():
    return jsonify(message="Hello from Flask!")

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(port=5000)
