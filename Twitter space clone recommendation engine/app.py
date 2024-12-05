from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from models import Database
import os


app = Flask(__name__)
app.secret_key = os.urandom(24)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"
db = Database(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)


@app.route("/", methods=["GET"])
def index():
    username = session.get("username")
    posts = db.get_all_posts()  # get all posts
    return render_template("index.html", username=username, posts=posts)


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect('/register')


        if not username or not password or not email:
            flash("Missing data")
            return jsonify({"error": "Missing data"}), 400


        if db.user_exists(username):
            flash("A user with that username already exists, please try another one.")
            return jsonify({"error": "User already exists"}), 409
        else:

            db.create_user(username, password, email)
            flash("You were successfully registered!")
            return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = db.get_user(username)

        if not user or user['password'] != password:
            flash("Invalid username or password, please try again.")
            return render_template('login.html')

        flash("Login successful!")
        session["username"] = user['username']
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out")
    return redirect(url_for('index'))


@app.route("/add_post", methods=["POST"])
def add_post():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    text = request.form["text"]
    tags = {tag.strip("#") for tag in text.split() if tag.startswith("#")}
    db.add_post(username, text, tags)
    return redirect(url_for("index"))


@app.route("/add_comment", methods=["POST"])
def add_comment():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    post_id = request.form["post_id"]
    comment_text = request.form["comment_text"]
    db.add_comment(username, post_id, comment_text)
    return redirect(url_for("index"))


@app.route("/toggle_like", methods=["POST"])
def toggle_like():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    post_id = data["post_id"]
    is_liked = data["is_liked"]
    try:
        if is_liked:
            db.like_post(username, post_id)
        else:
            db.unlike_post(username, post_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/toggle_follow", methods=["POST"])
def toggle_follow():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    target_username = data["username"]
    is_following = data["is_following"]
    try:
        if is_following:
            db.follow_user(username, target_username)
        else:
            db.unfollow_user(username, target_username)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route('/profile/<username>', methods=['GET'])
def profile(username):
    user = db.get_user(username)
    if not user:
        flash("User not found")
        return redirect(url_for('index'))
    posts = db.get_user_posts(username)
    reposts = db.get_user_reposts(username)
    following = db.get_following(username)
    followers = db.get_followers(username)

    current_user = session.get("username")
    is_following = db.is_following(current_user, username) if current_user else False

    return render_template("profile.html", user=user, posts=posts, reposts=reposts, following=following,
                           followers=followers, is_following=is_following)


@app.route("/repost_post", methods=["POST"])
def repost_post():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    post_id = data.get("post_id")
    try:
        db.repost_post(session['username'], post_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route('/space', methods=['GET'])
def space():
    username = session.get("username")

    if not username:
        return redirect(url_for("login"))
    # # Test Node similarity
    # user_recommendations = db.recommend_spaces_using_similarity(username, top_n=5)

    # 获取用户行为数据 这里开始是运行我设计的
    user_posts = db.get_user_posts(username)
    user_follows = db.get_following(username)
    user_recommendations = []

    # 根据不同用户情况选择推荐方式
    if not user_posts and not user_follows:
        # New users, with no behaviour or following anyone, return to the space of the latest release
        user_recommendations = db.get_latest_spaces(top_n=5)
    elif not user_posts and user_follows:
        # Users with followers but no behaviours, recommending spaces that friends have participated in
        user_recommendations = db.get_recommendations_from_friends(username, top_n=5)
    else:
        # Users with behavioural data, using behaviour-based recommendation logic
        user_recommendations = db.recommend_spaces(username, top_n=5)

    topics = db.get_all_topics()


    return render_template("space.html", username=username, topics=topics, spaces=user_recommendations)


@app.route('/create_space', methods=['POST'])
def create_space():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    space_name = request.form.get('space_name')
    space_description = request.form.get('space_description')
    topics = request.form.getlist('topics')

    if not space_name or not space_description:
        flash("Missing data, please check again!")
        return jsonify({"error": "Missing data"}), 400

    try:
        db.create_space(session['username'], space_name, space_description, topics)
        flash(f"Space '{space_name}' created successfully!")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for('space'))


@app.route('/join_space', methods=['POST'])
def join_space():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    space_id = request.form.get('space_id')
    role = request.form.get('role')
    try:
        db.join_space(session['username'], space_id, role)
        flash("Successfully joined the space!")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for('space'))

@app.route('/leave_space', methods=['POST'])
def leave_space():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    space_id = request.form.get('space_id')
    try:
        db.leave_space(session['username'], space_id)
        flash("Successfully left the space!")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for('space'))


@app.route('/user_durations', methods=['GET'])
def user_durations():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    durations = db.get_user_space_durations(session['username'])
    return render_template('user_durations.html', durations=durations)


@app.route('/delete_space', methods=['POST'])
def delete_space():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    space_id = request.form.get("space_id")
    print(f"Attempting to delete space with id: {space_id} for user: {username}")  # 调试输出
    try:
        db.delete_space(username, space_id)
        print(f"Space {space_id} deleted successfully by user {username}")
        flash("Space deleted successfully.")
    except ValueError as e:
        print(f"Failed to delete space: {str(e)}")
        flash(str(e))
    return redirect(url_for("space"))



@app.route('/delete_post', methods=['POST'])
def delete_post():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    post_id = request.form.get('post_id')
    try:
        db.delete_post(session['username'], post_id)
        flash("Post deleted successfully!")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for('index'))


@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    comment_id = request.form.get('comment_id')
    try:
        db.delete_comment(session['username'], comment_id)
        flash("Comment deleted successfully!")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for('index'))


@app.route('/end_space', methods=['POST'])
def end_space():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    space_id = request.form.get("space_id")
    try:
        db.end_space(username, space_id)
        flash("Space ended successfully.")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for("space"))




if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
