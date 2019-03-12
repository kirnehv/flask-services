import flask, sqlite3, hashlib
from flask import request, Response, jsonify
from flask_basicauth import BasicAuth

app = flask.Flask(__name__)
app.config['DEBUG'] = True


# overwrite check_credentials to read from database
class Auth(BasicAuth):
    def check_credentials(self, email, password):
        conn = sqlite3.connect('api.db')
        cur = conn.cursor()
        user_password = cur.execute('SELECT password FROM users WHERE email=?', [email]).fetchone()
        conn.close()

        if user_password:
            return hash_password(password) == user_password[0]
        else:
            return False


def hash_password(password):
    salt = "cpsc476"
    # salt adds difficulty to password (can't use rainbow table to crack)
    db_password = password + salt
    # hashing
    h = hashlib.md5(db_password.encode())
    # digest turns hasher into a string
    return h.hexdigest()


auth = Auth(app)


@app.route('/registration', methods=['POST'])
def register():
    name = request.json['name']
    email = request.json['email']
    password = request.json['password']
    new_user = [name, email, hash_password(password)]

    # check if all fields are populated
    if not (name or email or password):
        return 'Missing parameter.\n', 409

    conn = sqlite3.connect('api.db')
    cur = conn.cursor()
    email_exists = cur.execute('SELECT * FROM users WHERE email=?', [email]).fetchone()
    name_exists = cur.execute('SELECT * FROM users WHERE name=?', [name]).fetchone()

    # check if name or email exist before creating new user
    if email_exists:
        return 'Email is already in use.\n', 409
    elif name_exists:
        return 'Name is already in use.\n', 409
    
    cur.execute('INSERT INTO users (name, email, password) VALUES (?,?,?)', new_user)
    id = cur.execute('SELECT id FROM users WHERE email=?', [email])
    conn.commit()
    conn.close()
    
    return Response(
        'User created.\n',
        201,
        mimetype='application/json',
        headers={
            'Location':'/users/view?id=%s' % id
        }
    )
    # curl -X POST -H 'Content-Type: application/json' - d '{"email":"ari@test.com", "password":"password", "username":"ari"}' http://127.0.0.1:5000/registration


@app.route('/users/view', methods=['GET'])
def view_user():
    id = request.args.get('id')
    
    conn = sqlite3.connect('api.db')
    cur = conn.cursor()
    name = cur.execute('SELECT name FROM users WHERE id=?', [id]).fetchone()
    conn.close()

    return jsonify(name)


@app.route('/users/settings', methods=['PUT', 'DELETE'])
def options():
    if request.method == 'PUT':
        return change_password()
    elif request.method == 'DELETE':
        return delete()


@auth.required
def change_password():
    new_password = request.json['new-password']
    email = request.authorization['username']

    conn = sqlite3.connect('api.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET password=? WHERE email=?', [hash_password(new_password), email])
    conn.commit()
    conn.close()

    return 'Password has been changed.\n', 200
    # curl -X PUT --user ari@test.com:password -H 'Content-Type: application.json' -d '{"new-password":"12345"}'  http://127.0.0.1:5000/users/settings


@auth.required
def delete():
    email = request.authorization['username']

    conn = sqlite3.connect('api.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM users WHERE email=?', [email])
    conn.commit()
    conn.close()

    return 'User has been deleted.\n', 200
    # curl -X DELETE --user ari@test.com:password  http://127.0.0.1:5000/users/settings


app.run()
