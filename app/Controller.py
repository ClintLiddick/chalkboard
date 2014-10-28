import os
import webapp2
import logging
from google.appengine.ext.webapp import template
from google.appengine.api import users             
from google.appengine.ext import db 
from google.appengine.ext import blobstore     
from google.appengine.ext.webapp import blobstore_handlers         
from datetime import date

# logging setup
# TODO set to INFO in production
logging.getLogger(__name__).setLevel(logging.DEBUG)


# General Utilities
class UserData(db.Model) :
    user_id = db.StringProperty()
    course_name = db.StringProperty()
    user_name = db.StringProperty()
    user_email = db.StringProperty()
    documentlist = db.ListProperty(blobstore.BlobKey,indexed=False, default=[]);

def renderTemplate(response, templatename, templatevalues) :
    basepath = os.path.split(os.path.dirname(__file__)) #extract the base path, since we are in the "app" folder instead of the root folder
    path = os.path.join(basepath[0], 'templates/' + templatename)
    html = template.render(path, templatevalues)
    
    response.out.write(html)

def handle404(request, response, exception) :
    """ Custom 404 error page """
    logging.debug('404 Error GET request: ' + str(request))
    logging.exception(exception)
    
    template_values = {
        'page_title' : "Page Not Found",
        'current_year' : date.today().year
    }
        
    renderTemplate(response, '404.html', template_values)


# Handler classes
class IntroHandler(webapp2.RequestHandler):
    """RequestHandler for initial intro page"""

    def get(self):
        """Intro page GET request handler"""
        logging.debug('IntroHandler GET request: ' + str(self.request))
        
        template_values = {
            'page_title' : "Chalkboard",
            'current_year' : date.today().year
        }
        
        renderTemplate(self.response, 'index.html', template_values)
        
    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)
        
class InstructorHandler(webapp2.RequestHandler):
    """RequestHandler for instructor page"""
    def post(self):
        name = self.request.get('name')
        email = self.request.get('email')
        course = self.request.get('course')
        
        logging.debug('InstructorHandler POST request: ' + str(self.request))
    
        user = users.get_current_user();
        
        template_values = {}
        if user:
            #stores data
            user_data = UserData()
            
            user_data.user_id = user.user_id()
            user_data.user_name = name            
            user_data.user_email = email            
            user_data.course_name = course
            user_data.documents_list = [""];
            
            user_data.put()
            
            logout_url = users.create_logout_url('/')
            
            template_values = {
                'page_title' : "Chalkboard",
                'current_year' : date.today().year,
                'logout' : logout_url,
                'email' : user_data.user_email,
                'nickname' : user_data.user_name,
                'course' : user_data.course_name,
            }
            
        else:
            self.redirect(users.create_login_url('/instructor'))

        #redirects back to instructor page (should show new data)
        renderTemplate(self.response, 'instructor.html', template_values)
    
    def get(self):
        """Instructor page GET request handler"""
        logging.debug('InstructorHandler GET request: ' + str(self.request))
    
        #retrieve the current user
        user = users.get_current_user()
        
        login_url = ''
        logout_url = ''
        
        email = ''
        name = ''
        course = ''
        
        target_page = 'instructor.html'
        
        template_values = {
        
        }
        
        #check if signed in
        if user:
            logout_url = users.create_logout_url('/')
                        
            d = UserData.all()
            d.filter('user_id =', user.user_id())
            
            #if data was received, grab it
            if d.count(1):
                for user_data in d.run():
                    email = user_data.user_email
                    name = user_data.user_name
                    course = user_data.course_name
                
                template_values = {
                    'page_title' : "Chalkboard",
                    'current_year' : date.today().year,
                    'logout' : logout_url,
                    'email' : email,
                    'nickname' : name,
                    'course' : course,
                }
            #if no data was received, redirect to new course page (to make data)
            else:
                target_page = 'new_course.html'
                template_values = {
                    'page_title' : "Chalkboard",
                    'current_year' : date.today().year,
                    'logout' : logout_url,
                    'nickname' : user.nickname(),
                }
                
        else :
            self.redirect(users.create_login_url('/instructor'))        
        
        
        renderTemplate(self.response, target_page, template_values)

    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)

class DocumentsHandler(webapp2.RequestHandler):
    #"""RequestHandler for Documents page"""
    def post(self):
        
        name = self.request.get('name')
        email = self.request.get('email')
        course = self.request.get('course')
        
        logging.debug('UploadHandler POST request: ' + str(self.request))
    
        user = users.get_current_user();
        
        template_values = {}
        if user:
            #stores data
                        
            logout_url = users.create_logout_url('/')
            
            template_values = {
                'page_title' : "Chalkboard",
                'current_year' : date.today().year,
                'logout' : logout_url,
                'email' : user_data.user_email,
                'nickname' : user_data.user_name,
                'course' : user_data.course_name,
            }
            
        else:
            self.redirect(users.create_login_url('/instructor'))

        #redirects back to instructor page (should show new data)
        #renderTemplate(self.response, 'instructor.html', template_values)
    
    def get(self):
        upload_url = blobstore.create_upload_url('/upload');
    
        """Instructor page GET request handler"""
        logging.debug('UploadHandler GET request: ' + str(self.request))
    
        #retrieve the current user
        user = users.get_current_user()
    
        target_page = 'documents.html'
                
        #check if signed in
        if user:
            logout_url = users.create_logout_url('/')
                        
            d = UserData.all()
            d.filter('user_id =', user.user_id())
            
            #if data was received, grab it
            if d.count(1):
                for user_data in d.run():
                    email = user_data.user_email
                    name = user_data.user_name
                    course = user_data.course_name
                
                template_values = {
                    'page_title' : "Chalkboard",
                    'current_year' : date.today().year,
                    'logout' : logout_url,
                    'email' : email,
                    'nickname' : name,
                    'course' : course,
                    'upload_url' : upload_url
                }
            #if no data was received, redirect to new course page (to make data)
            else:
                target_page = 'instructor.html'
                            
        else :
            self.redirect(users.create_login_url('/instructor'))        
        
        
        renderTemplate(self.response, target_page, template_values)

    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)
        
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler) :
    def post(self):
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0];
        self.redirect(users.create_login_url('/instructor'))
        user = users.get_current_user();
        d = UserData.all()
        d.filter('user_id =', user.user_id())
        if d.count(1):
            for user_data in d.run():
                user_data.documentlist.append(blob_info.key());
                user_data.put();
        
        
class ErrorHandler(webapp2.RequestHandler):
    """Request handler for error pages"""

    def get(self):
        logging.debug('ErrorHandler GET request: ' + str(self.request))

        template_values = {
            'page_title' : "Oh no...",
            'current_year' : date.today().year
        }
        
        renderTemplate(self.response, 'error.html', template_values)

class AboutHandler(webapp2.RequestHandler) :
    """Request handler for about page"""

    def get(self):
        logging.debug('AboutHandler GET request: ' + str(self.request))

        template_values = {
            'page_title' : "About Chalkboard",
            'current_year' : date.today().year
        }

        renderTemplate(self.response, 'about.html', template_values)

# list of URI/Handler routing tuples
# the URI is a regular expression beginning with root '/' char
routeHandlers = [
    (r'/', IntroHandler),
    (r'/about', AboutHandler),
    (r'/error', ErrorHandler),
    (r'/instructor', InstructorHandler),
    (r'/documents', DocumentsHandler),
    (r'/upload', UploadHandler)
]

# application object
application = webapp2.WSGIApplication(routeHandlers, debug=True)

application.error_handlers[404] = handle404