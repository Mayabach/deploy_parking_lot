import json
import boto3
import time

dynamodb = boto3.resource('dynamodb')
table_name = "parking_tickets"
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    try:
        http_method = event['requestContext']['http']['method']
    except:
        return {
            "statusCode": 400,
            "body": json.dumps({'Error': 'HTTP method not specified'})
        }
    if http_method == 'POST':
        if event['rawPath'] == '/entry':
            return handle_entry_request(event)
        elif event['rawPath'] == '/exit':
            return handle_exit_request(event)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'Error': 'Path not found'})
            }
    else:
        return {
            'statusCode': 405,
            'body': json.dumps({'Error': 'Method not allowed'})
        }


def handle_entry_request(event):
    try:
        plate = event['queryStringParameters'].get('plate')
        parking_lot = event['queryStringParameters'].get('parkingLot')
    except:
        return {
            'statusCode': 400,
            'body': json.dumps({'Error': 'Invalid Request, plate and parkingLot are required'})
        }
    # Generate a unique ticket id
    ticket_id = str(int(time.time()))

    # Save the ticket information to DynamoDB
    ticket_data = {
        'ticket_id': ticket_id,
        'plate': plate,
        'parking_lot': parking_lot,
        'entry_time': int(time.time())
    }
    table.put_item(Item=ticket_data)

    # Return the ticket id as the response
    return {
        'statusCode': 200,
        'body': json.dumps({'ticket_id': ticket_id})
    }


def handle_exit_request(event):
    try:
        ticket_id = event['queryStringParameters'].get('ticketId')
    except:
        return {
            'statusCode': 400,
            'body': json.dumps({'Error': 'Invalid Request, ticketId is required'})
        }
    # Retrieve the ticket data from DynamoDB
    ticket_data = table.get_item(Key={'ticket_id': ticket_id}).get('Item')
    if not ticket_data:
        return {
            'statusCode': 404,
            'body': json.dumps({'Error': 'Ticket not found'})
        }
    if "exit_time" in ticket_data and ticket_data['exit_time']:
        return {
            'statusCode': 400,
            'body': json.dumps({'Error': 'Invalid Request, Ticket has already been paid'})
        }

    # Calculate the total parked time and the charge
    entry_time = ticket_data['entry_time']
    exit_time = int(time.time())
    parked_time = exit_time - entry_time
    parked_minutes = parked_time // 60
    charge = (parked_minutes // 15) * 10 / 4

    # Update the ticket data with exit time and charge
    ticket_data.update({
        'exit_time': exit_time,
        'parked_minutes': parked_minutes,
        'charge': charge
    })
    table.put_item(Item=ticket_data)

    # Return the ticket information as the response
    return {
        'statusCode': 200,
        'body': json.dumps({
            'plate': ticket_data['plate'],
            'parked_minutes': f'{parked_minutes} minutes',
            'parking_lot': ticket_data['parking_lot'],
            'charge': f'${charge}'
        })
    }
