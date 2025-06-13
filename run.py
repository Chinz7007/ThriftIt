import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import app, socketio

if __name__ == "__main__":
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run with Socket.IO support
    socketio.run(
        app, 
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=port
    )
