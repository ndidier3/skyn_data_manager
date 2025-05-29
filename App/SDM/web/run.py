import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from api.routes import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 