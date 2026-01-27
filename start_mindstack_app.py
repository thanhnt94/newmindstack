from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from mindstack_app import create_app

app = create_app()

if __name__ == '__main__':
    import sys
    import asyncio
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    app.run(host='0.0.0.0', port=5000, debug=True)
