from flask import Flask, request, jsonify
from werkzeug .security import generate_password_hash,check_password_hash
import random
from pymongo import MongoClient
from pymongo import  errors
from dotenv import load_dotenv
from bson import ObjectId,Binary
from flask_pymongo import PyMongo
from datetime import datetime
import os
import re

load_dotenv()

app = Flask(__name__)



app.config["MONGO_URI"] = "mongodb://localhost:27017/linking_db"
mongo_c = PyMongo(app)

app.config["MONGO_URI"] = "mongodb://localhost:27017/Students"
mongo_s = PyMongo(app)

app.config['MONGO_URI'] = 'mongodb://localhost:27017/Parents'
mongo_p = PyMongo(app)

app.config['MONGO_URI'] = 'mongodb://localhost:27017/Teachers'
mongo_t = PyMongo(app)

app.config['MONGO_URI'] = 'mongodb://localhost:27017/Managements'
mongo_m = PyMongo(app)



@app.route('/')
def home():
    return "Connection"


def get_student(user_id):
    user = mongo_s.db.student_profile.find_one({'user_id': user_id})
    if user:
        user['_id'] = str(user['_id'])  # Convert ObjectId to a string
    return (user)

def get_parent(user_id):
    user = mongo_p.db.parent_profile.find_one({'parent_useridname': user_id})
    if user:
        user['_id'] = str(user['_id'])  # Convert ObjectId to a string
    return (user)


def generate_unique_code():
    return ''.join(random.choices('0123456789', k=6))

#for generating unique code
@app.route('/connection/register', methods=['POST'])        #student/teacher
def register_connection():
    try:
        user_id = request.json.get('user_id')  # User Id of the person trying to connect;
        role = request.json.get('role')    #Role of person trying to connect
        unique_code = generate_unique_code()
        now = datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        if role == 'parent':
            user = get_parent(user_id) 
            user_name=user["parent_name"]
            user_image=user["parent_image"]
        
        elif role =='student':
            user = get_student(user_id)
            user_name=user['username']
            user_image=user['user_image']

        profile = mongo_c.db.connection.find_one({"user_id": user_id})
        if profile:
        # Check if the generated code is unique
            while mongo_c.db.connection.find_one({"unique_code": unique_code}):
                unique_code = generate_unique_code()
            profile['unique_code']= unique_code
            mongo_c.db.connection.update_one({"user_id": user_id}, {"$set": profile})
        else:

            connection = {"user_id": user_id,
                        "role":role, 
                        "unique_code": unique_code,
                            "user_name":user_name, 
                            "user_image":user_image, 
                            "timestamp":timestamp}
            mongo_c.db.connection.insert_one(connection)
        
        return jsonify({ "user_id": user_id,"role":role, "unique_code": unique_code})
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500



#For Entering code and make connection
@app.route('/connection/achieved', methods=['POST'])
def acheived_connection():
    try:
        # Get input data from the request
        unique_code = request.json.get('unique_code', '') #exist code that you already generated
        user_id = request.json.get('user_id', '')       # The person logged in; 
        role = request.json.get('role', '')             #Role of person logged in ;

        if not unique_code or not user_id or not role:
            return jsonify({"message": "Missing required data in the request."}), 400

        if role == 'parent':
            parent = mongo_p.db.parent_profile.find_one({"parent_useridname": user_id})
            student_array = None

            if parent:
                student_array = parent.get("child")

            user = get_parent(user_id)
            user_name = user.get("parent_name", "")
            user_image = user.get("parent_image", "")
            user_details = {
                'user_id': user_id,
                'user_name': user_name,
                'user_image': user_image
            }

        elif role == 'student':
            student = mongo_s.db.student_profile.find_one({"user_id": user_id})
            parents_array = None

            if student:
                parents_array = student.get("parents")

            user = get_student(user_id)
            user_name = user.get('username', "")
            user_image = user.get('user_image', "")
            user_details = {
                'user_id': user_id,
                'user_name': user_name,
                'user_image': user_image
            }

        connect = mongo_c.db.connection.find_one({'unique_code': unique_code})

        if unique_code == connect.get('unique_code', ''):
            generator_user_id = connect.get("user_id", "")
            generator_role = connect.get("role", "")
            generator_image = connect.get("user_image", "")
            generator_name = connect.get("user_name", "")
            generator_details = {
                'user_id': generator_user_id,
                'user_name': generator_name,
                'user_image': generator_image
            }

            if generator_role == 'student':
                if student_array:
                    for i in student_array:
                        if i["user_id"] != connect["user_id"]:
                            #Adding in student profile
                            mongo_s.db.student_profile.update_one({"user_id": generator_user_id }, {"$push": {"parents": user_details}})
                            #Adding in parent profile
                            mongo_p.db.parent_profile.update_one({"parent_useridname": user_id}, {"$push": {"child": generator_details}})
                        else:
                            return jsonify({"message": "Already Connected"}), 400
                else:
                    #Adding in student profile
                    mongo_s.db.student_profile.update_one({"user_id": generator_user_id }, {"$push": {"parents": user_details}})
                    #Adding in parent profile
                    mongo_p.db.parent_profile.update_one({"parent_useridname": user_id}, {"$push": {"child": generator_details}})
                    return jsonify({"message": "Connected successfully"}), 200

            elif generator_role == 'parent':
                if parents_array:
                    for i in parents_array:
                        if i["user_id"] != connect["user_id"]:
                            #Adding in student profile
                            mongo_s.db.student_profile.update_one({"user_id": user_id }, {"$push": {"parents": generator_details}})
                            #Adding in parent profile
                            mongo_p.db.parent_profile.update_one({"parent_useridname": generator_user_id}, {"$push": {"child": user_details}})
                        else:
                            return jsonify({"message": "Already Connected"}), 400
                else:
                    #Adding in student profile
                    mongo_s.db.student_profile.update_one({"user_id": user_id }, {"$push": {"parents": generator_details}})
                    #Adding in parent profile
                    mongo_p.db.parent_profile.update_one({"parent_useridname": generator_user_id}, {"$push": {"child": user_details}})
            return jsonify({"message": "Connected successfully"}), 200
        else:
            return jsonify("Enter Valid Code")
    except Exception as e:
        return jsonify({"message": "An error occurred.", "error": str(e)}), 500
  
    
#management register 
@app.route('/management/register', methods=['POST'])
def register_management():
    try:
        username = request.json.get('username')         #username of management
        schoolname = request.json.get('schoolname')        #Schoolname of management
        user_image = request.json.get('user_image')
        unique_code = generate_unique_code()

        profile = mongo_c.db.management_connection.find_one({"username": username})
        
        if profile:
            while mongo_c.db.management_connection.find_one({"unique_code": unique_code}):
                unique_code = generate_unique_code()
            profile["unique_code"] = unique_code
            mongo_c.db.management_connection.update_one({"username": username}, {"$set": profile})
        else:
            management = {
                "username": username,
                "schoolname": schoolname,
                "user_image": user_image,
                "unique_code": unique_code,
            }

            mongo_c.db.management_connection.insert_one(management)

        return jsonify({"username": username,"schoolname": schoolname,
            "user_image": user_image,"unique_code": unique_code
        })
    except Exception as e:
        return jsonify({"error": "An error occurred.", "details": str(e)}), 500

#Get management generated code
@app.route('/get_management_generated_code/<username>', methods=['GET'])
def get_management_generated_code(username):            #username of management
    try:
        management_data  = mongo_c.db.management_connection.find_one({"username": username})
        if management_data:
            code = management_data['unique_code']
            return jsonify({"Unique Code":code})
        else:
            return jsonify("management not found")
    except Exception as e:
        return jsonify({"error": "An error occurred.", "details": str(e)}), 500


#proceed for requesting to management
@app.route('/request_management_achieved', methods=['POST'])
def request_management_achieved():
    try:
        unique_code = request.json.get('unique_code')  # Enter code shared by management
        user_id = request.json.get('user_id')  # Candidate user_id
        role = request.json.get('role')  # Candidate role

        # Check if the code exists in the management_connection collection
        code_entry = mongo_c.db.management_connection.find_one({"unique_code": unique_code})
        if not code_entry:
            return jsonify({"error": "Invalid code"}), 400

        if role == 'student':
            user = mongo_s.db.student_profile.find_one({"user_id": user_id})
            if user:
                now = datetime.now()
                student_data = {
                    "user_id": user_id,
                    "username": user["username"],
                    "user_image": user["user_image"],
                    "user_class": user["user_class"],
                    "reject": False,
                    "accept": False,
                    "current_time": now.strftime("%d-%m-%Y %H:%M:%S")
                }
                modify_count = 0
                for exist in code_entry.get('students',[]):
                    if exist['user_id']==user_id:
                        mongo_c.db.management_connection.update_one(
                        {"_id": code_entry["_id"], "students.user_id": user_id},
                        {
                            "$set": {
                                "students.$.username": user["username"],
                                "students.$.user_image": user["user_image"],
                                "students.$.user_class": user["user_class"],
                                "students.$.reject": False,  # Set reject to False during update
                                "students.$.accept": False,
                                "current_time": now.strftime("%d-%m-%Y %H:%M:%S")
                            }
                        })
                        modify_count+=1
                        break
                if modify_count==0:
                    mongo_c.db.management_connection.update_one({"_id": code_entry["_id"]}, {
                        "$push": {"students": student_data}
                    })
                
                management = {
                    "username": code_entry["username"],
                    "schoolname": code_entry["schoolname"],
                    "user_image": code_entry["user_image"],
                    "reject": False,
                    "accept": False,
                    "current_time": now.strftime("%d-%m-%Y %H:%M:%S")
                }

                # Save management data to the student's profile
                mongo_s.db.student_profile.update_one({"user_id": user_id}, {
                    "$set": {"management":management }
                })
            else:
                return jsonify({"error": "User not found"}), 400
        elif role == 'teacher':
            user = mongo_t.db.teacher_profile.find_one({'profile.useridname_password.userid_name': user_id})
            if user:
                now = datetime.now()
                teacher_data = {
                    "username": user['username'],
                    "user_id": user["profile"]["useridname_password"]["userid_name"],
                    "user_image": user["user_image"],
                    "languages": user["languages"],
                    "reject": False,
                    "accept": False,
                    "current_time": now.strftime("%d-%m-%Y %H:%M:%S")
                }
                modify_count = 0
                for exist in code_entry.get('teachers',[]):
                    if exist['user_id']==user_id:
                        mongo_c.db.management_connection.update_one(
                        {"_id": code_entry["_id"], "teachers.user_id": user_id},
                        {
                            "$set": {
                                "teachers.$.username": user['username'],
                                "teachers.$.user_image": user["profile"]["useridname_password"]["userid_name"],
                                "teachers.$.languages": user["user_image"],
                                "teachers.$.reject": False,  # Set reject to False during update
                                "teachers.$.accept": False,
                                "current_time": now.strftime("%d-%m-%Y %H:%M:%S")
                            }
                        })
                        modify_count+=1
                        break
                if modify_count==0:
                    mongo_c.db.management_connection.update_one({"_id": code_entry["_id"]}, {
                        "$push": {"teachers": teacher_data}
                    })

                management = {
                    "username": code_entry["username"],
                    "schoolname": code_entry["schoolname"],
                    "user_image": code_entry["user_image"],
                    "reject": False,
                    "accept": False,
                    "current_time": now.strftime("%d-%m-%Y %H:%M:%S")
                }

                # Save management data to the teacher's profile
                mongo_t.db.teacher_profile.update_one(
                    {"profile.useridname_password.userid_name": user_id},
                    {"$set": {"management": management}}
                )
            else:
                return jsonify({"error": "User not found"}), 400
        else:
            return jsonify({"error": "Invalid role"}), 400

        return jsonify({"message": "Data appended & request sent to management successfully."})
    except Exception as e:
        return jsonify({"error": "An error occurred.", "details": str(e)}), 500

#To check request status in self profile 
@app.route('/management_pending_requests/<role>/<user_id>', methods=['GET'])
def management_pending_requests(user_id,role):
    try:
        if role == "teacher":
            role_data = mongo_t.db.teacher_profile.find_one({"profile.useridname_password.userid_name": user_id})
            requests_status = role_data.get("management", [])
        elif role == "student":
            role_data = mongo_s.db.student_profile.find_one({"user_id": user_id})
            requests_status = role_data.get("management", [])
        else:
            return jsonify({"error": "Invalid role"})
            
        return jsonify(requests_status)
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500



#teachers_pending_requests in management

@app.route('/teachers_pending_requests/<username>', methods=['GET'])
def teachers_pending_requests(username):
    try:
        # Check if the username exists in the management_connection collection
        management_entry = mongo_c.db.management_connection.find_one({"username": username})
        
        if not management_entry:
            return jsonify({"error": "Invalid username"}), 400

        # Retrieve the student and teacher requests
        teachers_requests = management_entry.get("teachers", [])
        
        # Filter requests where both "reject" and "accept" are "False"
        filtered_requests = [request for request in teachers_requests if request.get("reject") == False and request.get("accept") == False]
        
        # Construct a response with the filtered requests
        response = {
            "teachers": filtered_requests
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500


#students_pending_requests in management
@app.route('/students_pending_requests/<username>', methods=['GET'])
def students_pending_requests(username):
    try:
        # Check if the username exists in the management_connection collection
        management_entry = mongo_c.db.management_connection.find_one({"username": username})
        
        if not management_entry:
            return jsonify({"error": "Invalid username"}), 400

        # Retrieve the student and teacher requests
        student_requests = management_entry.get("students", [])
        
        # Filter requests where both "reject" and "accept" are "False"
        filtered_requests = [request for request in student_requests if request.get("reject") == False and request.get("accept") == False]
        
        # # Construct a response with the filtered requests
        response = {
            "students": filtered_requests
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500

#Recieved response that done by management on candidate request
@app.route('/request_response/<username>/<user_id>/<role>/<response>', methods=['POST'])
def request_response(username, user_id, role, response):
    try:
        # Check if the username exists in the management_connection collection
        management_data = mongo_c.db.management_connection.find_one({"username": username})
        
        if not management_data:
            return jsonify({"error": "Invalid username"}), 400

        # Determine whether it's a teacher or student
        if role == "teacher":
            role_data = mongo_t.db.teacher_profile.find_one({"profile.useridname_password.userid_name": user_id})
            data_list = management_data['teachers']
        elif role == "student":
            data_list = management_data['students']
            role_data = mongo_s.db.student_profile.find_one({"user_id": user_id})
        elif role_data is None:
            return jsonify("role_data is not found")
        else:
            return jsonify({"error": "Invalid role"}), 400
        
        # Find the specific user in the data list
        user = None
        for i in data_list:
            if i["user_id"] == user_id:
                user = i
        
        if not user:
            return jsonify({"error": "User not found"}), 400

        # Update the "reject" or "accept" status based on the 'response' parameter
        if response == 'accept':
            user['accept'] = True
            user['reject'] = False
        elif response == 'reject':
            user['accept'] = False
            user['reject'] = True

        # Update the management_connection document
        mongo_c.db.management_connection.update_one({"username": username}, {"$set": {role + "s": data_list}})
        
        # Update the role-specific document (e.g., teacher_profile or student_profile)
        if role_data:
            role_data['management']['accept'] = True if response == 'accept' else False
            role_data['management']['reject'] = True if response == 'reject' else False
            # Update the role-specific data
            if role == "teacher":
                mongo_t.db.teacher_profile.update_one({"profile.useridname_password.userid_name": user_id}, {"$set": role_data})
            elif role == "student":
                mongo_s.db.student_profile.update_one({"user_id": user_id}, {"$set": role_data})

        return jsonify({"message": f"{role} request response updated successfully."})
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500


# For accepting or rejecting all users whose are in pending means "accept" and "reject" is False 
@app.route('/accept_or_reject_all/<username>/<role>/<response>', methods=['POST'])
def accept_or_reject_all_responses(username, role, response):
    try:
        # Fetch the management data for the specified username
        management_data = mongo_c.db.management_connection.find_one({"username": username})

        if not management_data:
            return jsonify({"error": "Invalid username"}), 400

        if response not in ['accept', 'reject']:
            return jsonify({"error": "Invalid response specified"}), 400

        if role == "teacher":
            data_list = management_data['teachers']
            for user in data_list:
                user_id = user['user_id']
                role_data = mongo_t.db.teacher_profile.find_one({'profile.useridname_password.userid_name': user_id})
                if role_data and not (role_data['management']['accept'] or role_data['management']['reject']):
                    # Only  if both 'accept' and 'reject' are False
                    if response == 'accept':
                        role_data['management']['accept'] = True
                        role_data['management']['reject'] = False
                    elif response == 'reject':
                        role_data['management']['accept'] = False
                        role_data['management']['reject'] = True
                    # Update the teacher_profile document with the modified data
                    mongo_t.db.teacher_profile.update_one(
                        {"profile.useridname_password.userid_name": user_id},
                        {"$set": role_data}
                    )

        elif role == "student":
            data_list = management_data['students']
            for user in data_list:
                user_id = user['user_id']
                role_data = mongo_s.db.student_profile.find_one({'user_id': user_id})
                if role_data and not (role_data['management']['accept'] or role_data['management']['reject']):
                    # Only  if both 'accept' and 'reject' are False
                    if response == 'accept':
                        role_data['management']['accept'] = True
                        role_data['management']['reject'] = False
                    elif response == 'reject':
                        role_data['management']['accept'] = False
                        role_data['management']['reject'] = True
                    # Update the student_profile document with the modified data
                    mongo_s.db.student_profile.update_one(
                        {"user_id": user_id},
                        {"$set": role_data}
                    )

        else:
            return jsonify({"error": "Invalid role"}), 400

        # Iterate over teachers or students and set 'accept' and 'reject' based on the response
        data_list = management_data.get(role+'s', [])
        for user in data_list:
            if not (user['accept'] or user['reject']):
                # Only if both 'accept' and 'reject' are False
                if response == 'accept':
                    user['accept'] = True
                    user['reject'] = False
                elif response == 'reject':
                    user['accept'] = False
                    user['reject'] = True

        # Update the management_connection document with the modified data
        mongo_c.db.management_connection.update_one({"username": username}, {"$set": {role+'s': data_list}})

        return jsonify({"message": f"All {role} requests {response}ed successfully for users with 'accept' and 'reject' set to False."})
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500
    
#####################################
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'jfif'} 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def validate_password(password):
     """
     Validates password based on the following conditions:
     - At least 8 characters long
     - Contains at least one digit
     - Contains at least one uppercase letter
     - Contains at least one special character
     """
     if len(password) < 8:
         return False
     if not re.search("[0-9]", password):
         return False
     if not re.search("[A-Z]", password):
         return False
     # Assuming special characters are !@#$%^&*()-_+=
     if not re.search("[!@#$%^&*()\-_+=]", password):
         return False
     return True

def get_students():
    return list(mongo_s.db.student_profile.find())

def check_for_user(phone, user_id):
    student_data = get_students()
    # teacher_data = get_teachers()
    # parent_data = get_parents()
    # management_data = get_managements()

    phone_exists = False
    useridname_exists = False


    if phone:
        phone_exists = any(item['personal_info']['contact']['phone'] == phone for item in student_data)
        # if not phone_exists:
        #     phone_exists = any(item['profile']['contact']['phone'] == phone for item in teacher_data)
        # if not phone_exists:
        #     phone_exists = any(item['personal_info']['contact']['parent_phone'] == phone for item in parent_data)
        # if not phone_exists:
        #     phone_exists = any(item['contact']['phone'] == phone for item in management_data)

    if user_id:
        useridname_exists = any(item['user_id'] == user_id for item in student_data)
        # if not useridname_exists:
        #     useridname_exists = any(item['profile']['useridname_password']['userid_name'] == user_id for item in teacher_data)
        # if not useridname_exists:
        #     useridname_exists = any(item['parent_useridname'] == user_id for item in parent_data)
        # if not useridname_exists:
        #     useridname_exists = any(item['username'] == user_id for item in management_data)
    
    return [phone_exists, useridname_exists]

#student_profile
@app.route('/update_student_profile/<string:user_id>', methods=['PUT'])
def update_student_profile(user_id):
    try:
        user_data = mongo_s.db.student_profile.find_one({'user_id': user_id})
        _id = user_data['_id']
        username = request.form.get('username', user_data['username'])
        password = request.form.get('password')

        if password:
            if not validate_password(password):
                return jsonify({"error": "Not valid Password."}), 400
            hashed_password = generate_password_hash(password)
        else: 
            hashed_password = user_data['password']
        user_id = request.form.get('user_id')

        user_class = request.form.get('user_class', user_data['user_class'])
        status_title = request.form.get('status_title', user_data['status_title'])
        status_description = request.form.get('status_description', user_data['status_description'])
        about = request.form.get('about', user_data['personal_info']['about'])
        phone = request.form.get('phone')
        email = request.form.get('email', user_data['personal_info']['contact']['email'])
        street = request.form.get('street', user_data['personal_info']['contact']['address']['street'])
        city = request.form.get('city', user_data['personal_info']['contact']['address']['city'])
        state = request.form.get('state', user_data['personal_info']['contact']['address']['state'])
        pincode = request.form.get('pincode', user_data['personal_info']['contact']['address']['pincode'])


        address = {
            "street":street,
            "city":city,
            'state':state,
            "pincode":pincode
        }
        # Optional: Handle the user image update
        if 'user_image' in request.files:
                image = request.files['user_image']
                if image and allowed_file(image.filename):
                    image_data = Binary(image.read())
                    image_id = mongo_s.db.images.insert_one({"image_data": image_data}).inserted_id
                    user_image = str(image_id)
                else:
                    return jsonify({"error": "Invalid image or file format."}), 400
        else:
             user_image = user_data['user_image']
        result = check_for_user(phone,user_id)
        phone_exists = result[0]
        useridname = result[1]

        if phone != user_data['personal_info']['contact']['phone'] and phone_exists:
            return jsonify({"error": "This phone number is already exist"}), 400
        elif phone != user_data['personal_info']['contact']['phone'] and request.form.get('phone'):
            phone = request.form.get('phone')
        else:
            phone = user_data['personal_info']['contact']['phone']

        if useridname != user_data['user_id'] and useridname:
            return jsonify({"error": "This useridname is already exist"}), 400
        elif useridname != user_data['user_id'] and request.form.get('user_id'):
            useridname = request.form.get('user_id')
        else:
            useridname = user_data['user_id']
        
        user_data ={
                'user_id':useridname,
                'username': username,
                'password':hashed_password,
                'user_class': user_class,
                'user_image': user_image,
                'status_title': status_title,
                'status_description': status_description,
                'personal_info': {
                    'about': about,
                    'contact': {
                        'phone': phone,
                        'email': email,
                        'address': address
                    }
                },
        
            }
        result = mongo_s.db.student_profile.update_one({"_id":_id},
                                                    {"$set": user_data})
        
        if result.modified_count == 0:
            return jsonify({"error": "No changes found"}), 400
        updated_entity = mongo_s.db.student_profile.find_one({"_id": _id})
        return jsonify(updated_entity), 200
    except errors.PyMongoError as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)