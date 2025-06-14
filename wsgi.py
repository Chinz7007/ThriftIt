import os
from app import app, socketio

# This is what Gunicorn will serve
application = socketio

# Debug information
print(f"🔌 WSGI: SocketIO async mode: {socketio.async_mode}")
print(f"🌐 WSGI: Environment: {os.environ.get('FLASK_ENV', 'development')}")
print(f"📡 WSGI: Port: {os.environ.get('PORT', 'not set')}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)