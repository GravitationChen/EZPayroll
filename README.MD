# EZ Payroll - A Payroll Management Web Application
By Andy Boyu Chen

## Video Demo

## Description
This is a payroll management application named EZ Payroll. It provides a solution to small businesses to fulfill their financial management need.

## Features

### Security
1. Implemented Redis database to store the 20 recently used TOTP codes to prevent replay attack
2. Enforced 2FA for all management users (TOTP setup after registration) // TODO: Implement FIDO2/Webauthn to support hardware security key for better security
3. Store hashed user password in database and verify hash value to authenticate (not plain text)
4. TODO: Enforce HTTPS (Let's Encrypt Cert?)
5. TODO: Use nginx to reverse proxy flask server

### Productivity
1. Importing and updating employee data from a CSV file from the user
2. Exporting employee data into a CSV file
3. Exporting payrolls into personal T4 slips by a template file (User comstomizable).
4.  

# Copyright Disclosure
## The HTML template is under MIT license

