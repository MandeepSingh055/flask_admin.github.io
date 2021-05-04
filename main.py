from flask_mail import Mail
import flask_admin
from flask_admin import Admin ,AdminIndexView,expose
from flask_admin.contrib import sqla
from flask import Flask ,render_template,send_file,session
from flask_fontawesome import FontAwesome
from flask_admin import helpers as admin_helpers
from flask_security import current_user, Security,login_required, RoleMixin, SQLAlchemyUserDatastore, UserMixin, utils
from flask_sqlalchemy import SQLAlchemy
from flask_admin.menu import MenuLink
from wtforms.fields import PasswordField

from flask import Flask ,render_template,request,redirect
from flask_admin.contrib.sqla import ModelView
from flask_admin import BaseView, expose
import mysql.connector
import pandas as pd




# Initialize Flask and set some config values
app = Flask(__name__)
fa = FontAwesome(app)
app.config['DEBUG']=True
# Replace this with your own secret key
app.config['SECRET_KEY'] = 'super-secret'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:tiet@2009@localhost:3306/test'

app.config['SECURITY_PASSWORD_HASH'] = 'pbkdf2_sha512'
# Replace this with your own salt.
app.config['SECURITY_PASSWORD_SALT'] = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

db = SQLAlchemy(app)

# Create a table to support a many-to-many relationship between Users and Roles
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

# Role class
class Role(db.Model, RoleMixin):

    # Our Role has three fields, ID, name and description
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    # __str__ is required by Flask-Admin, so we can have human-readable values for the Role when editing a User.
    # If we were using Python 2.7, this would be __unicode__ instead.
    def __str__(self):
        return self.name

    # __hash__ is required to avoid the exception TypeError: unhashable type: 'Role' when saving a User
    def __hash__(self):
        return hash(self.name)


# User class
class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship(
        'Role',
        secondary=roles_users,
        backref=db.backref('users', lazy='dynamic')
    )
	
class mst_compaign(db.Model, UserMixin):

    compaign_id = db.Column(db.Integer, primary_key=True)
    compaign_code = db.Column(db.String(255))
    is_internal = db.Column(db.Boolean())
    is_active = db.Column(db.Boolean())
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())	

	
class mst_ideathon_data(db.Model, UserMixin):

    ideathon_id = db.Column(db.Integer, primary_key=True)
    compaign_id = db.Column(db.Integer)
    student_name = db.Column(db.String(255))
    institution_name = db.Column(db.String(255))
    email_id = db.Column(db.String(255))
    idea_title = db.Column(db.String(255))
    idea_description = db.Column(db.String(5000))
    interest_area = db.Column(db.String(255))
    registration_date = db.Column(db.Date())
    idea_status = db.Column(db.Boolean())

# Initialize the SQLAlchemy data store and Flask-Security.
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# Executes before the first request is processed.
@app.before_first_request
def before_first_request():

    # Create any database tables that don't exist yet.
    db.create_all()

    # Create the Roles "admin" and "end-user" -- unless they already exist
    user_datastore.find_or_create_role(name='admin', description='Administrator')
    user_datastore.find_or_create_role(name='end-user', description='End user')

    # Create two Users for testing purposes -- unless they already exists.
    # In each case, use Flask-Security utility function to encrypt the password.
    encrypted_password = utils.encrypt_password('password')
    if not user_datastore.get_user('someone@example.com'):
        user_datastore.create_user(email='someone@example.com', password='Mind$123')
    if not user_datastore.get_user('admin@example.com'):
        user_datastore.create_user(email='admin@example.com', password='mind$123')

    # Commit any database changes; the User and Roles must exist before we can add a Role to the User
    db.session.commit()

    user_datastore.add_role_to_user('someone@example.com', 'end-user')
    user_datastore.add_role_to_user('admin@example.com', 'admin')
    db.session.commit()


# Displays the home page.
@app.route('/')
@login_required
def index():
    return redirect("/admin", code=302)

@app.route('/download_attachments/<string:filename>', methods=['GET','POST'])
def download_attachments(filename):
    filepath = "C:\\Users\\mandeep2singh\\Desktop\\ideathon_views_testing\\views\\Ideathon_Home_Test\\Docs\\" + filename
    return send_file(filepath, as_attachment=True)
	
@app.route('/download_images/<string:filename>', methods=['GET','POST'])
def download_images(filename):
    filepath = "C:\\Users\\hp\\Desktop\\ideathon_views_testing\\New folder\\Flask_Admin\\images\\" + filename
    return send_file(filepath, as_attachment=True)

# Customized User model for SQL-Admin
class UserAdmin(sqla.ModelView):

    column_exclude_list = ('password',)
    form_excluded_columns = ('password',)

    column_auto_select_related = True

    # Prevent administration of Users unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role('admin')

    # On the form for creating or editing a User, don't display a field corresponding to the model's password field.
    # There are two reasons for this. First, we want to encrypt the password before storing in the database. Second,
    # we want to use a password field (with the input masked) rather than a regular text field.
    def scaffold_form(self):

        # Start with the standard form as provided by Flask-Admin. We've already told Flask-Admin to exclude the
        # password field from this form.
        form_class = super(UserAdmin, self).scaffold_form()

        # Add a password field, naming it "password2" and labeling it "New Password".
        form_class.password2 = PasswordField('New Password')
        return form_class

    # This callback executes when the user saves changes to a newly-created or edited User -- before the changes are
    # committed to the database.
    def on_model_change(self, form, model, is_created):

        # If the password field isn't blank...
        if len(model.password2):

            # ... then encrypt the new password prior to storing it in the database. If the password field is blank,
            # the existing password in the database will be retained.
            model.password = utils.encrypt_password(model.password2)


# Customized Role model for SQL-Admin
class RoleAdmin(sqla.ModelView):

    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role('admin')

class Ideathon_Table(sqla.ModelView):

    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    __tablename__='Ideathon Data'
    can_edit=False
    can_delete=False
    
    def is_accessible(self):
        return current_user.has_role('admin')

class NotificationsView(BaseView):
    @expose('/',methods=('GET','POST'))
    def index(self):
        conn = mysql.connector.connect(
        user="root",
        password="tiet@2009",
        host="localhost",
        database="test")
        campaign_id=''
        fetch_connector_value = '''select i.ideathon_id,i.student_name,i.institution_name,i.email_id,i.idea_title, count(v.ideathon_id) as number_of_votes from mst_ideathon_data i left join voting v 
								on i.ideathon_id = v.ideathon_id
								group by i.ideathon_id;
								'''
        if request.method == 'POST': 
            try:
                campaign_id = request.form['campaign_id']
            except:
                pass
          
            if(len(campaign_id) != 0):
                flag=1
                fetch_connector_value = "select i.ideathon_id,i.student_name,i.institution_name,i.email_id,i.idea_title, count(v.ideathon_id) as number_of_votes from mst_ideathon_data i left join voting v on i.ideathon_id = v.ideathon_id where i.compaign_id = " + campaign_id + " group by i.ideathon_id" 
        df_schedule_details = pd.read_sql(fetch_connector_value, conn)
        dct = df_schedule_details.to_dict('records')
        #print("***Dict*",df_connector)
        return self.render('admin/notify.html',result=dct,current_user=current_user,campaign_id=campaign_id)

    def is_accessible(self):
        return current_user.has_role('admin')
		
class SteeringCommitteView(BaseView):
    @expose('/',methods=('GET','POST'))
    def index(self):
        from datetime import date
        flag=0
        campaign_id=''
        close_image=''
        row_index=0
        campaign_dict={}
        today = date.today()
        conn = mysql.connector.connect(
        user="root",
        password="tiet@2009",
        host="localhost",
        database="test")
        cursor = conn.cursor()
        fetch_connector_value = "select i.ideathon_id,i.student_name,i.institution_name,i.compaign_id,i.email_id,i.idea_title,f.display_name ,f.file_name from mst_ideathon_data i left join file_info f on i.ideathon_id = f.ideathon_id"
			
        if request.method == 'POST':
            try:
                campaign_id = request.form['campaign_id']
            except:
                pass
            try:
                campaign_id = request.form['selected_campaign_id']
            except:
                pass	
				
            try:
                campaign_id_val = request.form['campaign_id_val']
            except:
                pass	
				
            try:	    
                ideathon_id_val = request.form['fname']
                row_index = request.form['row_index']
                like_btn_val = request.form['vote_btn']
				
                if(int(like_btn_val) == 1):
                    print('************Like Running************')
                    insert_into_vote_table = (
	                'insert into voting(ideathon_id,user_id,vote_date,campaign_id) values(%s,%s,%s,%s);'
                     )
                    insert_data = (ideathon_id_val,current_user.id,today,int(campaign_id_val))
                    cursor.execute(insert_into_vote_table, insert_data)
				
                else:
                    print('**********Delete Running**************')
                    delete_from_vote_table = (
                     "delete from voting where user_id = " + str(current_user.id) + " and ideathon_id = %s"
                    )
                    delete_data = (ideathon_id_val,)	
                    cursor.execute(delete_from_vote_table,delete_data)
                conn.commit()
            except:
                pass
            #print('****   Like Button  *****',like_btn_val)
            if(len(campaign_id) != 0):
                flag=1
                fetch_connector_value = "select i.ideathon_id,i.student_name,i.institution_name,i.compaign_id,i.email_id,i.idea_title,f.display_name ,f.file_name from mst_ideathon_data i left join file_info f on i.ideathon_id = f.ideathon_id where i.compaign_id=" + campaign_id
		
			
       
        df_ideathon = pd.read_sql(fetch_connector_value, conn)
        id_list=[]
        fetch_liked_values = "select ideathon_id from voting where  user_id = " + str(current_user.id) + " group by ideathon_id"
        df_like_list_details = pd.read_sql(fetch_liked_values, conn)
        id_list=(df_like_list_details['ideathon_id']).to_list()	
		
        fetch_campaign_id = "select compaign_id from mst_ideathon_data group by compaign_id"
        df_campaign_list = pd.read_sql(fetch_campaign_id, conn)
        campaign_id_list=(df_campaign_list['compaign_id']).to_list()	
		
        print('**************',campaign_id_list)
		
        for ele in campaign_id_list:
            campaign_dict[ele]="Campaign " + str(ele)
			
			
        print("***Dict**",campaign_dict)
		
		
       
      
        return self.render('admin/steering.html',result=df_ideathon,current_user=current_user,id_list=id_list,campaign_id=campaign_id,row_value=row_index,campaign_dict=campaign_dict)
    
    def is_accessible(self):
        return current_user.has_role('end-user')


	
class IdeathonCampaignView(sqla.ModelView):

    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role('admin')


class DashboardView(AdminIndexView):

    def is_visible(self):
        return False
		
    @expose('/')
    def index(self):
	
        session.pop('_flashes', None)

        return self.render(
            'admin/index.html',
        )
		
		
admin = Admin(app,
		name='',
        template_mode='bootstrap3',
        index_view=DashboardView())

# Add Flask-Admin views for Users and Roles
admin.add_view(UserAdmin(User, db.session))
admin.add_view(Ideathon_Table(mst_ideathon_data, db.session,category='Ideathon Data',name='Ideathon Data Table'))
admin.add_view(IdeathonCampaignView(mst_compaign, db.session,name='Ideathon Campaign'))
admin.add_view(SteeringCommitteView(name='Ideathon Report', endpoint='steering'))
admin.add_view(NotificationsView(name='Ideathon Report', endpoint='notify'))
admin.add_link(MenuLink(name='Sign Out', url='/logout' ))
admin.add_link(MenuLink(name='Ideathon Participation Form', url='http://ideathon.eastus.cloudapp.azure.com:8080/query?param1=mind_4362a82405234da7ba307d09d24',category='Ideathon Data' ))



if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int('6777'),
        debug=app.config['DEBUG']
    )
