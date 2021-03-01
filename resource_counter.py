import sys
import boto3
from botocore.exceptions import ClientError
import json

CUSTOMER_FILE_NAME = "customer_assessment.config.json"
SERVICES_FILE_NAME = "services.config.json"

def get_customer_config():
    customer_file = open(CUSTOMER_FILE_NAME)
    customer_config = json.loads(customer_file.read())
    customer_file.close()
    return customer_config

customer_config = get_customer_config()

def generate_account_list():

    if 'CUSTOMER_ORGANIZATION_ACCT' not in customer_config:
        sys.exit('\n[Fatal Err] Parameter CUSTOMER_ORGANIZATION_ACCT is mandatory in customer configuration.')

    account_list = []
    account_list.append(customer_config['CUSTOMER_ORGANIZATION_ACCT'])

    if 'OTHER_CUSTOMER_ACCT_LIST' in customer_config:
        for i in range(0, len(customer_config['OTHER_CUSTOMER_ACCT_LIST'])):
            account_list.append(customer_config['OTHER_CUSTOMER_ACCT_LIST'][i]['acct_id'])

    return account_list

def switch_role(acct_id):

    client = boto3.client('sts')

    try:
        response = client.assume_role(
            RoleArn='arn:aws:iam::' + str(acct_id) + ':role/' + str(customer_config['ROLE_NAME']),
            RoleSessionName=str(customer_config['ROLE_NAME']) + '-Resource_Counter'
        )
    except ClientError:
        print('\n[Err] Could switch role on acct ' + str(acct_id) + ' for role name '+ str(customer_config['ROLE_NAME']))
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
                client = boto3.client(service_data["BOTO3_CLIENT"], region,
                                      aws_access_key_id=extra_params['access_data']['access_key_id'],
                                      aws_secret_access_key=extra_params['access_data']['secret_access_key'],
                                      aws_session_token=extra_params['access_data']['session_token']
                                      )
            except:
                print('\n[Err] Could not connect to client '+str(service_data["BOTO3_CLIENT"])+" in region "+str(region))
                return 0
        else:
            try:
                client = boto3.client(service_data["BOTO3_CLIENT"], region)
            except:
                print('\n[Err] Could not connect to client '+str(service_data["BOTO3_CLIENT"])+" in region "+str(region))
                return 0
    else:
        if 'access_key_id' in extra_params['access_data']:
            try:
                client = boto3.client(service_data["BOTO3_CLIENT"],
                                      aws_access_key_id=extra_params['access_data']['access_key_id'],
                                      aws_secret_access_key=extra_params['access_data']['secret_access_key'],
                                      aws_session_token=extra_params['access_data']['session_token']
                                      )
            except:
                print('\n[Err] Could not connect to client '+str(service_data["BOTO3_CLIENT"]))
                return 0
        else:
            try:
                client = boto3.client(service_data["BOTO3_CLIENT"])
            except:
                print('\n[Err] Could not connect to client '+str(service_data["BOTO3_CLIENT"]))
                return 0

    filtered_params = ''
    if 'CLIENT_PREFILTERS' in service_data:
        ###########################
        ## TDL
        ## Fazer o loop para dois ou mais params
        ##(Precisa será? Ou melhor tirar a lista do json?)
        ###########################
        if service_data["CLIENT_PREFILTERS"][0]["filter_type"] == 'String':
            filtered_params = str(service_data["CLIENT_PREFILTERS"][0]["filter_name"])+" = '"+str(service_data["CLIENT_PREFILTERS"][0]["filter_value"])+"'"
        elif service_data["CLIENT_PREFILTERS"][0]["filter_type"] == 'List':
            filtered_params = str(service_data["CLIENT_PREFILTERS"][0]["filter_name"])+" = ['"+str(service_data["CLIENT_PREFILTERS"][0]["filter_value"])+"']"
        elif service_data["CLIENT_PREFILTERS"][0]["filter_type"] in ['Integer','Bool']:
            filtered_params = str(service_data["CLIENT_PREFILTERS"][0]["filter_name"])+" = "+str(service_data["CLIENT_PREFILTERS"][0]["filter_value"])
    if 'nexttoken' in extra_params:
        if filtered_params == '':
            filtered_params = 'NextToken=' + nexttoken
        else:
            filtered_params += ', NextToken=' + nexttoken
    try:
        response = eval("client."+service_data["CLIENT_FUNCTION"]+"("+filtered_params+")")
    except:
        if 'region' in extra_params:
            print('\n[Err] Could not run function '+str("client."+service_data["CLIENT_FUNCTION"]+"("+filtered_params+")")+' for client '+str(service_data["BOTO3_CLIENT"])+" in region "+str(region))
        else:
            print('\n[Err] Could not run function '+str("client."+service_data["CLIENT_FUNCTION"]+"("+filtered_params+")")+' for client '+str(service_data["BOTO3_CLIENT"]))
        return 0

    try:
        if response[service_data["COUNTED_RESOURCE_KEY"]]:
            if 'NextToken' in response:
                if 'region' in extra_params:
                    return len(response[service_data["COUNTED_RESOURCE_KEY"]]) + count_resources(service_data, region=region, nexttoken=response['NextToken'])
                else:
                    return len(response[service_data["COUNTED_RESOURCE_KEY"]]) + count_resources(service_data, nexttoken=response['NextToken'])
            else:
                return len(response[service_data["COUNTED_RESOURCE_KEY"]])
        else:
            return 0
    except KeyError:
        if 'region' in extra_params:
            print('\n[Err] Could not find key '+service_data["COUNTED_RESOURCE_KEY"]+' for client '+str(service_data["BOTO3_CLIENT"])+" in region "+str(region))
        else:
            print('\n[Err] Could not find key '+service_data["COUNTED_RESOURCE_KEY"]+' for client '+str(service_data["BOTO3_CLIENT"]))
        return 0

service_config_file = open(SERVICES_FILE_NAME)
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
    for service in service_config["SERVICES"]:
        print('.', end='')

        if 'Count' not in service_config["SERVICES"][i]: service_config["SERVICES"][i]["Count"] = 0

        if service['CLIENT_ENDPOINT_SCOPE'] == 'global':
            service_config["SERVICES"][i]["Count"] += count_resources(service, access_data=temporary_access_data)
        else:
            for region in customer_config['ASSESSMENT_REGION_COVERAGE_LIST']:
                if 'EXCEPTION_REGION_LIST' in service and region in service["EXCEPTION_REGION_LIST"]:
                    continue
                service_config["SERVICES"][i]["Count"] += count_resources(service, access_data=temporary_access_data, region=region)
        i += 1

    print(".[ok]")

print(json.dumps(service_config, indent=4, sort_keys=True))
