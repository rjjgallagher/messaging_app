import pickle

from flask import Flask, request, session
from flask_socketio import emit, disconnect, SocketIO

from model.message import Message
from model.user import User, UserList

# Configure and start the Flask app with the SocketIO extension
app = Flask(__name__)
app.secret_key = b"_5#y2L'F4Q8z\n\xec]/"
socketio = SocketIO(app)


# Endpoint to create a new user account using a POST request
@app.route("/create_account", methods=["POST"])
def create_account():
    data = request.json # Get request data as JSON
    new_user = User.from_dto(data) # Create a new User object from the JSON data

	# Attempt to add the new user to the user list
    try:
        users.add(new_user)
    except ValueError:
		# If adding user fails, return an error response
        return "Invalid Credentials", 401

	# If successful, return a success response
    return "Success", 200


# Endpoint to log in a user using a POST request
@app.route("/login", methods=["POST"])
def login():
    data = request.json # Get request data as JSON
    user_login = User.from_dto(data) # Create a User object from the JSON data
    user = users.get_user_by_name(user_login.name)  # Check if account exists

	# Validate user credentials and session
    if not user or user.password != user_login.password or user.sid != None:
        return "Invalid Credentials", 401

	# If successful, store username in session
    session["username"] = user_login.name
    return "Success", 200


# Endpoint to kick a user using a POST request
@app.route("/kick", methods=["POST"])
def kick():
    data = request.json # Get request data as JSON
    user = users.get_user_by_name(User.from_dto(data).name) # Get User object from the JSON data
	
	# Disconnect user by their Socket.IO session ID
    disconnect(user.sid, "/")
    return "Success", 200


# Event handler for outgoing messages
@socketio.on("message_out")
def messageout(message_dto):
	# Create a Message object from the JSON data
    message = Message.from_dto(message_dto)
	
	# Handle group messages
    if message.receiver.name == "group":
        message.type = "PM"
		# Broadcast the message to all connected clients
        emit("message_out", message.to_dto(), broadcast=True)
    else:
		# Handle direct messages
        message.type = "DM"
		# Get the session IDs for the sender and receiver
        receiver_sid = users.get_user_by_name(message.receiver.name).sid
        sender_sid = users.get_user_by_name(message.sender.name).sid
		
		# Send the message to the sender and receiver
        emit("message_out", message.to_dto(), room=receiver_sid)
        emit("message_out", message.to_dto(), room=sender_sid)
    

# Event handler for user disconnection
@socketio.on("disconnect")
def on_disconnect():
	# Get the User object from the session
    user = users.get_user_by_name(session.get("username"))
    
	if not user:
        return
    
	# Clear the user's Socket.IO session ID and remove the username from the session
	user.sid = None
    session.pop("username", None)
	
	# Broadcast the updated user list to all connected clients
    emit("user_change", users.to_dto(), broadcast=True)


# Event handler for user connection
@socketio.on("connect")
def connect():
	# Get the username from the session
    if session.get("username") is not None:
        user = users.get_user_by_name(session.get("username"))
		
        if not user:
            return False
		
		# Update the user's Socket.IO session ID
        user.sid = request.sid
		
		# Broadcast the updated user list to all connected clients
        emit("user_change", users.to_dto(), broadcast=True)
    else:
		# If there is no username in the session, do not allow the connection
        return False
    

if __name__ == "__main__":
    try:
        # Attempt to load existing user data from a file
        with open("users.pickle", "rb") as f:
            users = pickle.load(f)
    except:
        # If the file does not exist, create a new file with an empty user list and an admin user
        with open("users.pickle", "wb") as f:
            users = UserList()
            # create admin superuser
            admin = User(name="admin", password="admin")
            users.add(admin)
            pickle.dump(users, f)

	# Start the Flask-SocketIO app
    socketio.run(app)
