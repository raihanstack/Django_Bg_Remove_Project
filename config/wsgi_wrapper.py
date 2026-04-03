from config.wsgi import application
from mangum import Mangum 
handler = Mangum(application)