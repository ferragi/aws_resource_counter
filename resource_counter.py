import sys
import boto3
from botocore.exceptions import ClientError
import json

customer_file = open("customer_assessment_config.json")
customer_config = json.loads(customer_file.read())
customer_file.close()

def generate_account_list():

    if 'Customer_Organization_Acct' not in customer_config:
        sys.exit('\n[Fatal Err] Parameter Customer_Organization_Acct is mandatory in customer configuration.')

    account_list = []
    account_list.append(customer_config['Customer_Organization_Acct'])

    if 'Other_Customer_Acct_List' in customer_config:
        for i in range(0, len(customer_config['Other_Customer_Acct_List'])):
            account_list.append(customer_config['Other_Customer_Acct_List'][i]['Acct_Id'])

    return account_list

def switch_role(acct_id):

    client = boto3.client('sts')

    try:
        response = client.assume_role(
            RoleArn='arn:aws:iam::' + str(acct_id) + ':role/' + str(customer_config['Role_Name']),
            RoleSessionName=str(customer_config['Role_Name']) + '-Resource_Counter'
        )
    except ClientError:
        print('\n[Err] Could switch role on acct ' + str(acct_id) + ' for role name '+ str(customer_config['Role_Name']))
        return { 'AccessOK':False }

    return {
            'AccessOK': True,
            'access_key_id': response['Credentials']['AccessKeyId'],
            'secret_access_key': response['Credentials']['SecretAccessKey'],
            'session_token': response['Credentials']['SessionToken']
            }

def count_resources(service_data, **extra_params):

    if 'region' in extra_params:
        if 'access_key_id' in extra_params['access_data']:
            try:
                client = boto3.client(service_data["Boto3_Client"], region,
                                      aws_access_key_id=extra_params['access_data']['access_key_id'],
                                      aws_secret_access_key=extra_params['access_data']['secret_access_key'],
                                      aws_session_token=extra_params['access_data']['session_token']
                                      )
            except:
                print('\n[Err] Could not connect to client '+str(service_data["Boto3_Client"])+" in region "+str(region))
                return 0
        else:
            try:
                client = boto3.client(service_data["Boto3_Client"], region)
            except:
                print('\n[Err] Could not connect to client '+str(service_data["Boto3_Client"])+" in region "+str(region))
                return 0
    else:
        if 'access_key_id' in extra_params['access_data']:
            try:
                client = boto3.client(service_data["Boto3_Client"],
                                      aws_access_key_id=extra_params['access_data']['access_key_id'],
                                      aws_secret_access_key=extra_params['access_data']['secret_access_key'],
                                      aws_session_token=extra_params['access_data']['session_token']
                                      )
            except:
                print('\n[Err] Could not connect to client '+str(service_data["Boto3_Client"]))
                return 0
        else:
            try:
                client = boto3.client(service_data["Boto3_Client"])
            except:
                print('\n[Err] Could not connect to client '+str(service_data["Boto3_Client"]))
                return 0

    filtered_params = ''
    if 'Client_Prefilters' in service_data:
        ###########################
        ## TDL
        ## Fazer o loop para dois ou mais params
        ##(Precisa será? Ou melhor tirar a lista do json?)
        ###########################
        if service_data["Client_Prefilters"][0]["Filter_Type"] == 'String':
            filtered_params = str(service_data["Client_Prefilters"][0]["Filter_Name"])+" = '"+str(service_data["Client_Prefilters"][0]["Filter_Value"])+"'"
        elif service_data["Client_Prefilters"][0]["Filter_Type"] == 'List':
            filtered_params = str(service_data["Client_Prefilters"][0]["Filter_Name"])+" = ['"+str(service_data["Client_Prefilters"][0]["Filter_Value"])+"']"
        elif service_data["Client_Prefilters"][0]["Filter_Type"] == 'Integer':
            filtered_params = str(service_data["Client_Prefilters"][0]["Filter_Name"])+" = "+str(service_data["Client_Prefilters"][0]["Filter_Value"])
    if 'nexttoken' in extra_params:
        if filtered_params == '':
            filtered_params = 'NextToken=' + nexttoken
        else:
            filtered_params += ', NextToken=' + nexttoken
    try:
        response = eval("client."+service_data["Client_Function"]+"("+filtered_params+")")
    except:
        if 'region' in extra_params:
            print('\n[Err] Could not run function '+str("client."+service_data["Client_Function"]+"("+filtered_params+")")+' for client '+str(service_data["Boto3_Client"])+" in region "+str(region))
        else:
            print('\n[Err] Could not run function '+str("client."+service_data["Client_Function"]+"("+filtered_params+")")+' for client '+str(service_data["Boto3_Client"]))
        return 0

    try:
        if response[service_data["Counted_Resource_Key"]]:
            if 'NextToken' in response:
                if 'region' in extra_params:
                    return len(response[service_data["Counted_Resource_Key"]]) + count_resources(service_data, region=region, nexttoken=response['NextToken'])
                else:
                    return len(response[service_data["Counted_Resource_Key"]]) + count_resources(service_data, nexttoken=response['NextToken'])
            else:
                return len(response[service_data["Counted_Resource_Key"]])
        else:
            return 0
    except KeyError:
        if 'region' in extra_params:
            print('\n[Err] Could not find key '+service_data["Counted_Resource_Key"]+' for client '+str(service_data["Boto3_Client"])+" in region "+str(region))
        else:
            print('\n[Err] Could not find key '+service_data["Counted_Resource_Key"]+' for client '+str(service_data["Boto3_Client"]))
        return 0

    return 1

service_config_file = open("services_config.json")
service_config = json.loads(service_config_file.read())
service_config_file.close()

accts_to_run = generate_account_list()

for acct_run_id in accts_to_run:
    if acct_run_id != boto3.client('sts').get_caller_identity().get('Account'):
        temporary_access_data = switch_role(acct_run_id)
    else:
        temporary_access_data = { 'AccessOK': True }

    print('Checking resources on account ['+acct_run_id+'].', end='')

    if not temporary_access_data['AccessOK']:
        print(".[skipped]")
        continue

    i = 0
    for service in service_config["services"]:
        print('.', end='')

        if 'Count' not in service_config["services"][i]: service_config["services"][i]["Count"] = 0

        if service['Client_Endpoint_Scope'] == 'global':
            service_config["services"][i]["Count"] += count_resources(service, access_data=temporary_access_data)
        else:
            for region in customer_config['Assessment_Region_Coverage_List']:
                if 'Exception_Region_List' in service and region in service["Exception_Region_List"]:
                    continue
                service_config["services"][i]["Count"] += count_resources(service, access_data=temporary_access_data, region=region)
        i += 1

    print(".[ok]")

print(json.dumps(service_config, indent=4, sort_keys=True))
