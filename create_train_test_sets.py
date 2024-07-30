import pandas as pd
from sklearn.model_selection import train_test_split
import scipy.stats as stats
import numpy as np
import os



dataset = pd.read_csv('WA_Fn-UseC_-Telco-Customer-Churn.csv')
pd.set_option('max_colwidth', 200)

train_data, test_data = train_test_split(dataset, test_size=0.20, random_state=42)
train_data = train_data.reset_index(drop=True)
test_data = test_data.reset_index(drop=True)
# 1. User Demographics
user_demographics_train = train_data[['customerID', 'gender', 'SeniorCitizen', 'Partner', 'Dependents']]

# 2. User Services
user_services_train = train_data[['customerID', 'PhoneService', 'MultipleLines', 'InternetService',
                                  'OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport',
                                  'StreamingTV', 'StreamingMovies']]

# 3. User Payments
user_payments_train = train_data[
    ['customerID', 'Contract', 'PaperlessBilling', 'PaymentMethod', 'MonthlyCharges', 'TotalCharges']]

# 4. User Churn
user_churn_train = train_data[['customerID', 'Churn']]
# 1. User Demographics
user_demographics_test = test_data[['customerID', 'gender', 'SeniorCitizen', 'Partner', 'Dependents']]

# 2. User Services
user_services_test = test_data[['customerID', 'PhoneService', 'MultipleLines', 'InternetService',
                                'OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport',
                                'StreamingTV', 'StreamingMovies']]

# 3. User Payments
user_payments_test = test_data[
    ['customerID', 'Contract', 'PaperlessBilling', 'PaymentMethod', 'MonthlyCharges', 'TotalCharges']]

# 4. User Churn
user_churn_test = test_data[['customerID', 'Churn']]

# Random seed for reproducibility
np.random.seed(42)

# 1. Remove some rows from user_demographics
drop_indices = np.random.choice(user_demographics_train.index, size=int(0.05 * len(user_demographics_train)),
                                replace=False)
user_demographics_train = user_demographics_train.drop(drop_indices)

# 2. Add some new customer IDs to user_services
new_ids = ["NEW" + str(i) for i in range(100)]
new_data_train = pd.DataFrame({'customerID': new_ids})
user_services_train = pd.concat([user_services_train, new_data_train], ignore_index=True)

# 3. Add missing values to user_payments
for _ in range(100):
    row_idx = np.random.randint(user_payments_train.shape[0])
    col_idx = np.random.randint(1, user_payments_train.shape[1])  # skipping customerID column
    user_payments_train.iat[row_idx, col_idx] = np.nan

# 4. Add new customer IDs to user_churn
new_ids_churn_train = ["NEWCHURN" + str(i) for i in range(50)]
new_data_churn_train = pd.DataFrame({'customerID': new_ids_churn_train, 'Churn': ['Yes'] * 25 + ['No'] * 25})
user_churn_train = pd.concat([user_churn_train, new_data_churn_train], ignore_index=True)


print(user_churn_test.info())

if not os.path.exists('telco_data'):
    os.makedirs('telco_data')

# DataFrame to CSV
# user_demographics_train.to_csv('telco_data/user_demographics_train.csv', index=False)
# user_services_train.to_csv('telco_data/user_services_train.csv', index=False)
# user_payments_train.to_csv('telco_data/user_payments_train.csv', index=False)
# user_churn_train.to_csv('telco_data/user_churn_train.csv', index=False)
#
# user_demographics_test.to_csv('telco_data/user_demographics_test.csv', index=False)
# user_services_test.to_csv('telco_data/user_services_test.csv', index=False)
# user_payments_test.to_csv('telco_data/user_payments_test.csv', index=False)
# user_churn_test.to_csv('telco_data/user_churn_test.csv', index=False)

if __name__ == '__main__':
    print("this file transfers the Telco-Customer cvs file into eight tables and saves them in the 'telco_data' folder")


