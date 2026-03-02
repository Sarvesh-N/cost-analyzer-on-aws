import boto3
import datetime
import json
import os

ce = boto3.client('ce')
s3 = boto3.client('s3')

BUCKET_NAME = os.environ['BUCKET_NAME']


def get_cost(start, end):
    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': start.strftime('%Y-%m-%d'),
            'End': end.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        Filter={
            "Dimensions": {
                "Key": "RECORD_TYPE",
                "Values": ["Usage"]  # Matches UI filter: Charge type = Usage
            }
        }
    )

    total = 0
    daily_data = {}

    for day in response['ResultsByTime']:
        date = day['TimePeriod']['Start']
        amount = float(day['Total']['UnblendedCost']['Amount'])
        daily_data[date] = amount
        total += amount

    return total, daily_data


def lambda_handler(event, context):

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Last 7 Days
    start_7_days = today - datetime.timedelta(days=7)
    total_7_days, daily_7_data = get_cost(start_7_days, today)

    # Month-to-Date
    start_month = today.replace(day=1)
    total_mtd, daily_mtd_data = get_cost(start_month, today)

    # Yesterday's Cost (latest finalized data)
    today_cost = daily_7_data.get(yesterday.strftime('%Y-%m-%d'), 0)

    # Clean negative rounding
    today_cost = max(today_cost, 0)
    total_7_days = max(total_7_days, 0)
    total_mtd = max(total_mtd, 0)

    report = {
        "today_cost": f"{today_cost:.2f}",
        "last_7_days_total": f"{total_7_days:.2f}",
        "month_to_date_total": f"{total_mtd:.2f}",
        "generated_on": str(today)
    }

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="daily-report.json",
        Body=json.dumps(report),
        ContentType='application/json'
    )

    return {
        "statusCode": 200,
        "body": "AWS cost dashboard updated successfully"
    }
