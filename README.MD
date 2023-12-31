# EZ Payroll - A Payroll Management Web Application
By Andy Boyu Chen

## Video Demo
URL: https://youtu.be/oEgEdkJFs8U

## Description
This is a payroll management application named EZ Payroll. It provides a solution to small businesses to fulfill their financial management need.

## Features

### Security
1. Implemented Redis database to store the 20 recently used TOTP codes to prevent replay attack.
2. Enforced 2FA for all management users (TOTP setup after registration) // TODO: Implement FIDO2/Webauthn to support hardware security key for better security.
3. Store hashed user password in database and verify hash value to authenticate (not plain text).
4. Save a second copy of the file uploaded and the database data before changes.
5. Seession expires in 10 minutes after login.

### Productivity
1. Importing and updating employee data from a CSV file from the user
2. Exporting payrolls into personal payroll slips with PDF417 code as a convienience feature.
3. Viewing all the payrolls directly in the last 120 days in the dash board directly.

## Get Started

### Requirements

```
sudo apt install redis
sudo apt install python-3.11.4
sudo apt install sqlite3
pip install -r modules.txt
```

### Run
After change your working directory into .../EZ Payroll/app

You can run:
```
flask run
```

The website will run by default at: ``localhost:5000``

### Default Management Account
```
Username: test
Password: 123456
TOTP Key: 3LUX6RLFO2JLOIPP4K3TRAVFRBUEJUDX
TOTP Algorithm: SHA 1
Digits: 6
Refresh Period: 30s
```
*Warning: If going to use in production, it is recommended to create new management account and remove the current one from the database before deploying.*

# Copyright Disclosure and License Detail
## EZ Payroll is under MIT-FPA License
FPA License
Copyright 2023 Boyu Chen
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without limitation in the rights to use, copy, modify, merge, publish, and/ or distribute copies of the Software in an educational or personal context, subject to the following conditions: 

- The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

Permission is granted to sell and/ or distribute copies of the Software in a commercial context, subject to the following conditions:

- Substantial changes: adding, removing, or modifying large parts, shall be developed in the Software. Reorganizing logic in the software does not warrant a substantial change. 

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## The HTML template is under MIT license
MIT License
Copyright (c) 2020 Estevan Maito

Source:
https://themewagon.com/themes/free-tailwind-css-admin-dashboard-template-windmill/

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
