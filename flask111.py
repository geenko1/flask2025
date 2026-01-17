import os
import prk1

os.environ["RUN_FLASK_SERVER"] = "1"

prk1.app.run(debug=True)