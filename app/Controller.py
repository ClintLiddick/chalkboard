import os
import webapp2
import logging
import calendar
from google.appengine.ext.webapp import template
from google.appengine.api import users             
from google.appengine.api import mail 
from google.appengine.api import memcache    
from google.appengine.ext import db 
from google.appengine.ext import blobstore     
from google.appengine.ext.webapp import blobstore_handlers     
from datetime import date
from datetime import time

# logging setup
# TODO set to INFO in production
logging.getLogger(__name__).setLevel(logging.DEBUG)


# General Utilities
class CalendarEvent(db.Model) :
    course = db.StringProperty()
    name = db.StringProperty()
    time = db.TimeProperty()
    duration = db.StringProperty()
    day = db.IntegerProperty()
    month = db.IntegerProperty()
    year = db.IntegerProperty()
    notes = db.TextProperty()
    
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
    
def generateEventID() :
    generateEventID.counter += 1
    return str(generateEventID.counter)
    
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
    
def userCanEditCourse(courseID) : #Check if the user has a course
    currentUser = getCurrentUserData()
    
    if(currentUser):
        for course in currentUser.courses:
            c = CourseData().get(course)
            if(c):
                if c.course_id == courseID :
                    return True
    return False
    
def getCourseData(courseID) : #Returns the CourseData for the current course page
    #check memcache first
    courseCache = memcache.get(courseID)
    
    if courseCache is not None:
        if isinstance(courseCache, CourseData): #Make sure we didn't get a UserData that mapped to the same ID
            return courseCache
        else:  
            return None
    else:
        c = CourseData.all()
        c.filter('course_id =', courseID)
        
        if c.count(1):
            for course in c.run():
                memcache.set(courseID, course)
                return course
                
    return None

def getCurrentUserData() : #Returns the UserData for the current logged in user, otherwise returns None
    user = users.get_current_user()
    
    if(user):
        #Check memcache first
        userCache = memcache.get(user.user_id())
    
        if userCache is not None:
            if isinstance(userCache, UserData): #Make sure we didn't get a CourseData that mapped to the same ID
                return userCache
            else:
                return None
        else :
            d = UserData.all()
            d.filter('user_id =', user.user_id())
        
            if d.count(1):
                for element in d.run():
                    memcache.set(user.user_id(), element)
                    return element
    return None
 
# Handler classes
class AboutHandler(webapp2.RequestHandler) :
    """Request handler for about page"""

    def get(self):
        logging.debug('AboutHandler GET request: ' + str(self.request))
        template_values = {
            'page_title' : "About Chalkboard",
            'current_year' : date.today().year,
            'user' : getCurrentUserData(),
            'logout' : users.create_logout_url('/about'),
            'login' : users.create_login_url('/about')
        }

        renderTemplate(self.response, 'about.html', template_values)
        
class CourseHandler(webapp2.RequestHandler) :
    """Request handler for Course pages"""
    def get(self, id):
        logging.debug('CourseHandler GET request: ' + str(self.request) + id)
        
        login_url = users.create_login_url('/course-' + str(id))
        logout_url = users.create_logout_url('/course-' + str(id))
        
        course = getCourseData(id)
        
        if(course):
            if(userCanEditCourse(id)):
                user_data = getCurrentUserData()
                user_data.current_course_selected = id #Record "last edited" page
                user_data.put()
                memcache.set(user_data.user_id, user_data)
                            
                template_values = {
                    'page_title' : 'Edit: ' + course.course_name,
                    'current_year' : date.today().year,
                    'user' : getCurrentUserData(),
                    'logout' : logout_url,
                    'login' : login_url,
                    'course_name' : course.course_name,
                    'course_id' : course.course_id
                }
                        
                renderTemplate(self.response, 'edit_course.html', template_values) 
                return
            else:            
                #Not the user who owns the course
                template_values = {
                    'page_title' : course.course_name,
                    'current_year' : date.today().year,
                    'current_month' : date.today().month,
                    'user' : getCurrentUserData(),
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

                renderTemplate(self.response, 'course.html', template_values) 
        else:
            #redirect to error if course wasn't found (or if 2 courses share an ID???)
            self.redirect('/error')
            
class CourseListHandler(webapp2.RequestHandler) :
    def post(self):
        user_data = getCurrentUserData()
    
        if(user_data):
            template_values = {
                'courses' : CourseData.get(user_data.courses)
            }
                    
            renderTemplate(self.response, 'course_list.json', template_values) 
            return
                    
        #redirect to error if course wasn't found (or if 2 courses share an ID???)
        self.redirect('/instructor')

class CourseCalendarHandler(webapp2.RequestHandler):
    def post(self):
    #    course = getCourseData(id)
        month_list = ['','January', 'February', 'March', 'April', 'May', 'June', 
            'July', 'August', 'September', 'October', 'November', 'December']
        
        # get POST parameters (month and year)
        m = self.request.get('month')
        y = self.request.get('year')
        id = self.request.get('course')
        month = int(m)
        year = int(y)
        if ((month == 0) and (year == 0)):
            month = date.today().month
            year = date.today().year
        
        my_calendar = calendar.Calendar(6)
        calendar_weeks = my_calendar.monthdatescalendar(year, month)
        
        course = getCourseData(id)
        if(course):
            
            events = CalendarEvent().all()
            if (events):
                events.filter('course = ', id)
                events.filter('year = ', year)
                events.filter('month = ', month)

                template_values = {
                    'calendar' : calendar_weeks,
                    'month' : month,
                    'year' : year,
                    'month_name' : month_list[month],
                    'course_id' : course.course_id,
                    'event_list' : events                                
                }
                
                renderTemplate(self.response, 'course_calendar.json', template_values)
            else:    
                
                template_values = {
                    'calendar' : calendar_weeks,
                    'month' : month,
                    'year' : year,
                    'month_name' : month_list[month],
                    'event_list' : None
                }
        else:
            renderTemplate(self.response, 'error.html', template_values)
        return

        
class DocumentsHandler(webapp2.RequestHandler):
    def get(self):
        """Instructor page GET request handler"""
        logging.debug('UploadHandler GET request: ' + str(self.request))

        #retrieve the current user
        user_data = getCurrentUserData()
        
        if(user_data):
            template_values = {
                'page_title' : "Upload Document",
                'current_year' : date.today().year,
                'user' : getCurrentUserData(),
                'logout' : users.create_logout_url('/'),
                'login' : users.create_login_url('/documents'),
                'upload_url' : blobstore.create_upload_url('/upload')
            }
                    
            renderTemplate(self.response, 'documents.html', template_values)
            return
                    
        #if no data was received, redirect to new course page (to make data)
        self.redirect(users.create_login_url('/instructor'))
        
    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)
  
class EmailHandler(webapp2.RequestHandler):
    def post(self):
        user_data = getCurrentUserData()
        if user_data is None:
            self.redirect('/instructor')
        else:
            message = mail.EmailMessage()
            message.sender = user_data.user_email
            
            current_course = user_data.current_course_selected
            #logging.error(current_course)
            course_info = getCourseData(current_course)
            stu_list = course_info.student_list
            bcc_list = generateClassEmails(stu_list)
            #logging.error("The first student in the list is: " + stu_list[0])
            #logging.error("The message body was:" + self.request.get('message_body'))
            message.bcc = bcc_list
            message.body = self.request.get('message_body')
            message.to = user_data.user_email
            message.send()
            self.redirect('/instructor')               
        
class ErrorHandler(webapp2.RequestHandler):
    """Request handler for error pages"""

    def get(self):
        logging.debug('ErrorHandler GET request: ' + str(self.request))

        template_values = {
            'page_title' : "Oh no...",
            'current_year' : date.today().year,
            'user' : getCurrentUserData(),
            'logout' : users.create_logout_url('/'),
            'login' : users.create_login_url('/instructor')
        }
        
        renderTemplate(self.response, 'error.html', template_values)
  
class IntroHandler(webapp2.RequestHandler):
    """RequestHandler for initial intro page"""

    def get(self):
        """Intro page GET request handler"""
        logging.debug('IntroHandler GET request: ' + str(self.request))
        
        if(getCurrentUserData()):
            self.redirect('/instructor')
        else:
            template_values = {
                'page_title' : "Chalkboard",
                'current_year' : date.today().year,
                'user' : getCurrentUserData(),
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
  
        #check if signed in
        if getCurrentUserData():
            template_values = {
                'page_title' : "Chalkboard",
                'current_year' : date.today().year,
                'user' : getCurrentUserData(),
                'logout' : users.create_logout_url('/'),
                'login' : users.create_login_url('/instructor')
            }
            renderTemplate(self.response, 'instructor.html', template_values)
        else:  #if no data was received, add data entry
            user = users.get_current_user()
            user_data = UserData()
            
            user_data.user_id = user.user_id()
            user_data.user_name = user.nickname()            
            user_data.user_email = user.email()    
            user_data.current_course_selected = ""
            user_data.is_active = True
            user_data.courses = []
            
            user_data.put()
            memcache.set(user_data.user_id, user_data)
            
            template_values = {
                'page_title' : "Chalkboard",
                'current_year' : date.today().year,
                'user' : user_data,
                'logout' : users.create_logout_url('/'),
                'login' : users.create_login_url('/instructor')
            }
            
            renderTemplate(self.response, 'instructor.html', template_values)

    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)

class NewCalendarEventHandler(webapp2.RequestHandler):
    def get(self, id):
        login_url = users.create_login_url('/course-' + str(id) + '-new_event' )
        logout_url = users.create_logout_url('/course-' + str(id))
        
        course = getCourseData(id)
        
        if(course):
            if(userCanEditCourse(id)):
                user_data = getCurrentUserData()
                user_data.current_course_selected = id #Record "last edited" page
                user_data.put()
                memcache.set(user_data.user_id, user_data)
                            
                template_values = {
                    'page_title' : 'New Event: ' + course.course_name,
                    'current_year' : date.today().year,
                    'current_month' : date.today().month,
                    'user' : getCurrentUserData(),
                    'logout' : logout_url,
                    'login' : login_url,
                    'course_name' : course.course_name,
                    'course_id' : course.course_id
                }
                        
                renderTemplate(self.response, 'new_calendar_event.html', template_values) 
                return
            else:            
                #Not the user who owns the course
                template_values = {
                    'page_title' : course.course_name,
                    'current_year' : date.today().year,
                    'current_month' : date.today().month,
                    'user' : getCurrentUserData(),
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

                renderTemplate(self.response, 'course.html', template_values) 
        else:
            #redirect to error if course wasn't found (or if 2 courses share an ID???)
            self.redirect('/error')
            
    def post(self):
    
        id = self.request.get('course_id')
        login_url = users.create_login_url('/course-' + str(id) + '-new_event' )
        logout_url = users.create_logout_url('/course-' + str(id))

        course = getCourseData(id)

        if(course):
            if(userCanEditCourse(id)):
                event = CalendarEvent()
                
                #course id 
                event.course = id
                
                #event name
                event.name = self.request.get('event_name')
                
                #event duration
                durh = self.request.get('event_dur_h')
                durm = self.request.get('event_dur_m')
                event.duration = str(durh) + 'hr ' + str(durm) + 'mi'
                
                #event notes
                event.notes = self.request.get('event_notes')
                
                #event date info
                date_raw = self.request.get('event_date')
                date_parts = date_raw.split('-')
                my_date = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
                event.year = my_date.year
                event.month = my_date.month
                event.day = my_date.day
                
                #event start time info
                time_raw = self.request.get('event_time')
                time_parts_raw = time_raw.split('-')
                time_parts = time_parts_raw[0].split(':')
                my_time = time(int(time_parts[0]), int(time_parts[1]))
                event.time = my_time
                
                event.put()
                template_values = {
                    'page_title' : 'Edit: ' + course.course_name,
                    'current_year' : date.today().year,
                    'user' : getCurrentUserData(),
                    'logout' : logout_url,
                    'login' : login_url,
                    'course_name' : course.course_name,
                    'course_id' : course.course_id
                }
                renderTemplate(self.response, 'event_confirmation.html', template_values) 
                return
            else:            
                #Not the user who owns the course
                template_values = {
                    'page_title' : course.course_name,
                    'current_year' : date.today().year,
                    'current_month' : date.today().month,
                    'user' : getCurrentUserData(),
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

                renderTemplate(self.response, 'course.html', template_values) 
        else:
            #redirect to error if course wasn't found (or if 2 courses share an ID???)
            self.redirect('/error')
            
class EventListHandler(webapp2.RequestHandler):
    def get(self, id, year, month, day):
        login_url = users.create_login_url('/course-' + str(id) + '-event-' + str(year) +'-' + str(month) + '-' + str(day))
        logout_url = users.create_logout_url('/course-' + str(id) + '-event-' + str(year) +'-' + str(month) + '-' + str(day))
        course = getCourseData(id)
        my_date = date(int(year), int(month), int(day))
        if(course):
            
            month_list = ['','January', 'February', 'March', 'April', 'May', 'June', 
            'July', 'August', 'September', 'October', 'November', 'December']
            #grab list of events for the specific course and day
            events = CalendarEvent().all()
            events.filter('course = ', id)
            events.filter('year = ', my_date.year)
            events.filter('month = ', my_date.month)
            events.filter('day = ', my_date.day)
        
            template_values = {
                'page_title' : course.course_name,
                    'current_year' : date.today().year,
                    'current_month' : date.today().month,
                    'user' : getCurrentUserData(),
                    'logout' : logout_url,
                    'login' : login_url,
                    'course_name' : course.course_name,
                    'course_id' : course.course_id,
                    'event_list' : events,
                    'month_name' : month_list[int(month)]
            }
            renderTemplate(self.response, 'event.html', template_values)
        else:
            #redirect to error if course wasn't found (or if 2 courses share an ID???)
            self.redirect('/error')
            
        
class NewCourseHandler(webapp2.RequestHandler):
    def get(self):
    
        if getCurrentUserData():
            template_values = {
                'page_title' : "Add new course",
                'current_year' : date.today().year,
                'user' : getCurrentUserData(),
                'logout' : users.create_logout_url('/'),
                'login' : users.create_login_url('/instructor')
            }
                        
            renderTemplate(self.response, 'new_course.html', template_values)
        else:
            #Else - not logged in or not a user of our site, so redirect
            self.redirect(users.create_login_url('/instructor')) 
            
    def post(self):
        logging.debug('New Course POST request: ' + str(self.request))
        
        #retrieve the current user
        user_data = getCurrentUserData()
        
        if user_data:
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
            course.student_list = ["mlucient@gmail.com "] #TODO:  Remove hardcoded email for presentation
            course.is_active = True
            course.course_id = generateID()
            course.documents_list = [""]
            course.syllabus = None
            course.put()
            memcache.set(course.course_id, course)
            
            user_data.courses.append(course.key()) #Add course key to user data
            user_data.put()
            memcache.set(user_data.user_id, user_data)
            
            self.redirect('/instructor')
        else:
            #Else - not logged in or not in our datastore
            self.redirect(users.create_login_url('/instructor'))   

class SendEmailHandler(webapp2.RequestHandler):
    def get(self):
        #logging.error('Here successfully, I guess...')
        user_data = getCurrentUserData()
        
        if user_data :  
            current_course = user_data.current_course_selected
            logging.error(current_course)
            course_info = getCourseData(current_course)
            
            if course_info :
                students = course_info.student_list     
                template_values = {
                    'current_course' : course_info,
                    'student_list' : students,
                    'page_title' : "Chalkboard",
                    'current_year' : date.today().year,
                    'logout' : users.create_logout_url('/'),     
                    'login' : users.create_login_url('/'),  
                    'user' : getCurrentUserData()
                }
                
                renderTemplate(self.response, 'send_email.html', template_values)     
                return

        #Else - redirect
        self.redirect('/instructor')
        #logging.error('SendEmail Handler: not logged in for some reason.')  
        
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler) :
    def post(self):
        user_data = getCurrentUserData()
        
        if user_data:
            upload_files = self.get_uploads('file')
            blob_info = upload_files[0];
                    
            course = getCourseData(user_data.current_course_selected)
            
            if course:
                course.document_list.append(blob_info.key());
                course.put();
                memcache.set(course.course_id, course)
                                
                self.redirect('/course-' + user_data.current_course_selected)
                return            
                
        #if no data was received, redirect to new course page (to make data)
        self.redirect(users.create_login_url('/instructor')) 

# list of URI/Handler routing tuples
# the URI is a regular expression beginning with root '/' char
routeHandlers = [
    (r'/about', AboutHandler),
    ('/course-(\d+)-new_event', NewCalendarEventHandler),
    ('/course-(\d+)', CourseHandler), #Default catch all to handle a course page request
    ('/course-(\d+)-event-(\d+)-(\d+)-(\d+)', EventListHandler),
    (r'/course_list', CourseListHandler), #Handles JSON to list courses on /instructor
    (r'/documents', DocumentsHandler),
    (r'/email', EmailHandler),
    (r'/error', ErrorHandler),
    (r'/', IntroHandler),
    (r'/instructor', InstructorHandler),
    (r'/new_course', NewCourseHandler),
    (r'/send_email', SendEmailHandler),
    (r'/upload', UploadHandler),
    (r'/calendar', CourseCalendarHandler),
    (r'/new_event', NewCalendarEventHandler),
    (r'/.*', ErrorHandler)
]

# application object
application = webapp2.WSGIApplication(routeHandlers, debug=True)

application.error_handlers[404] = handle404
