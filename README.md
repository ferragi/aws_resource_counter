# aws_resource_counter
Python/boto3 counter for AWS resources under one or multiple accounts.

### Using with CloudShell

1. Setup your CloudShell instance.
2. Clone the repository with: `git clone https://github.com/ferragi/aws_resource_counter`
3. Modify `customer_assessment.config.json` file with the correct credentials.
4. Run `./resource_counter.py`.

### Modifying customer_assessment.config.json

This file is a simple json file that contains the parameters to run the resource counter at, as in the example:

```json
{
  "CUSTOMER_NAME": "SomeName",
  "CUSTOMER_ORGANIZATION_ACCT": "012345678912",
  "OTHER_CUSTOMER_ACCT_LIST": [
    {"name": "SomeOtherAcct1", "acct_id": "012345678913"},
    {"name": "SomeOtherAcct2", "acct_id": "012345678914"},
    {"name": "SomeOtherAcct3", "acct_id": "012345678915"}
  ],
  "ROLE_NAME": "unlimited_jedi_power",
  "ASSESSMENT_REGION_COVERAGE_LIST": [
    "us-east-1",
    "us-east-2",
    "sa-east-1"
  ]
}
```

####Description:

**CUSTOMER_NAME: [REQUIRED]** Any describing the name of the customer that the assessment is run at.

**CUSTOMER_ORGANIZATION_ACCT: [REQUIRED]** 12-digit AWS Account ID of the main account that the resources will be counted.

**OTHER_CUSTOMER_ACCT_LIST:** List of other account to be run together, if none leave an empty list.

**ROLE_NAME:** Required only if you are running the counting in other accounts different than the origin account the script is running at. You need to associate an IAM Role to the script account, beeing the easyest associate `ReadOnlyAccess` from AWS Managed Policies.

**ASSESSMENT_REGION_COVERAGE_LIST: [REQUIRED]** Required at least one region specified for all regional resources to be counted. Global resources are unnafected by this parameter. 