# import modules
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
import pyotp
import datetime
import time
import sqlite3 as sqlite4
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import csv
import redis
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from reportlab.platypus.flowables import Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
import os
import zipfile
from pdf417gen import encode, render_image
from PIL import Image as PILImage
from PyPDF4 import PdfFileMerger


# assume tax rate is 30%
TAX_RATE = 0.3

# assume Employer name is Gravitation Studio
EMPLOYER_NAME = "Gravitation Studio"

# available fund for payrolls, can integrate with bank API to get the balance
BALANCE = str(10242048.69).format(",.2f")

# start redis server
os.system("redis-server --daemonize yes")

# Initialize redis
r = redis.Redis(host='localhost', port=6379, db=0)


# initialize flask
app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../db/payroll.db'
#db = SQLAlchemy(app)

# Define routes and views
# Implement user registration, login, dashboard, employee management, etc.

# Make session expire in 10 minutes
app.config["PERMANENT_SESSION_LIFETIME"] = 600
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# global variables for register
tmp = {"usr":"","passwd":"","otp":""}

# login required decorator
def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

# index route
"""
Table schema:
CREATE TABLE employee (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, wage REAL NOT NULL, sin_num TEXT NOT NULL);
CREATE TABLE payrolls (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, employeeid INTEGER NOT NULL, hour REAL NOT NULL, date TEXT NOT NULL, FOREIGN KEY(employeeid) REFERENCES employee(id));
CREATE TABLE management (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, passwd TEXT NOT NULL, otp TEXT NOT NULL);
"""
@app.route('/', methods=['GET'])
@login_required
def index():
    sql = sqlite4.connect('../db/payroll.db', timeout=30)
    c = sql.cursor()
    e = c.execute("SELECT * FROM employee").fetchall()
    p = c.execute("SELECT * FROM payrolls").fetchall()
    e = len(e)
    # Get the employee id, name, sin number, wage, and employment income
    # database in " yyyy-mm-dd hh:mm:ss"
    tmp = c.execute("SELECT employee.id, employee.name, employee.sin_num, employee.wage, SUM(payrolls.hour * employee.wage), payrolls.date, payrolls.hour FROM employee JOIN payrolls ON employee.id = payrolls.employeeid WHERE payrolls.date BETWEEN \"{0}\" AND \"{1}\" GROUP BY employee.id;".format((datetime.datetime.now() - datetime.timedelta(days=120)).strftime(" %Y-%m-%d"), datetime.datetime.now().strftime(" %Y-%m-%d")))
    # if not found, return not found error
    employee_data = {}
    for row in tmp.fetchall():
        if row == None:
            return redirect('/notfound')
        employee_data[row[0]] = {"employee_id":row[0],"name": row[1], "sin_num": row[2], "wage": row[3], "employment_income": row[4], "employer_name": EMPLOYER_NAME, "date": row[5], "hour": row[6]}
    # Calculate tax deducted for each employee
    for employee_id in employee_data:
        employee_data[employee_id]["tax_deducted"] = employee_data[employee_id]["employment_income"] * TAX_RATE
        employee_data[employee_id]["payout"] = employee_data[employee_id]["employment_income"] - employee_data[employee_id]["tax_deducted"]

    print(employee_data)
    sql.close()

    return render_template("index.html",employee=e,balance=BALANCE,instances=employee_data)

# logout route
@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect("/login")

# login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        sql = sqlite4.connect("../db/payroll.db", timeout=30)
        c = sql.cursor()
        usr = request.form.get("username")
        pwd = request.form.get("password")
        print(pwd)
        otpcode = request.form.get("otpcode")
        rows = c.execute("SELECT * FROM management WHERE username=\"{0}\"".format(usr,pwd)).fetchall()
        print(rows)
        if len(rows) == 0 or not check_password_hash(
            rows[0][2], pwd
        ):
            print(generate_password_hash(pwd))
            print("error 1")
            sql.close()
            return userError()
        totp = pyotp.TOTP(rows[0][3])
        if checkTOTP(otpcode): # if the otp code is used, denie this login
            print("error 3")
            sql.close()
            session.clear()
            return userError()
            
        if totp.verify(otpcode):
            session["user_id"] = rows[0][2]
            sql.close()
            recordTOTP(otpcode)
            return redirect("/")
        print("error 2")
        sql.close()
        return userError()
    return render_template("login.html")

# register route
@app.route('/register', methods=['GET','POST'])
def register():
    session.clear()
    tmp = {"usr":"","passwd":"","otp":""}
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("ps1")
        password2 = request.form.get("ps2")
        if username == "":
            return userError()
        if password != password2:
            return userError()
        print(username, password, password2)
        tmp["usr"] = username
        tmp["passwd"] = generate_password_hash(password)
        
        session["user_id"] = username

        return redirect("/setotp")
        
    return render_template("register.html")

# TOTP route
@app.route("/setotp", methods=["GET","POST"])
def setotp():
    if request.method == "POST":
        sql = sqlite4.connect('../db/payroll.db', timeout=30)
        c = sql.cursor()
        # verify if the user_id is the same as the one in the session
        if session["user_id"] != tmp["usr"]:
            sql.close()
            session.clear()
            return userError()
        c.execute("INSERT INTO management (username, passwd, otp) VALUES (\"{0}\",\"{1}\",\"{2}\");".format(tmp["usr"], tmp["passwd"], tmp["otp"]))
        sql.commit()
        sql.close()
        session.clear()
        return redirect("/login")
    secret = pyotp.random_base32()
    tmp["otp"] = secret
    return render_template("setotp.html", secret=secret)
    
# error handler when 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# error handler when 400
def userError():
    return render_template('400.html'), 400

"""
Table schema:
CREATE TABLE employee (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, wage REAL NOT NULL, sin_num TEXT NOT NULL);
CREATE TABLE payrolls (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, employeeid INTEGER NOT NULL, hour REAL NOT NULL, date TEXT NOT NULL, FOREIGN KEY(employeeid) REFERENCES employee(id));
CREATE TABLE management (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, passwd TEXT NOT NULL, otp TEXT NOT NULL);
"""

# Take employee data csv file upload and store in database
@app.route('/upload_ee', methods=['GET', 'POST']) 
def upload_ee():
    if request.method == 'POST':
        f = request.files['file']
        # open f as a file object
        filename = secure_filename(f.filename)+time.strftime('%Y%m%d-%H%M%S')+".csv"
        f.save("../uploads/" + filename)
        f = open("../uploads/"+filename, "r")
        # parse csv file and store in sqlite table employee
        csv_file = csv.reader(f)
        next(csv_file, None) # skip the header
        sql = sqlite4.connect('../db/payroll.db', timeout=30)
        c = sql.cursor()
        # export current table to csv file for backup into folder ./backup
        c.execute("SELECT * FROM employee;")
        with open(f"./backup/employee_{time.strftime('%Y%m%d-%H%M%S')}.csv", "w") as backup:
            csv.writer(backup).writerows(c.fetchall())
        # delete all rows in table employee
        c.execute("DROP TABLE employee;")
        c.execute("CREATE TABLE employee (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, wage REAL NOT NULL, sin_num TEXT NOT NULL);")
        # insert new rows from csv file to finish the update
        for row in csv_file:
            print(row)
            c.execute("INSERT INTO employee (name, wage, sin_num) VALUES (\"{0}\",\"{1}\",\"{2}\");".format(row[0], row[1], row[2]))
        sql.commit()
        sql.close()
        f.close()
        return redirect('/')
    return render_template('update_ee.html')

# Take payroll data csv file upload and store in database
@app.route('/upload_payroll', methods=['GET', 'POST'])
def upload_payroll():
    if request.method == 'POST':
        f = request.files['file']
        # open f as file object
        filename = secure_filename(f.filename)+time.strftime('%Y%m%d-%H%M%S')+".csv"
        f.save("../uploads/" + filename)
        f = open("../uploads/"+filename, "r")
        # parse csv file and store in sqlite table payroll
        csv_file = csv.reader(f)
        next(csv_file, None) # skip the header
        sql = sqlite4.connect('../db/payroll.db', timeout=30)
        c = sql.cursor()
        # export current table to csv file for backup into folder ./backup
        c.execute("SELECT * FROM payrolls;")
        with open(f"./backup/payrolls_{time.strftime('%Y%m%d-%H%M%S')}.csv", "w") as backup:
            csv.writer(backup).writerows(c.fetchall())
        for row in csv_file:
            # check if employee id exists in employee table
            ls=c.execute("SELECT * FROM employee WHERE id = {0};".format(row[0])).fetchall()
            print(row)
            print(ls)
            if len(ls) == 0:
                print("error 6")
                return userError()
            # check if date format is correct
            try:
                datetime.datetime.strptime(row[2].strip(), '%Y-%m-%d')
            except ValueError:
                print("error 4")
                return userError()
            # check if hour is a number
            try:
                float(row[1])
            except ValueError:
                print("error 5")
                return userError()
            # insert new rows from csv file to finish the update
            c.execute("INSERT INTO payrolls (employeeid, hour, date) VALUES (\"{0}\",\"{1}\",\"{2}\");".format(row[0], row[1], row[2]))    
        sql.commit()
        sql.close()
        # Save a backup of the file at /uploads
        f.close()
        return redirect('/')
    return render_template('upload_payroll.html')

# Define function to record up to 20 recently used TOTP code to prevent replay attack to redis datebase
def recordTOTP(otp):
    r = redis.Redis(host='localhost', port=6379, db=0)
    if r.llen('totp') < 20:
        r.lpush('totp', otp)
    else:
        r.rpop('totp')
        r.lpush('totp', otp)

# Define function to check if TOTP code exists in redis datebase to prevent replay attack
def checkTOTP(otp):
    r = redis.Redis(host='localhost', port=6379, db=0)
    if r.llen('totp') == 0:
        return False
    else:
        for i in range(r.llen('totp')):
            if r.lindex('totp', i) == otp:
                return True
        return False
    

# Define function to calculate payroll data from database (employment income, tax deducted, sin number, employee name, employee id, and assume all other T4 fields are empty) and return it as a dictionary
# Take the selected fiscal year and week number as parameters
def calculatePayroll(fiscal_year, week_number):
    # Connect to database
    sql = sqlite4.connect('../db/payroll.db', timeout=30)
    c = sql.cursor()
    # Get the start date and end date of the week
    start_date = datetime.datetime.strptime(fiscal_year + '-W' + week_number + '-1', "%Y-W%W-%w").strftime("%Y-%m-%d")
    end_date = datetime.datetime.strptime(fiscal_year + '-W' + week_number + '-0', "%Y-W%W-%w").strftime("%Y-%m-%d")
    print(start_date, end_date)
    # Get the employee id, name, sin number, wage, and employment income
    tmp = c.execute("SELECT employee.id, employee.name, employee.sin_num, employee.wage, SUM(payrolls.hour * employee.wage) FROM employee JOIN payrolls ON employee.id = payrolls.employeeid WHERE payrolls.date BETWEEN \"{0}\" AND \"{1}\" GROUP BY employee.id;".format(" "+start_date, " "+end_date))
    # if not found, return not found error
    employee_data = {}
    for row in tmp.fetchall():
        if row == None:
            return redirect('/notfound')
        employee_data[row[0]] = {"employee_id":row[0],"name": row[1], "sin_num": row[2], "wage": row[3], "employment_income": row[4], "employer_name": EMPLOYER_NAME}
    # Calculate tax deducted for each employee
    for employee_id in employee_data:
        employee_data[employee_id]["tax_deducted"] = employee_data[employee_id]["employment_income"] * TAX_RATE
    # Close database connection
    sql.close()
    # Return the employee data dictionary
    print(employee_data)
    return employee_data

# Define function to fill payroll data in T4 slip and download as pdf template provided by CRA
def generate_t4_pdf(employee_data, output_file):
    # Create pdf merger object
    merger = PdfFileMerger()

    
    for employee_id in employee_data:
        pdf = SimpleDocTemplate(f"./slips/tmp/{employee_id}.pdf", pagesize=letter)
        elements = []
        data = [['Employee Name', 'Employee ID', 'SIN Number', 'Employment Income', 'Tax Deducted','Employer Name']]
        data.append([employee_data[employee_id]["name"], employee_id, employee_data[employee_id]["sin_num"], employee_data[employee_id]["employment_income"], employee_data[employee_id]["tax_deducted"], employee_data[employee_id]["employer_name"]])
        table = Table(data)
        table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))
        # generate PDF 417 barcode
        code = encode(str(employee_data[employee_id]), columns=6, security_level=6)
        barcode = render_image(code, scale=2)
        barcode.save('barcodetmp.jpg')
        barcode.close()
        print(type(barcode))
        # Create a flowable object to add barcode to PDF
        
        barcode = Image("./barcodetmp.jpg")
        print(type(barcode))
        # Add the barcode image to the elements list
        elements.append(barcode)
        elements.append(PageBreak())
        pdf.build(elements)
    
    for employee_id in employee_data:
        merger.append(fileobj=open(f"./slips/tmp/{employee_id}.pdf", 'rb'))
    merger.write(fileobj=open(output_file, 'wb'))
    merger.close()
    for employee_id in employee_data:
        os.remove(f"./slips/tmp/{employee_id}.pdf")

    # Save slip to ./slips/{date}/{employee_id}-{employee_name}.pdf
    # Create a folder for each day
    if not os.path.exists(f"./slips/{time.strftime('%Y%m%d')}"):
        os.makedirs(f"./slips/{time.strftime('%Y%m%d')}")
        
    # Build the PDF document
    
    os.remove("./barcodetmp.jpg")

# Call generate_t4_pdf() function to generate T4 slip for each employees
def generateT4s(fiscal_year, week_number):
    payroll = calculatePayroll(fiscal_year, week_number)
    generate_t4_pdf(payroll, f"./slips/{time.strftime('%Y%m%d')}/{time.strftime('%H-%M-%S')}.pdf")


# Route to download CSV template
@login_required
@app.route('/downloadcsv')
def downloadcsv():
    return send_file('./csv/template.csv', as_attachment=True)

# Call generateT4s to generate all the slips of the selected fiscal year and week (web form), and Download T4 slips in a {date}.zip file
@login_required
@app.route('/download', methods=['GET', 'POST'])
def download():
    if request.method == 'POST':
        # Get the selected fiscal year and week number from the web form
        fiscal_year = request.form.get('fiscal_year')
        week_number = request.form.get('week_number')
        # Generate T4 slips
        generateT4s(fiscal_year, week_number)
        # Zip all the slips
        zipf = zipfile.ZipFile(f"./slips/{time.strftime('%Y%m%d')}.zip", 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(f"./slips/{time.strftime('%Y%m%d')}"):
            for file in files:
                zipf.write(os.path.join(root, file))
        zipf.close()
        # Return the zip file
        return send_file(f"./slips/{time.strftime('%Y%m%d')}.zip", as_attachment=True)
    return render_template('download.html')


# run app
if __name__ == '__main__':
    app.run(port=5000,host='127.0.0.1',debug=True)


