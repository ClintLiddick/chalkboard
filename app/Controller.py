import os
import webapp2
import logging
import calendar
import uuid
from google.appengine.ext.webapp import template
from google.appengine.api import users             
from google.appengine.api import mail 
from google.appengine.api import memcache   
from google.appengine.api import search  
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

def generateID() :
    return str(uuid.uuid4())
    
def generateEventID() :
    return str(uuid.uuid4())
    
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
        if isinstance(courseCache, CourseData) and courseCache.is_active: #Make sure we didn't get a UserData that mapped to the same ID
            return courseCache
        else:  
            return None
    else:
        c = CourseData.all()
        c.filter('course_id =', courseID)
        
        if c.count(1):
            for course in c.run():
                if course.is_active == True:
                    memcache.set(courseID, course)
                    return course
                else:
                    return None
                
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

class CourseHandler(webapp2.RequestHandler) :
    """Request handler for Course pages"""
    def get(self, id):
        logging.debug('CourseHandler GET request: ' + str(self.request) + id)
        
        login_url = users.create_login_url('/' + str(id))
        logout_url = users.create_logout_url('' + str(id))
        
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

class CourseDeletedHandler(webapp2.RequestHandler) :
    def get(self):
        logging.debug('AboutHandler GET request: ' + str(self.request))
        if(getCurrentUserData()):
            template_values = {
                'page_title' : "Course Deleted",
                'current_year' : date.today().year,
                'user' : getCurrentUserData(),
                'logout' : users.create_logout_url('/'),
                'login' : users.create_login_url('/')
            }

            renderTemplate(self.response, 'course_deleted.html', template_values)
        else :
            self.redirect('/')
        
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
        
class EventListHandler(webapp2.RequestHandler):
    def get(self, id, year, month, day):
        login_url = users.create_login_url('/' + str(id) + '-event-' + str(year) +'-' + str(month) + '-' + str(day))
        logout_url = users.create_logout_url('/' + str(id) + '-event-' + str(year) +'-' + str(month) + '-' + str(day))
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
            
    def post(self):
        id = self.request.get('id');
        
        if(userCanEditCourse(id)):
            course_data = getCourseData(id)
            course_data.is_active = False
            course_data.put()
            memcache.set(id, course_data)
            doc_index = search.Index(name='courseIndex')
            doc_index.delete(id)
           

    def handle_exception(self, exception, debug):
        # overrides the built-in master exception handler
        logging.error('Template mapping exception, unmapped tag: ' + str(exception))
        
        return self.redirect(uri='/error', code=307)
        
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

class NewCalendarEventHandler(webapp2.RequestHandler):
    def get(self, id):
        login_url = users.create_login_url('/' + str(id) + '-new_event' )
        logout_url = users.create_logout_url('/' + str(id))
        
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
        login_url = users.create_login_url('/' + str(id) + '-new_event' )
        logout_url = users.create_logout_url('/' + str(id))

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
                event.duration = str(durh) + 'hr ' + str(durm) + 'min'
                
                #event notes
                event.notes = self.request.get('event_notes')
                
                #event date info
                date_time_raw = (self.request.get('event_datetime').encode('ascii','ignore'))
                                               
                if type(date_time_raw) is str:
                    logging.warning("It's a str!")
                else:
                    logging.warning("Not a str!")
                                               
                year = date_time_raw[0:4]
                month = date_time_raw[5:7]
                day = date_time_raw[8:10]
                hour = date_time_raw[11:13]
                minute = date_time_raw[14:16]
                
                logging.warning(year)
                logging.warning(month)
                logging.warning(day)
                logging.warning(hour)
                logging.warning(minute)
               
                
                #datetime_parts = re.split('/', date_time_raw)
                
                #logging.warning(datetime_parts)
                
                my_date = date(int(year), int(month), int(day))
                event.year = my_date.year
                event.month = my_date.month
                event.day = my_date.day
                
                #event start time info
                
                #time_raw = self.request.get('event_time')
                #time_parts_raw = time_raw.split('-')
                #time_parts = time_parts_raw[0].split(':')
                my_time = time(int(hour), int(minute))
                event.time = my_time
                
                logging.warning("Something is happening!")
                
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
            course_id = generateID()
            course.course_id = course_id
            course.documents_list = [""]
            course.syllabus = None
            course.put()
            memcache.set(course.course_id, course)
            
            user_data.courses.append(course.key()) #Add course key to user data
            user_data.put()
            memcache.set(user_data.user_id, user_data)
            
            new_course = search.Document(
            doc_id = course_id,
            fields = [
                search.TextField(name='course_name', value = self.request.get('course')),
                search.TextField(name='instructor', value = self.request.get('name')),
                search.TextField(name='email', value = self.request.get('email')),
                search.TextField(name='university', value = self.request.get('university')),
                search.TextField(name='department', value = self.request.get('department')),
                search.TextField(name='semester', value = self.request.get('semester')),
                search.TextField(name='ID', value = str(course_id)),
                search.NumberField(name='year', value = int(self.request.get('year')))
                ])
            try:
                search.Index(name='courseIndex').put(new_course)
            except search.Error:
                logging.debug('Indexing ERROR!') 
                self.redirect('/error')
            
            self.redirect('/instructor')
        else:
            #Else - not logged in or not in our datastore
            self.redirect(users.create_login_url('/instructor'))   
            
class SearchHandler(webapp2.RequestHandler) :
    """Request handler for Search page"""
    def get(self):
        #search should not be handled as a GET request ever (no searchable data has been posted!)
        logging.debug('SearchHandler GET request: ' + str(self.request) + id)
        self.redirect('/error')
    
    def post(self):
        
        #get the search index
        index = search.Index(name='courseIndex')
        
        #get search parameters`
        course = self.request.get('course')
        instructor = self.request.get('instructor')
        email = self.request.get('email')
        university = self.request.get('university')
        department = self.request.get('department')
        semester = self.request.get('semester')
        year = self.request.get('year')  
        
        query_exists = False 
        #build the query string
        
        #The following is ugly, but basically you just don't want misplaced ORs or extra ORs in the query string        
        query_str = ""
        if str(course) != "":
            query_str = query_str + "course_name=\"" + str(course) +"\"" 
            query_exists = True
        if str(instructor) != "":
            if query_exists == True: 
                query_str = query_str + " OR "
            else:
                query_exists = True
            query_str = query_str + "instructor=\"" + str(instructor) +"\"" 
        if str(email) != "":
            if query_exists == True:
                query_str = query_str + " OR "
            else:
                query_exists = True
            query_str = query_str + "email=\"" + str(email) +"\""    
        if str(university) != "":
            if query_exists == True: 
                query_str = query_str + " OR "
            else:
                query_exists = True
            query_str = query_str + "university=\"" + str(university) +"\""        
        if str(department) != "":
            if query_exists == True: 
                query_str = query_str + " OR "
            else:
                query_exists = True
            query_str = query_str + "department=\"" + str(department) +"\""      
        if str(semester) != "":
            if query_exists == True: 
                query_str = query_str + " OR "
            else:
                query_exists = True
            query_str = query_str + "semester=\"" + str(semester) +"\""     
        if str(year) != "":
            if query_exists == True: 
                query_str = query_str + " AND "
            else:
                query_exists = True
            query_str = query_str + "year=\"" + str(year) +"\""     
        ##query_str = query_str + " OR email=" + str(email) + " OR university=" + str(university)
        ##query_str = query_str + " OR department=" + str(department) + " OR semester=" + str(semester)
        ##query_string = query_string + " OR year=" + str(year)
        
        ##On the reasonably safe assumption that nobody is named NULL0NULL
        ##Because the empty query_str would return everything in the search index up to the search limit, indiscriminately.
        if query_str == "":
            query_str = "instructor=\"" + "NULL" +"\""
        
        logging.warning(query_str)
        
        #get the 3 sort keys
        sort1 = search.SortExpression(expression='university', direction=search.SortExpression.DESCENDING, default_value="")
        sort2 = search.SortExpression(expression='instructor', direction=search.SortExpression.DESCENDING, default_value="")
        sort3 = search.SortExpression(expression='course', direction=search.SortExpression.DESCENDING, default_value="")
        sort_opts = search.SortOptions(expressions=[sort1,sort2,sort3])
        
        #build query options
        query_options = search.QueryOptions(
            limit = 10,
            sort_options = sort_opts)
        
        #search
        search_list = []
        query = search.Query(query_string=query_str, options=query_options)
        try:
            result = index.search(query)
            logging.warning("Number of documents found: " + str(int(result.number_found))) 
            
            for doc in result:
                result_x = {
                'course_name' : doc.field('course_name').value,
                'instructor' : doc.field('instructor').value,
                'email' : doc.field('email').value,
                'university' : doc.field('university').value, 
                'department' : doc.field('department').value,
                'semester' : doc.field('semester').value,
                ##To make sure that year formats as '2014' and not '2014.0'
                'year' : "{:.0f}".format(doc.field('year').value),
                'url' : "/" + str(doc.field('ID').value)
                }
                search_list.append(result_x)
                                       
        except search.Error:
            logging.debug("Error with querying!")
           
               
        template_values = {
                    'page_title' : 'Search Results',
                    'current_year' : date.today().year,
                    'current_month' : date.today().month,
                    'user' : getCurrentUserData(),
                    'search_list' : search_list,
                    'login' : users.create_login_url('/'),
                    'logout' : users.create_logout_url('/')
                }

        renderTemplate(self.response, 'search.html', template_values) 
         
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
                                
                self.redirect(user_data.current_course_selected)
                return            
                
        #if no data was received, redirect to new course page (to make data)
        self.redirect(users.create_login_url('/instructor')) 


        
        
# list of URI/Handler routing tuples
# the URI is a regular expression beginning with root '/' char
routeHandlers = [
    (r'/about', AboutHandler),
    ('/([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12})-new_event', NewCalendarEventHandler),
    ('/([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-[a-f0-9]{12})', CourseHandler), #Default catch all to handle a course page request
    ('/([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12})-event-(\d+)-(\d+)-(\d+)', EventListHandler),
    (r'/course_list', CourseListHandler), #Handles JSON to list courses on /instructor
    (r'/course_deleted', CourseDeletedHandler),
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
    (r'/search', SearchHandler),
    (r'/.*', ErrorHandler)
]

# application object
application = webapp2.WSGIApplication(routeHandlers, debug=True)

application.error_handlers[404] = handle404
