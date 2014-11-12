import os
import webapp2
import logging
from google.appengine.ext.webapp import template
from google.appengine.api import users             
from google.appengine.api import mail 
from google.appengine.ext import db 
from google.appengine.ext import blobstore     
from google.appengine.ext.webapp import blobstore_handlers         
from datetime import date

# logging setup
# TODO set to INFO in production
logging.getLogger(__name__).setLevel(logging.DEBUG)


# General Utilities
class CourseData(db.Model):
    document_list = db.ListProperty(blobstore.BlobKey,indexed=False, default=[]) #Stores the keys for a list of documents
    course_name = db.StringProperty()
    course_number = db.IntegerProperty()
    student_list = db.StringListProperty() #Stores a list of string (emails)
    course_id = db.StringProperty() #unique course ID
    department = db.StringProperty()
    university = db.StringProperty()
    instructor = db.StringProperty()
    email = db.StringProperty()
    year = db.IntegerProperty()
    semester = db.StringProperty()
    syllabus = blobstore.BlobReferenceProperty() #Store the reference to syllabus in blobstore
    is_active = db.BooleanProperty()
    #TODO: calendar entry goes here eventually (not sure how to store it since this task should be hard)

class UserData(db.Model) :
    user_id = db.StringProperty()
    user_name = db.StringProperty()
    user_email = db.StringProperty()
    courses = db.ListProperty(db.Key) #Stores a list of keys for courses
    is_active = db.BooleanProperty()
    current_course_selected = db.StringProperty()

#TODO:  temporary borrowed from STACK OVERFLOW
def static_var(varname, value):
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate

@static_var("counter", 0)	

def generateID() :
    generateID.counter += 1
    return str(generateID.counter) #TODO: Generate real IDs

def generateClassEmails(student_list) : 
    class_list = ""
    l = len(student_list)
    #logging.error("The length of the student list is:")
    #logging.error(l)
    for num in xrange(0, l-2):
        class_list += student_list[num]
        class_list += ","
    class_list+=student_list[len(student_list)-1]
    return class_list
def renderTemplate(response, templatename, templatevalues) :
    basepath = os.path.split(os.path.dirname(__file__)) #extract the base path, since we are in the "app" folder instead of the root folder
    path = os.path.join(basepath[0], 'templates/' + templatename)
    html = template.render(path, templatevalues)
    logging.debug(html)
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
class AboutHandler(webapp2.RequestHandler) :
    """Request handler for about page"""

    def get(self):
        logging.debug('AboutHandler GET request: ' + str(self.request))
        template_values = {
            'page_title' : "About Chalkboard",
            'current_year' : date.today().year,
            'user' : users.get_current_user(),
            'logout' : users.create_logout_url('/about'),
            'login' : users.create_login_url('/about')
        }

        renderTemplate(self.response, 'about.html', template_values)
        
class CourseHandler(webapp2.RequestHandler) :
    """Request handler for Course pages (public view)"""
    def get(self, id):
        logging.debug('CourseHandler GET request: ' + str(self.request) + id)
        
        user = users.get_current_user()
        
        login_url = users.create_login_url('/course/' + str(id))
        logout_url = users.create_logout_url('/course/' + str(id))
        
        if(user):
            d = UserData.all()
            d.filter('user_id =', user.user_id())
            
            #User found, so edit page instead
            if d.count(1):
                for user_data in d.run():
                    c = CourseData.all()
                    c.filter('course_id =', id)
                    
                    if c.count(1):
                        for course in c.run():
                            user_data.current_course_selected = id #Record "last edited" page
                            user_data.put()
                        
                            template_values = {
                                'page_title' : 'Edit: ' + course.course_name,
                                'current_year' : date.today().year,
                                'user' : user,
                                'logout' : logout_url,
                                'login' : login_url,
                                'course_name' : course.course_name
                            }
                    
                            renderTemplate(self.response, 'edit_course.html', template_values) 
                            return
                    
        #Not logged in || not in datastore
        d = CourseData.all()
        d.filter('course_id =', id)
        if d.count(1):
            for course in d.run():
                template_values = {
                    'page_title' : course.course_name,
                    'current_year' : date.today().year,
                    'user' : user,
                    'logout' : logout_url,
                    'login' : login_url,
                    'course_name' : course.course_name,
                    'course_number' : course.course_number,
                    'student_list' : course.student_list,
                    'department' : course.department,
                    'university' : course.university,
                    'instructor' : course.instructor,
                    'email' : course.email,
                    'year' : course.year,
                    'semester' : course.semester,
                    'is_active' : course.is_active,
                    'course_id' : course.course_id
                }
            print "JHIDS"    
            renderTemplate(self.response, 'course.html', template_values) 
        else:
        #redirect to error if course wasn't found (or if 2 courses share an ID???)
            self.redirect('/error')
            
class CourseListHandler(webapp2.RequestHandler) :
    def post(self):
        user = users.get_current_user()
    
        if(user):
            d = UserData.all()
            d.filter('user_id =', user.user_id())
            
            #User found, so edit page instead
            if d.count(1):
                for user_data in d.run():
                    
                    template_values = {
                        'courses' : CourseData.get(user_data.courses)
                    }
                    
                    renderTemplate(self.response, 'course_list.json', template_values) 
                    return
                    
        #redirect to error if course wasn't found (or if 2 courses share an ID???)
        self.redirect('/instructor')

class DocumentsHandler(webapp2.RequestHandler):
    def get(self):
        """Instructor page GET request handler"""
        logging.debug('UploadHandler GET request: ' + str(self.request))

        #retrieve the current user
        user = users.get_current_user()

        target_page = 'documents.html'

        #check if signed in
        if(user):
            d = UserData.all()
            d.filter('user_id =', user.user_id())

            #User found, so edit page instead
            if d.count(1):
                for user_data in d.run():
                    template_values = {
                        'page_title' : "Upload Document",
                        'current_year' : date.today().year,
                        'user' : user,
                        'logout' : users.create_logout_url('/'),
                        'login' : users.create_login_url('/documents'),
                        'upload_url' : blobstore.create_upload_url('/upload')
                    }
                    
                    renderTemplate(self.response, target_page, template_values)
                    return
                    
        #if no data was received, redirect to new course page (to make data)
        self.redirect(users.create_login_url('/instructor'))
        
    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)
  
class EmailHandler(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if user is None:
            self.redirect('/instructor')
        message = mail.EmailMessage()
        message.sender = user.email()
        d = UserData.all()
        d.filter('user_id =', user.user_id())
        for user_data in d.run(): 
            current_course = user_data.current_course_selected
            #logging.error(current_course)
            e = CourseData.all()
            e.filter('course_id =', current_course)
            for course_info in e.run():
                stu_list = course_info.student_list
                bcc_list = generateClassEmails(stu_list)
                #logging.error("The first student in the list is: " + stu_list[0])
                #logging.error("The message body was:" + self.request.get('message_body'))
                message.bcc = bcc_list
                message.body = self.request.get('message_body')
                message.to = user.email()
                message.send()
                self.redirect('/instructor')               
        
class ErrorHandler(webapp2.RequestHandler):
    """Request handler for error pages"""

    def get(self):
        logging.debug('ErrorHandler GET request: ' + str(self.request))

        template_values = {
            'page_title' : "Oh no...",
            'current_year' : date.today().year,
            'user' : users.get_current_user(),
            'logout' : users.create_logout_url('/'),
            'login' : users.create_login_url('/instructor')
        }
        
        renderTemplate(self.response, 'error.html', template_values)
  
class IntroHandler(webapp2.RequestHandler):
    """RequestHandler for initial intro page"""

    def get(self):
        """Intro page GET request handler"""
        logging.debug('IntroHandler GET request: ' + str(self.request))
        
        template_values = {
            'page_title' : "Chalkboard",
            'current_year' : date.today().year,
            'user' : users.get_current_user(),
            'logout' : users.create_logout_url('/'),
            'login' : users.create_login_url('/instructor')
        }
        
        renderTemplate(self.response, 'index.html', template_values)
        
    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)

class InstructorHandler(webapp2.RequestHandler):
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
                
					#If we have at least a course, display them
							
                    template_values = {
                        'page_title' : "Chalkboard",
                        'current_year' : date.today().year,
                        'user' : user,
                        'logout' : logout_url,
                        'courses' : CourseData.get(user_data.courses)
                    }
            #if no data was received, add data entry
            else:
                #stores data
                user_data = UserData()
            
                user_data.user_id = user.user_id()
                user_data.user_name = user.nickname()            
                user_data.user_email = user.email()    
                user_data.current_course_selected = ""
                user_data.is_active = True
                user_data.courses = []
            
                user_data.put()
            
                logout_url = users.create_logout_url('/')
            
                template_values = {
                    'page_title' : "Chalkboard",
                    'current_year' : date.today().year,
                    'user' : user,
                    'logout' : logout_url,
                    'courses' : CourseData.get(user_data.courses)
                }
                
        else :
            self.redirect(users.create_login_url('/instructor'))        
        
        
        renderTemplate(self.response, 'instructor.html', template_values)

    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)
        
class NewCourseHandler(webapp2.RequestHandler):
    def get(self):
    
        user = users.get_current_user()
        
        if user:
            d = UserData.all()
            d.filter('user_id =', user.user_id())
            
            #if data was received, grab it
            if d.count(1):
                for user_data in d.run():
                    template_values = {
                        'page_title' : "Add new course",
                        'current_year' : date.today().year,
                        'user' : user,
                        'logout' : users.create_logout_url('/'),
                        'login' : users.create_login_url('/instructor')
                    }
                    
                    renderTemplate(self.response, 'new_course.html', template_values)
                    return
                    
        
        #Else - not logged in or not a user of our site, so redirect
        self.redirect(users.create_login_url('/instructor')) 
    def post(self):
        logging.debug('New Course POST request: ' + str(self.request))
        
        #retrieve the current user
        user = users.get_current_user()
        
        login_url = ''
        logout_url = '';
        
        target_page = 'instructor.html'
        
        template_values = {
            
        }
        
        if user :
            d = UserData.all()
            d.filter('user_id =', user.user_id())
            
            #if data was received, grab it
            if d.count(1):
                for user_data in d.run():
                    #grab all the post parameters and store into a course db model
                    course = CourseData()
                    
                    course.course_name = self.request.get('course')
                    course.instructor = self.request.get('name')
                    course.email = self.request.get('email')
                    course.course_number = int(self.request.get('number'))
                    course.university = self.request.get('university')
                    course.department = self.request.get('department')
                    course.semester = self.request.get('semester')
                    course.year = int(self.request.get('year'))
                    course.student_list = ["mlucient@gmail.com"] #TODO:  Remove hardcoded email for presentation
                    course.is_active = True
                    course.course_id = generateID()
                    course.documents_list = [""]
                    course.syllabus = None
                    course.put()
                    user_data.courses.append(course.key()) #Add course key to user data
                    user_data.put()
            
                    self.redirect('/instructor')
                    return
        
        #Else - not logged in or not in our datastore
        self.redirect(users.create_login_url('/instructor'))   

class SendEmailHandler(webapp2.RequestHandler):
    def get(self):
        #logging.error('Here successfully, I guess...')
        user = users.get_current_user()
        if user is None:
            self.redirect('/instructor')
            #logging.error('SendEmail Handler: not logged in for some reason.')    
        if user:
            logout_url = users.create_logout_url('/')
            d = UserData.all()
            d.filter('user_id =', user.user_id())
            if d.count(1):
                #logging.error('Here all right so far. #2')
                for user_data in d.run():
                    current_course = user_data.current_course_selected
                    logging.error(current_course)
                    e = CourseData.all()
                    e.filter('course_id =', current_course)
                    if e.count(1):
                        #logging.error('Here all right so far. #3')
                        for course_info in e.run():
                            students = course_info.student_list     
                            template_values = {
                                'current_course' : course_info,
                                'student_list' : students,
                                'page_title' : "Chalkboard",
                                'current_year' : date.today().year,
                                'logout' : users.create_logout_url,     
                                'login' : users.create_login_url,  
                                'user' : users.get_current_user
                            }
                        renderTemplate(self.response, 'send_email.html', template_values)                            
                    else:
                        self.redirect('/instructor')
            else:
                self.redirect('/insructor')           
        else:
            self.redirect('/instructor')
        
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler) :
    def post(self):
        user = users.get_current_user();

        if (user) :
            d = UserData.all()
            d.filter('user_id =', user.user_id())

            if d.count(1):
                for user_data in d.run():
                    upload_files = self.get_uploads('file')
                    blob_info = upload_files[0];
                    
                    c = CourseData.all()
                    c.filter('course_id =', user_data.current_course_selected)

                    if c.count(1) :
                        for course in c.run():
                            course.document_list.append(blob_info.key());
                            course.put();
                            
                            self.redirect('/course/' + user_data.current_course_selected)
                            return
                            
        #if no data was received, redirect to new course page (to make data)
        self.redirect(users.create_login_url('/instructor')) 

# list of URI/Handler routing tuples
# the URI is a regular expression beginning with root '/' char
routeHandlers = [
    (r'/about', AboutHandler),
    (r'/course/(\d+)', CourseHandler), #Default catch all to handle a course page request
    (r'/course_list', CourseListHandler), #Handles JSON to list courses on /instructor
    (r'/documents', DocumentsHandler),
    (r'/email', EmailHandler),
    (r'/error', ErrorHandler),
    (r'/', IntroHandler),
    (r'/instructor', InstructorHandler),
    (r'/new_course', NewCourseHandler),
    (r'/send_email', SendEmailHandler),
    (r'/upload', UploadHandler),
    (r'/.*', ErrorHandler)
]

# application object
application = webapp2.WSGIApplication(routeHandlers, debug=True)

application.error_handlers[404] = handle404
